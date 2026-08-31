#!/usr/bin/env python3
"""
axis_patcher.py - Fix indentation and import issues in staff_tenant_middleware.py

This script corrects:
1. Missing 'from django.shortcuts import redirect' at the top.
2. Removes incorrectly placed import inside the except block.
3. Fixes indentation of the logger lines inside the except block.

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

    # 1. Ensure the correct import is at the top after existing imports.
    lines = content.splitlines(keepends=True)

    # Check if import already exists.
    import_exists = any(re.search(r'^from django\.shortcuts import redirect\s*$', line) for line in lines)

    if not import_exists:
        # Find the last import line (from or import) and insert after it.
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

    # 2. Fix the except block: remove misplaced import and fix indentation.
    # We'll scan for the except block and re-indent the lines inside.
    # Specifically, we look for "except Exception as e:" then the following lines.
    # We'll ensure the 'logger = ...' lines are indented by 8 spaces (two levels) relative to the except.
    # The except line itself is indented by 4 spaces (within the try block).
    # So inside the except, we want 8 spaces for the statements.
    # Also remove any line that contains "from django.shortcuts import redirect" inside the block.

    new_lines = []
    i = 0
    inside_except = False
    except_indent = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        # Detect start of except block
        if re.match(r'^except Exception as e:', stripped):
            inside_except = True
            # Determine the indentation of the except line
            except_indent = len(line) - len(stripped)
            # Keep the except line as is
            new_lines.append(line)
            i += 1
            # Process the lines inside the block until we hit a line with indentation <= except_indent (or end)
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.lstrip()
                # Check if we are out of the block
                if next_stripped == '':
                    # Empty line - keep it, but we might be at the end of block? We'll keep it and continue.
                    new_lines.append(next_line)
                    i += 1
                    continue
                next_indent = len(next_line) - len(next_stripped)
                # If the next line has indentation <= except_indent (and is not empty), we are out of block.
                # However, we need to detect if it's another except/else/finally, or a return statement at the same level.
                if next_indent <= except_indent and next_stripped and not next_stripped.startswith(('except', 'finally', 'else')):
                    # We are out of the except block.
                    inside_except = False
                    break
                # Inside the block: we need to fix indentation of the statements.
                # The desired indentation is except_indent + 4 (standard 4 spaces per level).
                target_indent = except_indent + 4
                # If the line contains the broken import, skip it.
                if re.search(r'^from django\.shortcuts import redirect', next_stripped):
                    log(f"Removing broken import line: {next_line.strip()}", verbose)
                    modified = True
                    i += 1
                    continue
                # Otherwise, fix indentation by replacing the leading whitespace with target_indent spaces.
                # But we need to preserve the actual content.
                new_line = ' ' * target_indent + next_stripped
                if new_line != next_line:
                    modified = True
                    log(f"Re-indented line: {next_line.strip()} -> {new_line.strip()}", verbose)
                new_lines.append(new_line)
                i += 1
            # After processing the block, continue with the outer loop (i already at the next line after block)
            continue
        else:
            # Not inside except, just keep line
            new_lines.append(line)
            i += 1

    # Join lines
    new_content = ''.join(new_lines)

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
