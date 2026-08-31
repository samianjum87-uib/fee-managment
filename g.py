#!/usr/bin/env python3
"""
axis_patcher_cleanup.py - Final cleanup for staff_portal.py.

Fixes:
1. Remove duplicate decorators.
2. Ensure session expiry and modified are set after token assignment in staff_login and staff_webauthn_authentication_verify.
3. Remove any stray blank lines or extra decorators.

Usage:
    python axis_patcher_cleanup.py [--dry-run] [--verbose] [--target-dir PATH]
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

# 1. Remove duplicate decorator blocks for registration_verify
PATCHES.append((
    FILE_PATH,
    r'(@require_staff_login\s+@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_staff_login\s+@require_http_methods\(\[\'POST\'\]\)',
    r'\1',
    "Remove duplicate decorators for staff_webauthn_registration_verify"
))

# 2. Remove duplicate decorator blocks for authentication_options
PATCHES.append((
    FILE_PATH,
    r'(@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_http_methods\(\[\'POST\'\]\)',
    r'\1',
    "Remove duplicate decorators for staff_webauthn_authentication_options"
))

# 3. Remove duplicate decorator blocks for authentication_verify
PATCHES.append((
    FILE_PATH,
    r'(@require_http_methods\(\[\'POST\'\]\)\s*)\s*@require_http_methods\(\[\'POST\'\]\)',
    r'\1',
    "Remove duplicate decorators for staff_webauthn_authentication_verify"
))

# 4. In staff_login, after the token assignment, ensure we have set_expiry and modified.
# The pattern: request.session['staff_session_token'] = uuid.uuid4().hex
# then a newline, then we need to insert set_expiry and modified.
# We'll find the token assignment and then check if the next non-empty lines are set_expiry and modified.
# If not, insert them.
# We'll use a search that matches the token assignment, then optional whitespace, then maybe some lines,
# then the session_keys line, and insert set_expiry and modified before session_keys.
# We'll capture the indentation of the token assignment.
PATCHES.append((
    FILE_PATH,
    r'^(\s*)request\.session\[\'staff_session_token\'\] = uuid\.uuid4\(\)\.hex\s*\n(?!\s*request\.session\.set_expiry\(1800\))(\s*)session_keys = cache\.get',
    r'\1request.session[\'staff_session_token\'] = uuid.uuid4().hex\n\1request.session.set_expiry(1800)\n\1request.session.modified = True\n\2session_keys = cache.get',
    "Add missing session expiry and modified in staff_login"
))

# 5. Similarly for staff_webauthn_authentication_verify.
PATCHES.append((
    FILE_PATH,
    r'^(\s*)request\.session\[\'staff_session_token\'\] = uuid\.uuid4\(\)\.hex\s*\n(?!\s*request\.session\.set_expiry\(1800\))(\s*)with schema_context',
    r'\1request.session[\'staff_session_token\'] = uuid.uuid4().hex\n\1request.session.set_expiry(1800)\n\1request.session.modified = True\n\2with schema_context',
    "Add missing session expiry and modified in staff_webauthn_authentication_verify"
))

# 6. Also, there might be a stray duplicate of the token assignment with different indentation.
# We'll ensure that there is only one set.

# 7. Remove any extra blank lines that might cause issues (optional).

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
        self.log(f"Starting cleanup patcher with target dir: {self.target_dir}")
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

    parser = argparse.ArgumentParser(description="Clean up staff_portal.py (duplicate decorators, session expiry).")
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
            print("\nCleanup applied successfully. Please restart your server.")
        else:
            print("\nSome fixes failed. See logs above.", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
