from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect('login')

        if not (
            request.user.is_superuser or
            request.user.groups.filter(name='Admin').exists()
        ):
            messages.error(
                request,
                'Access denied. Admin privileges required.'
            )
            return redirect('dashboard_redirect')

        return view_func(request, *args, **kwargs)

    return wrapper


def manager_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        if not request.user.groups.filter(name='Manager').exists():
            messages.error(request, 'Access denied. Manager privileges required.')
            return redirect('dashboard_redirect')
        return view_func(request, *args, **kwargs)
    return wrapper


def employee_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        if not request.user.groups.filter(name='Employee').exists():
            messages.error(request, 'Access denied. Employee privileges required.')
            return redirect('dashboard_redirect')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper