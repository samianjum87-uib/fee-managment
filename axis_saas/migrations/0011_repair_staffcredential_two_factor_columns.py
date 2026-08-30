from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("axis_saas", "0010_rename_axis_saas_st_school__7b4d2a_idx_axis_saas_s_school__9ce8de_idx_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'ALTER TABLE "axis_saas_staffcredential" '
                'ADD COLUMN IF NOT EXISTS "two_factor_enabled" boolean '
                'NOT NULL DEFAULT false;'
                'ALTER TABLE "axis_saas_staffcredential" '
                'ADD COLUMN IF NOT EXISTS "two_factor_last_verified" '
                'timestamp with time zone NULL;'
                'ALTER TABLE "axis_saas_staffcredential" '
                'ADD COLUMN IF NOT EXISTS "two_factor_method" varchar(20) '
                "NOT NULL DEFAULT 'none';"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
