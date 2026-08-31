#!/usr/bin/env python3
"""
axis_middleware_fix.py - Fix staff_tenant_middleware.py.

Adds missing redirect import and reorders credential definition before logging.

Usage:
    python axis_middleware_fix.py [--dry-run] [--verbose] [--target-dir PATH]
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

    # 1. Add missing import of redirect if not present
    if "from django.shortcuts import redirect" not in content:
        # Find the existing imports and add after them
        # We'll add after the last import line before the class definition.
        import_lines = re.findall(r'^from .* import .*$', content, re.MULTILINE)
        if import_lines:
            # Add after the last import line
            last_import = import_lines[-1]
            # Find the position of the last import and insert after it
            pos = content.rfind(last_import) + len(last_import)
            content = content[:pos] + "\nfrom django.shortcuts import redirect" + content[pos:]
            changes.append("Added import for redirect")
        else:
            # No imports, add at the top
            content = "from django.shortcuts import redirect\n" + content
            changes.append("Added import for redirect at top")
        if verbose:
            print("Added missing redirect import.")

    # 2. Fix the try block: move credential definition before logger usage
    # We'll look for the pattern:
    # try:
    #     import logging
    #     logger = logging.getLogger(__name__)
    #     logger.info(f"Middleware: staff_id={staff_id}, schema={schema_name}")
    #     logger.info(f"Credential exists: {credential is not None}, has_passkey: {credential.has_passkey if credential else False}")
    #     from axis_saas.models import StaffCredential
    #     with schema_context('public'):
    #         credential = StaffCredential.objects.filter(...)
    # ...
    # We'll replace with the correct order: define credential first, then log.

    # We'll use a regex to match the try block and reorder.
    try_block_pattern = re.compile(
        r'(try:\s*)(import logging\s*logger = logging\.getLogger\(__name__\)\s*logger\.info\(f"Middleware: staff_id={staff_id}, schema={schema_name}"\)\s*logger\.info\(f"Credential exists: \{credential is not None\}, has_passkey: \{credential\.has_passkey if credential else False\}"\)\s*from axis_saas\.models import StaffCredential\s*with schema_context\(\'public\'\):\s*credential = StaffCredential\.objects\.filter\(.*?\)\.first\(\))',
        re.DOTALL
    )

    # We'll capture the indentation and the rest.
    # We'll rewrite the try block to define credential first, then log, but only if the pattern matches.
    # Since the pattern is complex, we'll do a simpler replacement: find the problematic section and swap.

    # Approach: find the try block from "try:" to the line before "request.staff_passkey_required = ..."
    # But we can also just remove the logger lines that reference credential before definition.
    # We'll replace them with a single log after credential is defined.

    # We'll find the entire try block and rewrite it.
    try_start = content.find("try:")
    if try_start != -1:
        # Find the end of the try block: look for the next "except" or "else" or "finally" at the same indentation.
        # We'll search from try_start to find the matching except.
        # This is tricky; we'll do a simpler approach: replace the specific lines with a corrected version.

        # The problematic lines are:
        #     import logging
        #     logger = logging.getLogger(__name__)
        #     logger.info(f"Middleware: staff_id={staff_id}, schema={schema_name}")
        #     logger.info(f"Credential exists: {credential is not None}, has_passkey: {credential.has_passkey if credential else False}")
        #     from axis_saas.models import StaffCredential
        #     with schema_context('public'):
        #         credential = StaffCredential.objects.filter(...).first()

        # We'll replace with:
        #     from axis_saas.models import StaffCredential
        #     with schema_context('public'):
        #         credential = StaffCredential.objects.filter(...).first()
        #     import logging
        #     logger = logging.getLogger(__name__)
        #     logger.info(f"Middleware: staff_id={staff_id}, schema={schema_name}")
        #     logger.info(f"Credential exists: {credential is not None}, has_passkey: {credential.has_passkey if credential else False}")

        # We'll search for the pattern and replace.

        # Build a regex to capture the whole block.
        pattern = re.compile(
            r'(import logging\s*logger = logging\.getLogger\(__name__\)\s*logger\.info\(f"Middleware: staff_id={staff_id}, schema={schema_name}"\)\s*logger\.info\(f"Credential exists: \{credential is not None\}, has_passkey: \{credential\.has_passkey if credential else False\}"\)\s*from axis_saas\.models import StaffCredential\s*with schema_context\(\'public\'\):\s*credential = StaffCredential\.objects\.filter\(\s*staff_id=staff_id,\s*schema_name=schema_name,\s*\)\.first\(\))',
            re.DOTALL
        )
        # We'll replace with the correct order.
        replacement = r'from axis_saas.models import StaffCredential\n        with schema_context(\'public\'):\n            credential = StaffCredential.objects.filter(\n                staff_id=staff_id,\n                schema_name=schema_name,\n            ).first()\n        import logging\n        logger = logging.getLogger(__name__)\n        logger.info(f"Middleware: staff_id={staff_id}, schema={schema_name}")\n        logger.info(f"Credential exists: {credential is not None}, has_passkey: {credential.has_passkey if credential else False}")'

        new_content, count = pattern.subn(replacement, content)
        if count:
            content = new_content
            changes.append(f"Reordered try block ({count} replacement)")
            if verbose:
                print("Reordered try block: credential defined before logging.")
        else:
            if verbose:
                print("Could not find the exact pattern to reorder; skipping try block fix.")

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
    parser = argparse.ArgumentParser(description="Fix staff_tenant_middleware.py (add redirect import and reorder try block).")
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
