from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("axis_saas", "0013_staffcredential_two_factor_secret_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name='WebAuthnCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credential_id', models.TextField(unique=True)),
                ('public_key', models.TextField()),
                ('sign_count', models.IntegerField(default=0)),
                ('device_name', models.CharField(default='Unknown Device', max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('staff_credential', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webauthn_credentials', to='axis_saas.staffcredential')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.RemoveField(
            model_name='staffcredential',
            name='two_factor_enabled',
        ),
        migrations.RemoveField(
            model_name='staffcredential',
            name='two_factor_last_verified',
        ),
        migrations.RemoveField(
            model_name='staffcredential',
            name='two_factor_method',
        ),
        migrations.RemoveField(
            model_name='staffcredential',
            name='two_factor_secret',
        ),
    ]
