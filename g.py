#!/usr/bin/env python3
"""
axis_quote_fixer.py - Fix escaped quotes in staff_portal.py.

Replaces all occurrences of:
    request.session[\'staff_session_token\']
with:
    request.session['staff_session_token']

Also removes any duplicate decorators that might cause issues.

Usage:
    python axis_quote_fixer.py [--dry-run] [--verbose] [--target-dir PATH]
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

FILE_PATH = "axis_saas/views/staff_portal.py"

# ----------------------------------------------------------------------
# PATCH DEFINITIONS
# ----------------------------------------------------------------------

PATCHES: List[Tuple[str, str, str, str]] = []

# 1. Fix the escaped quotes: replace [\'staff_session_token\'] with ['staff_session_token']
# This pattern matches the exact broken string.
PATCHES.append((
    FILE_PATH,
    r"request\.session\\\['staff_session_token'\\\]",
    "request.session['staff_session_token']",
    "Replace escaped quotes in staff_session_token assignment"
))

# 2. Remove duplicate decorator lines for registration_verify, authentication_options, authentication_verify.
# This is optional but cleans up the file.
PATCHES.append((
    FILE_PATH,
    r'(@require_staff_login\s+@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_staff_login\s+@require_http_methods\(\[\'POST\'\]\)',
    r'\1',
    "Remove duplicate decorators (staff_webauthn_registration_verify)"
))

PATCHES.append((
    FILE_PATH,
    r'(@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_http_methods\(\[\'POST\'\]\)',
    r'\1',
    "Remove duplicate decorators (authentication endpoints)"
))

# ----------------------------------------------------------------------
# PATCHER ENGINE
# ----------------------------------------------------------------------

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

    def apply_patch(self, file_path: str, search: str, replace: str, desc: str) -> bool:
        full_path = self.target_dir / file_path
        if not full_path.exists():
            self.log(f"File not found: {full_path}", "ERROR")
            return False

        try:
            content = full_path.read_text(encoding='utf-8')
        except Exception as e:
            self.log(f"Failed to read {full_path}: {e}", "ERROR")
            return False

        # Use regex with DOTALL and MULTILINE to match across lines.
        pattern = re.compile(search, re.MULTILINE | re.DOTALL)
        if not pattern.search(content):
            self.log(f"Pattern not found in {file_path}: {desc}", "WARNING")
            return False

        new_content, count = pattern.subn(replace, content)
        if count == 0:
            self.log(f"No replacement made for {file_path}: {desc}", "WARNING")
            return False

        if self.dry_run:
            self.log(f"[DRY RUN] Would patch {file_path}: {desc} ({count} replacements)", "INFO")
            return True

        try:
            full_path.write_text(new_content, encoding='utf-8')
            self.log(f"Patched {file_path}: {desc} ({count} replacements)", "INFO")
            return True
        except Exception as e:
            self.log(f"Failed to write {full_path}: {e}", "ERROR")
            return False

    def run(self):
        self.log(f"Starting patcher with target dir: {self.target_dir}")
        self.log(f"Dry run: {self.dry_run}, Verbose: {self.verbose}")

        success_count = 0
        fail_count = 0
        for file_path, search, replace, desc in PATCHES:
            if self.apply_patch(file_path, search, replace, desc):
                success_count += 1
            else:
                fail_count += 1

        self.log(f"Patches applied: {success_count} successful, {fail_count} failed.")
        return success_count > 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fix escaped quotes and duplicate decorators in staff_portal.py.")
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
            print("\nFixes applied successfully. Please restart your server.")
        else:
            print("\nSome fixes failed. See logs above.", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
