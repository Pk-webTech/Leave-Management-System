from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from leaveapp.models import (
    EmployeeProfile,
    LeaveQuota
)


class Command(BaseCommand):

    help = (
        "Backfill leave quotas for "
        "existing users."
    )

    def handle(self, *args, **kwargs):

        year = timezone.now().year

        defaults = getattr(
            settings,
            'DEFAULT_LEAVE_QUOTAS',
            {}
        )

        created_count = 0

        for profile in EmployeeProfile.objects.all():

            for leave_type, days in defaults.items():

                _, created = LeaveQuota.objects.get_or_create(
                    employee=profile.user,
                    leave_type=leave_type,
                    year=year,
                    defaults={
                        'total_quota': days
                    }
                )

                if created:
                    created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{created_count} quotas created."
            )
        )