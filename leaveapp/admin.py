from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    EmployeeProfile,
    LeaveRequest,
    LeaveApproval,
    LeaveQuota
)


class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    fk_name = 'user'
    can_delete = False
    verbose_name_plural = 'Profile'

    fields = [
        'department',
        'phone',
        'manager',
        'must_change_password'
    ]


class UserAdmin(BaseUserAdmin):
    inlines = (EmployeeProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role', 'is_active']
    list_filter = ['groups', 'is_active', 'is_staff']

    def get_role(self, obj):
        groups = obj.groups.values_list('name', flat=True)
        return ', '.join(groups) if groups else 'No Role'
    get_role.short_description = 'Role'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'department',
        'manager',
        'phone',
        'must_change_password',
        'created_at'
    ]

    list_filter = [
        'department',
        'must_change_password'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'department'
    ]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        'employee',
        'leave_type',
        'start_date',
        'end_date',
        'status',
        'current_level',
        'applied_on'
    ]
    list_filter = ['status', 'leave_type', 'applied_on']
    search_fields = ['employee__username', 'employee__email', 'reason']
    readonly_fields = ['applied_on', 'updated_on']
    fieldsets = (
        ('Leave Details', {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'reason')
        }),
        ('Status', {
            'fields': (
                'status',
                'current_level',
                'reviewed_by',
                'manager_comment'
            )
        }),
        ('Timestamps', {
            'fields': ('applied_on', 'updated_on'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveApproval)
class LeaveApprovalAdmin(admin.ModelAdmin):

    list_display = [
        'leave_request',
        'level',
        'approver',
        'status',
        'acted_on'
    ]

    list_filter = [
        'status',
        'level'
    ]

    search_fields = [
        'approver__username',
        'leave_request__employee__username'
    ]


@admin.register(LeaveQuota)
class LeaveQuotaAdmin(admin.ModelAdmin):

    list_display = [
        'employee',
        'leave_type',
        'year',
        'total_quota',
        'used',
        'remaining'
    ]

    list_filter = [
        'leave_type',
        'year'
    ]

    search_fields = [
        'employee__username'
    ]