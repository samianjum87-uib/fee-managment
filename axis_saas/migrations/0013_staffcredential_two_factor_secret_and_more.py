from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("axis_saas", "0012_repair_staffcredential_two_factor_secret"),
    ]

    operations = [
        migrations.AlterField(
            model_name="staffcredential",
            name="two_factor_method",
            field=models.CharField(
                choices=[("none", "Disabled"), ("authenticator", "Authenticator App")],
                default="none",
                max_length=20,
            ),
        ),
    ]
