from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import EmployeeProfile


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