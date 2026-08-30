from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('axis_saas', '0007_staff_portal'),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='cnic',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
