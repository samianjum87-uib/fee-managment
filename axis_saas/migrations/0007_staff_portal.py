from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('axis_saas', '0006_fix_sync'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=150, unique=True)),
                ('password', models.CharField(max_length=128)),
                ('staff_id', models.PositiveIntegerField()),
                ('schema_name', models.CharField(max_length=63)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('failed_attempts', models.PositiveIntegerField(default=0)),
                ('locked_until', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['username'],
            },
        ),
        migrations.AddField(
            model_name='staff',
            name='can_mark_attendance',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='staff',
            name='can_view_fees',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='staff',
            name='role',
            field=models.CharField(choices=[('teacher', 'Teacher'), ('class_teacher', 'Class Teacher'), ('subject_teacher', 'Subject Teacher'), ('admin', 'Admin')], default='teacher', max_length=30),
        ),
        migrations.CreateModel(
            name='StudentAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('status', models.CharField(choices=[('present', 'Present'), ('absent', 'Absent'), ('late', 'Late'), ('holiday', 'Holiday')], default='present', max_length=20)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('school_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to='axis_saas.schoolclass')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to='axis_saas.student')),
                ('teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marked_attendance', to='axis_saas.staff')),
            ],
            options={
                'ordering': ['-date', 'student__name'],
            },
        ),
        migrations.AddIndex(
            model_name='studentattendance',
            index=models.Index(fields=['school_class', 'date'], name='axis_saas_st_school__7b4d2a_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='studentattendance',
            unique_together={('student', 'date')},
        ),
    ]
