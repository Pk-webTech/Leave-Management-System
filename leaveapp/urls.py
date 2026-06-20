from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Password Management
    path(
        'force-change-password/',
        views.force_change_password,
        name='force_change_password'
    ),
    path(
        'forgot-password/',
        views.forgot_password,
        name='forgot_password'
    ),
    path(
        'reset-password/<uidb64>/<token>/',
        views.reset_password_confirm,
        name='reset_password_confirm'
    ),

    # Admin
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views.user_list, name='user_list'),
    path('admin-panel/users/create/', views.create_user, name='create_user'),
    path('admin-panel/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin-panel/users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path(
        'admin-panel/users/<int:user_id>/reset-password/',
        views.admin_reset_password,
        name='admin_reset_password'
    ),
    path(
    'admin-panel/leave/<int:leave_id>/',
    views.admin_leave_details,
    name='admin_leave_details'
),

    # Manager
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/leaves/', views.leave_requests, name='leave_requests'),
    path('manager/leaves/<int:leave_id>/', views.leave_details, name='leave_details'),
    path('manager/reports/', views.manager_reports, name='manager_reports'),
    path('manager/employee/<int:employee_id>/history/', views.employee_leave_history, name='employee_leave_history'),
    path(
        'manager/team/',
        views.manager_team,
        name='manager_team'
    ),
    path(
        'manager/user/<int:user_id>/reset-password/',
        views.manager_reset_password,
        name='manager_reset_password'
    ),

    # Employee
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('employee/apply/', views.apply_leave, name='apply_leave'),
    path('employee/my-leaves/', views.my_leaves, name='my_leaves'),
    path('employee/my-leaves/<int:leave_id>/cancel/', views.cancel_leave, name='cancel_leave'),
    path('employee/my-leaves/<int:leave_id>/', views.leave_detail_employee, name='leave_detail_employee'),
    
]