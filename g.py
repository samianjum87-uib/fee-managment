#!/usr/bin/env python3
"""
axis_patcher_final.py - Final comprehensive fix for Staff Portal passkey implementation.

This script applies all necessary corrections to:
  - axis_saas/views/staff_portal.py
  - axis_saas/middleware/staff_tenant_middleware.py

It fixes syntax errors, duplicates, and ensures the passkey flow works correctly.

Usage:
    python axis_patcher_final.py [--dry-run] [--verbose] [--target-dir PATH]
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# ----------------------------------------------------------------------
# PATCHES
# ----------------------------------------------------------------------

PATCHES: List[Tuple[str, str, str, str]] = []

# 1. MIDDLEWARE: Replace __call__ with corrected version.
MIDDLEWARE_FILE = "axis_saas/middleware/staff_tenant_middleware.py"

MIDDLEWARE_CALL_SEARCH = r'def __call__\(self, request\):.*?(?=\n\s*def |\Z)'
MIDDLEWARE_CALL_REPLACE = r'''
    def __call__(self, request):
        if not request.path_info.startswith('/portal/staff/'):
            return self.get_response(request)

        request.tenant = None
        request.staff = None

        if request.path_info in ['/portal/staff/login/', '/portal/staff/logout/']:
            connection.set_schema_to_public()
            return self.get_response(request)

        is_webauthn_auth = request.path_info in [
            '/portal/staff/security/webauthn/auth/options/',
            '/portal/staff/security/webauthn/auth/verify/',
        ]
        staff_id = request.session.get('staff_id')
        schema_name = request.session.get('staff_schema_name')
        if (not staff_id or not schema_name) and not is_webauthn_auth:
            request.session.flush()
            return redirect('staff_login')

        session_token = request.session.get('staff_session_token')
        cached_token = None
        try:
            from django.core.cache import cache
            cached_token = cache.get(f'staff_session_token:{schema_name}:{staff_id}')
        except Exception:
            cached_token = None

        is_webauthn_auth = request.path_info in [
            '/portal/staff/security/webauthn/auth/options/',
            '/portal/staff/security/webauthn/auth/verify/',
        ]
        is_pending_webauthn = request.session.get('staff_pending_webauthn') is True
        has_staff_session = bool(staff_id and schema_name)
        token_invalid = not session_token or cached_token in ['logged_out'] or cached_token != session_token
        if token_invalid and not (
            is_webauthn_auth and (
                is_pending_webauthn or not has_staff_session
            )
        ):
            request.session.flush()
            return redirect('staff_login')

        TenantModel = get_tenant_model()
        try:
            tenant = TenantModel.objects.get(schema_name=schema_name)
        except TenantModel.DoesNotExist:
            request.session.flush()
            return redirect('staff_login')

        request.tenant = tenant
        connection.set_tenant(tenant)
        try:
            with schema_context(schema_name):
                request.staff = Staff.objects.filter(pk=staff_id, status='active').first()
        except Exception:
            request.staff = None

        if request.staff is None:
            request.session.flush()
            return redirect('staff_login')

        # Determine if passkey is required and enforce redirect
        try:
            from axis_saas.models import StaffCredential
            with schema_context('public'):
                credential = StaffCredential.objects.filter(
                    staff_id=staff_id,
                    schema_name=schema_name,
                ).first()
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
                    from django.shortcuts import redirect
                    return redirect('staff_profile_page')
        except Exception:
            request.staff_passkey_required = False

        return self.get_response(request)
'''
PATCHES.append((MIDDLEWARE_FILE, MIDDLEWARE_CALL_SEARCH, MIDDLEWARE_CALL_REPLACE,
                "Rewrite middleware __call__ with corrected logic and redirect"))

# 2. STAFF_PORTAL: Fix staff_login function (remove duplicate set_expiry/modified).
STAFF_PORTAL = "axis_saas/views/staff_portal.py"

# We'll match the whole staff_login function and replace with a corrected version.
STAFF_LOGIN_SEARCH = r'def staff_login\(request\):.*?(?=\ndef staff_logout|\Z)'
STAFF_LOGIN_REPLACE = r'''
def staff_login(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        ip_key = f'staff_login_{get_client_ip(request)}'
        blocked_until = cache.get(f'{ip_key}_blocked_until')
        if blocked_until and blocked_until > timezone.now():
            return render(request, 'mobile/staff/login.html', {'error': 'Too many failed login attempts. Please try again in 15 minutes.'})

        attempts = cache.get(ip_key, 0)
        if attempts >= 10:
            cache.set(f'{ip_key}_blocked_until', timezone.now() + timezone.timedelta(minutes=15), 900)
            return render(request, 'mobile/staff/login.html', {'error': 'Too many failed login attempts. Please try again in 15 minutes.'})

        credential = StaffCredential.objects.filter(username=username).first()
        if credential and credential.is_active and (not credential.locked_until or credential.locked_until <= timezone.now()):
            if credential.check_password(password):
                with schema_context(credential.schema_name):
                    staff = Staff.objects.filter(pk=credential.staff_id).first()
                if staff is None or staff.status != 'active':
                    cache.set(ip_key, attempts + 1, 60)
                    return render(request, 'mobile/staff/login.html', {'error': 'Your staff account is inactive or missing.'})

                cache.delete(ip_key)
                cache.delete(f'{ip_key}_blocked_until')
                credential.reset_failed_attempts()
                credential.last_login = timezone.now()
                credential.save(update_fields=['last_login', 'failed_attempts', 'locked_until'])

                request.session.flush()
                request.session['school_admin_authenticated'] = False
                request.session['school_admin_schema'] = ''
                request.session['staff_id'] = staff.pk
                request.session['staff_schema_name'] = credential.schema_name
                request.session['staff_username'] = credential.username
                request.session['staff_role'] = staff.role
                request.session['staff_name'] = staff.full_name
                request.session['staff_session_token'] = uuid.uuid4().hex
                request.session.set_expiry(1800)
                request.session.modified = True

                session_keys = cache.get(f'staff_session_keys:{credential.schema_name}:{staff.pk}', [])
                if isinstance(session_keys, str):
                    session_keys = [session_keys]
                session_keys = [k for k in list(session_keys) if k]
                if request.session.session_key:
                    session_keys.append(request.session.session_key)
                cache.set(f'staff_session_keys:{credential.schema_name}:{staff.pk}', list(dict.fromkeys(session_keys)), 1800)
                cache.set(f'staff_online:{credential.schema_name}:{staff.pk}', request.session.session_key, 1800)
                cache.set(f'staff_session_token:{credential.schema_name}:{staff.pk}', request.session['staff_session_token'], 1800)
                return redirect('staff_dashboard')

        cache.set(ip_key, attempts + 1, 60)
        if credential:
            credential.increment_failed_attempts()
        return render(request, 'mobile/staff/login.html', {'error': 'Invalid username or password.'})

    return render(request, 'mobile/staff/login.html')
'''
PATCHES.append((STAFF_PORTAL, STAFF_LOGIN_SEARCH, STAFF_LOGIN_REPLACE,
                "Fix staff_login to remove duplicate set_expiry and modified"))

# 3. STAFF_PORTAL: Fix staff_webauthn_authentication_verify (remove duplicate set_expiry/modified).
AUTH_VERIFY_SEARCH = r'def staff_webauthn_authentication_verify\(request\):.*?(?=\n@require_staff_login|\ndef |\Z)'
AUTH_VERIFY_REPLACE = r'''
@require_http_methods(['POST'])
def staff_webauthn_authentication_verify(request):
    logger.info(f"Authentication verify called for credential {request.session.get('staff_username')}")
    expected_challenge = request.session.get('staff_webauthn_auth_challenge')
    login_username = request.session.get('staff_webauthn_login_username')
    login_staff_id = request.session.get('staff_webauthn_login_staff_id')
    login_schema_name = request.session.get('staff_webauthn_login_schema_name')
    staff_id = request.session.get('staff_id')
    schema_name = request.session.get('staff_schema_name')

    if not expected_challenge:
        return JsonResponse({'success': False, 'message': 'Passkey challenge expired. Please sign in again.'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid passkey payload.'}, status=400)

    credential_id = payload.get('id')
    if not credential_id:
        return JsonResponse({'success': False, 'message': 'Passkey identifier missing.'}, status=400)

    with schema_context('public'):
        webauthn_credential = WebAuthnCredential.objects.filter(credential_id=credential_id, is_active=True).select_related('staff_credential').first()
        if webauthn_credential is None:
            return JsonResponse({'success': False, 'message': 'Passkey not recognized.'}, status=404)
        if login_username and webauthn_credential.staff_credential.username != login_username:
            return JsonResponse({'success': False, 'message': 'This passkey does not belong to the provided username.'}, status=403)
        if login_staff_id and str(webauthn_credential.staff_credential.staff_id) != str(login_staff_id):
            return JsonResponse({'success': False, 'message': 'This passkey is not registered for the selected account.'}, status=403)
        if login_schema_name and webauthn_credential.staff_credential.schema_name != login_schema_name:
            return JsonResponse({'success': False, 'message': 'This passkey belongs to a different tenant.'}, status=403)
        verification = verify_authentication_response(
            credential=payload,
            expected_challenge=base64url_to_bytes(expected_challenge),
            expected_rp_id=_staff_compute_rp_id(request),
            expected_origin=_staff_expected_origins(request),
            credential_public_key=base64url_to_bytes(webauthn_credential.public_key),
            credential_current_sign_count=webauthn_credential.sign_count,
            require_user_verification=True,
        )
        webauthn_credential.sign_count = verification.new_sign_count
        webauthn_credential.last_used = timezone.now()
        webauthn_credential.save(update_fields=['sign_count', 'last_used'])

        target_staff_id = int(webauthn_credential.staff_credential.staff_id)
        target_schema_name = webauthn_credential.staff_credential.schema_name
        request.session['staff_id'] = target_staff_id
        request.session['staff_schema_name'] = target_schema_name
        request.session['staff_username'] = webauthn_credential.staff_credential.username
        request.session['staff_pending_webauthn'] = False
        request.session['staff_session_token'] = uuid.uuid4().hex
        request.session.set_expiry(1800)
        request.session.modified = True

        with schema_context(target_schema_name):
            staff = Staff.objects.filter(pk=target_staff_id).first()
            if staff:
                request.session['staff_role'] = staff.role
                request.session['staff_name'] = staff.full_name

        token = request.session['staff_session_token']
        cache.set(f'staff_session_token:{target_schema_name}:{target_staff_id}', token, 1800)
        session_keys = cache.get(f'staff_session_keys:{target_schema_name}:{target_staff_id}', [])
        if isinstance(session_keys, str):
            session_keys = [session_keys]
        session_keys = [k for k in list(session_keys) if k]
        if request.session.session_key:
            session_keys.append(request.session.session_key)
        cache.set(f'staff_session_keys:{target_schema_name}:{target_staff_id}', list(dict.fromkeys(session_keys)), 1800)
        cache.set(f'staff_online:{target_schema_name}:{target_staff_id}', request.session.session_key, 1800)

    request.session.pop('staff_webauthn_auth_challenge', None)
    request.session.pop('staff_webauthn_login_username', None)
    request.session.pop('staff_webauthn_login_staff_id', None)
    request.session.pop('staff_webauthn_login_schema_name', None)
    logger.info('Authentication success, returning redirect')
    return JsonResponse({'success': True, 'message': 'Passkey verified successfully.', 'redirect': '/portal/staff/dashboard/'})
'''
PATCHES.append((STAFF_PORTAL, AUTH_VERIFY_SEARCH, AUTH_VERIFY_REPLACE,
                "Fix staff_webauthn_authentication_verify to remove duplicate set_expiry"))

# 4. STAFF_PORTAL: Ensure staff_webauthn_authentication_options has correct decorator and logic.
AUTH_OPTIONS_SEARCH = r'def staff_webauthn_authentication_options\(request\):.*?(?=\n@require_http_methods|\ndef |\Z)'
AUTH_OPTIONS_REPLACE = r'''
@require_http_methods(['POST'])
def staff_webauthn_authentication_options(request):
    data = {}
    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            data = {}
    username = (data.get('username') or request.POST.get('username') or '').strip()

    # Require username for passkey login
    if not username:
        return JsonResponse({'error': 'Username is required for passkey login.'}, status=400)

    with schema_context('public'):
        credential = StaffCredential.objects.filter(username=username, is_active=True).first()
        if credential is None:
            return JsonResponse({'error': 'Account not found.'}, status=404)
        passkeys = list(WebAuthnCredential.objects.filter(staff_credential=credential, is_active=True))
        if not passkeys:
            return JsonResponse({'error': 'No passkeys registered for this account.'}, status=403)

        # Store login context in session
        request.session['staff_webauthn_login_username'] = credential.username
        request.session['staff_webauthn_login_staff_id'] = credential.staff_id
        request.session['staff_webauthn_login_schema_name'] = credential.schema_name

    challenge = secrets.token_bytes(32)
    request.session['staff_webauthn_auth_challenge'] = bytes_to_base64url(challenge)
    allow_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(item.credential_id), type='public-key')
        for item in passkeys
    ]
    options = generate_authentication_options(
        rp_id=_staff_compute_rp_id(request),
        challenge=challenge,
        timeout=60000,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return JsonResponse(json.loads(options_to_json(options)))
'''
PATCHES.append((STAFF_PORTAL, AUTH_OPTIONS_SEARCH, AUTH_OPTIONS_REPLACE,
                "Fix staff_webauthn_authentication_options with correct decorator and logic"))

# 5. STAFF_PORTAL: Ensure staff_webauthn_registration_verify has proper error handling.
REG_VERIFY_SEARCH = r'def staff_webauthn_registration_verify\(request\):.*?(?=\n@require_http_methods|\ndef |\Z)'
REG_VERIFY_REPLACE = r'''
@require_staff_login
@require_http_methods(['POST'])
def staff_webauthn_registration_verify(request):
    logger.info(f"Registration verify called for staff {request.session.get('staff_id')}")
    schema_name = request.session.get('staff_schema_name')
    staff_id = request.session.get('staff_id')
    expected_challenge = request.session.get('staff_webauthn_registration_challenge')
    if not schema_name or not staff_id or not expected_challenge:
        return JsonResponse({'success': False, 'message': 'Registration session expired.'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid registration payload.'}, status=400)

    with schema_context('public'):
        credential = StaffCredential.objects.filter(staff_id=staff_id, schema_name=schema_name).first()
        if credential is None:
            return JsonResponse({'success': False, 'message': 'Credential not found.'}, status=404)

        try:
            verification = verify_registration_response(
                credential=payload,
                expected_challenge=base64url_to_bytes(expected_challenge),
                expected_rp_id=_staff_compute_rp_id(request),
                expected_origin=_staff_expected_origins(request),
                require_user_verification=True,
            )
        except Exception as e:
            logger.error(f"WebAuthn registration verification failed: {e}")
            return JsonResponse({'success': False, 'message': f'Verification error: {str(e)}'}, status=400)

        logger.info(f"WebAuthn registration verification succeeded for credential_id={bytes_to_base64url(verification.credential_id)}")

        try:
            obj, created = WebAuthnCredential.objects.update_or_create(
                credential_id=bytes_to_base64url(verification.credential_id),
                defaults={
                    'staff_credential': credential,
                    'public_key': bytes_to_base64url(verification.credential_public_key),
                    'sign_count': verification.sign_count,
                    'device_name': payload.get('deviceName', 'Unknown Device'),
                    'is_active': True,
                },
            )
            if not created and obj.is_active is False:
                obj.is_active = True
                obj.save(update_fields=['is_active'])
        except Exception as e:
            logger.error(f"Failed to save WebAuthn credential: {e}")
            return JsonResponse({'success': False, 'message': f'Database error: {str(e)}'}, status=500)

        request.session.pop('staff_webauthn_registration_challenge', None)
        logger.info('Registration success, returning success response')
        return JsonResponse({'success': True, 'message': 'Passkey registered successfully.'})
'''
PATCHES.append((STAFF_PORTAL, REG_VERIFY_SEARCH, REG_VERIFY_REPLACE,
                "Fix staff_webauthn_registration_verify with proper error handling"))

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

        pattern = re.compile(search, re.DOTALL)
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

    parser = argparse.ArgumentParser(description="Final comprehensive fixes for Staff Portal passkey implementation.")
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
            print("\nAll final fixes applied successfully. Please restart your server.")
        else:
            print("\nSome fixes failed. See logs above.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
