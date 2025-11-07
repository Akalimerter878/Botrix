"""Email handling for account verification"""

import asyncio
import imaplib
import email
import re
import time
from pathlib import Path
from typing import Optional, List, Tuple, Set
from email.header import decode_header
from .utils import get_logger
from .config import Config

logger = get_logger(__name__)


class EmailVerificationError(Exception):
    """Base exception for email verification errors"""
    pass


class IMAPLoginError(EmailVerificationError):
    """Raised when IMAP login fails"""
    pass


class NoEmailReceivedError(EmailVerificationError):
    """Raised when no verification email is received within timeout"""
    pass


class EmailPoolEmptyError(EmailVerificationError):
    """Raised when email pool is empty"""
    pass


class MalformedEmailFormatError(EmailVerificationError):
    """Raised when email format in file is invalid"""
    pass


class EmailVerifier:
    """
    Handles email verification for Kick.com accounts using IMAP protocol
    
    Features:
    - Polls IMAP server for verification emails
    - Extracts verification codes using regex
    - Configurable timeout and poll interval
    - Comprehensive error handling
    """

    KICK_EMAIL_SENDER = "noreply@email.kick.com"
    # Regex patterns for verification codes (4-8 digits)
    CODE_PATTERNS = [
        r'\b(\d{4,8})\b',  # Generic 4-8 digit code
        r'code[:\s]+(\d{4,8})',  # "code: 123456" or "code 123456"
        r'verification[:\s]+(\d{4,8})',  # "verification: 123456"
        r'confirm[:\s]+(\d{4,8})',  # "confirm: 123456"
        r'your code is[:\s]+(\d{4,8})',  # "your code is: 123456"
    ]

    def __init__(
        self,
        email_address: str,
        password: str,
        imap_server: str = "imap.zmailservice.com",
        imap_port: int = 993
    ):
        """
        Initialize EmailVerifier
        
        Args:
            email_address: Email address to check
            password: Email password
            imap_server: IMAP server address
            imap_port: IMAP server port
        """
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.imap_connection: Optional[imaplib.IMAP4_SSL] = None
        
        logger.info(f"EmailVerifier initialized for {email_address}")

    def connect(self):
        """
        Connect to IMAP server
        
        Raises:
            IMAPLoginError: If connection or login fails
        """
        try:
            logger.info(f"Connecting to IMAP server {self.imap_server}:{self.imap_port}")
            
            self.imap_connection = imaplib.IMAP4_SSL(
                self.imap_server,
                self.imap_port
            )
            
            logger.debug(f"Attempting login for {self.email_address}")
            self.imap_connection.login(self.email_address, self.password)
            
            logger.info(f"✅ Successfully connected to IMAP server for {self.email_address}")
            
        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP login failed for {self.email_address}: {e}"
            logger.error(error_msg)
            raise IMAPLoginError(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to connect to IMAP server: {e}"
            logger.error(error_msg)
            raise IMAPLoginError(error_msg)

    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.imap_connection:
            try:
                self.imap_connection.logout()
                logger.info(f"Disconnected from IMAP server for {self.email_address}")
            except Exception as e:
                logger.warning(f"Error disconnecting from IMAP: {e}")
            finally:
                self.imap_connection = None

    def _decode_header(self, header_value: str) -> str:
        """
        Decode email header
        
        Args:
            header_value: Raw header value
            
        Returns:
            Decoded header string
        """
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            result = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    result += str(part)
            
            return result
        except Exception as e:
            logger.warning(f"Failed to decode header: {e}")
            return str(header_value)

    def _extract_code_from_text(self, text: str) -> Optional[str]:
        """
        Extract verification code from text using regex patterns
        
        Args:
            text: Text to search for verification code
            
        Returns:
            Verification code or None if not found
        """
        if not text:
            return None
        
        # Try each pattern
        for pattern in self.CODE_PATTERNS:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches:
                code = matches.group(1)
                logger.debug(f"Found code '{code}' using pattern: {pattern}")
                return code
        
        return None

    def _get_email_body(self, msg: email.message.Message) -> str:
        """
        Extract email body from message
        
        Args:
            msg: Email message object
            
        Returns:
            Email body as string
        """
        body = ""
        
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    
                    if content_type == "text/plain" or content_type == "text/html":
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or 'utf-8'
                                body += payload.decode(charset, errors='ignore')
                        except Exception as e:
                            logger.warning(f"Failed to decode part: {e}")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='ignore')
        
        except Exception as e:
            logger.error(f"Error extracting email body: {e}")
        
        return body

    def _search_verification_email(self) -> Optional[str]:
        """
        Search inbox for verification email and extract code
        
        Returns:
            Verification code or None if not found
        """
        try:
            # Select inbox
            self.imap_connection.select('INBOX')
            
            # Search for emails from Kick
            search_criteria = f'(FROM "{self.KICK_EMAIL_SENDER}")'
            logger.debug(f"Searching with criteria: {search_criteria}")
            
            status, messages = self.imap_connection.search(None, search_criteria)
            
            if status != 'OK':
                logger.warning("Failed to search inbox")
                return None
            
            email_ids = messages[0].split()
            
            if not email_ids:
                logger.debug("No emails found from Kick")
                return None
            
            logger.info(f"Found {len(email_ids)} email(s) from {self.KICK_EMAIL_SENDER}")
            
            # Check most recent email first
            for email_id in reversed(email_ids):
                try:
                    status, msg_data = self.imap_connection.fetch(email_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Get subject
                    subject = self._decode_header(msg.get('Subject', ''))
                    logger.debug(f"Checking email - Subject: {subject}")
                    
                    # Try to extract code from subject first
                    code = self._extract_code_from_text(subject)
                    if code:
                        logger.info(f"✅ Found verification code in subject: {code}")
                        return code
                    
                    # Try to extract from body
                    body = self._get_email_body(msg)
                    code = self._extract_code_from_text(body)
                    if code:
                        logger.info(f"✅ Found verification code in body: {code}")
                        return code
                    
                    logger.debug("No code found in this email")
                
                except Exception as e:
                    logger.warning(f"Error processing email {email_id}: {e}")
                    continue
            
            logger.debug("No verification code found in any email")
            return None
        
        except Exception as e:
            logger.error(f"Error searching for verification email: {e}")
            return None

    async def get_verification_code(
        self,
        timeout: int = 90,
        poll_interval: int = 5
    ) -> str:
        """
        Wait for and extract verification code from email
        
        Args:
            timeout: Maximum time to wait for email (seconds)
            poll_interval: Time between polls (seconds)
            
        Returns:
            Verification code
            
        Raises:
            IMAPLoginError: If IMAP connection fails
            NoEmailReceivedError: If no email received within timeout
        """
        logger.info(f"Waiting for verification email (timeout: {timeout}s, poll: {poll_interval}s)")
        
        # Connect if not already connected
        if not self.imap_connection:
            self.connect()
        
        start_time = time.time()
        attempts = 0
        
        while True:
            attempts += 1
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                error_msg = f"No verification email received within {timeout}s after {attempts} attempts"
                logger.error(error_msg)
                raise NoEmailReceivedError(error_msg)
            
            logger.debug(f"Attempt {attempts} - Elapsed: {elapsed:.1f}s")
            
            # Search for verification email
            code = await asyncio.get_event_loop().run_in_executor(
                None,
                self._search_verification_email
            )
            
            if code:
                logger.info(f"🎉 Verification code retrieved: {code}")
                return code
            
            # Wait before next poll
            remaining = timeout - elapsed
            wait_time = min(poll_interval, remaining)
            
            if wait_time > 0:
                logger.debug(f"Waiting {wait_time}s before next check...")
                await asyncio.sleep(wait_time)

    async def __aenter__(self):
        """Async context manager entry"""
        self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.disconnect()


class HotmailPool:
    """
    Manages a pool of Hotmail/email accounts for verification
    
    Email format in livelive.txt:
    email@example.com:password
    another@example.com:password123
    """

    def __init__(self, pool_file: str = "shared/livelive.txt"):
        """
        Initialize HotmailPool
        
        Args:
            pool_file: Path to file containing email:password pairs
        """
        self.pool_file = Path(pool_file)
        self.available_emails: List[Tuple[str, str]] = []
        self.used_emails: Set[str] = set()
        self.failed_emails: Set[str] = set()
        
        logger.info(f"HotmailPool initialized with file: {pool_file}")
        self._load_emails()

    def _load_emails(self):
        """
        Load emails from file
        
        Raises:
            MalformedEmailFormatError: If email format is invalid
            FileNotFoundError: If pool file doesn't exist
        """
        if not self.pool_file.exists():
            logger.warning(f"Pool file not found: {self.pool_file}")
            logger.info("Creating empty pool file")
            self.pool_file.parent.mkdir(parents=True, exist_ok=True)
            self.pool_file.touch()
            return
        
        logger.info(f"Loading emails from {self.pool_file}")
        
        try:
            with open(self.pool_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            loaded_count = 0
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse email:password format
                if ':' not in line:
                    error_msg = f"Invalid format at line {line_num}: '{line}' (expected email:password)"
                    logger.error(error_msg)
                    raise MalformedEmailFormatError(error_msg)
                
                parts = line.split(':', 1)
                if len(parts) != 2:
                    error_msg = f"Invalid format at line {line_num}: '{line}'"
                    logger.error(error_msg)
                    raise MalformedEmailFormatError(error_msg)
                
                email_address = parts[0].strip()
                password = parts[1].strip()
                
                # Basic email validation
                if '@' not in email_address or '.' not in email_address:
                    error_msg = f"Invalid email at line {line_num}: '{email_address}'"
                    logger.warning(error_msg)
                    continue
                
                # Skip already used or failed emails
                if email_address in self.used_emails or email_address in self.failed_emails:
                    logger.debug(f"Skipping already used/failed email: {email_address}")
                    continue
                
                self.available_emails.append((email_address, password))
                loaded_count += 1
            
            logger.info(f"✅ Loaded {loaded_count} available email(s) from pool")
            logger.info(f"   Used: {len(self.used_emails)}, Failed: {len(self.failed_emails)}")
        
        except MalformedEmailFormatError:
            raise
        
        except Exception as e:
            error_msg = f"Error loading email pool: {e}"
            logger.error(error_msg)
            raise EmailVerificationError(error_msg)

    def get_next_email(self) -> Tuple[str, str]:
        """
        Get next available email from pool
        
        Returns:
            Tuple of (email_address, password)
            
        Raises:
            EmailPoolEmptyError: If no emails available
        """
        if not self.available_emails:
            error_msg = "Email pool is empty - no available emails"
            logger.error(error_msg)
            logger.info(f"Stats - Total used: {len(self.used_emails)}, Failed: {len(self.failed_emails)}")
            raise EmailPoolEmptyError(error_msg)
        
        email_address, password = self.available_emails[0]
        logger.info(f"Retrieved email from pool: {email_address}")
        logger.debug(f"Remaining in pool: {len(self.available_emails) - 1}")
        
        return email_address, password

    def mark_as_used(self, email_address: str):
        """
        Mark email as successfully used and remove from pool
        
        Args:
            email_address: Email to mark as used
        """
        logger.info(f"Marking email as used: {email_address}")
        
        self.used_emails.add(email_address)
        
        # Remove from available pool
        self.available_emails = [
            (e, p) for e, p in self.available_emails
            if e != email_address
        ]
        
        logger.debug(f"Emails remaining: {len(self.available_emails)}")

    def mark_as_failed(self, email_address: str):
        """
        Mark email as failed and remove from pool permanently
        
        Args:
            email_address: Email to mark as failed
        """
        logger.warning(f"Marking email as failed: {email_address}")
        
        self.failed_emails.add(email_address)
        
        # Remove from available pool
        self.available_emails = [
            (e, p) for e, p in self.available_emails
            if e != email_address
        ]
        
        logger.debug(f"Emails remaining: {len(self.available_emails)}")

    def reload(self):
        """Reload emails from file"""
        logger.info("Reloading email pool")
        self.available_emails.clear()
        self._load_emails()

    def get_stats(self) -> dict:
        """
        Get pool statistics
        
        Returns:
            Dictionary with pool stats
        """
        stats = {
            'available': len(self.available_emails),
            'used': len(self.used_emails),
            'failed': len(self.failed_emails),
            'total': len(self.available_emails) + len(self.used_emails) + len(self.failed_emails)
        }
        
        logger.debug(f"Pool stats: {stats}")
        return stats

    def __len__(self) -> int:
        """Return number of available emails"""
        return len(self.available_emails)
