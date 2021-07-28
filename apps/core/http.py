from typing import Optional, Union

from django.http import HttpRequest as _HttpRequest

from core.timezone.typing import Timezone
from users.models import ExtendedAnonymousUser, User

__all__ = ["HttpRequest", "AuthenticatedHttpRequest"]


class HttpRequest(_HttpRequest):
    user: Union[User, ExtendedAnonymousUser]
    is_curator: bool
    roles: set
    time_zone: Optional[Timezone]


class AuthenticatedHttpRequest(HttpRequest):
    user: User
