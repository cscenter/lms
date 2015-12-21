from django.contrib.auth import get_user_model, get_user as auth_get_user
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import AnonymousUser
from django.utils.functional import SimpleLazyObject
from .models import NotAuthenticatedUser


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        # XXX this is fine, since @ is not allowed in usernames.
        field = "email" if "@" in username else "username"
        user_model = get_user_model()
        try:
            user = user_model.objects.get(**{field: username})
            if user.check_password(password):
                return user
        except user_model.DoesNotExist:
            # See comment in 'ModelBackend#authenticate'.
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            user_model().set_password(password)


def get_user(request):
    if not hasattr(request, '_cached_user'):
        request._cached_user = auth_get_user(request)
        if isinstance(request._cached_user, AnonymousUser):
            request._cached_user = NotAuthenticatedUser()
    return request._cached_user


class AuthenticationMiddleware(object):
    def process_request(self, request):
        assert hasattr(request, 'session'), (
            "The Django authentication middleware requires session middleware "
            "to be installed. Edit your MIDDLEWARE_CLASSES setting to insert "
            "'django.contrib.sessions.middleware.SessionMiddleware' before "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'."
        )
        request.user = SimpleLazyObject(lambda: get_user(request))
