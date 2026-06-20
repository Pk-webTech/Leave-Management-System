"""
Leave approval workflow: starting a request's approval chain, and
processing a manager's decision (approve escalates to the next level,
reject terminates immediately).
"""
from django.conf import settings
from django.utils import timezone
from .models import LeaveApproval
from .utils import get_approver_for_level


def start_leave_approval(leave_request):
    """
    Called right after a LeaveRequest is created. Creates the level-1
    LeaveApproval row pointing at the employee's direct manager.
    Returns the LeaveApproval, or None if the employee has no manager
    (callers should check this before creating the request at all).
    """
    approver = get_approver_for_level(leave_request.employee, 1)
    if not approver:
        return None

    return LeaveApproval.objects.create(
        leave_request=leave_request,
        level=1,
        approver=approver,
        status='PENDING',
    )


def process_leave_decision(leave_request, approval, decision, approver, comment=''):
    """
    Applies a manager's decision to `approval` (the LeaveApproval row at the
    leave request's current level).

    decision: 'APPROVED' or 'REJECTED'

    Rejection terminates the workflow immediately. Approval either escalates
    to the next level (if one exists and the configured max level hasn't
    been reached) or finalizes the request as fully approved.

    Returns: {'outcome': 'rejected' | 'escalated' | 'final_approved', 'next_approver': User|None}
    """
    approval.status = decision
    approval.comment = comment
    approval.acted_on = timezone.now()
    approval.save()

    if decision == 'REJECTED':
        leave_request.status = 'REJECTED'
        leave_request.reviewed_by = approver
        leave_request.manager_comment = comment
        leave_request.save()
        return {'outcome': 'rejected', 'next_approver': None}

    # APPROVED at this level — decide whether to escalate.
    max_levels = getattr(settings, 'LEAVE_APPROVAL_MAX_LEVELS', 2)
    next_level = approval.level + 1
    next_approver = None

    if next_level <= max_levels:
        next_approver = get_approver_for_level(leave_request.employee, next_level)

    if next_approver:
        LeaveApproval.objects.create(
            leave_request=leave_request,
            level=next_level,
            approver=next_approver,
            status='PENDING',
        )
        leave_request.current_level = next_level
        leave_request.manager_comment = comment
        leave_request.save()
        return {'outcome': 'escalated', 'next_approver': next_approver}

    # No further escalation — fully approved.
    leave_request.status = 'APPROVED'
    leave_request.reviewed_by = approver
    leave_request.manager_comment = comment
    leave_request.save()

    return {'outcome': 'final_approved', 'next_approver': None}