from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


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

    created_at = models.DateTimeField(auto_now_add=True)

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