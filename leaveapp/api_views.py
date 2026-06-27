"""
Curriculum: Django REST Framework — APIView / ViewSets.
REST API for leave requests, quota, and quick approval actions.
Token auth is supported (alongside session auth, so the browsable API
works in the browser when logged in too).

Endpoints:
  GET  /api/leave-requests/          — my leaves (employee) or team leaves (manager)
  POST /api/leave-requests/          — submit a leave request
  GET  /api/leave-requests/<id>/     — detail
  GET  /api/leave-quota/             — my current year quotas
  GET  /api/leave-quota/check/       — check balance for a type+duration (AJAX)
  POST /api/leave-requests/<id>/quick-action/  — approve/reject (AJAX, manager)
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import LeaveRequest, LeaveApproval, LeaveQuota
from .serializers import LeaveRequestSerializer, LeaveQuotaSerializer
from .utils import get_all_subordinates, get_approver_for_level, get_or_create_quota
from .workflow import start_leave_approval, process_leave_decision
from .filters import LeaveRequestFilter


class LeaveRequestListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/leave-requests/ — list leaves (own for employee, team for manager)
    POST /api/leave-requests/ — submit a new leave request
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveRequestSerializer
    filterset_class = LeaveRequestFilter

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name__in=['Manager', 'Admin']).exists() or user.is_superuser:
            subordinate_ids = [u.id for u in get_all_subordinates(user)]
            return LeaveRequest.objects.filter(
                employee_id__in=subordinate_ids
            ).select_related('employee').prefetch_related('approvals')
        return LeaveRequest.objects.filter(
            employee=user
        ).select_related('employee').prefetch_related('approvals')

    def perform_create(self, serializer):
        user = self.request.user
        l1_approver = get_approver_for_level(user, 1)
        if not l1_approver:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "You do not have a manager assigned. Cannot route leave for approval."
            )
        leave = serializer.save(employee=user, status='PENDING', current_level=1)
        start_leave_approval(leave)


class LeaveRequestDetailAPIView(generics.RetrieveAPIView):
    """GET /api/leave-requests/<id>/"""
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name__in=['Manager', 'Admin']).exists() or user.is_superuser:
            subordinate_ids = [u.id for u in get_all_subordinates(user)]
            return LeaveRequest.objects.filter(employee_id__in=subordinate_ids)
        return LeaveRequest.objects.filter(employee=user)


class LeaveQuotaAPIView(generics.ListAPIView):
    """GET /api/leave-quota/ — current year quota for the authenticated user"""
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveQuotaSerializer

    def get_queryset(self):
        return LeaveQuota.objects.filter(
            employee=self.request.user,
            year=timezone.now().year
        )


class LeaveQuotaCheckAPIView(APIView):
    """
    GET /api/leave-quota/check/?leave_type=Casual+Leave&days=3&year=2026
    Curriculum: JSON response + AJAX integration.
    Returns available balance for a specific leave type — used by the
    Apply Leave form to show real-time quota without a page reload.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leave_type = request.query_params.get('leave_type', '')
        year = int(request.query_params.get('year', timezone.now().year))
        try:
            days = int(request.query_params.get('days', 0))
        except (ValueError, TypeError):
            days = 0

        valid_types = [c[0] for c in LeaveRequest.LEAVE_TYPE_CHOICES]
        if leave_type not in valid_types:
            return Response(
                {'error': 'Invalid leave_type'},
                status=status.HTTP_400_BAD_REQUEST
            )

        quota = get_or_create_quota(request.user, leave_type, year)
        return Response({
            'leave_type': leave_type,
            'year': year,
            'total_quota': quota.total_quota,
            'used': quota.used,
            'remaining': quota.remaining,
            'requested_days': days,
            'sufficient': quota.remaining >= days if days > 0 else True,
        })


class QuickLeaveActionAPIView(APIView):
    """
    POST /api/leave-requests/<id>/quick-action/
    Curriculum: AJAX + JSON response + partial UI updates.
    Allows a manager to approve/reject a leave from the list view
    without navigating to the full detail page.
    Body: { "decision": "APPROVED"|"REJECTED", "comment": "optional" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, leave_id):
        leave = get_object_or_404(LeaveRequest, id=leave_id)
        current_approval = leave.approvals.filter(level=leave.current_level).first()

        is_my_approval = (
            current_approval is not None and
            current_approval.approver_id == request.user.id and
            current_approval.status == 'PENDING' and
            leave.status == 'PENDING'
        )

        if not is_my_approval:
            return Response(
                {'error': 'This request is not awaiting your approval.'},
                status=status.HTTP_403_FORBIDDEN
            )

        decision = request.data.get('decision', '').upper()
        comment = request.data.get('comment', '')

        if decision not in ('APPROVED', 'REJECTED'):
            return Response(
                {'error': 'decision must be APPROVED or REJECTED'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = process_leave_decision(leave, current_approval, decision, request.user, comment)

        # Send emails based on outcome
        from .emails import (
            send_leave_rejected_email,
            send_leave_escalated_email,
            send_leave_final_approved_email,
        )
        if result['outcome'] == 'rejected':
            send_leave_rejected_email(request, leave)
            message = 'Leave request rejected.'
        elif result['outcome'] == 'escalated':
            send_leave_escalated_email(request, leave, result['next_approver'])
            next_name = result['next_approver'].get_full_name() or result['next_approver'].username
            message = f'Approved at your level. Escalated to {next_name}.'
        else:
            send_leave_final_approved_email(request, leave)
            message = 'Leave request fully approved.'

        return Response({
            'outcome': result['outcome'],
            'message': message,
            'new_status': leave.status,
            'leave_id': leave.id,
        })