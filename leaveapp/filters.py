import django_filters
from django import forms
from .models import LeaveRequest

class LeaveRequestFilter(django_filters.FilterSet):
    # Using ChoiceFilter to provide custom empty labels
    status = django_filters.ChoiceFilter(
        choices=LeaveRequest.STATUS_CHOICES,
        empty_label="All Status"
    )

    leave_type = django_filters.ChoiceFilter(
        choices=LeaveRequest.LEAVE_TYPE_CHOICES,
        empty_label="All Leave Types"
    )

    # Date filters using Django forms widgets
    start_date_from = django_filters.DateFilter(
        field_name='start_date', 
        lookup_expr='gte', 
        label='Start Date From',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    start_date_to = django_filters.DateFilter(
        field_name='start_date', 
        lookup_expr='lte', 
        label='Start Date To',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = LeaveRequest
        fields = ['status', 'leave_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap 'form-select' to all choice fields automatically
        for field_name in ['status', 'leave_type']:
            if field_name in self.form.fields:
                self.form.fields[field_name].widget.attrs.update({'class': 'form-select'})