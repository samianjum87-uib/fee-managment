#!/usr/bin/env python3
"""
axis_patcher.py - Fix the syntax error in axis_saas/middleware/staff_tenant_middleware.py

This script corrects the malformed import statement that causes a SyntaxError
during Django startup. It adds the proper import for 'redirect' at the top of
the file and removes the broken inline import.

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
import shutil
from pathlib import Path
from datetime import datetime

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
TARGET_FILE = "axis_saas/middleware/staff_tenant_middleware.py"
IMPORT_LINE = "from django.shortcuts import redirect"
BROKEN_IMPORT = "from django.shortcuts import redirectCredential"

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
    """Apply the fix to the target file."""
    if not file_path.exists():
        log(f"ERROR: File not found: {file_path}", force=True)
        return False

    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    modified = False

    # 1. Remove the broken import line (if present) using re.subn
    pattern = r'^[ \t]*from django\.shortcuts import redirectCredential\s*$'
    new_content, count = re.subn(pattern, '', content, flags=re.MULTILINE)
    if count:
        log(f"Removed {count} occurrence(s) of broken import line.", verbose)
        modified = True
        content = new_content

    # 2. Ensure the correct import is present at the top.
    # We'll look for existing import lines. We want to add it after the last
    # import from django or axis_saas, but before any code.
    # A simple approach: check if the correct import already exists.
    if re.search(r'^from django\.shortcuts import redirect\s*$', content, re.MULTILINE):
        log("Correct import already present.", verbose)
    else:
        # Insert the import after the last existing import line.
        lines = content.splitlines(keepends=True)
        insert_index = -1
        for i, line in enumerate(lines):
            if line.lstrip().startswith(('import ', 'from ')):
                insert_index = i
        # If no import found, insert at beginning.
        if insert_index == -1:
            insert_index = 0
        else:
            # Insert after the last import line
            insert_index += 1

        new_line = IMPORT_LINE + '\n'
        lines.insert(insert_index, new_line)
        content = ''.join(lines)
        log(f"Inserted import at line {insert_index+1}.", verbose)
        modified = True

    if not modified:
        log("No changes needed.", verbose)
        return True

    # Show diff if dry-run
    if dry_run:
        log("--- DRY RUN: changes would be applied ---", force=True)
        # Show a simple diff (optional)
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

    # Write back
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
        description="Fix the middleware syntax error in axis_saas."
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
