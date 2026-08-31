from django.db import connection

from django_tenants.utils import get_tenant_model, schema_context

from axis_saas.models import Staff


class StaffTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    
    
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
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Middleware: staff_id={staff_id}, schema={schema_name}")
            logger.info(f"Credential exists: {credential is not None}, has_passkey: {credential.has_passkey if credential else False}")
            from axis_saas.models import Staff
from django.shortcuts import redirectCredential
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

                    return redirect('staff_profile_page')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Middleware error: {e}")
            request.staff_passkey_required = False

        return self.get_response(request)
