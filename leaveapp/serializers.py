"""
Curriculum: DRF Serializers.
Provides JSON representations for the Leave Management models,
used by the REST API (api_views.py).
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import LeaveRequest, LeaveApproval, LeaveQuota


class UserBasicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class LeaveApprovalSerializer(serializers.ModelSerializer):
    approver = UserBasicSerializer(read_only=True)

    class Meta:
        model = LeaveApproval
        fields = ['level', 'approver', 'status', 'comment', 'acted_on', 'created_at']


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee = UserBasicSerializer(read_only=True)
    duration = serializers.ReadOnlyField()
    approvals = LeaveApprovalSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'leave_type', 'start_date', 'end_date',
            'reason', 'status', 'status_display', 'current_level',
            'applied_on', 'updated_on', 'manager_comment', 'duration', 'approvals'
        ]
        read_only_fields = [
            'status', 'status_display', 'current_level',
            'applied_on', 'updated_on', 'manager_comment'
        ]

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        request = self.context.get('request')

        if start and end:
            if end < start:
                raise serializers.ValidationError("End date must be after start date.")

            if request and request.user:
                from .utils import get_or_create_quota
                duration = (end - start).days + 1
                leave_type = data.get('leave_type')

                # Overlap check
                overlap = LeaveRequest.objects.filter(
                    employee=request.user,
                    status__in=['PENDING', 'APPROVED'],
                    start_date__lte=end,
                    end_date__gte=start,
                )
                if overlap.exists():
                    raise serializers.ValidationError(
                        "You already have a leave request overlapping with these dates."
                    )

                # Quota check
                if leave_type:
                    quota = get_or_create_quota(request.user, leave_type, start.year)
                    if duration > quota.remaining:
                        raise serializers.ValidationError(
                            f"Insufficient {leave_type} balance. "
                            f"Remaining: {quota.remaining} day(s), Requested: {duration} day(s)."
                        )
        return data


class LeaveQuotaSerializer(serializers.ModelSerializer):
    used = serializers.ReadOnlyField()
    remaining = serializers.ReadOnlyField()
    leave_type_display = serializers.CharField(source='leave_type', read_only=True)

    class Meta:
        model = LeaveQuota
        fields = ['leave_type', 'leave_type_display', 'year', 'total_quota', 'used', 'remaining']