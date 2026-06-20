from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import EmployeeProfile, LeaveQuota
from django.conf import settings
from django.utils import timezone


@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    """Automatically create an EmployeeProfile whenever a new User is created."""
    if created:
        EmployeeProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_employee_profile(sender, instance, **kwargs):
    """Save profile whenever user is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        EmployeeProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=EmployeeProfile)
def create_default_leave_quotas(sender, instance, created, **kwargs):
    """
    Automatically create default leave quotas
    when a new EmployeeProfile is created.
    """

    if created:

        year = timezone.now().year

        defaults = getattr(
            settings,
            'DEFAULT_LEAVE_QUOTAS',
            {}
        )

        for leave_type, days in defaults.items():

            LeaveQuota.objects.get_or_create(
                employee=instance.user,
                leave_type=leave_type,
                year=year,
                defaults={
                    'total_quota': days
                }
            )