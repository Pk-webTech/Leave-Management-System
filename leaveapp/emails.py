from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse


def send_account_created_email(request, user, temp_password):
    subject = "Welcome to LeaveTrack — Your Account Details"
    login_url = request.build_absolute_uri(reverse('login'))
    message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"Your LeaveTrack account has been created.\n\n"
        f"Username: {user.username}\n"
        f"Temporary Password: {temp_password}\n\n"
        f"Log in here: {login_url}\n"
        f"You will be asked to set a new password before accessing your dashboard.\n\n"
        f"— LeaveTrack"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


def send_password_reset_by_admin_email(request, user, temp_password, reset_by):
    subject = "Your LeaveTrack password has been reset"
    login_url = request.build_absolute_uri(reverse('login'))
    message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"Your password was reset by {reset_by.get_full_name() or reset_by.username}.\n\n"
        f"Temporary Password: {temp_password}\n\n"
        f"Log in here: {login_url}\n"
        f"You will be asked to set a new password before accessing your dashboard.\n\n"
        f"If you did not expect this, please contact your administrator immediately.\n\n"
        f"— LeaveTrack"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


def send_password_reset_link_email(request, user, reset_url):
    subject = "Reset your LeaveTrack password"
    message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"We received a request to reset your LeaveTrack password.\n\n"
        f"Click the link below to choose a new password. This link can only "
        f"be used once and will expire after a few days:\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"— LeaveTrack"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


def send_password_changed_confirmation_email(request, user):
    subject = "Your LeaveTrack password was changed"
    message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"This is a confirmation that your LeaveTrack password was just changed.\n\n"
        f"If you did not make this change, please contact your administrator immediately.\n\n"
        f"— LeaveTrack"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
# ─────────────────────────────────────────────
# LEAVE WORKFLOW EMAILS
# ─────────────────────────────────────────────

def _leave_summary_lines(leave_request):
    duration_label = f"{leave_request.duration} day{'s' if leave_request.duration != 1 else ''}"
    return (
        f"Leave Type: {leave_request.leave_type}\n"
        f"Dates: {leave_request.start_date} to {leave_request.end_date} ({duration_label})\n"
        f"Reason: {leave_request.reason}\n"
    )


def send_leave_applied_email(request, leave_request, approver):
    """Sent to the L1 manager the moment an employee applies for leave."""
    employee_name = leave_request.employee.get_full_name() or leave_request.employee.username
    subject = f"Leave Approval Required — {employee_name}"
    review_url = request.build_absolute_uri(reverse('leave_details', args=[leave_request.id]))
    message = (
        f"Hello {approver.get_full_name() or approver.username},\n\n"
        f"{employee_name} has applied for leave and it is awaiting your approval "
        f"(Level {leave_request.current_level}).\n\n"
        f"{_leave_summary_lines(leave_request)}\n"
        f"Review it here: {review_url}\n\n"
        f"— LeaveTrack"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [approver.email], fail_silently=True)


def send_leave_escalated_email(request, leave_request, approver):
    """Sent to the next-level (e.g. L2) manager when a request escalates."""
    employee_name = leave_request.employee.get_full_name() or leave_request.employee.username
    subject = f"Leave Approval Required (Escalated) — {employee_name}"
    review_url = request.build_absolute_uri(reverse('leave_details', args=[leave_request.id]))
    message = (
        f"Hello {approver.get_full_name() or approver.username},\n\n"
        f"A leave request from {employee_name} was approved at the previous level and has "
        f"escalated to you for Level {leave_request.current_level} approval.\n\n"
        f"{_leave_summary_lines(leave_request)}\n"
        f"Review it here: {review_url}\n\n"
        f"— LeaveTrack"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [approver.email], fail_silently=True)


def send_leave_final_approved_email(request, leave_request):
    """Sent to the employee once their leave is fully approved (all levels)."""
    subject = "Your leave request has been approved"
    detail_url = request.build_absolute_uri(reverse('leave_detail_employee', args=[leave_request.id]))
    message = (
        f"Hello {leave_request.employee.get_full_name() or leave_request.employee.username},\n\n"
        f"Good news — your leave request has been fully approved.\n\n"
        f"{_leave_summary_lines(leave_request)}\n"
        f"View details: {detail_url}\n\n"
        f"— LeaveTrack"
    )
    send_mail(
        subject, message, settings.DEFAULT_FROM_EMAIL,
        [leave_request.employee.email], fail_silently=True
    )


def send_leave_rejected_email(request, leave_request):
    """Sent to the employee when their leave is rejected at any level."""
    subject = "Your leave request has been rejected"
    detail_url = request.build_absolute_uri(reverse('leave_detail_employee', args=[leave_request.id]))
    comment_line = f"\nComment: {leave_request.manager_comment}\n" if leave_request.manager_comment else ""
    message = (
        f"Hello {leave_request.employee.get_full_name() or leave_request.employee.username},\n\n"
        f"Your leave request has been rejected.\n\n"
        f"{_leave_summary_lines(leave_request)}"
        f"{comment_line}\n"
        f"View details: {detail_url}\n\n"
        f"— LeaveTrack"
    )
    send_mail(
        subject, message, settings.DEFAULT_FROM_EMAIL,
        [leave_request.employee.email], fail_silently=True
    )