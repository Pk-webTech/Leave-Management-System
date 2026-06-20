from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve, Resolver404

# URL names a user with must_change_password=True is still allowed to reach.
EXEMPT_URL_NAMES = {
    'force_change_password', 'logout', 'login',
    'forgot_password', 'reset_password_confirm',
}


class ForcePasswordChangeMiddleware:
    """
    If a logged-in user's profile has must_change_password=True, every
    request is redirected to the force-change-password page until they set
    a new password. Superusers are exempt so the bootstrap account never
    gets locked out of /admin/.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith(settings.MEDIA_URL):
            return self.get_response(request)

        if request.path.startswith('/admin/'):
            return self.get_response(request)

        user = request.user
        if user.is_authenticated and not user.is_superuser:
            profile = getattr(user, 'profile', None)
            if profile and profile.must_change_password:
                try:
                    url_name = resolve(request.path).url_name
                except Resolver404:
                    url_name = None
                if url_name not in EXEMPT_URL_NAMES:
                    return redirect('force_change_password')

        return self.get_response(request)