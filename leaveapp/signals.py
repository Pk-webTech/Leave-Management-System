import logging
from django.db.models.signals import post_save
from django.contrib.auth.models import User, Group
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from .models import EmployeeProfile, LeaveQuota

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_employee_profile(sender, instance, created, **kwargs):
    if created:
        EmployeeProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_employee_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        EmployeeProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=EmployeeProfile)
def create_default_leave_quotas(sender, instance, created, **kwargs):
    if created:
        year = timezone.now().year
        defaults = getattr(settings, 'DEFAULT_LEAVE_QUOTAS', {})
        for leave_type, days in defaults.items():
            LeaveQuota.objects.get_or_create(
                employee=instance.user,
                leave_type=leave_type,
                year=year,
                defaults={'total_quota': days}
            )


@receiver(post_save, sender=EmployeeProfile)
def sync_manager_roles(sender, instance, **kwargs):
    """
    Bug Fix 5: Auto-assign roles based on org hierarchy.
    When a user is set as someone's manager, they automatically get the
    Manager group. If they lose all reportees they revert to Employee.
    """
    try:
        employee_group, _ = Group.objects.get_or_create(name='Employee')
        manager_group, _ = Group.objects.get_or_create(name='Manager')

        # If this profile has a manager set, upgrade that manager's role
        if instance.manager and not instance.manager.is_superuser:
            mgr = instance.manager
            if not mgr.groups.filter(name='Manager').exists():
                mgr.groups.add(manager_group)
                mgr.groups.remove(employee_group)

        # Recalculate role for the current profile's user:
        user = instance.user
        if not user.is_superuser and not user.groups.filter(name='Admin').exists():
            has_reports = EmployeeProfile.objects.filter(manager=user).exists()
            if has_reports:
                user.groups.add(manager_group)
                user.groups.remove(employee_group)
            else:
                # Revert to Employee if no reports and not explicitly kept as Manager
                if not user.groups.filter(name='Manager').exists():
                    if not user.groups.filter(name='Employee').exists():
                        user.groups.add(employee_group)
    except Exception as e:
        logger.exception("Error syncing manager roles")