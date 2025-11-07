"""
Example usage of EmailVerifier and HotmailPool

This file demonstrates how to use the email verification system
for Kick.com account creation
"""

import asyncio
import os
from dotenv import load_dotenv
from workers.email_handler import (
    EmailVerifier,
    HotmailPool,
    IMAPLoginError,
    NoEmailReceivedError,
    EmailPoolEmptyError
)

# Load environment variables
load_dotenv()


async def example_email_verifier_basic():
    """Basic EmailVerifier usage"""
    print("=" * 60)
    print("Example 1: Basic EmailVerifier Usage")
    print("=" * 60)
    
    # Create verifier (replace with actual credentials)
    verifier = EmailVerifier(
        email_address="your_email@hotmail.com",
        password="your_password",
        imap_server=os.getenv("IMAP_SERVER", "imap.zmailservice.com"),
        imap_port=int(os.getenv("IMAP_PORT", "993"))
    )
    
    try:
        # Connect to IMAP server
        print("\n📧 Connecting to IMAP server...")
        verifier.connect()
        print("✅ Connected successfully")
        
        # Wait for verification code
        print("\n⏳ Waiting for verification email (timeout: 90s)...")
        code = await verifier.get_verification_code(timeout=90, poll_interval=5)
        
        print(f"\n🎉 Verification code received: {code}")
        
    except IMAPLoginError as e:
        print(f"\n❌ IMAP login failed: {e}")
        print("   Check your email credentials")
    
    except NoEmailReceivedError as e:
        print(f"\n❌ No email received: {e}")
        print("   The verification email may not have been sent")
    
    finally:
        verifier.disconnect()
        print("\n✅ Disconnected from IMAP server\n")


async def example_email_verifier_context_manager():
    """Using EmailVerifier with context manager"""
    print("=" * 60)
    print("Example 2: EmailVerifier with Context Manager")
    print("=" * 60)
    
    try:
        async with EmailVerifier(
            email_address="your_email@hotmail.com",
            password="your_password"
        ) as verifier:
            print("\n📧 Connected via context manager")
            
            # This will automatically disconnect when done
            code = await verifier.get_verification_code(timeout=60)
            print(f"✅ Code: {code}")
        
        print("✅ Context manager automatically disconnected\n")
    
    except Exception as e:
        print(f"❌ Error: {e}\n")


def example_hotmail_pool_basic():
    """Basic HotmailPool usage"""
    print("=" * 60)
    print("Example 3: Basic HotmailPool Usage")
    print("=" * 60)
    
    # Initialize pool
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    print(f"\n📊 Pool stats: {pool.get_stats()}")
    
    try:
        # Get next email
        email, password = pool.get_next_email()
        print(f"\n📧 Retrieved email: {email}")
        print(f"   Password: {'*' * len(password)}")
        
        # Simulate successful use
        print("\n✅ Simulating successful account creation...")
        pool.mark_as_used(email)
        print(f"✅ Email marked as used")
        
        print(f"\n📊 Updated stats: {pool.get_stats()}")
        
    except EmailPoolEmptyError:
        print("\n❌ Email pool is empty!")
        print("   Add emails to shared/livelive.txt")
    
    print()


def example_hotmail_pool_with_failure():
    """HotmailPool with failure handling"""
    print("=" * 60)
    print("Example 4: HotmailPool with Failure Handling")
    print("=" * 60)
    
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    try:
        email, password = pool.get_next_email()
        print(f"\n📧 Trying email: {email}")
        
        # Simulate IMAP login failure
        print("❌ Simulating IMAP login failure...")
        pool.mark_as_failed(email)
        print("✅ Email marked as failed and removed from pool")
        
        # Try next email
        email2, password2 = pool.get_next_email()
        print(f"\n📧 Trying next email: {email2}")
        print("✅ Second email retrieved successfully")
        
        print(f"\n📊 Final stats: {pool.get_stats()}")
        
    except EmailPoolEmptyError:
        print("\n❌ No more emails available in pool")
    
    print()


async def example_complete_workflow():
    """Complete workflow: Pool + Verifier"""
    print("=" * 60)
    print("Example 5: Complete Email Verification Workflow")
    print("=" * 60)
    
    # Initialize pool
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    print(f"\n📊 Starting pool stats: {pool.get_stats()}\n")
    
    try:
        # Get email from pool
        email, password = pool.get_next_email()
        print(f"📧 Using email from pool: {email}")
        
        # Create verifier
        async with EmailVerifier(
            email_address=email,
            password=password,
            imap_server=os.getenv("IMAP_SERVER", "imap.zmailservice.com")
        ) as verifier:
            
            print("✅ Connected to IMAP server")
            
            # Simulate: Kick.com account creation would happen here
            print("\n🔄 [Simulated] Creating Kick account...")
            print("🔄 [Simulated] Kick sends verification email...")
            
            # Wait for verification code
            print("\n⏳ Waiting for verification email...")
            
            try:
                code = await verifier.get_verification_code(timeout=90, poll_interval=5)
                print(f"🎉 Verification code: {code}")
                
                # Simulate: Use code to verify account
                print("\n🔄 [Simulated] Verifying account with code...")
                print("✅ Account verified successfully!")
                
                # Mark email as used
                pool.mark_as_used(email)
                print(f"✅ Email {email} marked as used")
                
            except NoEmailReceivedError:
                print("❌ No verification email received")
                pool.mark_as_failed(email)
                print(f"⚠️  Email {email} marked as failed")
        
        print(f"\n📊 Final pool stats: {pool.get_stats()}")
        
    except EmailPoolEmptyError:
        print("❌ No emails available in pool")
        print("   Add emails to shared/livelive.txt in format:")
        print("   email@example.com:password")
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    print()


def example_pool_file_format():
    """Show correct pool file format"""
    print("=" * 60)
    print("Example 6: Pool File Format (shared/livelive.txt)")
    print("=" * 60)
    
    print("\nCorrect format:\n")
    print("# Lines starting with # are comments")
    print("email1@hotmail.com:password123")
    print("email2@outlook.com:mySecurePass456")
    print("email3@live.com:anotherPassword789")
    print()
    print("# Blank lines are ignored")
    print()
    print("email4@gmail.com:finalPassword000")
    
    print("\n❌ Invalid formats:")
    print("   - email_without_colon_password")
    print("   - not-an-email:password")
    print("   - @missing-local-part.com:password")
    
    print("\n✅ Tips:")
    print("   - Use one email:password pair per line")
    print("   - Email must contain @ and .")
    print("   - Password can contain any characters (no spaces recommended)")
    print("   - Use # for comments")
    print()


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print(" Email Handler - Usage Examples")
    print("=" * 60 + "\n")
    
    # Note: Examples 1 and 2 require actual email credentials
    print("⚠️  Examples 1-2 require actual email credentials")
    print("   Set up your email in the code or skip to Example 3\n")
    
    # Uncomment to run with real credentials:
    # await example_email_verifier_basic()
    # await example_email_verifier_context_manager()
    
    example_hotmail_pool_basic()
    example_hotmail_pool_with_failure()
    
    # Uncomment to run full workflow with real credentials:
    # await example_complete_workflow()
    
    example_pool_file_format()
    
    print("=" * 60)
    print(" Examples completed!")
    print("=" * 60)
    print("\n💡 To test email verification:")
    print("   1. Add your email credentials to shared/livelive.txt")
    print("   2. Uncomment the example functions in this file")
    print("   3. Run: python example_email_handler.py\n")


if __name__ == "__main__":
    asyncio.run(main())
