from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Admin
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views.user_list, name='user_list'),
    path('admin-panel/users/create/', views.create_user, name='create_user'),
    path('admin-panel/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin-panel/users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),

    # Manager
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/leaves/', views.leave_requests, name='leave_requests'),
    path('manager/leaves/<int:leave_id>/', views.leave_details, name='leave_details'),
    path('manager/reports/', views.manager_reports, name='manager_reports'),
    path('manager/employee/<int:employee_id>/history/', views.employee_leave_history, name='employee_leave_history'),

    # Employee
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('employee/apply/', views.apply_leave, name='apply_leave'),
    path('employee/my-leaves/', views.my_leaves, name='my_leaves'),
    path('employee/my-leaves/<int:leave_id>/cancel/', views.cancel_leave, name='cancel_leave'),
    path('employee/my-leaves/<int:leave_id>/', views.leave_detail_employee, name='leave_detail_employee'),
]