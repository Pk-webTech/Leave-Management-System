from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from .models import EmployeeProfile, LeaveRequest
from .utils import get_or_create_quota
import datetime


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
        })
    )


class CreateUserForm(forms.ModelForm):
    ROLE_CHOICES = [
        ('Manager', 'Manager'),
        ('Employee', 'Employee'),
    ]

    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ChoiceField(
        choices=EmployeeProfile.DEPARTMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    manager = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Optional — leave blank for top-of-hierarchy roles (e.g. Director)."
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['manager'].queryset = User.objects.filter(is_superuser=False).order_by('first_name', 'username')

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "A user with this username already exists."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_manager(self):
        manager = self.cleaned_data.get('manager')
        username = self.cleaned_data.get('username')

        if manager and manager.username == username:
            raise forms.ValidationError(
                "A user cannot be their own manager."
            )

        return manager


class LeaveRequestForm(forms.ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': datetime.date.today().isoformat(),
        })
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': datetime.date.today().isoformat(),
        })
    )

    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Please describe the reason for your leave request...'
            }),
        }

    def __init__(self, *args, employee=None, **kwargs):
        self.employee = employee
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        leave_type = cleaned_data.get('leave_type')

        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date must be after or equal to start date.")
            if start_date < datetime.date.today():
                raise forms.ValidationError("Start date cannot be in the past.")

            if leave_type and self.employee:
                duration = (end_date - start_date).days + 1
                quota = get_or_create_quota(self.employee, leave_type, start_date.year)
                if duration > quota.remaining:
                    raise forms.ValidationError(
                        f"Insufficient leave balance. You have {quota.remaining} day(s) remaining "
                        f"for {leave_type} this year (requested {duration})."
                    )

        return cleaned_data


class LeaveActionForm(forms.Form):
    STATUS_CHOICES = [
        ('APPROVED', 'Approve'),
        ('REJECTED', 'Reject'),
    ]
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    manager_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add a comment (optional)...'
        })
    )


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = EmployeeProfile
        fields = ['department', 'phone']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
        }
# ─────────────────────────────────────────────
# AUTH: forced change / forgot password forms
# ─────────────────────────────────────────────

class StyledPasswordChangeForm(PasswordChangeForm):
    """First-login / post-reset forced password change (user knows the old/temp password)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Current (temporary) password', 'autofocus': True
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'New password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Confirm new password'
        })


class StyledSetPasswordForm(SetPasswordForm):
    """Token-based forgot-password reset (no old password needed)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'New password', 'autofocus': True
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control', 'placeholder': 'Confirm new password'
        })


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email',
            'autofocus': True,
        })
    )