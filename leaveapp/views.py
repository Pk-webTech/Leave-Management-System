import calendar
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import update_session_auth_hash
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date

from .models import (
    EmployeeProfile,
    LeaveRequest,
    LeaveQuota,
    LeaveApproval
)
from .forms import (
    LoginForm, 
    CreateUserForm, 
    LeaveRequestForm,
    LeaveActionForm, 
    ProfileUpdateForm,
    StyledPasswordChangeForm,
    StyledSetPasswordForm,
    ForgotPasswordForm
)
from .decorators import admin_required, manager_required, employee_required, login_required_custom

# FIXED: Updated utils imports for Phase 3
from .utils import (
    generate_temp_password,
    get_all_subordinates,
    get_or_create_quota,
    get_approver_for_level,
)

# FIXED: Added workflow imports for Phase 3
from .workflow import (
    start_leave_approval,
    process_leave_decision,
)

from .emails import (
    send_account_created_email,
    send_password_reset_by_admin_email,
    send_password_reset_link_email,
    send_password_changed_confirmation_email,
    send_leave_applied_email,
    send_leave_escalated_email,
    send_leave_final_approved_email,
    send_leave_rejected_email,
)

# ─────────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                    return redirect('dashboard_redirect')
                else:
                    messages.error(request, 'Your account has been deactivated. Contact admin.')
            else:
                messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('login')
    return redirect('dashboard_redirect')


@login_required_custom
def force_change_password(request):
    profile = request.user.profile

    if not profile.must_change_password:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = StyledPasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():
            print("FORM VALID")

            user = form.save()

            profile.must_change_password = False
            profile.save()

            update_session_auth_hash(request, user)

            send_password_changed_confirmation_email(
                request, 
                user
            )

            messages.success(
                request,
                "Password changed successfully."
            )

            return redirect('dashboard_redirect')
        else:
            print(form.errors)

    else:
        form = StyledPasswordChangeForm(request.user)

    return render(
        request,
        'auth/force_change_password.html',
        {'form': form}
    )


def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            users = User.objects.filter(email=email, is_active=True)
            for user in users:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_link = request.build_absolute_uri(
                    reverse('reset_password_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                send_password_reset_link_email(request, user, reset_link)
            
            messages.success(request, 'If an account with that email exists, a password reset link has been sent.')
            return redirect('login')
    else:
        form = ForgotPasswordForm()
        
    return render(request, 'auth/forgot_password.html', {'form': form})


def reset_password_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = StyledSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()

                user.profile.must_change_password = False
                user.profile.save()

                messages.success(
                    request,
                    'Your password has been reset successfully. You can now login.'
                )

                return redirect('login')
        else:
            form = StyledSetPasswordForm(user)
        return render(request, 'auth/reset_password_confirm.html', {'form': form})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return render(request, 'auth/reset_password_invalid.html')


@login_required_custom
def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.user.groups.filter(name='Admin').exists():
        return redirect('admin_dashboard')

    elif request.user.groups.filter(name='Manager').exists():
        return redirect('manager_dashboard')

    elif request.user.groups.filter(name='Employee').exists():
        return redirect('employee_dashboard')

    else:
        messages.warning(
            request,
            'Your account has no role assigned. Contact the administrator.'
        )
        return render(request, 'no_role.html')

# ─────────────────────────────────────────────
# ADMIN VIEWS
# ─────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    total_users = User.objects.filter(is_superuser=False).count()
    total_managers = User.objects.filter(groups__name='Manager').count()
    total_employees = User.objects.filter(
        groups__name='Employee'
    ).distinct().count()

    total_leaves = LeaveRequest.objects.count()
    approved_leaves = LeaveRequest.objects.filter(status='APPROVED').count()
    pending_leaves = LeaveRequest.objects.filter(status='PENDING').count()
    rejected_leaves = LeaveRequest.objects.filter(status='REJECTED').count()
    cancelled_leaves = LeaveRequest.objects.filter(status='CANCELLED').count()

    recent_leaves = LeaveRequest.objects.select_related(
        'employee'
    ).order_by('-applied_on')[:10]

    recent_users = User.objects.filter(
        is_superuser=False
    ).order_by('-date_joined')[:5]

    my_pending_approvals = LeaveRequest.objects.filter(
        status='PENDING',
        approvals__approver=request.user,
        approvals__status='PENDING'
    ).select_related('employee').distinct()

    context = {
        'total_users': total_users,
        'total_managers': total_managers,
        'total_employees': total_employees,
        'total_leaves': total_leaves,
        'approved_leaves': approved_leaves,
        'pending_leaves': pending_leaves,
        'rejected_leaves': rejected_leaves,
        'cancelled_leaves': cancelled_leaves,
        'recent_leaves': recent_leaves,
        'recent_users': recent_users,

        'my_pending_approvals': my_pending_approvals,
        'my_pending_count': my_pending_approvals.count(),
    }

    return render(
        request,
        'admin/admin_dashboard.html',
        context
    )


@admin_required
def admin_leave_details(request, leave_id):

    leave = get_object_or_404(
        LeaveRequest,
        id=leave_id
    )

    current_approval = leave.approvals.filter(
        level=leave.current_level
    ).first()

    is_my_approval = (
        current_approval
        and current_approval.approver == request.user
        and current_approval.status == 'PENDING'
        and leave.status == 'PENDING'
    )

    form = LeaveActionForm()

    if request.method == 'POST':

        if not is_my_approval:
            messages.error(
                request,
                "This request is not awaiting your approval."
            )
            return redirect('admin_dashboard')

        form = LeaveActionForm(request.POST)

        if form.is_valid():

            decision = form.cleaned_data['status']
            comment = form.cleaned_data.get(
                'manager_comment',
                ''
            )

            result = process_leave_decision(
                leave,
                current_approval,
                decision,
                request.user,
                comment
            )

            if result['outcome'] == 'rejected':
                messages.success(
                    request,
                    'Leave request rejected.'
                )

            elif result['outcome'] == 'final_approved':
                messages.success(
                    request,
                    'Leave request fully approved.'
                )

            return redirect('admin_dashboard')

    return render(
        request,
        'admin/leave_details.html',
        {
            'leave': leave,
            'form': form,
            'is_my_approval': is_my_approval,
            'approval_history': leave.approvals.all(),
        }
    )


@admin_required
def user_list(request):
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')

    users = User.objects.filter(is_superuser=False).select_related('profile').prefetch_related('groups')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if role_filter:
        users = users.filter(groups__name=role_filter)

    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
    }
    return render(request, 'admin/user_list.html', context)


@admin_required
def create_user(request):
    form = CreateUserForm()
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            temp_password = generate_temp_password()

            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=temp_password,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )

            role_name = form.cleaned_data['role']
            group, _ = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)

            profile, _ = EmployeeProfile.objects.get_or_create(user=user)
            profile.department = form.cleaned_data['department']
            profile.phone = form.cleaned_data.get('phone', '')
            
            profile.manager = form.cleaned_data.get('manager')
            profile.must_change_password = True
            profile.save()

            send_account_created_email(request, user, temp_password)

            messages.success(request, f'User "{user.username}" created successfully with role "{role_name}".')
            return redirect('user_list')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'admin/create_user.html', {'form': form})


@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id, is_superuser=False)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" has been deleted successfully.')
        return redirect('user_list')
    return render(request, 'admin/confirm_delete.html', {'user': user})


@admin_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id, is_superuser=False)
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User "{user.username}" has been {status}.')
    return redirect('user_list')


@admin_required
def admin_reset_password(request, user_id):
    user = get_object_or_404(User, id=user_id, is_superuser=False)
    if request.method == 'POST':
        temp_password = generate_temp_password()
        user.set_password(temp_password)
        user.save()
        
        profile, _ = EmployeeProfile.objects.get_or_create(user=user)
        profile.must_change_password = True
        profile.save()
        
        send_password_reset_by_admin_email(request, user, temp_password, request.user)
        messages.success(request, f'Password for user "{user.username}" has been reset and emailed.')
        return redirect('user_list')
        
    return render(request, 'admin/confirm_reset_password.html', {'user': user})


# ─────────────────────────────────────────────
# MANAGER VIEWS
# ─────────────────────────────────────────────

@manager_required
def manager_dashboard(request):
    subordinates = get_all_subordinates(request.user)
    subordinate_ids = [u.id for u in subordinates]

    team_leaves = LeaveRequest.objects.filter(employee_id__in=subordinate_ids)

    my_pending_approvals = LeaveRequest.objects.filter(
        status='PENDING',
        approvals__approver=request.user,
        approvals__status='PENDING',
    ).select_related('employee').distinct().order_by('-applied_on')

    recent_activity = team_leaves.select_related('employee').order_by('-updated_on')[:10]

    context = {
        'team_size': len(subordinates),
        'total_leaves': team_leaves.count(),
        'approved_count': team_leaves.filter(status='APPROVED').count(),
        'rejected_count': team_leaves.filter(status='REJECTED').count(),
        'my_pending_count': my_pending_approvals.count(),
        'my_pending_approvals': my_pending_approvals[:5],
        'recent_activity': recent_activity,
    }
    return render(request, 'manager/manager_dashboard.html', context)


@manager_required
def leave_requests(request):
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    leave_type_filter = request.GET.get('leave_type', '')
    mine_only = request.GET.get('mine', '')

    subordinate_ids = [u.id for u in get_all_subordinates(request.user)]
    leaves = LeaveRequest.objects.filter(
        employee_id__in=subordinate_ids
    ).select_related('employee', 'reviewed_by')

    if mine_only:
        leaves = leaves.filter(
            status='PENDING',
            approvals__approver=request.user,
            approvals__status='PENDING',
        ).distinct()

    if status_filter:
        leaves = leaves.filter(status=status_filter)
    if leave_type_filter:
        leaves = leaves.filter(leave_type=leave_type_filter)
    if search_query:
        leaves = leaves.filter(
            Q(employee__username__icontains=search_query) |
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query)
        )

    my_pending_approval_ids = set(
        LeaveApproval.objects.filter(
            approver=request.user, status='PENDING', leave_request__status='PENDING'
        ).values_list('leave_request_id', flat=True)
    )

    context = {
        'leaves': leaves.order_by('-applied_on'),
        'status_filter': status_filter,
        'search_query': search_query,
        'leave_type_filter': leave_type_filter,
        'mine_only': mine_only,
        'my_pending_approval_ids': my_pending_approval_ids,
        'status_choices': LeaveRequest.STATUS_CHOICES,
        'leave_type_choices': LeaveRequest.LEAVE_TYPE_CHOICES,
    }
    return render(request, 'manager/leave_requests.html', context)


@manager_required
def leave_details(request, leave_id):
    leave = get_object_or_404(LeaveRequest, id=leave_id)

    current_approval = leave.approvals.filter(level=leave.current_level).first()

    is_my_approval = (
        current_approval is not None and
        current_approval.approver_id == request.user.id and
        current_approval.status == 'PENDING' and
        leave.status == 'PENDING'
    )

    form = LeaveActionForm()

    if request.method == 'POST':
        if not is_my_approval:
            messages.error(request, 'This request is not awaiting your approval.')
            return redirect('leave_requests')

        form = LeaveActionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['status']
            comment = form.cleaned_data.get('manager_comment', '')

            result = process_leave_decision(leave, current_approval, decision, request.user, comment)

            if result['outcome'] == 'rejected':
                send_leave_rejected_email(
                    request,
                    leave
                )
                messages.success(request, 'Leave request has been rejected.')
                
            elif result['outcome'] == 'escalated':
                send_leave_escalated_email(
                    request,
                    leave,
                    result['next_approver']
                )
                next_name = (
                    result['next_approver'].get_full_name()
                    or result['next_approver'].username
                )
                messages.success(
                    request,
                    f'Approved at your level. Escalated to {next_name} for final approval.'
                )
                
            else:
                send_leave_final_approved_email(
                    request,
                    leave
                )
                messages.success(request, 'Leave request fully approved.')

            return redirect('leave_requests')

    context = {
        'leave': leave,
        'form': form,
        'is_my_approval': is_my_approval,
        'current_approval': current_approval,
        'approval_history': leave.approvals.select_related('approver').all(),
    }
    return render(request, 'manager/leave_details.html', context)


@manager_required
def manager_reports(request):
    subordinates = get_all_subordinates(request.user)
    subordinate_ids = [u.id for u in subordinates]

    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    try:
        selected_year = int(request.GET.get('year', timezone.now().year))
    except ValueError:
        selected_year = timezone.now().year

    leaves = LeaveRequest.objects.filter(employee_id__in=subordinate_ids).select_related('employee')

    if from_date:
        leaves = leaves.filter(applied_on__date__gte=from_date)
    if to_date:
        leaves = leaves.filter(applied_on__date__lte=to_date)

    total = leaves.count()
    approved = leaves.filter(status='APPROVED').count()
    rejected = leaves.filter(status='REJECTED').count()
    pending = leaves.filter(status='PENDING').count()
    cancelled = leaves.filter(status='CANCELLED').count()

    by_type = leaves.values('leave_type').annotate(count=Count('id')).order_by('-count')

    # ── Pending Approvals: split into "awaiting me" vs "awaiting someone else" ──
    pending_requests = list(leaves.filter(status='PENDING').select_related('employee'))
    pending_ids = [lv.id for lv in pending_requests]
    my_pending_ids = set(
        LeaveApproval.objects.filter(
            approver=request.user, status='PENDING', leave_request_id__in=pending_ids
        ).values_list('leave_request_id', flat=True)
    )
    my_pending = [lv for lv in pending_requests if lv.id in my_pending_ids]
    others_pending = [lv for lv in pending_requests if lv.id not in my_pending_ids]

    # ── Team Leave Summary: per-employee breakdown for the selected year ──
    team_summary = []
    for member in subordinates:
        member_leaves = LeaveRequest.objects.filter(employee=member)
        quotas = LeaveQuota.objects.filter(employee=member, year=selected_year)
        total_used = sum(q.used for q in quotas)
        total_quota_days = sum(q.total_quota for q in quotas)
        team_summary.append({
            'employee': member,
            'total_requests': member_leaves.count(),
            'approved': member_leaves.filter(status='APPROVED').count(),
            'pending': member_leaves.filter(status='PENDING').count(),
            'rejected': member_leaves.filter(status='REJECTED').count(),
            'total_quota': total_quota_days,
            'used': total_used,
            'remaining': max(total_quota_days - total_used, 0),
        })
    team_summary.sort(key=lambda row: row['pending'], reverse=True)

    # ── Monthly Leave Stats for the selected year ──
    year_leaves = LeaveRequest.objects.filter(
        employee_id__in=subordinate_ids,
        start_date__year=selected_year,
    ).exclude(status='CANCELLED')

    monthly_stats = []
    for month_num in range(1, 13):
        month_leaves = year_leaves.filter(start_date__month=month_num)
        days = sum(lv.duration for lv in month_leaves)
        monthly_stats.append({
            'month': calendar.month_abbr[month_num],
            'count': month_leaves.count(),
            'days': days,
        })

    max_monthly_days = max([m['days'] for m in monthly_stats], default=0) or 1
    for m in monthly_stats:
        m['pct'] = round((m['days'] / max_monthly_days) * 100, 1)

    available_years = [timezone.now().year - i for i in range(3)]

    context = {
        'total': total,
        'approved': approved,
        'rejected': rejected,
        'pending': pending,
        'cancelled': cancelled,
        'by_type': by_type,
        'from_date': from_date,
        'to_date': to_date,
        'leaves': leaves.order_by('-applied_on')[:20],
        'my_pending': my_pending,
        'others_pending': others_pending,
        'team_summary': team_summary,
        'monthly_stats': monthly_stats,
        'selected_year': selected_year,
        'available_years': available_years,
    }
    return render(request, 'manager/reports.html', context)


@manager_required
def employee_leave_history(request, employee_id):
    employee = get_object_or_404(User, id=employee_id)
    leaves = LeaveRequest.objects.filter(employee=employee).order_by('-applied_on')

    context = {
        'employee': employee,
        'leaves': leaves,
        'total': leaves.count(),
        'approved': leaves.filter(status='APPROVED').count(),
        'rejected': leaves.filter(status='REJECTED').count(),
        'pending': leaves.filter(status='PENDING').count(),
    }
    return render(request, 'manager/employee_history.html', context)


@manager_required
def manager_reset_password(request, user_id):
    user = get_object_or_404(User, id=user_id, is_superuser=False)
    if request.method == 'POST':
        temp_password = generate_temp_password()
        user.set_password(temp_password)
        user.save()
        
        profile, _ = EmployeeProfile.objects.get_or_create(user=user)
        profile.must_change_password = True
        profile.save()
        
        send_password_reset_by_admin_email(request, user, temp_password, request.user)
        messages.success(request, f'Password for team member "{user.username}" has been reset.')
        return redirect('manager_team')
        
    return render(request, 'manager/confirm_reset_password.html', {'user': user})


@manager_required
def manager_team(request):
    team_members = get_all_subordinates(request.user)
    
    context = {
        'team_members': team_members,
    }
    return render(request, 'manager/team.html', context)


# ─────────────────────────────────────────────
# EMPLOYEE VIEWS
# ─────────────────────────────────────────────

@employee_required
def employee_dashboard(request):
    year = date.today().year

    quotas = LeaveQuota.objects.filter(
        employee=request.user,
        year=year
    )

    leaves = LeaveRequest.objects.filter(employee=request.user)
    context = {
        'total_requests': leaves.count(),
        'approved_count': leaves.filter(status='APPROVED').count(),
        'rejected_count': leaves.filter(status='REJECTED').count(),
        'pending_count': leaves.filter(status='PENDING').count(),
        'recent_leaves': leaves.order_by('-applied_on')[:5],
        'quotas': quotas,
    }
    return render(request, 'employee/employee_dashboard.html', context)


@employee_required
def apply_leave(request):
    quotas = LeaveQuota.objects.filter(employee=request.user, year=timezone.now().year)
    form = LeaveRequestForm(employee=request.user)

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, employee=request.user)
        if form.is_valid():
            l1_approver = get_approver_for_level(request.user, 1)
            if not l1_approver:
                messages.error(
                    request,
                    'You do not have a manager assigned, so leave requests cannot be '
                    'routed for approval. Please contact your administrator.'
                )
                return render(request, 'employee/apply_leave.html', {'form': form, 'quotas': quotas})

            leave = form.save(commit=False)
            leave.employee = request.user
            leave.status = 'PENDING'
            leave.current_level = 1
            leave.save()

            start_leave_approval(leave)
            
            send_leave_applied_email(
                request,
                leave,
                l1_approver
            )

            messages.success(request, 'Your leave request has been submitted and sent for approval.')
            return redirect('my_leaves')
        else:
            messages.error(request, 'Please correct the errors in the form.')

    return render(request, 'employee/apply_leave.html', {'form': form, 'quotas': quotas})


@employee_required
def my_leaves(request):
    status_filter = request.GET.get('status', '')
    leaves = LeaveRequest.objects.filter(employee=request.user)

    if status_filter:
        leaves = leaves.filter(status=status_filter)

    context = {
        'leaves': leaves,
        'status_filter': status_filter,
        'status_choices': LeaveRequest.STATUS_CHOICES,
    }
    return render(request, 'employee/my_leaves.html', context)


@employee_required
def cancel_leave(request, leave_id):
    leave = get_object_or_404(LeaveRequest, id=leave_id, employee=request.user)

    if request.method == 'POST':
        if leave.status != 'PENDING':
            messages.error(request, 'Only pending leave requests can be cancelled.')
        else:
            leave.status = 'CANCELLED'
            leave.save()
            messages.success(request, 'Your leave request has been cancelled.')
        return redirect('my_leaves')

    return render(request, 'employee/confirm_cancel.html', {'leave': leave})


@employee_required
def leave_detail_employee(request, leave_id):
    leave = get_object_or_404(LeaveRequest, id=leave_id, employee=request.user)
    
    approval_history = leave.approvals.select_related('approver').order_by('level')

    return render(request, 'employee/leave_detail.html', {
        'leave': leave,
        'approval_history': approval_history
    })