from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import EmployeeProfile, LeaveRequest


class EmployeeProfileInline(admin.StackedInline):
    model = EmployeeProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['department', 'phone']


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
    list_display = ['user', 'department', 'phone', 'created_at']
    list_filter = ['department']
    search_fields = ['user__username', 'user__email', 'department']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status', 'applied_on']
    list_filter = ['status', 'leave_type', 'applied_on']
    search_fields = ['employee__username', 'employee__email', 'reason']
    readonly_fields = ['applied_on', 'updated_on']
    fieldsets = (
        ('Leave Details', {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'reason')
        }),
        ('Status', {
            'fields': ('status', 'reviewed_by', 'manager_comment')
        }),
        ('Timestamps', {
            'fields': ('applied_on', 'updated_on'),
            'classes': ('collapse',)
        }),
    )