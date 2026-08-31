#!/usr/bin/env python3
"""
axis_final_fix.py - Fix UnboundLocalError in staff_tenant_middleware.py.

This script removes the inner import of redirect that shadows the top-level import,
causing UnboundLocalError when redirect is used before assignment.

Usage:
    python axis_final_fix.py [--dry-run] [--verbose] [--target-dir PATH]
"""

import re
import sys
from pathlib import Path
from datetime import datetime

MIDDLEWARE_FILE = "axis_saas/middleware/staff_tenant_middleware.py"

# The line we want to remove: the inner import of redirect inside the if block
INNER_IMPORT = "from django.shortcuts import redirect"

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

    if INNER_IMPORT not in content:
        print(f"Pattern '{INNER_IMPORT}' not found in {full_path}. Already fixed?")
        return True

    new_content = content.replace(INNER_IMPORT, "")
    # Clean up extra whitespace: remove the line entirely, leaving a blank line.
    # We'll replace the exact line with nothing, but we need to also handle indentation.
    # Since it's indented, we can just replace the line with a comment or nothing.
    # We'll replace the line with nothing but keep the newline? Let's just remove the line.
    # We'll use regex to remove the line with its indentation.
    # But simple replace works if we include the newline.
    pattern = re.compile(r'^(\s*)from django\.shortcuts import redirect\s*$', re.MULTILINE)
    new_content, count = pattern.subn('', content)
    if count == 0:
        print("No replacement made.")
        return True

    if dry_run:
        print("Dry run: would write changes to", full_path)
        if verbose:
            print("--- Original (first 500 chars)")
            print(content[:500])
            print("--- New (first 500 chars)")
            print(new_content[:500])
        return True

    try:
        full_path.write_text(new_content, encoding='utf-8')
        print("Successfully updated", full_path)
        print(f"Removed {count} occurrence(s) of inner redirect import.")
        return True
    except Exception as e:
        print(f"Failed to write {full_path}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix UnboundLocalError in staff_tenant_middleware.")
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
