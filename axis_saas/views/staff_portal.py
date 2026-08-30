import json
from datetime import datetime

from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from axis_saas.models import Notification, SchoolClass, Staff, StaffCredential, Student, StudentAttendance


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def staff_login(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        ip_key = f'staff_login_{get_client_ip(request)}'
        blocked_until = cache.get(f'{ip_key}_blocked_until')
        if blocked_until and blocked_until > timezone.now():
            return render(request, 'mobile/staff/login.html', {'error': 'Too many failed login attempts. Please try again in 15 minutes.'})

        attempts = cache.get(ip_key, 0)
        if attempts >= 10:
            cache.set(f'{ip_key}_blocked_until', timezone.now() + timezone.timedelta(minutes=15), 900)
            return render(request, 'mobile/staff/login.html', {'error': 'Too many failed login attempts. Please try again in 15 minutes.'})

        credential = StaffCredential.objects.filter(username=username).first()
        if credential and credential.is_active and (not credential.locked_until or credential.locked_until <= timezone.now()):
            if credential.check_password(password):
                from django_tenants.utils import schema_context
                with schema_context(credential.schema_name):
                    staff = Staff.objects.filter(pk=credential.staff_id, status='active').first()
                if staff is None:
                    cache.set(ip_key, attempts + 1, 60)
                    return render(request, 'mobile/staff/login.html', {'error': 'Your staff account is inactive or missing.'})

                cache.delete(ip_key)
                cache.delete(f'{ip_key}_blocked_until')
                credential.reset_failed_attempts()
                credential.last_login = timezone.now()
                credential.save(update_fields=['last_login', 'failed_attempts', 'locked_until'])

                request.session.flush()
                request.session['staff_id'] = staff.pk
                request.session['staff_schema_name'] = credential.schema_name
                request.session['staff_username'] = credential.username
                request.session['staff_role'] = staff.role
                request.session['staff_name'] = staff.full_name
                request.session.set_expiry(1800)
                request.session.modified = True
                return redirect('staff_dashboard')

        cache.set(ip_key, attempts + 1, 60)
        if credential:
            credential.increment_failed_attempts()
        return render(request, 'mobile/staff/login.html', {'error': 'Invalid username or password.'})

    return render(request, 'mobile/staff/login.html')


def staff_logout(request):
    request.session.flush()
    return redirect('staff_login')


def require_staff_login(view_func):
    def wrapped(request, *args, **kwargs):
        if not request.session.get('staff_id') or not request.session.get('staff_schema_name'):
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapped


def staff_accessible_classes(staff, schema_name):
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        classes = SchoolClass.objects.filter(Q(class_teacher=staff) | Q(class_subjects__teacher=staff)).distinct().order_by('name', 'section')
    return classes


@require_staff_login
def staff_dashboard(request):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
        classes = SchoolClass.objects.filter(Q(class_teacher=staff) | Q(class_subjects__teacher=staff)).distinct().order_by('name', 'section')
        today = timezone.localdate()
        student_count = Student.objects.filter(school_class__in=classes).count()
        attendance_today = StudentAttendance.objects.filter(date=today, school_class__in=classes).count()
        notifications = Notification.objects.filter(is_read=False).order_by('-created_at')[:5]

    return render(
        request,
        'mobile/staff/dashboard.html',
        {
            'staff': staff,
            'classes': classes,
            'student_count': student_count,
            'attendance_today': attendance_today,
            'notifications': notifications,
            'schema_name': schema_name,
        },
    )


@require_staff_login
def staff_classes(request):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
        classes = SchoolClass.objects.filter(Q(class_teacher=staff) | Q(class_subjects__teacher=staff)).distinct().order_by('name', 'section')
        classes = list(classes)
        for school_class in classes:
            school_class.student_count = Student.objects.filter(school_class=school_class).count()
    return render(request, 'mobile/staff/classes.html', {'staff': staff, 'classes': classes})


@require_staff_login
def staff_class_students(request, class_id):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        if not (school_class.class_teacher_id == staff.pk or school_class.class_subjects.filter(teacher=staff).exists()):
            return render(request, 'mobile/staff/403.html', status=403)
        students = Student.objects.filter(school_class=school_class).order_by('roll_number')
        today = timezone.localdate()
        attendance_map = dict(
            StudentAttendance.objects.filter(school_class=school_class, date=today).values_list('student_id', 'status')
        )
        for student in students:
            student.attendance_status = attendance_map.get(student.pk, 'present')
    return render(request, 'mobile/staff/class_students.html', {'staff': staff, 'school_class': school_class, 'students': students, 'attendance_map': attendance_map})


@require_staff_login
def staff_attendance_list(request):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
        classes = SchoolClass.objects.filter(Q(class_teacher=staff) | Q(class_subjects__teacher=staff)).distinct().order_by('name', 'section')
    return render(request, 'mobile/staff/attendance.html', {'staff': staff, 'classes': classes})


@require_staff_login
def staff_attendance_mark(request, class_id, attendance_date):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        if not (school_class.class_teacher_id == staff.pk or school_class.class_subjects.filter(teacher=staff).exists()):
            return render(request, 'mobile/staff/403.html', status=403)
        if request.method == 'POST':
            students = Student.objects.filter(school_class=school_class).order_by('roll_number')
            for student in students:
                choice = request.POST.get(f'status_{student.pk}', 'present')
                defaults = {'present': 'present', 'absent': 'absent', 'late': 'late'}
                status = defaults.get(choice, 'present')
                remarks = request.POST.get(f'remarks_{student.pk}', '')
                StudentAttendance.objects.update_or_create(
                    student=student,
                    date=datetime.strptime(attendance_date, '%Y-%m-%d').date(),
                    defaults={'school_class': school_class, 'status': status, 'teacher': staff, 'remarks': remarks},
                )
            return redirect('staff_attendance_list')

        students = Student.objects.filter(school_class=school_class).order_by('roll_number')
        attendance_day = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        marks = dict(StudentAttendance.objects.filter(school_class=school_class, date=attendance_day).values_list('student_id', 'status'))
        for student in students:
            student.attendance_status = marks.get(student.pk, 'present')
    return render(request, 'mobile/staff/attendance_mark.html', {'staff': staff, 'school_class': school_class, 'students': students, 'attendance_date': attendance_date, 'marks': marks})


@require_staff_login
@require_http_methods(['GET'])
def staff_profile(request):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = Staff.objects.get(pk=request.session['staff_id'])
    with schema_context('public'):
        credential = StaffCredential.objects.filter(staff_id=staff.pk, schema_name=schema_name).first()
    if credential is not None:
        credential.raw_password = getattr(staff, '_generated_password', None) or getattr(credential, 'raw_password', None)
    return render(request, 'mobile/staff/profile.html', {'staff': staff, 'credential': credential})


@require_staff_login
@require_http_methods(['POST'])
def staff_change_password(request):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    old_password = request.POST.get('old_password')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')
    with schema_context('public'):
        credential = StaffCredential.objects.filter(staff_id=request.session['staff_id'], schema_name=schema_name).first()
        if not credential or not credential.check_password(old_password):
            return JsonResponse({'success': False, 'message': 'Current password is incorrect.'}, status=400)
        if new_password != confirm_password:
            return JsonResponse({'success': False, 'message': 'New passwords do not match.'}, status=400)
        if len(new_password) < 12 or not any(ch.isupper() for ch in new_password) or not any(ch.isdigit() for ch in new_password) or not any(ch in '!@#$%^&*' for ch in new_password):
            return JsonResponse({'success': False, 'message': 'Password must contain at least 12 chars, one uppercase, one digit, and one symbol.'}, status=400)
        credential.set_password(new_password)
        credential.save(update_fields=['password'])
        return JsonResponse({'success': True, 'message': 'Password updated successfully.'})


@require_staff_login
@require_http_methods(['GET'])
def staff_notifications(request):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        notifications = Notification.objects.all().order_by('-created_at')
    return render(request, 'mobile/staff/notifications.html', {'notifications': notifications})


@require_staff_login
@require_http_methods(['POST'])
def staff_mark_notification_read(request, notif_id):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        notification = get_object_or_404(Notification, pk=notif_id)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@require_staff_login
def staff_student_profile(request, student_id):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
        student = get_object_or_404(Student, pk=student_id)
        if student.school_class and not (student.school_class.class_teacher_id == staff.pk or student.school_class.class_subjects.filter(teacher=staff).exists()):
            return render(request, 'mobile/staff/403.html', status=403)
        attendance_summary = StudentAttendance.objects.filter(student=student).order_by('-date')[:10]
    return render(request, 'mobile/staff/student_profile.html', {'staff': staff, 'student': student, 'attendance_summary': attendance_summary})


@require_staff_login
def staff_api_classes(request):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = Staff.objects.get(pk=request.session['staff_id'])
        classes = SchoolClass.objects.filter(Q(class_teacher=staff) | Q(class_subjects__teacher=staff)).distinct().annotate(student_count=Count('students')).order_by('name', 'section')
        payload = [
            {'id': cls.pk, 'name': str(cls), 'student_count': cls.student_count}
            for cls in classes
        ]
    return JsonResponse({'classes': payload})


@require_staff_login
def staff_api_attendance(request, class_id, attendance_date):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        allowed = school_class.class_teacher_id == staff.pk or school_class.class_subjects.filter(teacher=staff).exists()
        if not allowed:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        records = list(StudentAttendance.objects.filter(school_class=school_class, date=attendance_date).values('student_id', 'status', 'remarks'))
    return JsonResponse({'attendance': records})


@require_staff_login
@require_http_methods(['POST'])
def staff_api_attendance_submit(request, class_id, attendance_date):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        allowed = school_class.class_teacher_id == staff.pk or school_class.class_subjects.filter(teacher=staff).exists()
        if not allowed:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        for record in payload.get('attendance', []):
            student_id = record.get('student_id')
            status = record.get('status', 'present')
            if student_id is None:
                continue
            student = Student.objects.filter(pk=student_id, school_class=school_class).first()
            if student is None:
                continue
            StudentAttendance.objects.update_or_create(
                student=student,
                date=datetime.strptime(attendance_date, '%Y-%m-%d').date(),
                defaults={'school_class': school_class, 'status': status, 'teacher': staff, 'remarks': record.get('remarks', '')},
            )
    return JsonResponse({'success': True})


@require_staff_login
def staff_api_profile(request):
    schema_name = request.session['staff_schema_name']
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        staff = get_object_or_404(Staff, pk=request.session['staff_id'])
    return JsonResponse({'id': staff.pk, 'name': staff.full_name, 'role': staff.role, 'email': staff.email, 'phone': staff.phone})
