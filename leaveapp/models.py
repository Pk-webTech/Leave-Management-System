from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone


def current_year():
    return timezone.now().year


class EmployeeProfile(models.Model):
    DEPARTMENT_CHOICES = [
        ('Engineering', 'Engineering'),
        ('Marketing', 'Marketing'),
        ('Finance', 'Finance'),
        ('Human Resources', 'Human Resources'),
        ('Operations', 'Operations'),
        ('Sales', 'Sales'),
        ('IT', 'IT'),
        ('Legal', 'Legal'),
        ('Other', 'Other'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    department = models.CharField(
        max_length=100,
        choices=DEPARTMENT_CHOICES,
        default='Other'
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports',
        help_text="Direct manager of this employee"
    )

    must_change_password = models.BooleanField(
        default=False,
        help_text="Force user to change password on first login"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.manager and self.manager == self.user:
            raise ValidationError("Employee cannot be their own manager.")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.department}"

    def get_role(self):
        if self.user.groups.filter(name='Admin').exists():
            return 'Admin'
        elif self.user.groups.filter(name='Manager').exists():
            return 'Manager'
        elif self.user.groups.filter(name='Employee').exists():
            return 'Employee'
        return 'Unknown'

    class Meta:
        verbose_name = 'Employee Profile'
        verbose_name_plural = 'Employee Profiles'


class LeaveRequest(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('Casual Leave', 'Casual Leave'),
        ('Sick Leave', 'Sick Leave'),
        ('Emergency Leave', 'Emergency Leave'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )

    leave_type = models.CharField(
        max_length=50,
        choices=LEAVE_TYPE_CHOICES
    )

    start_date = models.DateField()
    end_date = models.DateField()

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    current_level = models.PositiveSmallIntegerField(
        default=1
    )

    applied_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leaves'
    )

    manager_comment = models.TextField(
        blank=True,
        null=True
    )

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError(
                "End date cannot be earlier than start date."
            )

    @property
    def duration(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return (
            f"{self.employee.username} | "
            f"{self.leave_type} | "
            f"{self.start_date}"
        )

    class Meta:
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'
        ordering = ['-applied_on']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['employee']),
        ]


class LeaveApproval(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name='approvals'
    )

    level = models.PositiveSmallIntegerField()

    approver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='leave_approvals'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    comment = models.TextField(
        blank=True,
        null=True
    )

    acted_on = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['level']
        unique_together = ('leave_request', 'level')

    def __str__(self):
        return (
            f"Leave #{self.leave_request.id} "
            f"L{self.level} "
            f"{self.approver.username}"
        )


class LeaveQuota(models.Model):
    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='leave_quotas'
    )

    leave_type = models.CharField(
        max_length=50,
        choices=LeaveRequest.LEAVE_TYPE_CHOICES
    )

    year = models.PositiveIntegerField(
        default=current_year
    )

    total_quota = models.PositiveIntegerField(
        default=0
    )

    class Meta:
        unique_together = (
            'employee',
            'leave_type',
            'year'
        )

    def __str__(self):
        return (
            f"{self.employee.username} - "
            f"{self.leave_type}"
        )

    @property
    def used(self):
        """
        BUG FIX: A PENDING leave request must also count against quota,
        not just APPROVED ones. Otherwise an employee could submit several
        overlapping-quota requests while they're all still awaiting manager
        approval, and the "X / Y days remaining" cards would lie by showing
        full balance until a manager finally approves something.

        Quota is "reserved" the moment a request is submitted, and only
        released again if that request is REJECTED or CANCELLED.
        """
        leaves = LeaveRequest.objects.filter(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date__year=self.year,
            status__in=['PENDING', 'APPROVED']
        )
        return sum(leave.duration for leave in leaves)

    @property
    def remaining(self):
        return max(
            self.total_quota - self.used,
            0
        )