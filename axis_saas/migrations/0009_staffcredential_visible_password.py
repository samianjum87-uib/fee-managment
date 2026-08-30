from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("axis_saas", "0008_staff_cnic"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffcredential",
            name="visible_password",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]