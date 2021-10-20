from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuthConfig(AppConfig):
    """
    Customization of the `django.contrib.auth`. This  application relies on
    custom `User` model defined in `users` app.
    """
    name = 'auth'
    label = 'custom_auth'
    verbose_name = _("Authentication and Authorization")
