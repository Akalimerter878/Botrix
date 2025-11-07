"""
CLI wrapper script - shortcut for python workers/cli.py
"""

import sys
import subprocess
from pathlib import Path

# Get the project root
project_root = Path(__file__).parent

# Run the CLI module
cli_path = project_root / "workers" / "cli.py"
result = subprocess.run([sys.executable, str(cli_path)] + sys.argv[1:])

sys.exit(result.returncode)
