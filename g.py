#!/usr/bin/env python3
"""
axis_patcher.py - Fix indentation and import issues in staff_tenant_middleware.py

This script corrects:
1. Adds 'from django.shortcuts import redirect' at the top if missing.
2. Removes duplicate/incorrect import inside the except block.
3. Fixes indentation of the except block to avoid IndentationError.

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
    modified = False
    lines = content.splitlines(keepends=True)

    # Step 1: Ensure the correct import is at the top.
    # Check if the import already exists anywhere.
    import_exists = any(re.search(IMPORT_LINE, line) for line in lines)

    if not import_exists:
        # Find the last import line and insert after it.
        insert_idx = -1
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith(('import ', 'from ')):
                insert_idx = i
        if insert_idx == -1:
            insert_idx = 0
        else:
            insert_idx += 1
        lines.insert(insert_idx, IMPORT_LINE + '\n')
        log(f"Inserted '{IMPORT_LINE}' at top.", verbose)
        modified = True

    # Step 2: Remove the broken import line inside the except block.
    # We'll find lines that contain the BROKEN_IMPORT_PATTERN and are not indented
    # or are incorrectly indented. We'll remove them.
    new_lines = []
    for line in lines:
        if re.search(BROKEN_IMPORT_PATTERN, line):
            # Check if it's inside an except block? We'll remove it regardless,
            # because the correct import is now at the top.
            log(f"Removing broken import line: {line.strip()}", verbose)
            modified = True
            continue
        new_lines.append(line)
    lines = new_lines

    # Step 3: Fix indentation inside the except block.
    # We need to ensure that lines under 'except Exception as e:' are indented by 4 spaces.
    # We'll look for the pattern: 'except Exception as e:' and then ensure the following lines
    # (until the next line with same or lower indentation) are indented by 4 spaces.
    # We'll use a regex to find the except block and fix indentation.
    # This is tricky with line-by-line, but we can do a targeted replacement.
    # We'll search for the except block and correct the indentation of the lines inside.
    # We'll assume the except block is already present with some indentation issues.
    # Simpler: we can just replace the entire except block with a properly indented one.
    # But we need to preserve the content. We'll parse the file to find the except block.

    # Let's use a regex to find the except block and capture its content.
    # We'll look for the line containing 'except Exception as e:' and then the next few lines.
    # However, it's easier to read the file line by line, detect when we are inside the except block,
    # and adjust indentation.

    # We'll rebuild lines with proper indentation.
    # We'll scan for the start of the except block.
    block_started = False
    block_indent = None
    final_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        # Check if this line is the start of the except block.
        if re.match(r'^except Exception as e:', stripped):
            # Determine the indentation of this line.
            indent = len(line) - len(stripped)
            block_indent = indent
            block_started = True
            # Add the except line as is (with its original indentation).
            final_lines.append(line)
            i += 1
            # Now process the following lines until we hit a line with indentation <= block_indent (or end of file).
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.lstrip()
                # If the line is empty, just keep it.
                if next_stripped == '':
                    final_lines.append(next_line)
                    i += 1
                    continue
                # Determine its indentation.
                next_indent = len(next_line) - len(next_stripped)
                # If the indentation is less than or equal to the block indent (but not empty), we are out of the block.
                if next_indent <= block_indent and next_stripped and not next_stripped.startswith(('except', 'finally', 'else')):
                    # We are out of the except block.
                    block_started = False
                    break
                # Inside the block: ensure it is indented by exactly 4 spaces more than block_indent.
                # Actually, we want each line inside to be indented with 4 spaces relative to the except line.
                # So target_indent = block_indent + 4
                target_indent = block_indent + 4
                # Remove any leading spaces/tabs and then add target_indent spaces.
                # We'll preserve tabs? We'll just use spaces for simplicity.
                # We'll replace the leading whitespace with target_indent spaces.
                # But we need to be careful with mixed tabs/spaces. We'll assume spaces.
                # We'll compute the new line: spaces*target_indent + next_stripped.
                new_line = ' ' * target_indent + next_stripped
                # If the line is the broken import, we already removed it, so it won't be here.
                final_lines.append(new_line)
                log(f"Indented line: {next_stripped.strip()} -> {new_line.strip()}", verbose)
                modified = True
                i += 1
            # After the block, continue with the rest.
            continue
        else:
            # Not inside except block, keep line as is.
            final_lines.append(line)
            i += 1

    # If we didn't process any except block (or it's missing), we might still have the broken import removed.
    # But we already removed it.

    # Step 4: Write back if modified.
    new_content = ''.join(final_lines)

    if new_content == original_content and not modified:
        log("No changes needed.", verbose)
        return True

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
        description="Fix the middleware syntax and indentation errors."
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
