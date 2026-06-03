from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone

from .models import EmployeeProfile, LeaveRequest
from .forms import (
    LoginForm, CreateUserForm, LeaveRequestForm,
    LeaveActionForm, ProfileUpdateForm
)
from .decorators import admin_required, manager_required, employee_required, login_required_custom


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

    recent_leaves = LeaveRequest.objects.select_related('employee').order_by('-applied_on')[:10]
    recent_users = User.objects.filter(is_superuser=False).order_by('-date_joined')[:5]

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
    }
    return render(request, 'admin/admin_dashboard.html', context)


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
            user = form.save(commit=False)
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()

            role_name = form.cleaned_data['role']
            group, _ = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)

            profile, _ = EmployeeProfile.objects.get_or_create(user=user)
            profile.department = form.cleaned_data['department']
            profile.phone = form.cleaned_data.get('phone', '')
            profile.save()

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


# ─────────────────────────────────────────────
# MANAGER VIEWS
# ─────────────────────────────────────────────

@manager_required
def manager_dashboard(request):
    all_leaves = LeaveRequest.objects.select_related('employee').all()
    pending_leaves = all_leaves.filter(status='PENDING')
    approved_leaves = all_leaves.filter(status='APPROVED')
    rejected_leaves = all_leaves.filter(status='REJECTED')
    recent_activity = all_leaves.order_by('-updated_on')[:10]

    context = {
        'total_leaves': all_leaves.count(),
        'pending_count': pending_leaves.count(),
        'approved_count': approved_leaves.count(),
        'rejected_count': rejected_leaves.count(),
        'recent_activity': recent_activity,
        'pending_leaves': pending_leaves[:5],
    }
    return render(request, 'manager/manager_dashboard.html', context)


@manager_required
def leave_requests(request):
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    leave_type_filter = request.GET.get('leave_type', '')

    leaves = LeaveRequest.objects.select_related('employee', 'reviewed_by').all()

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

    context = {
        'leaves': leaves,
        'status_filter': status_filter,
        'search_query': search_query,
        'leave_type_filter': leave_type_filter,
        'status_choices': LeaveRequest.STATUS_CHOICES,
        'leave_type_choices': LeaveRequest.LEAVE_TYPE_CHOICES,
    }
    return render(request, 'manager/leave_requests.html', context)


@manager_required
def leave_details(request, leave_id):
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    form = LeaveActionForm()

    if request.method == 'POST':
        form = LeaveActionForm(request.POST)
        if form.is_valid():
            if leave.status != 'PENDING':
                messages.error(request, 'This leave request has already been processed.')
                return redirect('leave_details', leave_id=leave_id)

            leave.status = form.cleaned_data['status']
            leave.manager_comment = form.cleaned_data.get('manager_comment', '')
            leave.reviewed_by = request.user
            leave.save()

            action = 'approved' if leave.status == 'APPROVED' else 'rejected'
            messages.success(request, f'Leave request has been {action} successfully.')
            return redirect('leave_requests')

    context = {
        'leave': leave,
        'form': form,
    }
    return render(request, 'manager/leave_details.html', context)


@manager_required
def manager_reports(request):
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    leaves = LeaveRequest.objects.select_related('employee').all()

    if from_date:
        leaves = leaves.filter(applied_on__date__gte=from_date)
    if to_date:
        leaves = leaves.filter(applied_on__date__lte=to_date)

    total = leaves.count()
    approved = leaves.filter(status='APPROVED').count()
    rejected = leaves.filter(status='REJECTED').count()
    pending = leaves.filter(status='PENDING').count()
    cancelled = leaves.filter(status='CANCELLED').count()

    by_type = leaves.values('leave_type').annotate(count=Count('id'))
    by_department = (
        leaves
        .values('employee__profile__department')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    context = {
        'total': total,
        'approved': approved,
        'rejected': rejected,
        'pending': pending,
        'cancelled': cancelled,
        'by_type': by_type,
        'by_department': by_department,
        'from_date': from_date,
        'to_date': to_date,
        'leaves': leaves.order_by('-applied_on')[:20],
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


# ─────────────────────────────────────────────
# EMPLOYEE VIEWS
# ─────────────────────────────────────────────

@employee_required
def employee_dashboard(request):
    leaves = LeaveRequest.objects.filter(employee=request.user)
    context = {
        'total_requests': leaves.count(),
        'approved_count': leaves.filter(status='APPROVED').count(),
        'rejected_count': leaves.filter(status='REJECTED').count(),
        'pending_count': leaves.filter(status='PENDING').count(),
        'recent_leaves': leaves.order_by('-applied_on')[:5],
    }
    return render(request, 'employee/employee_dashboard.html', context)


@employee_required
def apply_leave(request):
    form = LeaveRequestForm()
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = request.user
            leave.status = 'PENDING'
            leave.save()
            messages.success(request, 'Your leave request has been submitted successfully!')
            return redirect('my_leaves')
        else:
            messages.error(request, 'Please correct the errors in the form.')

    return render(request, 'employee/apply_leave.html', {'form': form})


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
    return render(request, 'employee/leave_detail.html', {'leave': leave})