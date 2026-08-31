#!/usr/bin/env python3
"""
axis_import_fixer.py - Fix missing redirect import in staff_tenant_middleware.py.

This script adds the missing `from django.shortcuts import redirect` import
to axis_saas/middleware/staff_tenant_middleware.py, resolving the NameError.

Usage:
    python axis_import_fixer.py [--dry-run] [--verbose] [--target-dir PATH]

Options:
    --dry-run       Preview changes without applying.
    --verbose       Show detailed output.
    --target-dir    Project root directory (default: current directory).
"""

import re
import sys
from pathlib import Path
from datetime import datetime

MIDDLEWARE_FILE = "axis_saas/middleware/staff_tenant_middleware.py"
IMPORT_LINE = "from django.shortcuts import redirect"


def fix_middleware(target_dir, dry_run=False, verbose=False):
    full_path = target_dir / MIDDLEWARE_FILE
    if not full_path.exists():
        print(f"Error: {full_path} not found.")
        return False

    try:
        content = full_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Failed to read {full_path}: {e}")
        return False

    original = content

    # Check if the import already exists
    if IMPORT_LINE in content:
        if verbose:
            print(f"Import '{IMPORT_LINE}' already present in {MIDDLEWARE_FILE}.")
        return True

    # Find the last import line to insert after
    import_lines = re.findall(r'^from .* import .*$', content, re.MULTILINE)
    if import_lines:
        last_import = import_lines[-1]
        pos = content.rfind(last_import) + len(last_import)
        # Insert a newline and the import
        new_content = content[:pos] + "\n" + IMPORT_LINE + content[pos:]
        if verbose:
            print(f"Inserting import after line: {last_import}")
    else:
        # No imports found, insert at the top after any shebang or docstring
        # We'll just prepend with a newline
        new_content = IMPORT_LINE + "\n\n" + content
        if verbose:
            print("No imports found; inserting at top.")

    if dry_run:
        print("Dry run: would write changes to", full_path)
        if verbose:
            print("--- Original (first 500 chars)")
            print(original[:500])
            print("--- New (first 500 chars)")
            print(new_content[:500])
        return True

    try:
        full_path.write_text(new_content, encoding='utf-8')
        print(f"Successfully added import to {MIDDLEWARE_FILE}.")
        return True
    except Exception as e:
        print(f"Failed to write {full_path}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix missing redirect import in staff_tenant_middleware.py.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying.")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output.")
    parser.add_argument("--target-dir", default=".", help="Project root directory (default: current directory).")
    args = parser.parse_args()

    target_dir = Path(args.target_dir).resolve()
    if not target_dir.is_dir():
        print(f"Error: {target_dir} is not a valid directory.")
        sys.exit(1)

    success = fix_middleware(target_dir, dry_run=args.dry_run, verbose=args.verbose)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
