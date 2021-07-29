from typing import Union

from django.http import HttpRequest as _HttpRequest

from users.models import ExtendedAnonymousUser, User

__all__ = ["HttpRequest", "AuthenticatedHttpRequest"]


class HttpRequest(_HttpRequest):
    user: Union[User, ExtendedAnonymousUser]


class AuthenticatedHttpRequest(HttpRequest):
    user: User
