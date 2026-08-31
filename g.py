#!/usr/bin/env python3
"""
axis_patcher_fix_syntax.py - Fix the garbled staff_session_token assignment.

This script replaces:
    request.session[['staff_session_token']staff_session_token['staff_session_token']] = uuid.uuid4().hex
with:
    request.session['staff_session_token'] = uuid.uuid4().hex

in both occurrences in axis_saas/views/staff_portal.py.

Usage:
    python axis_patcher_fix_syntax.py [--dry-run] [--verbose] [--target-dir PATH]
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# The exact broken string (as it appears in the file)
BROKEN = "request.session[['staff_session_token']staff_session_token['staff_session_token']]"
CORRECT = "request.session['staff_session_token']"

FILE_PATH = "axis_saas/views/staff_portal.py"


class Patcher:
    def __init__(self, target_dir: Path, dry_run: bool = False, verbose: bool = False):
        self.target_dir = target_dir
        self.dry_run = dry_run
        self.verbose = verbose
        self.logs: List[str] = []

    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {level}: {msg}"
        self.logs.append(log_line)
        if self.verbose or level in ("ERROR", "WARNING"):
            print(log_line)

    def run(self):
        full_path = self.target_dir / FILE_PATH
        if not full_path.exists():
            self.log(f"File not found: {full_path}", "ERROR")
            return False

        try:
            content = full_path.read_text(encoding='utf-8')
        except Exception as e:
            self.log(f"Failed to read {full_path}: {e}", "ERROR")
            return False

        if BROKEN not in content:
            self.log(f"Pattern '{BROKEN}' not found in {full_path}. Nothing to fix.", "WARNING")
            return False

        # Count occurrences
        count = content.count(BROKEN)
        new_content = content.replace(BROKEN, CORRECT)

        if self.dry_run:
            self.log(f"[DRY RUN] Would replace {count} occurrence(s) in {FILE_PATH}", "INFO")
            return True

        try:
            full_path.write_text(new_content, encoding='utf-8')
            self.log(f"Replaced {count} occurrence(s) in {FILE_PATH}", "INFO")
            return True
        except Exception as e:
            self.log(f"Failed to write {full_path}: {e}", "ERROR")
            return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix garbled session token assignment in staff_portal.py")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying.")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output.")
    parser.add_argument("--target-dir", default=".", help="Project root directory (default: current directory).")
    args = parser.parse_args()

    target_dir = Path(args.target_dir).resolve()
    if not target_dir.is_dir():
        print(f"Error: {target_dir} is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    patcher = Patcher(target_dir, dry_run=args.dry_run, verbose=args.verbose)
    success = patcher.run()

    if args.dry_run:
        print("\nDry run completed. No files were modified.")
    else:
        if success:
            print("\nSyntax fix applied successfully. Please restart your server.")
        else:
            print("\nNo changes were made. See logs above.", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
