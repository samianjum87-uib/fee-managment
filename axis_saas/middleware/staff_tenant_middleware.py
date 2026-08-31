from django.db import connection
from django.shortcuts import redirect
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

        try:
            from axis_saas.models import StaffCredential
            with schema_context('public'):
                credential = StaffCredential.objects.filter(
                    staff_id=staff_id,
                    schema_name=schema_name,
                ).first()
            request.staff_passkey_required = credential is None or not credential.has_passkey
        except Exception:
            request.staff_passkey_required = False

        return self.get_response(request)
