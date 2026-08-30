from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("axis_saas", "0009_staffcredential_visible_password"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="studentattendance",
            old_name="axis_saas_st_school__7b4d2a_idx",
            new_name="axis_saas_s_school__9ce8de_idx",
        ),
        migrations.AddField(
            model_name="staffcredential",
            name="two_factor_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="staffcredential",
            name="two_factor_last_verified",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="staffcredential",
            name="two_factor_method",
            field=models.CharField(
                choices=[
                    ("none", "Disabled"),
                    ("face", "Face Lock"),
                    ("fingerprint", "Fingerprint"),
                    ("both", "Face + Fingerprint"),
                ],
                default="none",
                max_length=20,
            ),
        ),
    ]
