"""
Example usage of KickAccountCreator

This demonstrates the complete account creation workflow
"""

import asyncio
import os
from dotenv import load_dotenv

from workers.account_creator import KickAccountCreator
from workers.kasada_solver import KasadaSolver
from workers.email_handler import HotmailPool
from workers.config import Config
from workers.utils import get_logger

load_dotenv()
logger = get_logger(__name__)


async def example_single_account_test_mode():
    """Create a single account in test mode"""
    print("=" * 60)
    print("Example 1: Single Account Creation (Test Mode)")
    print("=" * 60)
    
    # Initialize components
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    # Check pool status
    stats = pool.get_stats()
    print(f"\n📊 Email pool stats: {stats}")
    
    if stats['available'] == 0:
        print("\n⚠️  Email pool is empty!")
        print("   Add emails to shared/livelive.txt")
        print("   Format: email@example.com:password\n")
        return
    
    # Create Kasada solver in test mode
    async with KasadaSolver(api_key="test", test_mode=True) as kasada_solver:
        # Create account creator
        async with KickAccountCreator(
            email_pool=pool,
            kasada_solver=kasada_solver,
            output_file="shared/kicks.json"
        ) as creator:
            
            print("\n🚀 Creating account...\n")
            
            # Create account (will use random username/password)
            result = await creator.create_account()
            
            print("\n📊 Result:")
            print(f"   Success: {result['success']}")
            if result['success']:
                print(f"   Email: {result['email']}")
                print(f"   Username: {result['username']}")
                print(f"   Password: {result['password']}")
            else:
                print(f"   Error: {result.get('error')}")
                print(f"   Message: {result.get('message')}")
    
    print()


async def example_single_account_custom():
    """Create account with custom username/password"""
    print("=" * 60)
    print("Example 2: Custom Username and Password")
    print("=" * 60)
    
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    if len(pool) == 0:
        print("\n⚠️  Email pool is empty!\n")
        return
    
    async with KasadaSolver(api_key="test", test_mode=True) as kasada_solver:
        async with KickAccountCreator(
            email_pool=pool,
            kasada_solver=kasada_solver
        ) as creator:
            
            # Create with custom credentials
            result = await creator.create_account(
                username="MyCustomUsername123",
                password="MySecurePass!@#456"
            )
            
            if result['success']:
                print(f"\n✅ Account created successfully!")
                print(f"   Username: {result['username']}")
            else:
                print(f"\n❌ Failed: {result.get('message')}")
    
    print()


async def example_batch_creation():
    """Create multiple accounts in batch"""
    print("=" * 60)
    print("Example 3: Batch Account Creation")
    print("=" * 60)
    
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    # Number of accounts to create
    num_accounts = 3
    
    print(f"\n📊 Creating {num_accounts} accounts...")
    print(f"   Available emails: {len(pool)}\n")
    
    if len(pool) < num_accounts:
        print(f"⚠️  Not enough emails in pool!")
        print(f"   Need {num_accounts}, have {len(pool)}\n")
        return
    
    async with KasadaSolver(api_key="test", test_mode=True) as kasada_solver:
        async with KickAccountCreator(
            email_pool=pool,
            kasada_solver=kasada_solver
        ) as creator:
            
            results = []
            
            for i in range(num_accounts):
                print(f"\n{'=' * 60}")
                print(f"Creating account {i + 1}/{num_accounts}")
                print(f"{'=' * 60}\n")
                
                result = await creator.create_account()
                results.append(result)
                
                # Small delay between accounts
                if i < num_accounts - 1:
                    print("\n⏳ Waiting 3 seconds before next account...")
                    await asyncio.sleep(3)
            
            # Summary
            print("\n" + "=" * 60)
            print("📊 BATCH CREATION SUMMARY")
            print("=" * 60)
            
            successful = sum(1 for r in results if r['success'])
            failed = num_accounts - successful
            
            print(f"\n✅ Successful: {successful}/{num_accounts}")
            print(f"❌ Failed: {failed}/{num_accounts}")
            
            if successful > 0:
                print("\n✅ Created accounts:")
                for r in results:
                    if r['success']:
                        print(f"   • {r['username']} ({r['email']})")
            
            if failed > 0:
                print("\n❌ Failed accounts:")
                for r in results:
                    if not r['success']:
                        print(f"   • {r.get('email', 'unknown')}: {r.get('error')}")
            
            print(f"\n📊 Final pool stats: {pool.get_stats()}")
    
    print()


async def example_with_error_handling():
    """Example with comprehensive error handling"""
    print("=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)
    
    try:
        pool = HotmailPool(pool_file="shared/livelive.txt")
        
        async with KasadaSolver(api_key="test", test_mode=True) as kasada_solver:
            async with KickAccountCreator(
                email_pool=pool,
                kasada_solver=kasada_solver
            ) as creator:
                
                result = await creator.create_account()
                
                if result['success']:
                    print(f"\n✅ Success!")
                    print(f"   Account: {result['username']}")
                    print(f"   Saved to: shared/kicks.json")
                else:
                    error_type = result.get('error')
                    
                    if error_type == 'Email verification failed':
                        print(f"\n❌ Email verification failed")
                        print(f"   The email account might be invalid")
                        print(f"   Email: {result.get('email')}")
                    
                    elif error_type == 'Kasada challenge failed':
                        print(f"\n❌ Kasada challenge failed")
                        print(f"   Check your RapidAPI key and quota")
                    
                    elif error_type == 'Registration failed':
                        print(f"\n❌ Registration failed")
                        print(f"   Username might be taken or invalid")
                    
                    else:
                        print(f"\n❌ Unknown error: {result.get('message')}")
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    
    print()


async def example_live_api():
    """Example using live API (requires valid credentials)"""
    print("=" * 60)
    print("Example 5: Live API Mode")
    print("=" * 60)
    
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key or api_key == "your_key_here":
        print("\n⚠️  Skipped: RAPIDAPI_KEY not configured")
        print("   Set RAPIDAPI_KEY in .env file to use live API\n")
        return
    
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    if len(pool) == 0:
        print("\n⚠️  Email pool is empty!\n")
        return
    
    print("\n⚠️  WARNING: This will make real API calls!")
    print("   - Uses RapidAPI quota")
    print("   - Creates real Kick.com account")
    print("   - Uses real email from pool\n")
    
    # Set test_mode=False for production
    async with KasadaSolver(api_key=api_key, test_mode=False) as kasada_solver:
        async with KickAccountCreator(
            email_pool=pool,
            kasada_solver=kasada_solver
        ) as creator:
            
            result = await creator.create_account()
            
            if result['success']:
                print(f"\n🎉 Real account created!")
                print(f"   Username: {result['username']}")
                print(f"   Email: {result['email']}")
                print(f"   Password: {result['password']}")
            else:
                print(f"\n❌ Failed: {result.get('message')}")
    
    print()


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print(" Kick Account Creator - Usage Examples")
    print("=" * 60 + "\n")
    
    # Run examples
    await example_single_account_test_mode()
    
    # Uncomment to run other examples:
    # await example_single_account_custom()
    # await example_batch_creation()
    # await example_with_error_handling()
    
    # Only run with valid API key:
    # await example_live_api()
    
    print("=" * 60)
    print(" Examples completed!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Add emails to shared/livelive.txt")
    print("   2. Configure RAPIDAPI_KEY in .env")
    print("   3. Set test_mode=False for production")
    print("   4. Run: python example_account_creator.py\n")


if __name__ == "__main__":
    asyncio.run(main())
