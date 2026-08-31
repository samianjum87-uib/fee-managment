#!/usr/bin/env python3
"""
axis_quote_fixer.py - Fix broken quotes and duplicate decorators in staff_portal.py.

Usage:
    python axis_quote_fixer.py [--dry-run] [--verbose] [--target-dir PATH]
"""

import sys
import re
from pathlib import Path
from datetime import datetime

TARGET_FILE = "axis_saas/views/staff_portal.py"

# The exact broken string (with backslashes as they appear in the file)
BROKEN_QUOTE = "request.session[\\'staff_session_token\\']"
CORRECT_QUOTE = "request.session['staff_session_token']"

# Patterns for duplicate decorator removal
DECORATOR_PATTERN = re.compile(
    r'(@require_staff_login\s+@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_staff_login\s+@require_http_methods\(\[\'POST\'\]\)',
    re.DOTALL | re.MULTILINE
)
DECORATOR_REPLACE = r'\1'

DECORATOR2_PATTERN = re.compile(
    r'(@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_http_methods\(\[\'POST\'\]\)',
    re.DOTALL | re.MULTILINE
)
DECORATOR2_REPLACE = r'\1'


def fix_file(target_dir, dry_run=False, verbose=False):
    full_path = target_dir / TARGET_FILE
    if not full_path.exists():
        print(f"Error: {full_path} not found.")
        return False

    try:
        content = full_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Failed to read {full_path}: {e}")
        return False

    original = content
    changes = []

    # 1. Fix the broken quotes using string replacement (exact match)
    if BROKEN_QUOTE in content:
        content = content.replace(BROKEN_QUOTE, CORRECT_QUOTE)
        changes.append("Replaced broken staff_session_token assignment")
        if verbose:
            print("Fixed broken quotes")
    else:
        if verbose:
            print("Broken quotes not found (already fixed?)")

    # 2. Remove duplicate decorators for registration_verify
    new_content, count = DECORATOR_PATTERN.subn(DECORATOR_REPLACE, content)
    if count:
        content = new_content
        changes.append(f"Removed {count} duplicate decorator block(s) for registration_verify")
        if verbose:
            print(f"Removed {count} duplicate decorators")

    # 3. Remove duplicate decorators for authentication endpoints
    new_content, count = DECORATOR2_PATTERN.subn(DECORATOR2_REPLACE, content)
    if count:
        content = new_content
        changes.append(f"Removed {count} duplicate decorator block(s) for authentication endpoints")
        if verbose:
            print(f"Removed {count} duplicate decorators")

    if content == original:
        print("No changes needed.")
        return True

    if dry_run:
        print("Dry run: would write changes to", full_path)
        if verbose:
            print("--- Original (first 500 chars)")
            print(original[:500])
            print("--- New (first 500 chars)")
            print(content[:500])
        return True

    try:
        full_path.write_text(content, encoding='utf-8')
        print("Successfully updated", full_path)
        for change in changes:
            print(" -", change)
        return True
    except Exception as e:
        print(f"Failed to write {full_path}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix broken quotes and duplicate decorators in staff_portal.py.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying.")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output.")
    parser.add_argument("--target-dir", default=".", help="Project root directory (default: current directory).")
    args = parser.parse_args()

    target_dir = Path(args.target_dir).resolve()
    if not target_dir.is_dir():
        print(f"Error: {target_dir} is not a valid directory.")
        sys.exit(1)

    success = fix_file(target_dir, dry_run=args.dry_run, verbose=args.verbose)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
