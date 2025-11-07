#!/usr/bin/env python3
"""Verify Botrix setup is complete"""
import os
import sys
from pathlib import Path

def check_file(filepath, required=True):
    exists = Path(filepath).exists()
    status = "✓" if exists else "✗"
    req = "REQUIRED" if required else "OPTIONAL"
    print(f"{status} {filepath} [{req}]")
    return exists or not required

print("=" * 60)
print("BOTRIX SETUP VERIFICATION")
print("=" * 60)

all_ok = True

print("\nCore Files:")
all_ok &= check_file("workers/aiocurl.py")
all_ok &= check_file("workers/worker_daemon.py")
all_ok &= check_file("workers/account_creator.py")
all_ok &= check_file(".env")
all_ok &= check_file("requirements.txt")

print("\nShared Data:")
all_ok &= check_file("shared/livelive.txt")
all_ok &= check_file("shared/kicks.json")

print("\nBackend:")
all_ok &= check_file("backend/main.go")
all_ok &= check_file("backend/data/", required=False)
all_ok &= check_file("backend/logs/", required=False)

print("\n" + "=" * 60)
if all_ok:
    print("✓ ALL CHECKS PASSED - System ready!")
    sys.exit(0)
else:
    print("✗ SOME CHECKS FAILED - Review above")
    sys.exit(1)
