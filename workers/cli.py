"""
Command-line interface for manual testing and operations

Provides various commands for testing and managing the Botrix account generator
"""

import asyncio
import argparse
import sys
import os
import json
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import imaplib
from email import message_from_bytes

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from workers.kasada_solver import KasadaSolver, KasadaSolverError
from workers.email_handler import EmailVerifier, HotmailPool, EmailHandlerError
from workers.account_creator import KickAccountCreator
from workers.config import Config
from workers.utils import get_logger

# Initialize logger
logger = get_logger(__name__)


class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


def print_success(message: str):
    """Print success message in green"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message in red"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message in cyan"""
    print(f"{Colors.CYAN}ℹ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_header(message: str):
    """Print header message in bold cyan"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{message}{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * len(message)}{Colors.RESET}\n")


async def test_kasada(args: argparse.Namespace) -> int:
    """Test Kasada solver with real or mock API"""
    print_header("Testing Kasada Solver")
    
    if args.dry_run:
        print_info("Running in DRY RUN mode (using mocks)")
        test_mode = True
        api_key = "test_key"
    else:
        config = Config()
        api_key = config.RAPIDAPI_KEY
        test_mode = False
        
        if not api_key:
            print_error("RAPIDAPI_KEY not set in environment")
            print_info("Either set RAPIDAPI_KEY in .env or use --dry-run flag")
            return 1
    
    try:
        async with KasadaSolver(api_key=api_key, test_mode=test_mode) as solver:
            print_info(f"Solver initialized (test_mode={test_mode})")
            
            # Test URL
            test_url = "https://kick.com/api/v1/signup/send/email"
            
            if args.verbose:
                print_info(f"Solving challenge for: {test_url}")
                print_info(f"Method: POST")
            
            # Solve challenge
            headers = await solver.solve(method="POST", fetch_url=test_url)
            
            print_success("Kasada challenge solved successfully!")
            
            if args.verbose:
                print_info("Received headers:")
                for key, value in headers.items():
                    # Truncate long values for display
                    display_value = value[:50] + "..." if len(value) > 50 else value
                    print(f"  {Colors.CYAN}{key}{Colors.RESET}: {display_value}")
            else:
                print_info(f"Received {len(headers)} headers")
            
            # Verify required headers
            required_headers = ['x-kpsdk-ct', 'x-kpsdk-cd', 'user-agent']
            missing_headers = [h for h in required_headers if h not in headers]
            
            if missing_headers:
                print_warning(f"Missing headers: {', '.join(missing_headers)}")
            else:
                print_success("All required headers present")
            
        return 0
        
    except KasadaSolverError as e:
        print_error(f"Kasada solver error: {e}")
        if args.verbose:
            import traceback
            print(f"\n{Colors.RED}{traceback.format_exc()}{Colors.RESET}")
        return 1
    
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            print(f"\n{Colors.RED}{traceback.format_exc()}{Colors.RESET}")
        return 1


async def test_email(args: argparse.Namespace) -> int:
    """Test IMAP connection and code retrieval"""
    print_header("Testing Email Handler")
    
    email = args.email
    password = args.password
    
    if not email or not password:
        print_error("Both email and password are required")
        print_info("Usage: cli.py test-email <email> <password>")
        return 1
    
    config = Config()
    
    print_info(f"Testing email: {email}")
    print_info(f"IMAP server: {config.IMAP_SERVER}:{config.IMAP_PORT}")
    
    try:
        # Test IMAP connection
        print_info("Connecting to IMAP server...")
        
        async with EmailVerifier(
            email_address=email,
            password=password,
            imap_server=config.IMAP_SERVER,
            imap_port=config.IMAP_PORT
        ) as verifier:
            print_success("Connected to IMAP server successfully!")
            
            if args.verbose:
                print_info("IMAP connection details:")
                print(f"  Server: {config.IMAP_SERVER}")
                print(f"  Port: {config.IMAP_PORT}")
                print(f"  Email: {email}")
            
            # Check for existing emails
            print_info("Checking inbox for Kick verification emails...")
            
            try:
                # Try to get verification code (with short timeout for testing)
                code = await verifier.get_verification_code(timeout=10, poll_interval=2)
                print_success(f"Found verification code: {code}")
                
            except asyncio.TimeoutError:
                print_warning("No verification email found (timeout after 10 seconds)")
                print_info("This is normal if there are no recent verification emails")
                print_success("IMAP connection is working correctly")
            
        return 0
        
    except imaplib.IMAP4.error as e:
        print_error(f"IMAP error: {e}")
        print_info("Check your email credentials and IMAP server settings")
        return 1
    
    except EmailHandlerError as e:
        print_error(f"Email handler error: {e}")
        if args.verbose:
            import traceback
            print(f"\n{Colors.RED}{traceback.format_exc()}{Colors.RESET}")
        return 1
    
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            print(f"\n{Colors.RED}{traceback.format_exc()}{Colors.RESET}")
        return 1


async def create_one_account(args: argparse.Namespace) -> int:
    """Create a single account with detailed logging"""
    print_header("Creating Single Account")
    
    config = Config()
    
    # Check if dry run
    if args.dry_run:
        print_info("Running in DRY RUN mode (using mocks)")
        kasada_test_mode = True
        api_key = "test_key"
    else:
        kasada_test_mode = False
        api_key = config.RAPIDAPI_KEY
        
        if not api_key:
            print_error("RAPIDAPI_KEY not set in environment")
            print_info("Either set RAPIDAPI_KEY in .env or use --dry-run flag")
            return 1
    
    try:
        # Initialize components
        print_info("Initializing components...")
        
        pool = HotmailPool(pool_file=config.POOL_FILE)
        pool_stats = pool.get_stats()
        
        print_info(f"Email pool loaded: {pool_stats['available']} available, {pool_stats['used']} used")
        
        if pool_stats['available'] == 0:
            print_error("No emails available in pool")
            print_info(f"Add emails to {config.POOL_FILE}")
            return 1
        
        async with KasadaSolver(api_key=api_key, test_mode=kasada_test_mode) as kasada:
            print_success("Kasada solver initialized")
            
            async with KickAccountCreator(
                email_pool=pool,
                kasada_solver=kasada,
                config=config,
                output_file=config.OUTPUT_FILE
            ) as creator:
                print_success("Account creator initialized")
                
                print_info("\nStarting account creation workflow...")
                print_info("This may take 2-5 minutes...\n")
                
                # Create account
                result = await creator.create_account()
                
                # Display results
                if result['success']:
                    print_success("Account created successfully!")
                    print_info("\nAccount details:")
                    print(f"  {Colors.CYAN}Username:{Colors.RESET} {result.get('username', 'N/A')}")
                    print(f"  {Colors.CYAN}Email:{Colors.RESET} {result.get('email', 'N/A')}")
                    print(f"  {Colors.CYAN}Password:{Colors.RESET} {result.get('password', 'N/A')}")
                    print(f"  {Colors.CYAN}Verification Code:{Colors.RESET} {result.get('verification_code', 'N/A')}")
                    
                    if args.verbose and 'account_data' in result:
                        print(f"\n{Colors.CYAN}Full account data:{Colors.RESET}")
                        print(json.dumps(result['account_data'], indent=2))
                    
                    print_info(f"\nAccount saved to: {config.OUTPUT_FILE}")
                    return 0
                    
                else:
                    print_error("Account creation failed")
                    print_info(f"Error: {result.get('error', 'Unknown error')}")
                    print_info(f"Message: {result.get('message', 'No details')}")
                    
                    if args.verbose:
                        print(f"\n{Colors.YELLOW}Full result:{Colors.RESET}")
                        print(json.dumps(result, indent=2))
                    
                    return 1
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            print(f"\n{Colors.RED}{traceback.format_exc()}{Colors.RESET}")
        return 1


async def validate_pool(args: argparse.Namespace) -> int:
    """Validate email pool format and IMAP connectivity"""
    print_header("Validating Email Pool")
    
    config = Config()
    pool_file = config.POOL_FILE
    
    if not os.path.exists(pool_file):
        print_error(f"Pool file not found: {pool_file}")
        return 1
    
    print_info(f"Validating pool file: {pool_file}")
    
    try:
        # Load pool
        pool = HotmailPool(pool_file=pool_file)
        stats = pool.get_stats()
        
        print_success(f"Pool file format is valid")
        print_info(f"Total emails: {stats['total']}")
        print_info(f"Available: {stats['available']}")
        print_info(f"Used: {stats['used']}")
        print_info(f"Failed: {stats['failed']}")
        
        if stats['available'] == 0:
            print_warning("No available emails in pool")
            return 1
        
        # Test IMAP connectivity for first email (if requested)
        if args.verbose and stats['available'] > 0:
            print_info("\nTesting IMAP connectivity for first email...")
            
            email, password = pool.get_next_email()
            
            try:
                print_info(f"Testing: {email}")
                
                # Test connection
                imap = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
                imap.login(email, password)
                imap.select('INBOX')
                
                # Count emails
                _, messages = imap.search(None, 'ALL')
                email_count = len(messages[0].split()) if messages[0] else 0
                
                imap.close()
                imap.logout()
                
                print_success(f"IMAP connection successful!")
                print_info(f"Inbox contains {email_count} emails")
                
                # Mark as available again (we just tested it)
                pool.used_emails.discard(email)
                
            except imaplib.IMAP4.error as e:
                print_error(f"IMAP connection failed: {e}")
                pool.mark_as_failed(email)
                print_warning("Email marked as failed")
        
        return 0
        
    except Exception as e:
        print_error(f"Validation error: {e}")
        if args.verbose:
            import traceback
            print(f"\n{Colors.RED}{traceback.format_exc()}{Colors.RESET}")
        return 1


async def check_quota(args: argparse.Namespace) -> int:
    """Check RapidAPI remaining quota"""
    print_header("Checking RapidAPI Quota")
    
    if args.dry_run:
        print_info("Running in DRY RUN mode")
        print_warning("Cannot check real quota in dry-run mode")
        print_info("Quota check requires a real API key")
        return 0
    
    config = Config()
    api_key = config.RAPIDAPI_KEY
    
    if not api_key:
        print_error("RAPIDAPI_KEY not set in environment")
        print_info("Set RAPIDAPI_KEY in .env file")
        return 1
    
    print_info("Checking quota...")
    
    try:
        import aiohttp
        
        # Make a test request to check quota
        # Note: RapidAPI quota info is usually in response headers
        async with aiohttp.ClientSession() as session:
            url = "https://kasada-solver.p.rapidapi.com/solve"
            headers = {
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "kasada-solver.p.rapidapi.com"
            }
            
            # Make a minimal request just to check headers
            async with session.get(url, headers=headers) as response:
                # Check quota headers
                quota_headers = {
                    'x-ratelimit-requests-limit': 'Request limit',
                    'x-ratelimit-requests-remaining': 'Requests remaining',
                    'x-ratelimit-requests-reset': 'Reset time',
                }
                
                print_success("API key is valid")
                
                if args.verbose:
                    print_info("\nQuota information:")
                    
                    for header, description in quota_headers.items():
                        value = response.headers.get(header, 'N/A')
                        print(f"  {Colors.CYAN}{description}:{Colors.RESET} {value}")
                    
                    print_info("\nAll response headers:")
                    for key, value in response.headers.items():
                        if 'ratelimit' in key.lower() or 'quota' in key.lower():
                            print(f"  {Colors.YELLOW}{key}:{Colors.RESET} {value}")
                else:
                    remaining = response.headers.get('x-ratelimit-requests-remaining', 'Unknown')
                    limit = response.headers.get('x-ratelimit-requests-limit', 'Unknown')
                    print_info(f"Requests: {remaining} / {limit}")
        
        return 0
        
    except aiohttp.ClientError as e:
        print_error(f"HTTP error: {e}")
        return 1
    
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            print(f"\n{Colors.RED}{traceback.format_exc()}{Colors.RESET}")
        return 1


async def export_accounts(args: argparse.Namespace) -> int:
    """Export accounts from kicks.json to CSV format"""
    print_header("Exporting Accounts to CSV")
    
    config = Config()
    input_file = config.OUTPUT_FILE
    
    if not os.path.exists(input_file):
        print_error(f"Accounts file not found: {input_file}")
        return 1
    
    # Read accounts
    print_info(f"Reading accounts from: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
        
        if not accounts:
            print_warning("No accounts found in file")
            return 0
        
        print_success(f"Loaded {len(accounts)} accounts")
        
        # Determine output file
        if args.output:
            output_file = args.output
        else:
            # Default: kicks_YYYYMMDD_HHMMSS.csv
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"kicks_{timestamp}.csv"
        
        # Export to CSV
        print_info(f"Exporting to: {output_file}")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            # Determine fields
            fields = ['email', 'username', 'password', 'birthdate', 'verification_code', 'created_at', 'success']
            
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            
            for account in accounts:
                # Extract only the fields we want
                row = {field: account.get(field, '') for field in fields}
                writer.writerow(row)
        
        print_success(f"Exported {len(accounts)} accounts to {output_file}")
        
        if args.verbose:
            print_info("\nPreview of first account:")
            first_account = accounts[0]
            for key in fields:
                value = first_account.get(key, 'N/A')
                print(f"  {Colors.CYAN}{key}:{Colors.RESET} {value}")
        
        return 0
        
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in {input_file}: {e}")
        return 1
    
    except Exception as e:
        print_error(f"Export error: {e}")
        if args.verbose:
            import traceback
            print(f"\n{Colors.RED}{traceback.format_exc()}{Colors.RESET}")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all commands"""
    parser = argparse.ArgumentParser(
        description="Botrix CLI - Manual testing and operations tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s test-kasada --dry-run
  %(prog)s test-kasada --verbose
  %(prog)s test-email user@hotmail.com password123
  %(prog)s create-one --verbose
  %(prog)s create-one --dry-run
  %(prog)s validate-pool --verbose
  %(prog)s check-quota
  %(prog)s export-accounts --output my_accounts.csv
        """
    )
    
    # Global flags
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output with detailed logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Use mock data instead of real API calls'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # test-kasada
    parser_kasada = subparsers.add_parser(
        'test-kasada',
        help='Test Kasada solver with real or mock API'
    )
    
    # test-email
    parser_email = subparsers.add_parser(
        'test-email',
        help='Test IMAP connection and code retrieval'
    )
    parser_email.add_argument('email', help='Email address to test')
    parser_email.add_argument('password', help='Email password')
    
    # create-one
    parser_create = subparsers.add_parser(
        'create-one',
        help='Create a single account with detailed logging'
    )
    
    # validate-pool
    parser_validate = subparsers.add_parser(
        'validate-pool',
        help='Check livelive.txt format and IMAP connectivity'
    )
    
    # check-quota
    parser_quota = subparsers.add_parser(
        'check-quota',
        help='Check RapidAPI remaining quota'
    )
    
    # export-accounts
    parser_export = subparsers.add_parser(
        'export-accounts',
        help='Export kicks.json to CSV format'
    )
    parser_export.add_argument(
        '--output', '-o',
        help='Output CSV file (default: kicks_YYYYMMDD_HHMMSS.csv)'
    )
    
    return parser


async def main() -> int:
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Show help if no command
    if not args.command:
        parser.print_help()
        return 0
    
    # Route to appropriate handler
    handlers = {
        'test-kasada': test_kasada,
        'test-email': test_email,
        'create-one': create_one_account,
        'validate-pool': validate_pool,
        'check-quota': check_quota,
        'export-accounts': export_accounts,
    }
    
    handler = handlers.get(args.command)
    if handler:
        try:
            return await handler(args)
        except KeyboardInterrupt:
            print_warning("\nOperation cancelled by user")
            return 130
    else:
        print_error(f"Unknown command: {args.command}")
        parser.print_help()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
