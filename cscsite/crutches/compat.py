from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


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
            user_model().set_password(password)
