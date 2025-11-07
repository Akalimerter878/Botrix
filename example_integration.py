"""
Complete Integration Example: Kick Account Generator

This demonstrates how all components work together:
1. HotmailPool - Get email from pool
2. KasadaSolver - Bypass Kasada protection
3. EmailVerifier - Get verification code
4. Account creation workflow
"""

import asyncio
import os
import aiohttp
from dotenv import load_dotenv

from workers.kasada_solver import KasadaSolver, KasadaSolverError
from workers.email_handler import (
    EmailVerifier,
    HotmailPool,
    EmailPoolEmptyError,
    IMAPLoginError,
    NoEmailReceivedError
)
from workers.utils import get_logger

# Load environment
load_dotenv()
logger = get_logger(__name__)


async def create_kick_account(
    email: str,
    password: str,
    username: str,
    kasada_solver: KasadaSolver
) -> dict:
    """
    Simulated Kick.com account creation workflow
    
    Args:
        email: Email for account
        password: Password for account
        username: Desired username
        kasada_solver: KasadaSolver instance
        
    Returns:
        Dict with account creation status
    """
    logger.info(f"🎮 Creating Kick account for {username}")
    
    try:
        # Step 1: Solve Kasada challenge for signup endpoint
        logger.info("Step 1: Solving Kasada challenge...")
        kasada_headers = await kasada_solver.solve(
            method="POST",
            fetch_url="https://kick.com/api/v1/signup/send/email"
        )
        logger.info("✅ Kasada headers obtained")
        
        # Step 2: Send signup request (simulated)
        logger.info("Step 2: Sending signup request...")
        logger.info(f"   Email: {email}")
        logger.info(f"   Username: {username}")
        
        # In real implementation, you would:
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(
        #         "https://kick.com/api/v1/signup/send/email",
        #         headers=kasada_headers,
        #         json={"email": email, "username": username, "password": password}
        #     ) as response:
        #         result = await response.json()
        
        logger.info("✅ Signup request sent (simulated)")
        
        return {
            "success": True,
            "email": email,
            "username": username,
            "message": "Account creation initiated"
        }
        
    except KasadaSolverError as e:
        logger.error(f"❌ Kasada solver failed: {e}")
        return {
            "success": False,
            "error": "Kasada challenge failed",
            "message": str(e)
        }


async def verify_kick_account(
    email: str,
    email_password: str,
    verification_timeout: int = 90
) -> dict:
    """
    Verify Kick account using email verification code
    
    Args:
        email: Email address
        email_password: Email password
        verification_timeout: Timeout for email verification
        
    Returns:
        Dict with verification status
    """
    logger.info(f"📧 Verifying account for {email}")
    
    try:
        # Create email verifier
        async with EmailVerifier(
            email_address=email,
            password=email_password,
            imap_server=os.getenv("IMAP_SERVER", "imap.zmailservice.com"),
            imap_port=int(os.getenv("IMAP_PORT", "993"))
        ) as verifier:
            
            logger.info("✅ Connected to IMAP server")
            
            # Wait for verification code
            logger.info(f"⏳ Waiting for verification email (timeout: {verification_timeout}s)...")
            code = await verifier.get_verification_code(
                timeout=verification_timeout,
                poll_interval=5
            )
            
            logger.info(f"✅ Verification code received: {code}")
            
            # In real implementation, you would:
            # - Send verification code to Kick.com
            # - Complete account verification
            
            return {
                "success": True,
                "code": code,
                "message": "Verification code retrieved"
            }
            
    except IMAPLoginError as e:
        logger.error(f"❌ IMAP login failed: {e}")
        return {
            "success": False,
            "error": "IMAP login failed",
            "message": str(e)
        }
    
    except NoEmailReceivedError as e:
        logger.error(f"❌ No verification email: {e}")
        return {
            "success": False,
            "error": "No email received",
            "message": str(e)
        }


async def complete_account_workflow(
    username: str,
    account_password: str,
    pool: HotmailPool,
    kasada_solver: KasadaSolver
) -> dict:
    """
    Complete workflow: Create and verify Kick account
    
    Args:
        username: Desired username
        account_password: Password for Kick account
        pool: HotmailPool instance
        kasada_solver: KasadaSolver instance
        
    Returns:
        Dict with workflow status
    """
    logger.info("=" * 60)
    logger.info(f"🚀 Starting complete workflow for: {username}")
    logger.info("=" * 60)
    
    email = None
    
    try:
        # Step 1: Get email from pool
        logger.info("\n📊 Step 1: Getting email from pool...")
        email, email_password = pool.get_next_email()
        logger.info(f"✅ Using email: {email}")
        
        # Step 2: Create account
        logger.info("\n🎮 Step 2: Creating Kick account...")
        creation_result = await create_kick_account(
            email=email,
            password=account_password,
            username=username,
            kasada_solver=kasada_solver
        )
        
        if not creation_result["success"]:
            logger.error("❌ Account creation failed")
            pool.mark_as_failed(email)
            return creation_result
        
        logger.info("✅ Account creation initiated")
        
        # Step 3: Verify account
        logger.info("\n📧 Step 3: Verifying account via email...")
        verification_result = await verify_kick_account(
            email=email,
            email_password=email_password,
            verification_timeout=90
        )
        
        if not verification_result["success"]:
            logger.error("❌ Verification failed")
            
            # Mark as failed if IMAP login failed
            if verification_result.get("error") == "IMAP login failed":
                pool.mark_as_failed(email)
            
            return verification_result
        
        logger.info(f"✅ Account verified with code: {verification_result['code']}")
        
        # Step 4: Mark email as used
        pool.mark_as_used(email)
        logger.info(f"✅ Email {email} marked as used")
        
        # Success!
        logger.info("\n" + "=" * 60)
        logger.info("🎉 ACCOUNT CREATED SUCCESSFULLY!")
        logger.info("=" * 60)
        
        return {
            "success": True,
            "email": email,
            "username": username,
            "verification_code": verification_result["code"],
            "message": "Account created and verified successfully"
        }
        
    except EmailPoolEmptyError:
        logger.error("❌ Email pool is empty!")
        return {
            "success": False,
            "error": "Pool empty",
            "message": "No emails available in pool"
        }
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if email:
            pool.mark_as_failed(email)
        return {
            "success": False,
            "error": "Unexpected error",
            "message": str(e)
        }


async def batch_create_accounts(
    usernames: list,
    password_template: str = "KickPass123!"
) -> list:
    """
    Create multiple Kick accounts in batch
    
    Args:
        usernames: List of desired usernames
        password_template: Password template for accounts
        
    Returns:
        List of results for each account
    """
    logger.info("=" * 60)
    logger.info(f"📦 BATCH ACCOUNT CREATION - {len(usernames)} accounts")
    logger.info("=" * 60)
    
    # Initialize components
    pool = HotmailPool(pool_file="shared/livelive.txt")
    logger.info(f"\n📊 Pool stats: {pool.get_stats()}")
    
    # Use test mode for Kasada (set to False for production)
    async with KasadaSolver(
        api_key=os.getenv("RAPIDAPI_KEY", "test"),
        test_mode=True
    ) as kasada_solver:
        
        results = []
        
        for i, username in enumerate(usernames, 1):
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Account {i}/{len(usernames)}: {username}")
            logger.info(f"{'=' * 60}")
            
            result = await complete_account_workflow(
                username=username,
                account_password=password_template,
                pool=pool,
                kasada_solver=kasada_solver
            )
            
            results.append(result)
            
            # Small delay between accounts
            if i < len(usernames):
                logger.info("\n⏳ Waiting 3 seconds before next account...")
                await asyncio.sleep(3)
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 BATCH CREATION SUMMARY")
        logger.info("=" * 60)
        
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        logger.info(f"\n✅ Successful: {successful}/{len(results)}")
        logger.info(f"❌ Failed: {failed}/{len(results)}")
        
        logger.info(f"\n📊 Final pool stats: {pool.get_stats()}")
        
        return results


async def main():
    """Main example runner"""
    print("\n" + "=" * 60)
    print(" Kick Account Generator - Complete Integration Example")
    print("=" * 60 + "\n")
    
    # Example 1: Single account creation
    print("Example 1: Single Account Creation (Test Mode)\n")
    
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    if len(pool) == 0:
        print("⚠️  Email pool is empty!")
        print("   Add emails to shared/livelive.txt in format:")
        print("   email@example.com:password\n")
        print("   Example:")
        print("   test1@hotmail.com:password123")
        print("   test2@outlook.com:securePass456\n")
    else:
        async with KasadaSolver(api_key="test", test_mode=True) as solver:
            result = await complete_account_workflow(
                username="TestUser123",
                account_password="KickPass123!",
                pool=pool,
                kasada_solver=solver
            )
            
            print(f"\nResult: {result}\n")
    
    # Example 2: Batch creation (commented out)
    # print("\nExample 2: Batch Account Creation\n")
    # usernames = ["KickUser1", "KickUser2", "KickUser3"]
    # results = await batch_create_accounts(usernames)
    
    print("=" * 60)
    print(" Example completed!")
    print("=" * 60)
    print("\n💡 To run with real API:")
    print("   1. Set test_mode=False in KasadaSolver")
    print("   2. Add valid RAPIDAPI_KEY to .env")
    print("   3. Add email accounts to shared/livelive.txt")
    print("   4. Implement actual Kick.com API calls\n")


if __name__ == "__main__":
    asyncio.run(main())
