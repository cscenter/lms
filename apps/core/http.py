from typing import Union

from rest_framework.request import Request as _HttpDRFRequest

from django.http import HttpRequest as _HttpDjangoRequest

from users.models import ExtendedAnonymousUser, User

__all__ = ["HttpRequest", "AuthenticatedHttpRequest", "APIRequest", "AuthenticatedAPIRequest"]


class HttpRequest(_HttpDjangoRequest):
    user: Union[User, ExtendedAnonymousUser]


class AuthenticatedHttpRequest(HttpRequest):
    user: User


class APIRequest(_HttpDRFRequest):
    user: Union[User, ExtendedAnonymousUser]


class AuthenticatedAPIRequest(_HttpDRFRequest):
    user: User
