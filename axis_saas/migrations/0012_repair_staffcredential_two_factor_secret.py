from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("axis_saas", "0011_repair_staffcredential_two_factor_columns"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "axis_saas_staffcredential" '
                'ADD COLUMN IF NOT EXISTS "two_factor_secret" varchar(64) NULL;'
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
