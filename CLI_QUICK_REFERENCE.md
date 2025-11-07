# CLI Quick Reference

## Basic Commands

```bash
# Test Kasada solver
python cli.py test-kasada [--dry-run] [--verbose]

# Test email/IMAP
python cli.py test-email <email> <password> [--verbose]

# Create single account
python cli.py create-one [--dry-run] [--verbose]

# Validate pool
python cli.py validate-pool [--verbose]

# Check quota
python cli.py check-quota [--verbose]

# Export accounts
python cli.py export-accounts [--output FILE] [--verbose]
```

## Global Flags

- `--verbose`, `-v` - Detailed output
- `--dry-run` - Use mocks (no real API calls)

## Quick Examples

```bash
# First-time testing
python cli.py validate-pool --verbose
python cli.py test-kasada --dry-run
python cli.py test-email user@hotmail.com pass123

# Create test account
python cli.py create-one --dry-run --verbose

# Create real account
python cli.py create-one --verbose

# Export to CSV
python cli.py export-accounts --output my_accounts.csv

# Check API usage
python cli.py check-quota
```

## Exit Codes

- `0` - Success
- `1` - Error
- `130` - User cancelled (Ctrl+C)

## Color Legend

- ✓ Green - Success
- ✗ Red - Error
- ℹ Cyan - Info
- ⚠ Yellow - Warning

---

For full documentation, see [CLI_DOCUMENTATION.md](CLI_DOCUMENTATION.md)
