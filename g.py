#!/usr/bin/env python3
"""
axis_patcher.py - Remove redundant inner import of Staff in staff_tenant_middleware.py

This script removes the line `from axis_saas.models import Staff` from inside the
try block in StaffTenantMiddleware.__call__ to fix an UnboundLocalError.

Usage:
    python3 axis_patcher.py [--dry-run] [--verbose] [--target-dir PATH]
"""

import argparse
import datetime
import re
import sys
from pathlib import Path


def log(message, verbose=False):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if verbose:
        print(f"[{timestamp}] {message}")
    else:
        print(message)


def main():
    parser = argparse.ArgumentParser(
        description="Remove redundant inner import of Staff in staff_tenant_middleware.py"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output."
    )
    parser.add_argument(
        "--target-dir",
        default=".",
        help="Project root directory (default: current directory)."
    )
    args = parser.parse_args()

    target_dir = Path(args.target_dir).resolve()
    file_path = target_dir / "axis_saas" / "middleware" / "staff_tenant_middleware.py"
    if not file_path.is_file():
        log(f"ERROR: File not found: {file_path}", args.verbose)
        sys.exit(1)

    log(f"Target file: {file_path}", args.verbose)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match the line "from axis_saas.models import Staff" inside the try block.
    # We'll look for the line that has that import, possibly with leading whitespace.
    # We want to delete the line entirely.
    # The line is inside a try block that starts with "try:" and contains that import.
    # We'll match the line with its indentation and newline.
    pattern = re.compile(
        r"^[ \t]+from axis_saas\.models import Staff\s*$",
        re.MULTILINE
    )

    # Check if the line exists.
    if not pattern.search(content):
        log("The inner import line was not found. No changes needed.", args.verbose)
        return

    # Remove all occurrences (should be one) of that line.
    new_content = pattern.sub("", content)

    # Also, ensure there is no blank line left from the removal. We can strip extra blank lines,
    # but that's optional. We'll just replace.

    if args.dry_run:
        log("--- DRY RUN: Preview of changes ---", args.verbose)
        import difflib
        diff = difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=str(file_path),
            tofile=str(file_path) + " (fixed)"
        )
        for line in diff:
            print(line, end="")
        log("--- END DRY RUN ---", args.verbose)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        log(f"File updated: {file_path}", args.verbose)


if __name__ == "__main__":
    main()
