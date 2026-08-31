from django.db import connection

from django_tenants.utils import get_tenant_model, schema_context

from axis_saas.models import Staff, StaffCredential
from django.shortcuts import redirect
import logging
from django.conf import settings
logger = logging.getLogger(__name__)


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


        cached_token = None
        try:
            from django.core.cache import cache
            cached_token = cache.get(f'staff_session_token:{schema_name}:{staff_id}')
        except Exception:
            cached_token = None

        if not settings.DEBUG:
            session_token = request.session.get('staff_session_token')
            token_invalid = not session_token or cached_token in ['logged_out'] or cached_token != session_token
        else:
            # In development, skip token validation
            session_token = None
            token_invalid = False

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

        if not settings.DEBUG:
            try:
                with schema_context(schema_name):
                    request.staff = Staff.objects.filter(pk=staff_id, status='active').first()
            except Exception:
                request.staff = None
        
            if request.staff is None:
                request.session.flush()
                return redirect('staff_login')
        else:
            # In development, bypass staff existence check to allow access.
            # We still need request.staff for templates, so we create a dummy.
            try:
                request.staff = Staff.objects.get(pk=staff_id)
            except Staff.DoesNotExist:
                # If staff doesn't exist, create a dummy with minimal fields.
                request.staff = Staff(pk=staff_id, full_name='Developer', status='active')


        # Passkey enforcement disabled to allow immediate login.
        request.staff_passkey_required = False
        try:

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
            logger = logging.getLogger(__name__)
            logger.error(f"Middleware error: {e}")
            request.staff_passkey_required = False

        return self.get_response(request)
