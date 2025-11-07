"""
Main entry point for Kick Account Generator

Usage:
    python main.py --count 5                    # Create 5 accounts
    python main.py --count 10 --test-mode      # Test mode (no real API calls)
    python main.py --username MyUser --password MyPass123
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from workers.account_creator import KickAccountCreator
from workers.kasada_solver import KasadaSolver
from workers.email_handler import HotmailPool
from workers.config import Config
from workers.utils import get_logger

# Load environment variables
load_dotenv()
logger = get_logger(__name__)


async def create_single_account(
    creator: KickAccountCreator,
    username: str = None,
    password: str = None
) -> dict:
    """
    Create a single account
    
    Args:
        creator: KickAccountCreator instance
        username: Optional custom username
        password: Optional custom password
        
    Returns:
        Result dictionary
    """
    try:
        result = await creator.create_account(
            username=username,
            password=password
        )
        return result
    except Exception as e:
        logger.error(f"Failed to create account: {e}")
        return {
            "success": False,
            "error": "Unexpected error",
            "message": str(e)
        }


async def create_multiple_accounts(
    count: int,
    test_mode: bool = False,
    delay_between: int = 3
) -> list:
    """
    Create multiple accounts
    
    Args:
        count: Number of accounts to create
        test_mode: Use test mode (no real API calls)
        delay_between: Seconds to wait between accounts
        
    Returns:
        List of results
    """
    logger.info("=" * 60)
    logger.info(f"🚀 Kick Account Generator - Creating {count} accounts")
    logger.info("=" * 60)
    
    # Initialize components
    pool = HotmailPool(pool_file="shared/livelive.txt")
    config = Config()
    
    # Check pool has enough emails
    pool_stats = pool.get_stats()
    logger.info(f"📊 Email pool: {pool_stats['available']} available")
    
    if pool_stats['available'] < count:
        logger.error(f"❌ Not enough emails in pool!")
        logger.error(f"   Need: {count}, Have: {pool_stats['available']}")
        logger.error(f"   Add more emails to shared/livelive.txt")
        return []
    
    # Get API key
    api_key = os.getenv("RAPIDAPI_KEY", "test")
    
    if not test_mode:
        if not api_key or api_key == "your_key_here":
            logger.error("❌ RAPIDAPI_KEY not configured in .env file")
            logger.error("   Either add your API key or use --test-mode")
            return []
        
        logger.warning("⚠️  Running in LIVE mode - will make real API calls!")
    else:
        logger.info("ℹ️  Running in TEST mode - no real API calls")
    
    # Validate config
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return []
    
    results = []
    
    # Create Kasada solver
    async with KasadaSolver(api_key=api_key, test_mode=test_mode) as kasada_solver:
        # Create account creator
        async with KickAccountCreator(
            email_pool=pool,
            kasada_solver=kasada_solver,
            config=config,
            output_file="shared/kicks.json"
        ) as creator:
            
            for i in range(count):
                logger.info("")
                logger.info("=" * 60)
                logger.info(f"Account {i + 1}/{count}")
                logger.info("=" * 60)
                
                result = await create_single_account(creator)
                results.append(result)
                
                # Delay between accounts (except after last one)
                if i < count - 1:
                    logger.info(f"\n⏳ Waiting {delay_between} seconds before next account...")
                    await asyncio.sleep(delay_between)
    
    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 FINAL SUMMARY")
    logger.info("=" * 60)
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    logger.info(f"\n✅ Successful: {len(successful)}/{count}")
    logger.info(f"❌ Failed: {len(failed)}/{count}")
    
    if successful:
        logger.info("\n✅ Created accounts:")
        for r in successful:
            logger.info(f"   • {r['username']} ({r['email']})")
        logger.info(f"\n💾 Accounts saved to: shared/kicks.json")
    
    if failed:
        logger.info("\n❌ Failed accounts:")
        for r in failed:
            email = r.get('email', 'unknown')
            error = r.get('error', 'unknown error')
            logger.info(f"   • {email}: {error}")
    
    logger.info(f"\n📊 Final pool stats: {pool.get_stats()}")
    logger.info("")
    
    return results


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Kick.com Account Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --count 5                     Create 5 accounts
  python main.py --count 10 --test-mode       Create 10 accounts in test mode
  python main.py --username MyUser --password MyPass123
  python main.py --count 3 --delay 5          Create 3 accounts with 5s delay
        """
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=1,
        help='Number of accounts to create (default: 1)'
    )
    
    parser.add_argument(
        '--username',
        type=str,
        help='Custom username (only for single account)'
    )
    
    parser.add_argument(
        '--password',
        type=str,
        help='Custom password (only for single account)'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode (no real API calls)'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=3,
        help='Seconds to wait between accounts (default: 3)'
    )
    
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Show banner
    print("\n" + "=" * 60)
    print(" Kick.com Account Generator")
    print(" Created with ❤️  for automation")
    print("=" * 60 + "\n")
    
    # Validate arguments
    if args.count > 1 and (args.username or args.password):
        logger.error("❌ Cannot use --username or --password with --count > 1")
        logger.error("   Custom credentials only work for single account creation")
        return
    
    # Check if required files exist
    if not Path("shared/livelive.txt").exists():
        logger.error("❌ shared/livelive.txt not found!")
        logger.error("   Create this file and add your email accounts")
        logger.error("   Format: email@example.com:password")
        return
    
    if not Path(".env").exists():
        logger.warning("⚠️  .env file not found")
        logger.warning("   Copy .env.example to .env and configure it")
        if not args.test_mode:
            logger.error("❌ Cannot run in live mode without .env file")
            return
    
    try:
        if args.count == 1 and (args.username or args.password):
            # Single account with custom credentials
            pool = HotmailPool(pool_file="shared/livelive.txt")
            
            async with KasadaSolver(
                api_key=os.getenv("RAPIDAPI_KEY", "test"),
                test_mode=args.test_mode
            ) as kasada_solver:
                async with KickAccountCreator(
                    email_pool=pool,
                    kasada_solver=kasada_solver
                ) as creator:
                    result = await create_single_account(
                        creator,
                        username=args.username,
                        password=args.password
                    )
                    
                    if result['success']:
                        logger.info("\n🎉 Account created successfully!")
                    else:
                        logger.error(f"\n❌ Failed: {result.get('message')}")
        else:
            # Multiple accounts or single with auto-generated credentials
            await create_multiple_accounts(
                count=args.count,
                test_mode=args.test_mode,
                delay_between=args.delay
            )
    
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Interrupted by user")
        logger.info("Shutting down gracefully...")
    
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        return 1
    
    print("\n" + "=" * 60)
    print(" Done!")
    print("=" * 60 + "\n")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code or 0)
