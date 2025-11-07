#!/usr/bin/env python3
"""
Botrix Setup Verification Script
Verifies all required files and dependencies are in place
"""
import os
import sys
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def check_file(filepath, required=True):
    """Check if file exists"""
    exists = Path(filepath).exists()
    status = f"{Colors.GREEN}✓{Colors.RESET}" if exists else f"{Colors.RED}✗{Colors.RESET}"
    req_text = "REQUIRED" if required else "OPTIONAL"
    print(f"{status} {filepath:<40} [{req_text}]")
    return exists or not required

def check_import(module_name):
    """Check if Python module can be imported"""
    try:
        __import__(module_name.replace('-', '_'))
        print(f"{Colors.GREEN}✓{Colors.RESET} {module_name:<40} [INSTALLED]")
        return True
    except ImportError:
        print(f"{Colors.RED}✗{Colors.RESET} {module_name:<40} [MISSING]")
        return False

print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
print(f"{Colors.CYAN}{Colors.BOLD}{'BOTRIX SETUP VERIFICATION':^60}{Colors.RESET}")
print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

all_checks = []

# Python Dependencies
print(f"{Colors.BOLD}Python Dependencies:{Colors.RESET}")
all_checks.append(check_import('aiohttp'))
all_checks.append(check_import('dotenv'))
all_checks.append(check_import('redis'))
all_checks.append(check_import('pytest'))
all_checks.append(check_import('pytest_asyncio'))
all_checks.append(check_import('pytest_cov'))

# Core Files
print(f"\n{Colors.BOLD}Core Files:{Colors.RESET}")
all_checks.append(check_file('workers/aiocurl.py'))
all_checks.append(check_file('workers/worker_daemon.py'))
all_checks.append(check_file('workers/account_creator.py'))
all_checks.append(check_file('workers/kasada_solver.py'))
all_checks.append(check_file('workers/email_handler.py'))
all_checks.append(check_file('workers/cli.py'))
all_checks.append(check_file('workers/config.py'))
all_checks.append(check_file('workers/utils.py'))

# Configuration
print(f"\n{Colors.BOLD}Configuration:{Colors.RESET}")
all_checks.append(check_file('.env'))
all_checks.append(check_file('requirements.txt'))

# Data Files
print(f"\n{Colors.BOLD}Data Files:{Colors.RESET}")
all_checks.append(check_file('shared/livelive.txt'))
all_checks.append(check_file('shared/kicks.json'))

# Backend
print(f"\n{Colors.BOLD}Backend:{Colors.RESET}")
all_checks.append(check_file('backend/main.go'))
all_checks.append(check_file('backend/go.mod'))

# Docker
print(f"\n{Colors.BOLD}Docker:{Colors.RESET}")
all_checks.append(check_file('docker-compose.yml'))
all_checks.append(check_file('Dockerfile.worker'))

# Summary
print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
print(f"{Colors.CYAN}{Colors.BOLD}{'SUMMARY':^60}{Colors.RESET}")
print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

total = len(all_checks)
passed = sum(all_checks)
failed = total - passed

print(f"Total Checks: {total}")
print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
if failed > 0:
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")

percentage = (passed / total) * 100

if percentage == 100:
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED!{Colors.RESET}")
    print(f"{Colors.GREEN}System is ready to use.{Colors.RESET}\n")
    sys.exit(0)
elif percentage >= 90:
    print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ MOST CHECKS PASSED ({percentage:.0f}%){Colors.RESET}")
    print(f"{Colors.YELLOW}Review failures above and fix before proceeding.{Colors.RESET}\n")
    sys.exit(1)
else:
    print(f"\n{Colors.RED}{Colors.BOLD}✗ SETUP INCOMPLETE ({percentage:.0f}%){Colors.RESET}")
    print(f"{Colors.RED}Multiple checks failed. Please fix issues above.{Colors.RESET}\n")
    sys.exit(2)
