from django.conf import settings
from django.contrib.auth import get_user as auth_get_user
from django.contrib.auth.middleware import \
    AuthenticationMiddleware as _AuthenticationMiddleware
from django.contrib.auth.models import AnonymousUser
from django.utils.functional import SimpleLazyObject

from users.models import ExtendedAnonymousUser


def get_user(request):
    if not hasattr(request, '_cached_user'):
        request._cached_user = auth_get_user(request)
        if isinstance(request._cached_user, AnonymousUser):
            request._cached_user = ExtendedAnonymousUser()
    return request._cached_user


class AuthenticationMiddleware(_AuthenticationMiddleware):
    def process_request(self, request):
        assert hasattr(request, 'session'), (
            "The Django authentication middleware requires session middleware "
            "to be installed. Edit your MIDDLEWARE%s setting to insert "
            "'django.contrib.sessions.middleware.SessionMiddleware' before "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'."
        ) % ("_CLASSES" if settings.MIDDLEWARE is None else "")
        request.user = SimpleLazyObject(lambda: get_user(request))
