from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("axis_saas", "0014_remove_totp_webauthn"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name="staffcredential",
                    name="two_factor_enabled",
                ),
                migrations.RemoveField(
                    model_name="staffcredential",
                    name="two_factor_last_verified",
                ),
                migrations.RemoveField(
                    model_name="staffcredential",
                    name="two_factor_method",
                ),
            ],
        ),
    ]
