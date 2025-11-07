# CLI Documentation

## Overview

The Botrix CLI (`cli.py`) provides a comprehensive command-line interface for manual testing and operations. All commands support `--verbose` and `--dry-run` flags.

## Installation

Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

## Global Flags

These flags work with all commands:

- `--verbose`, `-v`: Enable detailed output with extra logging
- `--dry-run`: Use mock data instead of real API calls (for testing)

## Commands

### 1. test-kasada

Test the Kasada solver with real or mock API.

**Usage**:
```bash
# Test with mocks (no API key required)
python cli.py test-kasada --dry-run

# Test with real API
python cli.py test-kasada

# Test with verbose output
python cli.py test-kasada --verbose
```

**What it does**:
- Initializes the Kasada solver
- Solves a challenge for the Kick.com signup endpoint
- Displays received headers
- Verifies all required headers are present

**Output Example**:
```
Testing Kasada Solver
=====================

ℹ Solver initialized (test_mode=False)
✓ Kasada challenge solved successfully!
ℹ Received 4 headers
✓ All required headers present
```

**Verbose Output**:
```
Testing Kasada Solver
=====================

ℹ Solver initialized (test_mode=False)
ℹ Solving challenge for: https://kick.com/api/v1/signup/send/email
ℹ Method: POST
✓ Kasada challenge solved successfully!
ℹ Received headers:
  x-kpsdk-ct: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  x-kpsdk-cd: 4f2e8a9c1d3b7e...
  user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...
  cookie: session=abc123...
✓ All required headers present
```

**Exit Codes**:
- `0`: Success
- `1`: Error (invalid API key, network error, etc.)

---

### 2. test-email

Test IMAP connection and email code retrieval.

**Usage**:
```bash
# Basic test
python cli.py test-email user@hotmail.com password123

# With verbose output
python cli.py test-email user@hotmail.com password123 --verbose
```

**Arguments**:
- `email`: Email address to test
- `password`: Email password

**What it does**:
- Connects to IMAP server
- Checks for Kick verification emails
- Attempts to extract verification code (10-second timeout)
- Reports success even if no emails found (connection test)

**Output Example**:
```
Testing Email Handler
=====================

ℹ Testing email: user@hotmail.com
ℹ IMAP server: imap.zmailservice.com:993
ℹ Connecting to IMAP server...
✓ Connected to IMAP server successfully!
ℹ Checking inbox for Kick verification emails...
⚠ No verification email found (timeout after 10 seconds)
ℹ This is normal if there are no recent verification emails
✓ IMAP connection is working correctly
```

**With Existing Email**:
```
Testing Email Handler
=====================

ℹ Testing email: user@hotmail.com
ℹ IMAP server: imap.zmailservice.com:993
ℹ Connecting to IMAP server...
✓ Connected to IMAP server successfully!
ℹ Checking inbox for Kick verification emails...
✓ Found verification code: 123456
```

**Exit Codes**:
- `0`: Success (connection works)
- `1`: Error (invalid credentials, server error)

---

### 3. create-one

Create a single account with detailed logging.

**Usage**:
```bash
# Create account with real API
python cli.py create-one

# Create account with verbose output
python cli.py create-one --verbose

# Test mode (no real API calls)
python cli.py create-one --dry-run
```

**What it does**:
- Checks email pool availability
- Initializes Kasada solver and account creator
- Creates one account through complete workflow
- Displays detailed account information
- Saves account to `shared/kicks.json`

**Output Example**:
```
Creating Single Account
=======================

ℹ Initializing components...
ℹ Email pool loaded: 5 available, 3 used
✓ Kasada solver initialized
✓ Account creator initialized

ℹ Starting account creation workflow...
ℹ This may take 2-5 minutes...

✓ Account created successfully!
ℹ 
Account details:
  Username: test_user_abc123
  Email: user1@hotmail.com
  Password: SecureP@ss456!
  Verification Code: 123456

ℹ Account saved to: shared/kicks.json
```

**Verbose Output** (additional info):
```
Full account data:
{
  "id": 12345,
  "username": "test_user_abc123",
  "email": "user1@hotmail.com",
  "created_at": "2025-11-07T10:30:00Z"
}
```

**Exit Codes**:
- `0`: Success (account created)
- `1`: Error (pool empty, API error, verification failed, etc.)

**Workflow Steps** (visible in logs):
1. Get email from pool
2. Solve Kasada challenge
3. Send verification email
4. Wait for verification code
5. Verify email code
6. Register account
7. Save account data

---

### 4. validate-pool

Validate email pool format and optionally test IMAP connectivity.

**Usage**:
```bash
# Validate format only
python cli.py validate-pool

# Validate format and test first email
python cli.py validate-pool --verbose
```

**What it does**:
- Checks if `shared/livelive.txt` exists
- Validates format (email:password per line)
- Counts available, used, and failed emails
- (Verbose) Tests IMAP connection for first email

**Output Example**:
```
Validating Email Pool
=====================

ℹ Validating pool file: shared/livelive.txt
✓ Pool file format is valid
ℹ Total emails: 10
ℹ Available: 7
ℹ Used: 2
ℹ Failed: 1
```

**Verbose Output** (additional testing):
```
Validating Email Pool
=====================

ℹ Validating pool file: shared/livelive.txt
✓ Pool file format is valid
ℹ Total emails: 10
ℹ Available: 7
ℹ Used: 2
ℹ Failed: 1

ℹ Testing IMAP connectivity for first email...
ℹ Testing: user1@hotmail.com
✓ IMAP connection successful!
ℹ Inbox contains 15 emails
```

**Exit Codes**:
- `0`: Success (pool is valid)
- `1`: Error (file not found, invalid format, no available emails)

**Pool File Format**:
```
# Email pool - Format: email:password
user1@hotmail.com:password123
user2@outlook.com:password456
user3@live.com:password789

# Comments start with #
# Blank lines are ignored
```

---

### 5. check-quota

Check RapidAPI remaining quota for Kasada solver.

**Usage**:
```bash
# Check quota
python cli.py check-quota

# Check quota with verbose output
python cli.py check-quota --verbose
```

**What it does**:
- Makes a test request to RapidAPI
- Extracts quota information from response headers
- Displays remaining requests and limits

**Output Example**:
```
Checking RapidAPI Quota
=======================

ℹ Checking quota...
✓ API key is valid
ℹ Requests: 450 / 500
```

**Verbose Output**:
```
Checking RapidAPI Quota
=======================

ℹ Checking quota...
✓ API key is valid

ℹ Quota information:
  Request limit: 500
  Requests remaining: 450
  Reset time: 1699372800

ℹ All response headers:
  x-ratelimit-requests-limit: 500
  x-ratelimit-requests-remaining: 450
  x-ratelimit-requests-reset: 1699372800
```

**Exit Codes**:
- `0`: Success (quota checked)
- `1`: Error (invalid API key, network error)

**Note**: Cannot be used with `--dry-run` flag (requires real API key).

---

### 6. export-accounts

Export accounts from `shared/kicks.json` to CSV format.

**Usage**:
```bash
# Export with auto-generated filename
python cli.py export-accounts

# Export to specific file
python cli.py export-accounts --output my_accounts.csv
python cli.py export-accounts -o accounts_backup.csv

# With verbose output (shows preview)
python cli.py export-accounts --verbose
```

**What it does**:
- Reads accounts from `shared/kicks.json`
- Exports to CSV format
- Includes fields: email, username, password, birthdate, verification_code, created_at, success

**Output Example**:
```
Exporting Accounts to CSV
==========================

ℹ Reading accounts from: shared/kicks.json
✓ Loaded 15 accounts
ℹ Exporting to: kicks_20251107_103045.csv
✓ Exported 15 accounts to kicks_20251107_103045.csv
```

**Verbose Output**:
```
Exporting Accounts to CSV
==========================

ℹ Reading accounts from: shared/kicks.json
✓ Loaded 15 accounts
ℹ Exporting to: kicks_20251107_103045.csv
✓ Exported 15 accounts to kicks_20251107_103045.csv

ℹ Preview of first account:
  email: user1@hotmail.com
  username: test_user_abc
  password: SecureP@ss123
  birthdate: 1995-06-15
  verification_code: 123456
  created_at: 2025-11-07T10:30:00.123456
  success: True
```

**CSV Format**:
```csv
email,username,password,birthdate,verification_code,created_at,success
user1@hotmail.com,test_user_abc,SecureP@ss123,1995-06-15,123456,2025-11-07T10:30:00.123456,True
user2@outlook.com,test_user_xyz,AnotherPass456,1992-03-20,789012,2025-11-07T10:35:00.789012,True
```

**Exit Codes**:
- `0`: Success (exported)
- `1`: Error (file not found, JSON parse error)

---

## Common Workflows

### First-Time Setup

```bash
# 1. Validate pool file
python cli.py validate-pool --verbose

# 2. Test Kasada solver
python cli.py test-kasada --dry-run

# 3. Test with real API
python cli.py test-kasada

# 4. Create test account
python cli.py create-one --dry-run --verbose

# 5. Create real account
python cli.py create-one --verbose
```

### Testing IMAP Connectivity

```bash
# Test each email in your pool
python cli.py test-email email1@hotmail.com password123
python cli.py test-email email2@outlook.com password456

# Or validate entire pool
python cli.py validate-pool --verbose
```

### Monitoring API Usage

```bash
# Check quota before batch creation
python cli.py check-quota

# Create accounts
python main.py --count 10

# Check quota again
python cli.py check-quota
```

### Exporting and Backing Up

```bash
# Export all accounts
python cli.py export-accounts --output backup_$(date +%Y%m%d).csv

# Or with verbose preview
python cli.py export-accounts --verbose
```

---

## Exit Codes

All commands use standard exit codes:

- `0`: Success
- `1`: Error (various reasons)
- `130`: User cancelled (Ctrl+C)

Use exit codes in scripts:
```bash
if python cli.py test-kasada; then
    echo "Kasada test passed"
else
    echo "Kasada test failed"
fi
```

---

## Environment Variables

The CLI reads configuration from `.env` file:

```env
RAPIDAPI_KEY=your_rapidapi_key_here
IMAP_SERVER=imap.zmailservice.com
IMAP_PORT=993
POOL_FILE=shared/livelive.txt
OUTPUT_FILE=shared/kicks.json
```

**Required for**:
- `test-kasada` (without --dry-run)
- `create-one` (without --dry-run)
- `check-quota`

**Not required for**:
- `test-email` (uses provided credentials)
- `validate-pool`
- `export-accounts`
- Any command with `--dry-run`

---

## Colored Output

The CLI uses colored output for better readability:

- ✓ **Green**: Success messages
- ✗ **Red**: Error messages
- ℹ **Cyan**: Info messages
- ⚠ **Yellow**: Warning messages

Colors can be disabled by redirecting output:
```bash
python cli.py test-kasada > output.txt 2>&1
```

---

## Error Handling

All commands handle errors gracefully:

```bash
# Invalid credentials
$ python cli.py test-email invalid@email.com wrongpass
✗ IMAP error: [AUTHENTICATIONFAILED] Invalid credentials
ℹ Check your email credentials and IMAP server settings

# Missing API key
$ python cli.py test-kasada
✗ RAPIDAPI_KEY not set in environment
ℹ Either set RAPIDAPI_KEY in .env or use --dry-run flag

# Empty pool
$ python cli.py create-one
✗ No emails available in pool
ℹ Add emails to shared/livelive.txt
```

Use `--verbose` flag for detailed error information including stack traces.

---

## Tips and Tricks

### Quick Testing
```bash
# Test everything without real API calls
python cli.py test-kasada --dry-run
python cli.py create-one --dry-run --verbose
```

### Debugging
```bash
# Enable verbose output for all commands
python cli.py create-one --verbose
python cli.py validate-pool --verbose
python cli.py check-quota --verbose
```

### Automation
```bash
# Script to create and export accounts
python cli.py create-one && \
python cli.py create-one && \
python cli.py create-one && \
python cli.py export-accounts --output batch_$(date +%Y%m%d).csv
```

### Monitoring
```bash
# Check quota periodically
watch -n 60 "python cli.py check-quota"
```

---

## Troubleshooting

### Command Not Found
```bash
# Use Python to run CLI
python cli.py <command>

# Or from workers directory
python workers/cli.py <command>
```

### Import Errors
```bash
# Install dependencies
pip install -r requirements.txt
```

### Permission Errors
```bash
# Ensure files are writable
chmod +w shared/kicks.json
chmod +w shared/livelive.txt
```

### IMAP Errors
- Verify email credentials are correct
- Check IMAP server address in `.env`
- Ensure IMAP is enabled for the email account
- Try logging in via webmail first

### API Errors
- Verify `RAPIDAPI_KEY` is set in `.env`
- Check quota with `python cli.py check-quota`
- Use `--dry-run` flag to test without API calls

---

## Examples

### Complete Testing Workflow
```bash
# 1. Validate setup
python cli.py validate-pool --verbose

# 2. Test Kasada (dry run)
python cli.py test-kasada --dry-run

# 3. Test Kasada (real)
python cli.py test-kasada --verbose

# 4. Test email
python cli.py test-email user@hotmail.com password123

# 5. Create test account
python cli.py create-one --dry-run --verbose

# 6. Create real account
python cli.py create-one --verbose

# 7. Export results
python cli.py export-accounts --output test_accounts.csv
```

### Batch Account Creation
```bash
# Check quota first
python cli.py check-quota

# Create accounts using main script
python main.py --count 10

# Export to CSV
python cli.py export-accounts --output batch_accounts.csv

# Check quota again
python cli.py check-quota
```

---

## Related Documentation

- [README.md](README.md) - Main project documentation
- [TESTING.md](TESTING.md) - Test suite documentation
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Complete project overview
- [NEXT_STEPS.md](NEXT_STEPS.md) - Setup and next steps guide
