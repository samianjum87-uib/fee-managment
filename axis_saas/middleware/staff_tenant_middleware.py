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

        staff_id = request.session.get('staff_id')
        schema_name = request.session.get('staff_schema_name')
        if not staff_id or not schema_name:
            request.session.flush()
            return redirect('staff_login')

        session_token = request.session.get('staff_session_token')
        cached_token = None
        try:
            from django.core.cache import cache
            cached_token = cache.get(f'staff_session_token:{schema_name}:{staff_id}')
        except Exception:
            cached_token = None

        is_2fa_submission = request.path_info == '/portal/staff/security/submit-2fa/'
        is_pending_2fa = request.session.get('staff_2fa_pending') is True
        token_invalid = not session_token or cached_token in ['logged_out'] or cached_token != session_token
        if token_invalid and not (is_2fa_submission and is_pending_2fa and session_token):
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
            request.staff_2fa_required = credential is None or not credential.two_factor_enabled
        except Exception:
            request.staff_2fa_required = False

        return self.get_response(request)
