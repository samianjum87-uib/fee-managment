#!/usr/bin/env python3
"""
axis_patcher.py - Fix IndentationError and missing imports in staff_tenant_middleware.py

This script corrects:
1. Missing 'from django.shortcuts import redirect' at top.
2. Missing 'import logging' at top.
3. Missing logger definition: logger = logging.getLogger(__name__)
4. Removes the incorrectly placed import line inside the except block.
5. Fixes indentation of the except block contents.

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
import difflib
from pathlib import Path
from datetime import datetime

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
TARGET_FILE = "axis_saas/middleware/staff_tenant_middleware.py"

# Lines to ensure are present at top (in order)
IMPORT_REDIRECT = "from django.shortcuts import redirect"
IMPORT_LOGGING = "import logging"
LOGGER_DEF = "logger = logging.getLogger(__name__)"

# Pattern to match the broken import line inside except
BROKEN_IMPORT_PATTERN = r'^[ \t]*from django\.shortcuts import redirect\s*$'

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
    lines = content.splitlines(keepends=True)

    # Step 1: Insert necessary imports at top if missing.
    # We'll find the index after the last existing import (top-level, not indented).
    last_import_idx = -1
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
            last_import_idx = i

    insert_idx = last_import_idx + 1 if last_import_idx != -1 else 0

    # List of lines to insert (in order)
    to_insert = []
    if not any(re.search(re.escape(IMPORT_REDIRECT), line) for line in lines):
        to_insert.append(IMPORT_REDIRECT)
    if not any(re.search(re.escape(IMPORT_LOGGING), line) for line in lines):
        to_insert.append(IMPORT_LOGGING)
    if not any(re.search(re.escape(LOGGER_DEF), line) for line in lines):
        to_insert.append(LOGGER_DEF)

    if to_insert:
        for imp in reversed(to_insert):
            lines.insert(insert_idx, imp + '\n')
            log(f"Inserted line: {imp}", verbose)

    # Step 2: Fix the except block.
    # We'll rebuild lines, processing the except block to remove the broken import
    # and fix indentation.
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        # Detect the start of the except block (the one causing the error)
        if re.match(r'^except Exception as e:', stripped):
            # Keep the except line as is
            except_indent = len(line) - len(stripped)
            new_lines.append(line)
            i += 1
            # Now process lines inside the except block until we exit (indentation <= except_indent)
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.lstrip()
                if next_stripped == '':
                    # Keep empty lines with correct indentation? We'll keep them as is, but they might be inside.
                    new_lines.append(next_line)
                    i += 1
                    continue
                next_indent = len(next_line) - len(next_stripped)
                # If indentation <= except_indent and not empty, we're out of the block.
                if next_indent <= except_indent and next_stripped:
                    break
                # Inside block: if this line is the broken import, skip it.
                if re.search(BROKEN_IMPORT_PATTERN, next_stripped):
                    log(f"Removing broken import line inside except: {next_line.strip()}", verbose)
                    i += 1
                    continue
                # Re-indent to except_indent + 4 spaces
                new_line = ' ' * (except_indent + 4) + next_stripped
                if new_line != next_line:
                    log(f"Re-indented line: {next_line.strip()} -> {new_line.strip()}", verbose)
                new_lines.append(new_line)
                i += 1
            # After block, continue with the rest (i already at the next line after block)
            continue
        else:
            new_lines.append(line)
            i += 1

    # Step 3: Any leftover broken import lines that might have been missed (top-level)?
    # We already handled the except, but we can scan and remove any top-level broken imports as well.
    # However, the correct import is already added, so we'll remove duplicates.
    # We'll filter out lines that are exactly the broken import and not indented.
    final_lines = []
    for line in new_lines:
        stripped = line.lstrip()
        if re.search(BROKEN_IMPORT_PATTERN, stripped):
            # If this line is not inside an except (i.e., top-level), remove it.
            if not line.startswith(' '):
                log(f"Removing top-level broken import: {line.strip()}", verbose)
                continue
        final_lines.append(line)

    new_content = ''.join(final_lines)

    if new_content == original_content:
        log("No changes needed.", verbose)
        return True

    if dry_run:
        log("--- DRY RUN: changes would be applied ---", force=True)
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
        description="Fix the middleware indentation and import errors."
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
