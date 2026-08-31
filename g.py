#!/usr/bin/env python3
"""
axis_patcher.py - Add missing 'from django.shortcuts import redirect' to middleware

This script corrects the NameError caused by missing redirect import.

Usage:
    python axis_patcher.py [--dry-run] [--verbose] [--target-dir PATH]

Options:
    --dry-run      Show what would be changed without writing.
    --verbose      Print detailed output.
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
    """Add missing import to the target file."""
    if not file_path.exists():
        log(f"ERROR: File not found: {file_path}", force=True)
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    lines = content.splitlines(keepends=True)

    # Check if the import is already present (top-level, not indented)
    import_exists = False
    for line in lines:
        if line.lstrip().startswith(IMPORT_LINE) and not line.startswith(' '):
            import_exists = True
            break

    if import_exists:
        log("Import already present. No changes needed.", verbose)
        return True

    # Find the last top-level import line
    last_import_idx = -1
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
            last_import_idx = i

    insert_idx = last_import_idx + 1 if last_import_idx != -1 else 0
    lines.insert(insert_idx, IMPORT_LINE + '\n')
    log(f"Inserted '{IMPORT_LINE}' at line {insert_idx+1}.", verbose)

    new_content = ''.join(lines)

    if dry_run:
        log("--- DRY RUN: changes would be applied ---", force=True)
        import difflib
        diff = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=str(file_path),
            tofile=str(file_path) + " (patched)"
        )
        for line in diff:
            sys.stdout.write(line)
        return True

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    log(f"Successfully patched {file_path}", force=True)
    return True

# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Fix missing redirect import in middleware."
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
