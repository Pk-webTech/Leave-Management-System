"""
Helper functions for navigating the manager/reportee organizational
hierarchy, plus small shared utilities (temp password generation, quota
lookups).
"""
import secrets
import string

from django.conf import settings
from django.contrib.auth.models import User

from .models import LeaveQuota


def generate_temp_password(length=10):
    """Generates a random temporary password using letters, digits, and a couple of symbols."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_manager_chain(user, max_levels=10):
    """
    Returns an ordered list of managers above `user`:
    [L1 manager, L2 manager, L3 manager, ...]
    Stops at the top of the org chart, or after max_levels, or if a cycle
    is detected.
    """
    chain = []
    visited = {user.id}
    current = user

    for _ in range(max_levels):
        profile = getattr(current, 'profile', None)
        manager = getattr(profile, 'manager', None)
        if not manager or manager.id in visited:
            break
        chain.append(manager)
        visited.add(manager.id)
        current = manager

    return chain


def get_approver_for_level(user, level):
    """
    Returns the User who should approve `user`'s leave request at the given
    level (1 = direct manager, 2 = direct manager's manager, ...), or None
    if there's nobody at that level.
    """
    chain = get_manager_chain(user)
    index = level - 1
    if 0 <= index < len(chain):
        return chain[index]
    return None


def get_all_subordinates(user, _visited=None):
    """
    Returns a flat list of Users who report to `user`, directly or
    indirectly, by walking down the org chart.
    """
    if _visited is None:
        _visited = set()

    direct_reports = User.objects.filter(profile__manager=user).exclude(id__in=_visited)
    subordinates = []

    for emp in direct_reports:
        if emp.id in _visited:
            continue
        _visited.add(emp.id)
        subordinates.append(emp)
        subordinates.extend(get_all_subordinates(emp, _visited))

    return subordinates


def get_or_create_quota(employee, leave_type, year):
    """
    Returns the LeaveQuota row for (employee, leave_type, year), creating it
    with the configured default if it doesn't exist yet (e.g. a new year
    that hasn't been seeded by the management command).
    """
    quota, _ = LeaveQuota.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        year=year,
        defaults={'total_quota': settings.DEFAULT_LEAVE_QUOTAS.get(leave_type, 0)}
    )
    return quota