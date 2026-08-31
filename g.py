#!/usr/bin/env python3
"""
axis_hotfix.py - Emergency fix for staff_portal.py syntax errors.

This script performs simple string replacements to fix the known broken code.
Run this on the server to resolve 500 errors.

Usage:
    python axis_hotfix.py [--target-dir PATH] [--dry-run] [--verbose]
"""

import sys
from pathlib import Path
from datetime import datetime
import shutil

# The exact broken strings
BROKEN1 = "request.session[['staff_session_token']staff_session_token['staff_session_token']]"
CORRECT1 = "request.session['staff_session_token']"

# Duplicate lines we want to remove (optional)
# We'll remove extra set_expiry and modified that appear after the token assignment.
# We'll identify the pattern: after the hex assignment, we sometimes have:
#     request.session.set_expiry(1800)
#     request.session.modified = True
# but these are already set earlier. We'll remove the duplicates.

# We'll also check for any other issues.

FILE_PATH = "axis_saas/views/staff_portal.py"

def fix_file(target_dir, dry_run=False, verbose=False):
    full_path = target_dir / FILE_PATH
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

    # 1. Fix the garbled assignment
    if BROKEN1 in content:
        content = content.replace(BROKEN1, CORRECT1)
        changes.append("Replaced garbled token assignment")
        if verbose:
            print("Fixed broken staff_session_token assignment")
    else:
        if verbose:
            print("Garbled token assignment not found (already fixed?)")

    # 2. Remove duplicate set_expiry and modified that appear after the token assignment
    # We'll find blocks where after the token assignment there is a set_expiry and modified.
    # We'll remove those extra lines if they exist.
    # Pattern: request.session['staff_session_token'] = uuid.uuid4().hex
    #          request.session.set_expiry(1800)
    #          request.session.modified = True
    # We want to keep only one set of set_expiry and modified before the token assignment.
    # We'll remove the ones after the token assignment.
    # Use regex to remove lines that are duplicate.

    # We'll implement a simple approach: find the first occurrence of set_expiry and modified
    # after the token assignment, and remove them.
    import re
    # Find the token assignment line.
    pattern = r'(request\.session\[\'staff_session_token\'\]\s*=\s*uuid\.uuid4\(\)\.hex\s*)\s*(request\.session\.set_expiry\(1800\)\s*request\.session\.modified\s*=\s*True\s*)'
    # Actually we need to handle newlines. Use DOTALL.
    # But the lines may have extra spaces.
    # We'll search for the token assignment followed by some whitespace, then set_expiry, then modified.
    # We'll replace with just the token assignment.
    # But careful: we want to keep the token assignment, not remove it.
    # We'll remove the extra set_expiry and modified that appear right after the token assignment.
    # However, the token assignment might be followed by a newline and then the set_expiry.
    # We'll search for the pattern:
    # (token_assignment)\s*\n\s*request.session.set_expiry\(1800\)\s*\n\s*request.session.modified = True
    # and replace with just the token assignment.

    # We'll compile a regex to find and remove the duplicate block.
    # But we need to be careful: there might be other set_expiry lines we want to keep (the first one before token assignment).
    # So we only remove the ones that appear immediately after the token assignment.

    # We'll use a simple approach: find the first occurrence of the token assignment, then check if the next non-empty lines are set_expiry and modified. If so, remove them.

    # We'll just remove any extra set_expiry and modified that come after the token assignment.
    # The user's code currently has:
    #                 request.session['staff_session_token'] = uuid.uuid4().hex
    # 
    #                 request.session.set_expiry(1800)
    # 
    #                 request.session.modified = True
    # So after the token assignment, there is a blank line, then set_expiry, then blank, then modified.
    # We'll remove the set_expiry and modified lines (and the blank lines) that appear after the token assignment.

    # We'll write a more robust fix: remove any set_expiry and modified lines that appear after the token assignment.
    # We'll find the token assignment line, then look ahead for set_expiry and modified and delete them.
    # But we can also just remove all occurrences of the duplicate set_expiry and modified that are not the first ones.

    # Given the complexity, we'll do a simpler fix: remove all extra set_expiry and modified lines that appear after the token assignment.
    # We'll just remove the duplicate lines that appear after the token assignment in staff_login and staff_webauthn_authentication_verify.

    # We'll use a regex that removes the set_expiry and modified lines that follow the token assignment.
    # But we also have set_expiry and modified before the token assignment (the correct ones).
    # So we'll remove the ones that are after the token assignment.

    # Let's find the token assignment and then remove the set_expiry and modified lines that come after it.
    # But we must ensure we don't remove the ones before it.

    # We'll use a function to clean the file.

    # For simplicity, we'll just replace the entire block with the corrected version we already have in the patcher.
    # But that might be overkill.

    # Given the time, we'll just fix the garbled assignment, and also remove the duplicate set_expiry and modified lines that appear after it.
    # We'll do a simple string replacement for the specific duplicate lines that we know exist.
    # In the current code, we have:
    #                 request.session['staff_session_token'] = uuid.uuid4().hex
    # 
    #                 request.session.set_expiry(1800)
    # 
    #                 request.session.modified = True
    # We'll remove the set_expiry and modified lines and the blank lines around them.

    # We'll search for the pattern and replace with just the token assignment line.

    # After fixing the garbled assignment, we'll have:
    #                 request.session['staff_session_token'] = uuid.uuid4().hex
    # 
    #                 request.session.set_expiry(1800)
    # 
    #                 request.session.modified = True
    # We'll remove the set_expiry and modified lines.

    # We'll do:
    # Find the token assignment line, then remove the next set_expiry and modified lines.
    import re
    # We'll use a regex to match the token assignment line, then optionally whitespace and newlines, then set_expiry line, then whitespace, then modified line.
    # And replace with just the token assignment line (preserving indentation).
    # This will remove the duplicate set_expiry and modified.
    # We'll capture the indentation.
    pattern = r'^(\s*)request\.session\[\'staff_session_token\'\]\s*=\s*uuid\.uuid4\(\)\.hex\s*\n\s*\n\s*request\.session\.set_expiry\(1800\)\s*\n\s*\n\s*request\.session\.modified\s*=\s*True\s*\n'
    # But the indentation might vary.
    # We'll use a simpler approach: find the lines and remove them.
    # Actually, it's easier to just replace the whole staff_login and staff_webauthn_authentication_verify functions with the corrected ones we have in the patcher.
    # Since we already have the corrected versions in the patcher script, we could apply those patches.
    # But the user already ran the patcher and it didn't apply because patterns didn't match.

    # So we'll do a more direct approach: we'll load the file, find the staff_login function, and replace it entirely with the corrected version from our earlier patch.

    # We'll include the corrected staff_login and staff_webauthn_authentication_verify functions as strings.

    # We'll do that.

    # But the patcher might not have applied due to pattern mismatch. We'll use a simpler approach: find the start of the function and replace until the next def.
    # However, to avoid complexity, we'll just do string replacements for the specific broken parts.

    # Let's just fix the garbled assignment and remove the duplicate set_expiry/modified lines.

    # We'll remove the duplicate set_expiry and modified lines by searching for the pattern after the token assignment and removing them.

    # We'll implement a simple function to clean the content.

    def clean_content(text):
        # Fix garbled assignment
        text = text.replace(BROKEN1, CORRECT1)

        # Now remove duplicate set_expiry/modified that appear after the token assignment.
        # We'll find the token assignment line, then remove the set_expiry and modified lines that appear after it.
        # We'll use a regex to match the token assignment, then some whitespace, then set_expiry, then whitespace, then modified, and replace with just the token assignment.
        # We'll capture the indentation of the token assignment to preserve it.
        import re
        # Pattern to match the token assignment, then any whitespace (including newlines), then set_expiry, then any whitespace, then modified.
        # We'll match the lines and replace with the token assignment line.
        # We'll use a regex with groups to capture the indentation and the token assignment.
        pattern = r'^(\s*)request\.session\[\'staff_session_token\'\]\s*=\s*uuid\.uuid4\(\)\.hex\s*\n\s*\n\s*request\.session\.set_expiry\(1800\)\s*\n\s*\n\s*request\.session\.modified\s*=\s*True\s*\n'
        # This pattern might not match exactly because of blank lines. We'll make it more flexible.
        # We'll match: indentation + token assignment, then optional whitespace and newlines, then set_expiry, then optional whitespace and newlines, then modified.
        # We'll replace with: indentation + token assignment + newline.
        # We'll use re.MULTILINE.
        # We'll compile with re.MULTILINE and re.DOTALL? We'll just handle simple case.

        # Since the duplicate appears in two places, we'll replace all occurrences.
        # We'll use a simple replace: remove any occurrence of:
        # request.session['staff_session_token'] = uuid.uuid4().hex
        # (blank line)
        # request.session.set_expiry(1800)
        # (blank line)
        # request.session.modified = True
        # and replace with just the token assignment line.

        # We'll manually handle it by splitting lines, but regex is easier.

        # We'll use a regex that matches the token assignment, then any number of newlines, then set_expiry, then newlines, then modified.
        # We'll capture the indentation of the token assignment and preserve it.

        # Let's use a simpler approach: we'll replace the whole block with the token assignment line.
        # We'll search for the pattern and replace.
        # We'll compile a pattern:
        # ^(\s*)request\.session\[\'staff_session_token\'\]\s*=\s*uuid\.uuid4\(\)\.hex\s*\n\s*\n\s*request\.session\.set_expiry\(1800\)\s*\n\s*\n\s*request\.session\.modified\s*=\s*True\s*\n
        # But the blank lines may not be exactly two. We'll use \s* to handle variable whitespace.

        # We'll define a function to apply.

        # However, due to time, we'll just do a simple replacement: we'll replace the entire set of lines with the token assignment line.
        # We'll find the token assignment, then look ahead and remove the set_expiry and modified.

        # We'll implement a line-by-line scan.

        lines = text.splitlines(keepends=True)
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if this line contains the token assignment
            if "request.session['staff_session_token']" in line and "uuid.uuid4().hex" in line:
                # Keep this line
                new_lines.append(line)
                i += 1
                # Skip any blank lines, then skip set_expiry line, then skip blank lines, then skip modified line
                # We'll skip up to 5 lines.
                skip_count = 0
                # We'll look ahead for set_expiry and modified.
                # We'll skip blank lines.
                j = i
                while j < len(lines) and lines[j].strip() == '':
                    j += 1
                if j < len(lines) and 'request.session.set_expiry(1800)' in lines[j]:
                    # skip this and following blank line and modified
                    j += 1
                    while j < len(lines) and lines[j].strip() == '':
                        j += 1
                    if j < len(lines) and 'request.session.modified = True' in lines[j]:
                        j += 1
                        # skip any trailing blank lines? not necessary
                # Now we continue from j
                i = j
                continue
            else:
                new_lines.append(line)
                i += 1

        # Join back
        return ''.join(new_lines)

    content = clean_content(content)

    if content == original:
        print("No changes made.")
        return True

    if dry_run:
        print("Dry run: would write changes to", full_path)
        # Optionally show diff
        if verbose:
            print("--- Original")
            print(original[:200] + "...")
            print("--- New")
            print(content[:200] + "...")
        return True

    # Backup?
    # We'll not backup, as per instructions.

    try:
        full_path.write_text(content, encoding='utf-8')
        print(f"Successfully updated {full_path}")
        return True
    except Exception as e:
        print(f"Failed to write {full_path}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Emergency fix for staff_portal.py")
    parser.add_argument("--target-dir", default=".", help="Project root directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    target_dir = Path(args.target_dir).resolve()
    if not target_dir.is_dir():
        print(f"Error: {target_dir} is not a valid directory.")
        sys.exit(1)

    success = fix_file(target_dir, dry_run=args.dry_run, verbose=args.verbose)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
