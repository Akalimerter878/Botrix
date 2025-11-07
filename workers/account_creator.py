"""Account creation worker for Kick.com"""

import asyncio
import aiohttp
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
from .utils import get_logger
from .kasada_solver import KasadaSolver, KasadaSolverError
from .email_handler import EmailVerifier, HotmailPool, EmailVerificationError
from .config import Config

logger = get_logger(__name__)


class AccountCreationError(Exception):
    """Base exception for account creation errors"""
    pass


class VerificationFailedError(AccountCreationError):
    """Raised when email verification fails"""
    pass


class RegistrationFailedError(AccountCreationError):
    """Raised when account registration fails"""
    pass


def generate_random_username(length: int = 10) -> str:
    """
    Generate a random username for Kick.com
    
    Args:
        length: Length of username (default: 10)
        
    Returns:
        Random username string
    """
    # Kick usernames: letters, numbers, underscores
    chars = string.ascii_letters + string.digits + '_'
    # Start with a letter
    username = random.choice(string.ascii_letters)
    # Add random characters
    username += ''.join(random.choices(chars, k=length - 1))
    
    logger.debug(f"Generated username: {username}")
    return username


def generate_random_password(length: int = 16) -> str:
    """
    Generate a secure random password
    
    Args:
        length: Length of password (default: 16)
        
    Returns:
        Random password string
    """
    # Mix of uppercase, lowercase, digits, and special characters
    chars = string.ascii_letters + string.digits + '!@#$%^&*'
    password = ''.join(random.choices(chars, k=length))
    
    logger.debug(f"Generated password with length: {length}")
    return password


def generate_random_birthdate() -> str:
    """
    Generate a random birthdate for account (18-35 years old)
    
    Returns:
        Birthdate in YYYY-MM-DD format
    """
    # Random age between 18 and 35
    age = random.randint(18, 35)
    
    # Calculate birthdate
    today = datetime.now()
    birth_year = today.year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)  # Safe for all months
    
    birthdate = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
    logger.debug(f"Generated birthdate: {birthdate} (age: {age})")
    
    return birthdate


class KickAccountCreator:
    """
    Main account creation orchestrator for Kick.com
    
    Coordinates:
    - Email pool management
    - Kasada challenge solving
    - Email verification
    - Account registration
    """

    # Kick.com API endpoints
    KICK_API_BASE = "https://kick.com/api"
    SEND_CODE_ENDPOINT = f"{KICK_API_BASE}/v1/signup/send/email"
    VERIFY_CODE_ENDPOINT = f"{KICK_API_BASE}/v1/signup/verify/email"
    REGISTER_ENDPOINT = f"{KICK_API_BASE}/v1/signup/register"
    
    # Rate limiting
    REQUEST_DELAY = 2.0  # Seconds between requests
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5.0

    def __init__(
        self,
        email_pool: HotmailPool,
        kasada_solver: KasadaSolver,
        config: Optional[Config] = None,
        output_file: str = "shared/kicks.json"
    ):
        """
        Initialize KickAccountCreator
        
        Args:
            email_pool: HotmailPool instance for email management
            kasada_solver: KasadaSolver instance for bypassing protection
            config: Optional Config instance
            output_file: Path to save successful accounts
        """
        self.email_pool = email_pool
        self.kasada_solver = kasada_solver
        self.config = config or Config()
        self.output_file = Path(output_file)
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info("KickAccountCreator initialized")
        logger.info(f"Output file: {self.output_file}")

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.debug("Created new aiohttp session")

    async def _make_request(
        self,
        method: str,
        url: str,
        kasada_headers: Dict,
        json_data: Optional[Dict] = None,
        retry: bool = True
    ) -> Tuple[int, Dict]:
        """
        Make HTTP request with Kasada headers
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            kasada_headers: Headers from KasadaSolver
            json_data: JSON payload
            retry: Whether to retry on failure
            
        Returns:
            Tuple of (status_code, response_json)
        """
        await self._ensure_session()
        
        # Merge headers
        headers = {
            **kasada_headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://kick.com",
            "Referer": "https://kick.com/"
        }
        
        attempts = self.RETRY_ATTEMPTS if retry else 1
        
        for attempt in range(1, attempts + 1):
            try:
                logger.debug(f"Request attempt {attempt}/{attempts}: {method} {url}")
                
                async with self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    status = response.status
                    
                    try:
                        data = await response.json()
                    except:
                        data = {"error": await response.text()}
                    
                    logger.debug(f"Response status: {status}")
                    
                    if status == 200:
                        return status, data
                    elif status < 500:
                        # Client error, don't retry
                        logger.warning(f"Client error {status}: {data}")
                        return status, data
                    else:
                        # Server error, retry if enabled
                        logger.warning(f"Server error {status}, attempt {attempt}/{attempts}")
                        if attempt < attempts:
                            await asyncio.sleep(self.RETRY_DELAY)
                            continue
                        return status, data
            
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout, attempt {attempt}/{attempts}")
                if attempt < attempts:
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                raise
            
            except Exception as e:
                logger.error(f"Request error: {e}")
                if attempt < attempts:
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                raise
        
        raise AccountCreationError("Max retry attempts reached")

    async def _send_verification_email(
        self,
        email: str,
        kasada_headers: Dict
    ) -> bool:
        """
        Send verification code to email
        
        Args:
            email: Email address
            kasada_headers: Kasada headers
            
        Returns:
            True if successful
        """
        logger.info(f"📧 Sending verification code to {email}")
        
        payload = {
            "email": email,
            "agreed_to_terms": True
        }
        
        status, data = await self._make_request(
            "POST",
            self.SEND_CODE_ENDPOINT,
            kasada_headers,
            json_data=payload
        )
        
        if status == 200:
            logger.info(f"✅ Verification email sent to {email}")
            return True
        else:
            logger.error(f"❌ Failed to send verification email: {data}")
            return False

    async def _verify_email_code(
        self,
        email: str,
        code: str,
        kasada_headers: Dict
    ) -> Optional[str]:
        """
        Verify email code with Kick.com
        
        Args:
            email: Email address
            code: Verification code
            kasada_headers: Kasada headers
            
        Returns:
            Verification token or None if failed
        """
        logger.info(f"🔐 Verifying code {code} for {email}")
        
        payload = {
            "email": email,
            "code": code
        }
        
        status, data = await self._make_request(
            "POST",
            self.VERIFY_CODE_ENDPOINT,
            kasada_headers,
            json_data=payload
        )
        
        if status == 200 and "token" in data:
            token = data["token"]
            logger.info(f"✅ Email verified, token received")
            return token
        else:
            logger.error(f"❌ Failed to verify email: {data}")
            return None

    async def _register_account(
        self,
        email: str,
        username: str,
        password: str,
        birthdate: str,
        verification_token: str,
        kasada_headers: Dict
    ) -> Optional[Dict]:
        """
        Complete account registration
        
        Args:
            email: Email address
            username: Username
            password: Password
            birthdate: Birthdate (YYYY-MM-DD)
            verification_token: Token from email verification
            kasada_headers: Kasada headers
            
        Returns:
            Account data or None if failed
        """
        logger.info(f"📝 Registering account: {username}")
        
        payload = {
            "email": email,
            "username": username,
            "password": password,
            "password_confirmation": password,
            "birthdate": birthdate,
            "agreed_to_terms": True,
            "verification_token": verification_token
        }
        
        status, data = await self._make_request(
            "POST",
            self.REGISTER_ENDPOINT,
            kasada_headers,
            json_data=payload
        )
        
        if status == 200 or status == 201:
            logger.info(f"✅ Account registered: {username}")
            return data
        else:
            logger.error(f"❌ Failed to register account: {data}")
            return None

    def _save_account(self, account_data: Dict):
        """
        Save account to kicks.json
        
        Args:
            account_data: Account information to save
        """
        logger.info(f"💾 Saving account: {account_data.get('username')}")
        
        try:
            # Ensure directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing accounts
            accounts = []
            if self.output_file.exists():
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    accounts = json.load(f)
            
            # Add new account
            accounts.append({
                **account_data,
                "created_at": datetime.now().isoformat()
            })
            
            # Save back to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(accounts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Account saved to {self.output_file}")
            logger.info(f"   Total accounts: {len(accounts)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save account: {e}")

    async def create_account(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        birthdate: Optional[str] = None
    ) -> Dict:
        """
        Create a complete Kick.com account
        
        Args:
            username: Username (generated if None)
            password: Password (generated if None)
            birthdate: Birthdate (generated if None)
            
        Returns:
            Dict with account creation result
        """
        logger.info("=" * 60)
        logger.info("🚀 Starting Kick.com account creation")
        logger.info("=" * 60)
        
        email = None
        email_password = None
        
        try:
            # Generate random data if not provided
            username = username or generate_random_username()
            password = password or generate_random_password()
            birthdate = birthdate or generate_random_birthdate()
            
            logger.info(f"Username: {username}")
            logger.info(f"Birthdate: {birthdate}")
            
            # Step 1: Get email from pool
            logger.info("\n📊 Step 1/6: Getting email from pool...")
            email, email_password = self.email_pool.get_next_email()
            logger.info(f"✅ Using email: {email}")
            
            # Step 2: Solve Kasada challenge
            logger.info("\n🔓 Step 2/6: Solving Kasada challenge...")
            kasada_headers = await self.kasada_solver.solve(
                method="POST",
                fetch_url=self.SEND_CODE_ENDPOINT
            )
            logger.info("✅ Kasada headers obtained")
            
            # Rate limiting
            await asyncio.sleep(self.REQUEST_DELAY)
            
            # Step 3: Send verification email
            logger.info("\n📧 Step 3/6: Requesting verification email...")
            email_sent = await self._send_verification_email(email, kasada_headers)
            
            if not email_sent:
                raise VerificationFailedError("Failed to send verification email")
            
            # Rate limiting
            await asyncio.sleep(self.REQUEST_DELAY)
            
            # Step 4: Get verification code from email
            logger.info("\n📬 Step 4/6: Waiting for verification code...")
            async with EmailVerifier(
                email_address=email,
                password=email_password,
                imap_server=self.config.IMAP_SERVER,
                imap_port=self.config.IMAP_PORT
            ) as verifier:
                verification_code = await verifier.get_verification_code(
                    timeout=90,
                    poll_interval=5
                )
            
            logger.info(f"✅ Verification code received: {verification_code}")
            
            # Rate limiting
            await asyncio.sleep(self.REQUEST_DELAY)
            
            # Step 5: Verify the code
            logger.info("\n🔐 Step 5/6: Verifying code with Kick.com...")
            verification_token = await self._verify_email_code(
                email,
                verification_code,
                kasada_headers
            )
            
            if not verification_token:
                raise VerificationFailedError("Failed to verify email code")
            
            # Rate limiting
            await asyncio.sleep(self.REQUEST_DELAY)
            
            # Step 6: Register the account
            logger.info("\n📝 Step 6/6: Registering account...")
            account_data = await self._register_account(
                email=email,
                username=username,
                password=password,
                birthdate=birthdate,
                verification_token=verification_token,
                kasada_headers=kasada_headers
            )
            
            if not account_data:
                raise RegistrationFailedError("Failed to register account")
            
            # Mark email as used
            self.email_pool.mark_as_used(email)
            logger.info(f"✅ Email {email} marked as used")
            
            # Prepare result
            result = {
                "success": True,
                "email": email,
                "username": username,
                "password": password,
                "birthdate": birthdate,
                "verification_code": verification_code,
                "account_data": account_data
            }
            
            # Save account
            self._save_account(result)
            
            # Success!
            logger.info("\n" + "=" * 60)
            logger.info("🎉 ACCOUNT CREATED SUCCESSFULLY!")
            logger.info("=" * 60)
            logger.info(f"Email: {email}")
            logger.info(f"Username: {username}")
            logger.info(f"Password: {password}")
            logger.info("=" * 60)
            
            return result
            
        except EmailVerificationError as e:
            logger.error(f"❌ Email verification error: {e}")
            if email:
                self.email_pool.mark_as_failed(email)
            return {
                "success": False,
                "error": "Email verification failed",
                "message": str(e),
                "email": email
            }
        
        except KasadaSolverError as e:
            logger.error(f"❌ Kasada solver error: {e}")
            if email:
                self.email_pool.mark_as_failed(email)
            return {
                "success": False,
                "error": "Kasada challenge failed",
                "message": str(e),
                "email": email
            }
        
        except VerificationFailedError as e:
            logger.error(f"❌ Verification failed: {e}")
            if email:
                self.email_pool.mark_as_failed(email)
            return {
                "success": False,
                "error": "Verification failed",
                "message": str(e),
                "email": email
            }
        
        except RegistrationFailedError as e:
            logger.error(f"❌ Registration failed: {e}")
            if email:
                self.email_pool.mark_as_used(email)  # Email was verified but registration failed
            return {
                "success": False,
                "error": "Registration failed",
                "message": str(e),
                "email": email
            }
        
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            if email:
                self.email_pool.mark_as_failed(email)
            return {
                "success": False,
                "error": "Unexpected error",
                "message": str(e),
                "email": email
            }

    async def close(self):
        """Close the HTTP session and cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("KickAccountCreator session closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
