#!/usr/bin/env python3
"""
axis_fixer_final.py - Final fix for staff_portal.py and middleware.

This script applies known fixes:
1. Removes duplicate decorators in staff_portal.py.
2. Ensures no escaped quotes remain.
3. Adds proper error handling in middleware.
4. Adds logging to help debug issues.

Run this on your server (or locally and redeploy) to fix the 500 error.

Usage:
    python axis_fixer_final.py [--dry-run] [--verbose] [--target-dir PATH]
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# ----------------------------------------------------------------------
# PATCH DEFINITIONS
# ----------------------------------------------------------------------

PATCHES: List[Tuple[str, str, str, str]] = []

STAFF_PORTAL = "axis_saas/views/staff_portal.py"
MIDDLEWARE_FILE = "axis_saas/middleware/staff_tenant_middleware.py"

# 1. Remove duplicate decorators in staff_portal.py
PATCHES.append((
    STAFF_PORTAL,
    r'(@require_staff_login\s+@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_staff_login\s+@require_http_methods\(\[\'POST\'\]\)',
    r'\1',
    "Remove duplicate decorators (registration_verify)"
))

PATCHES.append((
    STAFF_PORTAL,
    r'(@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_http_methods\(\[\'POST\'\]\)',
    r'\1',
    "Remove duplicate decorators (authentication endpoints)"
))

# 2. Fix any escaped quotes that might remain
PATCHES.append((
    STAFF_PORTAL,
    r"request\.session\\\['staff_session_token'\\\]",
    "request.session['staff_session_token']",
    "Fix escaped quotes in staff_session_token assignment"
))

# 3. Add try/except logging in middleware to capture errors
PATCHES.append((
    MIDDLEWARE_FILE,
    r'(# Determine if passkey is required and enforce redirect\s*try:)',
    r'\1\n            import logging\n            logger = logging.getLogger(__name__)\n            logger.info(f"Middleware: staff_id={staff_id}, schema={schema_name}")\n            logger.info(f"Credential exists: {credential is not None}, has_passkey: {credential.has_passkey if credential else False}")',
    "Add logging to middleware"
))

# 4. Ensure that request.staff_passkey_required is always set, even on exception
PATCHES.append((
    MIDDLEWARE_FILE,
    r'(except Exception:\s+request\.staff_passkey_required = False)',
    r'except Exception as e:\n            import logging\n            logger = logging.getLogger(__name__)\n            logger.error(f"Middleware error: {e}")\n            request.staff_passkey_required = False',
    "Add error logging in middleware exception"
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

        pattern = re.compile(search, re.DOTALL | re.MULTILINE)
        new_content, count = pattern.subn(replace, content)
        if count == 0:
            self.log(f"Pattern not found or no replacement made in {file_path}: {desc}", "WARNING")
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
        self.log(f"Starting final patcher with target dir: {self.target_dir}")
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

    parser = argparse.ArgumentParser(description="Final fixes for Staff Portal 500 error.")
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
            print("If the issue persists, check the server logs for the specific error.")
        else:
            print("\nSome fixes failed. See logs above.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
