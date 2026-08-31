urlpatterns = [
    # WebAuthn staff endpoints
    path('staff/security/webauthn/register/options/', staff_views.staff_webauthn_registration_options, name='staff_webauthn_registration_options'),
    path('staff/security/webauthn/register/verify/', staff_views.staff_webauthn_registration_verify, name='staff_webauthn_registration_verify'),
    path('staff/security/webauthn/auth/options/', staff_views.staff_webauthn_authentication_options, name='staff_webauthn_authentication_options'),
    path('staff/security/webauthn/auth/verify/', staff_views.staff_webauthn_authentication_verify, name='staff_webauthn_authentication_verify'),
    path('staff/security/webauthn/remove/<int:credential_id>/', staff_views.staff_webauthn_remove_credential, name='staff_webauthn_remove_credential'),

    path('admin/', admin.site.urls),
        path('voucher/html/<int:student_id>/', voucher_html_api, name='voucher_html'),
]