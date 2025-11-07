# Kick.com Account Generator

A Python-based account generator for Kick.com with Kasada protection bypass.

## Project Structure

```
Botrix/
├── workers/                      # Main application modules
│   ├── __init__.py
│   ├── account_creator.py        # Account creation orchestrator
│   ├── kasada_solver.py          # Kasada bypass solver
│   ├── email_handler.py          # Email verification & pool management
│   ├── config.py                 # Environment configuration
│   ├── utils.py                  # Logger and utilities
│   └── cli.py                    # Command-line interface
├── backend/                      # Go backend API
│   ├── main.go                   # Application entry point
│   ├── config/                   # Configuration management
│   │   └── config.go
│   ├── models/                   # Data models
│   │   ├── account.go
│   │   └── job.go
│   ├── services/                 # Business logic
│   │   ├── database.go
│   │   └── queue.go
│   ├── handlers/                 # HTTP handlers
│   │   ├── health.go
│   │   └── accounts.go
│   ├── go.mod                    # Go dependencies
│   ├── Makefile                  # Build automation
│   ├── .air.toml                 # Hot reload config
│   ├── README.md                 # Backend docs
│   └── QUICKSTART.md             # Quick start guide
├── tests/                        # Comprehensive test suite (58+ tests)
│   ├── conftest.py               # Shared fixtures
│   ├── test_kasada.py            # Kasada solver tests
│   ├── test_email.py             # Email handler tests
│   ├── test_account_creator.py   # Account creator tests
│   └── test_integration.py       # Integration tests
├── shared/                       # Data files
│   ├── livelive.txt              # Email pool (email:password)
│   └── kicks.json                # Generated accounts
├── logs/                         # Application logs
│   └── kick_generator_*.log      # Daily rotating logs
├── cli.py                        # CLI wrapper script
├── main.py                       # Batch account creation
├── quickstart.py                 # Setup verification
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Test configuration
├── run_tests.ps1                 # Test runner script
├── .env.example                  # Environment template
├── .gitignore                    # Git exclusions
├── README.md                     # Main documentation
├── TESTING.md                    # Test suite documentation
├── CLI_DOCUMENTATION.md          # CLI usage guide
├── PROJECT_STATUS.md             # Complete project overview
└── NEXT_STEPS.md                 # Setup checklist
```

## Installation

### Python Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Botrix
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```env
   RAPIDAPI_KEY=your_actual_rapidapi_key_here
   IMAP_SERVER=imap.zmailservice.com
   IMAP_PORT=993
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

### Go Backend Setup (Optional)

The Go backend provides a REST API for managing account creation jobs:

1. **Install Go 1.21+**
   - Download from https://golang.org/dl/

2. **Install dependencies**
   ```powershell
   cd backend
   go mod download
   ```

3. **Start Redis**
   ```powershell
   # Using Docker
   docker run -d -p 6379:6379 redis:alpine
   
   # Or install Redis locally
   ```

4. **Run the backend**
   ```powershell
   # Using Make
   make run
   
   # Or directly
   go run main.go
   ```

See **[backend/QUICKSTART.md](backend/QUICKSTART.md)** for detailed setup instructions.

## KasadaSolver Module

### Features

- ✅ **Retry Logic**: 3 attempts with exponential backoff (2s, 4s, 8s)
- ✅ **Timeout Handling**: 30-second timeout per request
- ✅ **Rate Limiting**: Enforces 1 request/second for free tier
- ✅ **Test Mode**: Returns mock data without API calls
- ✅ **Detailed Logging**: Colored console output + file logging
- ✅ **Error Handling**: Custom exceptions for different failure modes
- ✅ **Async Context Manager**: Clean resource management

### Usage

#### Basic Usage

```python
import os
from workers.kasada_solver import KasadaSolver

# Initialize solver
solver = KasadaSolver(api_key=os.getenv("RAPIDAPI_KEY"))

# Solve Kasada challenge
headers = await solver.solve(
    method="POST",
    fetch_url="https://kick.com/api/v1/signup/send/email"
)

# Use headers in your request
# headers will contain: x-kpsdk-cd, x-kpsdk-ct, user-agent, cookie

await solver.close()
```

#### Using Context Manager (Recommended)

```python
async with KasadaSolver(api_key=os.getenv("RAPIDAPI_KEY")) as solver:
    headers = await solver.solve(
        method="POST",
        fetch_url="https://kick.com/api/v1/signup/send/email"
    )
    # Automatically closes when done
```

#### Test Mode (Development)

```python
# Use test_mode=True to get mock data without API calls
solver = KasadaSolver(api_key="any_key", test_mode=True)
headers = await solver.solve(method="POST", fetch_url="https://kick.com/test")
# Returns mock headers instantly
```

### Error Handling

```python
from workers.kasada_solver import (
    KasadaSolver,
    KasadaSolverError,
    InvalidAPIKeyError,
    RateLimitError,
    TimeoutError
)

try:
    async with KasadaSolver(api_key=api_key) as solver:
        headers = await solver.solve(method="POST", fetch_url=url)
        
except InvalidAPIKeyError:
    print("Your API key is invalid or missing")
    
except RateLimitError:
    print("Rate limit exceeded - please wait or upgrade your plan")
    
except TimeoutError:
    print("Request timed out after 30 seconds")
    
except KasadaSolverError as e:
    print(f"Solver error: {e}")
```

### API Parameters

#### `KasadaSolver.__init__(api_key, test_mode=False)`
- `api_key` (str): Your RapidAPI key for Kasada solver
- `test_mode` (bool): If True, returns mock data without API calls

#### `KasadaSolver.solve(method="POST", fetch_url="")`
- `method` (str): HTTP method - "GET", "POST", "PUT", or "DELETE"
- `fetch_url` (str): Target URL that requires Kasada bypass
- **Returns**: Dict containing Kasada headers

### Configuration

The module uses these constants (can be customized if needed):

```python
MAX_RETRIES = 3              # Number of retry attempts
TIMEOUT_SECONDS = 30         # Request timeout
RATE_LIMIT_DELAY = 1.0       # Delay between requests (seconds)
```

## EmailVerifier & HotmailPool Modules

### Features

**EmailVerifier:**
- ✅ **IMAP Protocol**: Connects to any IMAP server
- ✅ **Polling Mechanism**: Configurable timeout and poll interval
- ✅ **Smart Code Extraction**: Multiple regex patterns for verification codes
- ✅ **Error Handling**: Graceful handling of IMAP errors
- ✅ **Async Support**: Fully async with context manager
- ✅ **Detailed Logging**: Track every step of verification

**HotmailPool:**
- ✅ **Email Pool Management**: Load emails from file
- ✅ **Track Usage**: Mark emails as used or failed
- ✅ **Statistics**: Get pool stats (available, used, failed)
- ✅ **Auto-reload**: Reload pool from file
- ✅ **Format Validation**: Validates email format

### Usage

#### EmailVerifier Basic Usage

```python
from workers.email_handler import EmailVerifier

# Create verifier
async with EmailVerifier(
    email_address="your_email@hotmail.com",
    password="your_password",
    imap_server="imap.zmailservice.com",
    imap_port=993
) as verifier:
    # Wait for verification email (90 second timeout, check every 5 seconds)
    code = await verifier.get_verification_code(timeout=90, poll_interval=5)
    print(f"Verification code: {code}")
```

#### HotmailPool Usage

```python
from workers.email_handler import HotmailPool

# Initialize pool from file
pool = HotmailPool(pool_file="shared/livelive.txt")

# Get next available email
email, password = pool.get_next_email()

# After successful use
pool.mark_as_used(email)

# Or if it failed
pool.mark_as_failed(email)

# Get statistics
stats = pool.get_stats()
print(f"Available: {stats['available']}, Used: {stats['used']}")
```

#### Complete Workflow

```python
from workers.email_handler import EmailVerifier, HotmailPool

# Initialize pool
pool = HotmailPool(pool_file="shared/livelive.txt")

# Get email from pool
email, password = pool.get_next_email()

# Use it for verification
async with EmailVerifier(email, password) as verifier:
    # Trigger Kick.com to send verification email
    # ... your account creation code here ...
    
    # Wait for and extract code
    code = await verifier.get_verification_code(timeout=90)
    
    # Use code to verify account
    # ... your verification code here ...
    
    # Mark as successfully used
    pool.mark_as_used(email)
```

### Email Pool File Format

Create `shared/livelive.txt` with this format:

```
# Email Pool - Format: email:password
email1@hotmail.com:password123
email2@outlook.com:securePass456
email3@live.com:myPassword789

# Comments start with #
# Blank lines are ignored
```

### Error Handling

```python
from workers.email_handler import (
    EmailVerifier,
    HotmailPool,
    IMAPLoginError,
    NoEmailReceivedError,
    EmailPoolEmptyError,
    MalformedEmailFormatError
)

try:
    pool = HotmailPool()
    email, password = pool.get_next_email()
    
    async with EmailVerifier(email, password) as verifier:
        code = await verifier.get_verification_code(timeout=90)
        
except EmailPoolEmptyError:
    print("No emails available in pool")
    
except IMAPLoginError:
    print("Failed to login to IMAP server")
    pool.mark_as_failed(email)
    
except NoEmailReceivedError:
    print("No verification email received within timeout")
    
except MalformedEmailFormatError:
    print("Email file has invalid format")
```

### API Reference

#### EmailVerifier

**`__init__(email_address, password, imap_server, imap_port)`**
- `email_address` (str): Email to check for verification
- `password` (str): Email password
- `imap_server` (str): IMAP server address (default: imap.zmailservice.com)
- `imap_port` (int): IMAP port (default: 993)

**`async get_verification_code(timeout=90, poll_interval=5)`**
- `timeout` (int): Max seconds to wait for email
- `poll_interval` (int): Seconds between checks
- **Returns**: Verification code (str)

**`connect()` / `disconnect()`**
- Manually manage IMAP connection

#### HotmailPool

**`__init__(pool_file="shared/livelive.txt")`**
- `pool_file` (str): Path to email pool file

**`get_next_email()`**
- **Returns**: Tuple of (email, password)

**`mark_as_used(email)`**
- Mark email as successfully used

**`mark_as_failed(email)`**
- Mark email as failed and remove from pool

**`get_stats()`**
- **Returns**: Dict with pool statistics

**`reload()`**
- Reload emails from file

### Verification Code Patterns

The EmailVerifier recognizes these code formats:
- `code: 123456`
- `verification: 123456`
- `confirm: 123456`
- `your code is: 123456`
- Any 4-8 digit number in subject/body

### Configuration

The module uses these constants (can be customized if needed):

```python
KICK_EMAIL_SENDER = "noreply@email.kick.com"  # Email sender to search for
CODE_PATTERNS = [...]  # Regex patterns for code extraction
```

### Logging

The module provides detailed colored logging:

- **🔵 INFO**: General operations (cyan)
- **🟡 WARNING**: Retry attempts, timeouts (yellow)
- **🔴 ERROR**: Failed requests, invalid keys (red)
- **⚪ DEBUG**: Detailed request/response data (gray)

Logs are saved to `logs/kick_generator_YYYYMMDD.log`

## Running Tests

### Quick Test Execution

Use the PowerShell test runner for easy testing:

```powershell
# Run all tests
.\run_tests.ps1

# Run specific test categories
.\run_tests.ps1 unit              # Unit tests only
.\run_tests.ps1 integration       # Integration tests only
.\run_tests.ps1 kasada           # Kasada module tests
.\run_tests.ps1 email            # Email handler tests
.\run_tests.ps1 account          # Account creator tests

# Run with coverage reporting
.\run_tests.ps1 --coverage        # Generates htmlcov/index.html
.\run_tests.ps1 -c                # Short form

# Run with verbose output
.\run_tests.ps1 --verbose
.\run_tests.ps1 -v
```

### Manual pytest Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_kasada.py
pytest tests/test_email.py
pytest tests/test_account_creator.py
pytest tests/test_integration.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=workers --cov-report=html --cov-report=term-missing

# Run specific test markers
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Exclude slow tests

# Run async tests
pytest --asyncio-mode=auto
```

### Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── test_kasada.py             # KasadaSolver tests (20+ test cases)
├── test_email.py              # EmailVerifier & HotmailPool tests (20+ test cases)
├── test_account_creator.py    # KickAccountCreator tests (10+ test cases)
└── test_integration.py        # End-to-end integration tests (8+ test cases)
```

### Test Coverage

The test suite includes:

**KasadaSolver Tests (`test_kasada.py`):**
- ✅ Initialization tests
- ✅ Test mode functionality
- ✅ Mock API response handling (200, 401, 429, 500 status codes)
- ✅ Retry logic with exponential backoff
- ✅ Rate limiting verification
- ✅ Timeout handling
- ✅ Error propagation
- ✅ Context manager functionality

**Email Handler Tests (`test_email.py`):**
- ✅ EmailVerifier IMAP connection (mocked)
- ✅ Email code extraction from subject/body
- ✅ Multiple code pattern matching
- ✅ Timeout behavior
- ✅ Connection failure handling
- ✅ HotmailPool email management
- ✅ Pool statistics and usage tracking
- ✅ Concurrent access patterns
- ✅ Integration workflow

**Account Creator Tests (`test_account_creator.py`):**
- ✅ Complete workflow with mocked services
- ✅ Username/password/birthdate generation
- ✅ Email pool integration
- ✅ Kasada integration
- ✅ Error handling for each step
- ✅ Account saving to JSON
- ✅ Failed email tracking

**Integration Tests (`test_integration.py`):**
- ✅ Complete dry-run workflow (all components)
- ✅ Kasada failure scenarios
- ✅ Email verification timeout
- ✅ Registration failure (username taken)
- ✅ Multiple account creation
- ✅ Error propagation through stack
- ✅ Pool exhaustion handling
- ✅ Component initialization verification

### Shared Fixtures (`conftest.py`)

Available pytest fixtures:
- `mock_env_vars` - Mock environment variables
- `test_config` - Test configuration object
- `temp_email_pool` - Temporary email pool file
- `temp_output_file` - Temporary output JSON file
- `mock_imap_connection` - Mocked IMAP connection
- `mock_verification_email` - Sample verification email
- `mock_kasada_response` - Successful Kasada response
- `mock_kick_api_responses` - Kick.com API responses
- `mock_aiohttp_session` - Mocked aiohttp session
- `suppress_logging` - Suppress log output during tests

### Test Markers

Custom markers for test organization:
- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.integration` - Integration tests for multiple components
- `@pytest.mark.slow` - Tests that take a long time
- `@pytest.mark.network` - Tests requiring network (should be mocked)

### Mocking Strategy

All external dependencies are mocked:
- ✅ **IMAP Connections**: `imaplib.IMAP4_SSL` fully mocked
- ✅ **HTTP Requests**: `aiohttp.ClientSession` mocked with AsyncMock
- ✅ **File System**: Uses `tmp_path` fixture for temporary files
- ✅ **Environment**: `monkeypatch` for env vars
- ✅ **Kasada API**: Mock responses for all status codes
- ✅ **Kick.com API**: Mock responses for all endpoints

### Coverage Reporting

After running tests with coverage:

```powershell
# View coverage report in browser
.\run_tests.ps1 --coverage
# Then open htmlcov/index.html

# View coverage in terminal
pytest --cov=workers --cov-report=term-missing

# Generate multiple report formats
pytest --cov=workers --cov-report=html --cov-report=xml --cov-report=term
```

## Usage

### CLI Tool (Recommended)

The project includes a comprehensive CLI for testing and operations:

```bash
# Test Kasada solver
python cli.py test-kasada --dry-run        # Test with mocks
python cli.py test-kasada --verbose        # Test with real API

# Test email/IMAP connection
python cli.py test-email user@hotmail.com password123

# Create single account with detailed logging
python cli.py create-one --verbose
python cli.py create-one --dry-run         # Test mode

# Validate email pool
python cli.py validate-pool                # Check format
python cli.py validate-pool --verbose      # Also test IMAP

# Check RapidAPI quota
python cli.py check-quota

# Export accounts to CSV
python cli.py export-accounts
python cli.py export-accounts --output my_accounts.csv
```

**Global Flags**:
- `--verbose`, `-v`: Enable detailed output
- `--dry-run`: Use mocks instead of real API calls

### Main Script (Batch Creation)

1. **Add email accounts to pool**
   ```bash
   # Edit shared/livelive.txt
   email1@hotmail.com:password123
   email2@outlook.com:password456
   ```

2. **Run in test mode** (no real API calls)
   ```bash
   python main.py --count 1 --test-mode
   ```

3. **Run in production mode**
   ```bash
   # Set RAPIDAPI_KEY in .env first
   python main.py --count 5
   ```

### Command Line Options

```bash
# Create 5 accounts
python main.py --count 5

# Create accounts in test mode (no real API calls)
python main.py --count 10 --test-mode

# Create single account with custom credentials
python main.py --username MyUsername --password MyPass123

# Create accounts with custom delay between each
python main.py --count 3 --delay 5

# Show help
python main.py --help
```

### Programmatic Usage

```python
import asyncio
from workers.account_creator import KickAccountCreator
from workers.kasada_solver import KasadaSolver
from workers.email_handler import HotmailPool

async def create_accounts():
    pool = HotmailPool(pool_file="shared/livelive.txt")
    
    async with KasadaSolver(api_key="your_key", test_mode=False) as kasada:
        async with KickAccountCreator(
            email_pool=pool,
            kasada_solver=kasada
        ) as creator:
            # Create account with auto-generated credentials
            result = await creator.create_account()
            
            # Or with custom credentials
            result = await creator.create_account(
                username="MyUsername",
                password="MyPassword123"
            )
            
            if result['success']:
                print(f"Created: {result['username']}")

asyncio.run(create_accounts())
```

## Account Creation Workflow

The complete account creation process:

1. **Get Email** - Retrieve email from HotmailPool
2. **Solve Kasada** - Bypass Kasada protection using RapidAPI
3. **Request Verification** - Send verification email to the account
4. **Wait for Code** - Poll IMAP server for verification email (90s timeout)
5. **Verify Code** - Submit verification code to Kick.com
6. **Register Account** - Complete registration with username/password
7. **Save Account** - Save to `shared/kicks.json`

## KickAccountCreator Module

### Features

- ✅ **Complete Workflow**: End-to-end account creation
- ✅ **Retry Logic**: Automatic retries for transient failures
- ✅ **Rate Limiting**: Configurable delays between requests
- ✅ **Error Handling**: Comprehensive error handling for all failure modes
- ✅ **Auto-save**: Saves successful accounts to JSON file
- ✅ **Pool Management**: Marks emails as used/failed automatically
- ✅ **Detailed Logging**: Logs every step with timestamps
- ✅ **Random Generation**: Username, password, birthdate generators

### Helper Functions

```python
from workers.account_creator import (
    generate_random_username,
    generate_random_password,
    generate_random_birthdate
)

# Generate random username (letters, numbers, underscores)
username = generate_random_username(length=10)  # e.g., "aB3_xY9z2K"

# Generate secure password
password = generate_random_password(length=16)  # Mixed chars

# Generate birthdate (18-35 years old)
birthdate = generate_random_birthdate()  # e.g., "1995-06-15"
```

### Error Handling

```python
from workers.account_creator import (
    KickAccountCreator,
    AccountCreationError,
    VerificationFailedError,
    RegistrationFailedError
)

try:
    result = await creator.create_account()
    
    if not result['success']:
        error_type = result['error']
        
        if error_type == 'Email verification failed':
            # Email account is invalid or IMAP login failed
            pass
        elif error_type == 'Kasada challenge failed':
            # Kasada solver failed (check API key/quota)
            pass
        elif error_type == 'Verification failed':
            # Email code verification failed
            pass
        elif error_type == 'Registration failed':
            # Account registration failed (username taken?)
            pass

except Exception as e:
    print(f"Unexpected error: {e}")
```

### Configuration

```python
class KickAccountCreator:
    # API Endpoints
    KICK_API_BASE = "https://kick.com/api"
    SEND_CODE_ENDPOINT = f"{KICK_API_BASE}/v1/signup/send/email"
    VERIFY_CODE_ENDPOINT = f"{KICK_API_BASE}/v1/signup/verify/email"
    REGISTER_ENDPOINT = f"{KICK_API_BASE}/v1/signup/register"
    
    # Rate Limiting
    REQUEST_DELAY = 2.0        # Seconds between requests
    RETRY_ATTEMPTS = 3         # Number of retries
    RETRY_DELAY = 5.0          # Delay between retries
```

### Output Format

Successful accounts are saved to `shared/kicks.json`:

```json
[
  {
    "success": true,
    "email": "test@hotmail.com",
    "username": "RandomUser123",
    "password": "SecurePass!@#456",
    "birthdate": "1995-06-15",
    "verification_code": "123456",
    "account_data": { ... },
    "created_at": "2025-11-07T10:30:00.123456"
  }
]
```

## Documentation

- **[README.md](README.md)** - Main project documentation (this file)
- **[CLI_DOCUMENTATION.md](CLI_DOCUMENTATION.md)** - Complete CLI usage guide
- **[backend/README.md](backend/README.md)** - Go backend API documentation
- **[backend/QUICKSTART.md](backend/QUICKSTART.md)** - Backend quick start guide
- **[TESTING.md](TESTING.md)** - Test suite documentation (58+ tests)
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Complete project overview
- **[NEXT_STEPS.md](NEXT_STEPS.md)** - Setup and installation checklist

## Examples

Run the example files to see modules in action:

```bash
# Kasada solver examples
python example_kasada_usage.py

# Email handler examples
python example_email_handler.py

# Account creator examples
python example_account_creator.py

# Complete integration workflow
python example_integration.py
```

These demonstrate:
1. Basic usage patterns
2. Context manager usage
3. Error handling
4. Multiple requests with rate limiting
5. Live API calls (requires valid API key)

## Dependencies

- **aiohttp>=3.8.0**: Async HTTP client
- **python-dotenv>=1.0.0**: Environment variable management
- **redis>=4.0.0**: Redis client (for future features)
- **pytest>=7.4.0**: Testing framework
- **pytest-asyncio>=0.21.0**: Async test support
- **pytest-cov>=4.1.0**: Coverage reporting

Install all dependencies:
```bash
pip install -r requirements.txt
```

## Reference

Based on: [wezaxy/kick-account-generator](https://github.com/wezaxy/kick-account-generator)

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Ensure all tests pass (`.\run_tests.ps1 --coverage`)
5. Update documentation
6. Submit a pull request

## Support

For issues or questions:
- Review **[CLI_DOCUMENTATION.md](CLI_DOCUMENTATION.md)** for CLI usage
- Check **[TESTING.md](TESTING.md)** for test information
- Review example files in project root
- Run tests to verify setup: `.\run_tests.ps1`
- Enable debug logging for detailed output
- Use `--verbose` flag with CLI commands
