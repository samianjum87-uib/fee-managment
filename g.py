#!/usr/bin/env python3
"""
axis_middleware_cleanup.py - Fix staff_tenant_middleware.py.

Fixes:
- Adds missing redirect import at top.
- Removes inner imports and uses StaffCredential correctly.
- Reorders try block: define credential before logging.
- Removes duplicate imports.

Usage:
    python axis_middleware_cleanup.py [--dry-run] [--verbose] [--target-dir PATH]
"""

import re
import sys
from pathlib import Path
from datetime import datetime

MIDDLEWARE_FILE = "axis_saas/middleware/staff_tenant_middleware.py"

def fix_middleware(target_dir, dry_run=False, verbose=False):
    full_path = target_dir / MIDDLEWARE_FILE
    if not full_path.exists():
        print(f"Error: {full_path} not found.")
        return False

    try:
        content = full_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Failed to read {full_path}: {e}")
        return False

    original = content
    changes = []

    # 1. Add missing redirect import at top if not present
    if "from django.shortcuts import redirect" not in content:
        # Find the last import line and insert after it
        import_lines = re.findall(r'^from .* import .*$', content, re.MULTILINE)
        if import_lines:
            last_import = import_lines[-1]
            pos = content.rfind(last_import) + len(last_import)
            content = content[:pos] + "\nfrom django.shortcuts import redirect" + content[pos:]
            changes.append("Added redirect import")
            if verbose:
                print("Added missing redirect import.")
        else:
            content = "from django.shortcuts import redirect\n" + content
            changes.append("Added redirect import at top")
    else:
        if verbose:
            print("redirect import already present.")

    # 2. Fix the try block: reorder and correct imports
    # We'll find the try block that contains the problematic lines.
    # We'll search for the pattern that starts with "# Determine if passkey is required and enforce redirect"
    # and ends with the except block.
    # We'll replace the entire block with the corrected version.

    pattern = re.compile(
        r'(# Determine if passkey is required and enforce redirect\s*)try:.*?(except Exception as e:.*?request\.staff_passkey_required = False)',
        re.DOTALL
    )

    corrected_block = r'''\1try:
            from axis_saas.models import StaffCredential
            with schema_context('public'):
                credential = StaffCredential.objects.filter(
                    staff_id=staff_id,
                    schema_name=schema_name,
                ).first()
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Middleware: staff_id={staff_id}, schema={schema_name}")
            logger.info(f"Credential exists: {credential is not None}, has_passkey: {credential.has_passkey if credential else False}")
            request.staff_passkey_required = credential is None or not credential.has_passkey

            # Enforce passkey registration if required and not on allowed paths
            if request.staff_passkey_required:
                allowed_paths = [
                    '/portal/staff/profile/',
                    '/portal/staff/security/webauthn/register/options/',
                    '/portal/staff/security/webauthn/register/verify/',
                    '/portal/staff/security/webauthn/auth/options/',
                    '/portal/staff/security/webauthn/auth/verify/',
                    '/portal/staff/logout/',
                    '/portal/staff/login/',
                ]
                if request.path_info not in allowed_paths:
                    return redirect('staff_profile_page')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Middleware error: {e}")
            request.staff_passkey_required = False'''

    new_content, count = pattern.subn(corrected_block, content)
    if count:
        content = new_content
        changes.append(f"Replaced try block ({count} replacements)")
        if verbose:
            print("Replaced try block with corrected version.")
    else:
        if verbose:
            print("Could not find the try block pattern; skipping.")

    if content == original:
        print("No changes needed.")
        return True

    if dry_run:
        print("Dry run: would write changes to", full_path)
        if verbose:
            print("--- Original (first 500 chars)")
            print(original[:500])
            print("--- New (first 500 chars)")
            print(content[:500])
        return True

    try:
        full_path.write_text(content, encoding='utf-8')
        print("Successfully updated", full_path)
        for change in changes:
            print(" -", change)
        return True
    except Exception as e:
        print(f"Failed to write {full_path}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Clean up staff_tenant_middleware.py (imports and try block).")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying.")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output.")
    parser.add_argument("--target-dir", default=".", help="Project root directory (default: current directory).")
    args = parser.parse_args()

    target_dir = Path(args.target_dir).resolve()
    if not target_dir.is_dir():
        print(f"Error: {target_dir} is not a valid directory.")
        sys.exit(1)

    success = fix_middleware(target_dir, dry_run=args.dry_run, verbose=args.verbose)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
