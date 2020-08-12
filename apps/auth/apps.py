from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuthConfig(AppConfig):
    # FIXME: Make sure we are not depends on custom User and Group model from `users` app. Add checks otherwise. Looks like we need only `.groups` related manager to work with base User model?
    """
    Customization of the `django.contrib.auth`. This  application relies on
    custom `User` model defined in `users` app.
    """
    name = 'auth'
    label = 'custom_auth'
    verbose_name = _("Authentication and Authorization")
