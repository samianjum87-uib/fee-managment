from django.test import TestCase
from django_tenants.utils import schema_context

from axis_saas.models import SchoolClient, Staff, StaffCredential


class StaffPortalTests(TestCase):
    def setUp(self):
        self.tenant = SchoolClient.objects.create(
            schema_name='staffportal-test',
            name='Staff Portal Test School',
            admin_username='admin',
            admin_password='Admin@123',
        )

    def test_staff_credentials_are_generated_and_login_works(self):
        with schema_context(self.tenant.schema_name):
            staff = Staff.objects.create(
                first_name='Ayesha',
                last_name='Khan',
                email='ayesha@example.com',
                job_title='Mathematics Teacher',
                department='teaching',
                phone='03001234567',
                role='teacher',
            )

        credential = StaffCredential.objects.get(staff_id=staff.id, schema_name=self.tenant.schema_name)
        self.assertTrue(credential.username.startswith('ayesha.khan'))
        self.assertTrue(credential.is_active)
        self.assertTrue(credential.check_password(credential.raw_password))

        response = self.client.post(
            '/portal/staff/login/',
            {'username': credential.username, 'password': credential.raw_password},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get('staff_id'), staff.id)
        self.assertEqual(self.client.session.get('staff_schema_name'), self.tenant.schema_name)

    def test_webauthn_registration_options_require_platform_authenticator(self):
        with schema_context(self.tenant.schema_name):
            staff = Staff.objects.create(
                first_name='Bilal',
                last_name='Ahmad',
                email='bilal@example.com',
                job_title='Accountant',
                department='support',
                phone='03009876543',
                role='class_teacher',
            )

        credential = StaffCredential.objects.get(staff_id=staff.id, schema_name=self.tenant.schema_name)
        session = self.client.session
        session['staff_id'] = staff.id
        session['staff_schema_name'] = self.tenant.schema_name
        session.save()

        response = self.client.post('/portal/staff/security/webauthn/register/options/', secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['authenticatorSelection']['authenticatorAttachment'], 'platform')
        self.assertEqual(data['authenticatorSelection']['userVerification'], 'required')
        self.assertIn('rpId', data)
