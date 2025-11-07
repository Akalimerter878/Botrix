"""
Quick Start Script for Kick Account Generator

This script helps you verify your setup and test the KasadaSolver
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv


def check_setup():
    """Check if the project is set up correctly"""
    print("🔍 Checking project setup...\n")
    
    issues = []
    
    # Check .env file
    env_path = Path(".env")
    if not env_path.exists():
        issues.append("❌ .env file not found. Copy .env.example to .env and add your credentials")
    else:
        print("✅ .env file exists")
        load_dotenv()
        
        # Check API key
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key or api_key == "your_key_here":
            issues.append("⚠️  RAPIDAPI_KEY not set in .env file")
        else:
            print("✅ RAPIDAPI_KEY is configured")
    
    # Check required directories
    required_dirs = ["workers", "tests", "shared", "logs"]
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_name == "logs":
            # Create logs directory if it doesn't exist
            dir_path.mkdir(exist_ok=True)
            print(f"✅ {dir_name}/ directory ready")
        elif dir_path.exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            issues.append(f"❌ {dir_name}/ directory missing")
    
    # Check key files
    key_files = [
        "workers/kasada_solver.py",
        "workers/utils.py",
        "workers/config.py",
        "requirements.txt"
    ]
    
    for file_path in key_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} exists")
        else:
            issues.append(f"❌ {file_path} missing")
    
    print()
    
    if issues:
        print("⚠️  Issues found:\n")
        for issue in issues:
            print(f"  {issue}")
        print()
        return False
    else:
        print("✨ All checks passed! Your setup looks good.\n")
        return True


async def test_kasada_solver():
    """Test KasadaSolver in test mode"""
    print("🧪 Testing KasadaSolver (test mode)...\n")
    
    try:
        from workers.kasada_solver import KasadaSolver
        
        # Test in test mode (no API key required)
        async with KasadaSolver(api_key="test", test_mode=True) as solver:
            print("✅ KasadaSolver initialized")
            
            headers = await solver.solve(
                method="POST",
                fetch_url="https://kick.com/api/v1/signup/send/email"
            )
            
            print(f"✅ Received {len(headers)} mock headers:")
            for key in headers:
                print(f"   • {key}")
            
        print("\n✨ KasadaSolver test mode works correctly!\n")
        return True
        
    except Exception as e:
        print(f"❌ Error testing KasadaSolver: {e}\n")
        return False


async def test_logger():
    """Test the logging system"""
    print("📝 Testing logger...\n")
    
    try:
        from workers.utils import get_logger
        
        logger = get_logger("quickstart")
        logger.debug("Debug message test")
        logger.info("Info message test")
        logger.warning("Warning message test")
        
        print("\n✅ Logger is working (check above for colored output)")
        print(f"✅ Log file created in logs/ directory\n")
        return True
        
    except Exception as e:
        print(f"❌ Error testing logger: {e}\n")
        return False


async def test_email_pool():
    """Test the HotmailPool"""
    print("📧 Testing HotmailPool...\n")
    
    try:
        from workers.email_handler import HotmailPool, EmailPoolEmptyError
        
        pool = HotmailPool(pool_file="shared/livelive.txt")
        print(f"✅ HotmailPool initialized")
        
        stats = pool.get_stats()
        print(f"✅ Pool stats: Available={stats['available']}, Used={stats['used']}, Failed={stats['failed']}")
        
        if stats['available'] > 0:
            email, password = pool.get_next_email()
            print(f"✅ Successfully retrieved email: {email}")
            print(f"   (Password length: {len(password)} characters)")
        else:
            print(f"⚠️  Pool is empty - add emails to shared/livelive.txt")
            print(f"   Format: email@example.com:password")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error testing HotmailPool: {e}\n")
        return False


async def test_account_creator():
    """Test the KickAccountCreator"""
    print("🎮 Testing KickAccountCreator...\n")
    
    try:
        from workers.account_creator import (
            generate_random_username,
            generate_random_password,
            generate_random_birthdate
        )
        
        # Test helper functions
        username = generate_random_username()
        print(f"✅ Generated username: {username}")
        
        password = generate_random_password()
        print(f"✅ Generated password: {'*' * len(password)} (length: {len(password)})")
        
        birthdate = generate_random_birthdate()
        print(f"✅ Generated birthdate: {birthdate}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error testing KickAccountCreator: {e}\n")
        return False


async def main():
    """Main quick start routine"""
    print("\n" + "=" * 60)
    print(" Kick Account Generator - Quick Start")
    print("=" * 60 + "\n")
    
    # Check setup
    setup_ok = check_setup()
    
    if not setup_ok:
        print("⚠️  Please fix the issues above before continuing.\n")
        print("Quick fixes:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your RAPIDAPI_KEY to .env")
        print("  3. Run: pip install -r requirements.txt\n")
        return
    
    # Test logger
    await test_logger()
    
    # Test email pool
    await test_email_pool()
    
    # Test account creator
    await test_account_creator()
    
    # Test KasadaSolver
    await test_kasada_solver()
    
    # Final message
    print("=" * 60)
    print(" Next Steps")
    print("=" * 60 + "\n")
    print("1. Add email accounts to shared/livelive.txt:")
    print("   Format: email@example.com:password\n")
    print("2. Configure your .env file:")
    print("   cp .env.example .env")
    print("   Edit .env and add your RAPIDAPI_KEY\n")
    print("3. Run examples:")
    print("   python example_kasada_usage.py")
    print("   python example_email_handler.py")
    print("   python example_account_creator.py\n")
    print("4. Create accounts:")
    print("   python main.py --count 5 --test-mode   # Test mode")
    print("   python main.py --count 5                # Production mode\n")
    print("5. Run tests:")
    print("   pytest\n")
    print("6. Check documentation:")
    print("   See README.md for full documentation\n")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
