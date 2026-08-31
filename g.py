#!/usr/bin/env python3
"""
axis_patcher.py - Add missing 'redirect' import to staff_tenant_middleware.py

This script corrects the NameError caused by missing 'redirect' import.

Usage:
    python axis_patcher.py [--dry-run] [--verbose] [--target-dir PATH]

Options:
    --dry-run      Show what would be changed without writing.
    --verbose      Print detailed logs.
    --target-dir   Path to the project root (default: current directory).
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
TARGET_FILE = "axis_saas/middleware/staff_tenant_middleware.py"
IMPORT_LINE = "from django.shortcuts import redirect"
BROKEN_IMPORT_PATTERN = r'^[ \t]*from django\.shortcuts import redirectCredential\s*$'

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
def log(msg, verbose=False, force=False):
    if verbose or force:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {msg}")

# ----------------------------------------------------------------------
# Patcher logic
# ----------------------------------------------------------------------
def patch_file(file_path, dry_run=False, verbose=False):
    """Apply fixes to the target file."""
    if not file_path.exists():
        log(f"ERROR: File not found: {file_path}", force=True)
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    modified = False

    # 1. Remove any broken import lines (if present)
    new_content, count = re.subn(BROKEN_IMPORT_PATTERN, '', content, flags=re.MULTILINE)
    if count:
        log(f"Removed {count} broken import line(s).", verbose)
        content = new_content
        modified = True

    # 2. Ensure the correct import is present at the top.
    # Check if the import already exists.
    if re.search(r'^from django\.shortcuts import redirect\s*$', content, re.MULTILINE):
        log("Correct import already present.", verbose)
    else:
        # Insert the import after the last existing import line.
        lines = content.splitlines(keepends=True)
        insert_index = -1
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith(('import ', 'from ')):
                insert_index = i
        if insert_index == -1:
            insert_index = 0
        else:
            insert_index += 1
        lines.insert(insert_index, IMPORT_LINE + '\n')
        content = ''.join(lines)
        log(f"Inserted import at line {insert_index+1}.", verbose)
        modified = True

    if not modified:
        log("No changes needed.", verbose)
        return True

    if dry_run:
        log("--- DRY RUN: changes would be applied ---", force=True)
        import difflib
        diff = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=str(file_path),
            tofile=str(file_path) + " (patched)"
        )
        for line in diff:
            sys.stdout.write(line)
        return True

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    log(f"Successfully patched {file_path}", force=True)
    return True

# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Fix the middleware import error."
    )
    parser.add_argument('--dry-run', action='store_true',
                        help="Preview changes without writing.")
    parser.add_argument('--verbose', action='store_true',
                        help="Show detailed output.")
    parser.add_argument('--target-dir', default='.',
                        help="Project root directory (default: current).")
    args = parser.parse_args()

    target_dir = Path(args.target_dir).resolve()
    if not target_dir.is_dir():
        log(f"ERROR: Target directory not found: {target_dir}", force=True)
        sys.exit(1)

    file_path = target_dir / TARGET_FILE
    if not file_path.exists():
        log(f"ERROR: {TARGET_FILE} not found in {target_dir}", force=True)
        sys.exit(1)

    success = patch_file(file_path, dry_run=args.dry_run, verbose=args.verbose)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
