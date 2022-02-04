from dataclasses import dataclass
from typing import List, Optional, Union

from auth.models import ConnectedAuthService
from users.models import User


@dataclass
class ServiceProvider:
    name: str
    code: str
    is_readonly: bool = False


def get_connected_accounts(*, user: Union[User, int]) -> List[ConnectedAuthService]:
    connected_accounts = (ConnectedAuthService.objects
                          .filter(user=user)
                          # in case multiple ids were associated with provider
                          .order_by('pk'))
    return list(connected_accounts)


def get_available_service_providers() -> List[ServiceProvider]:
    return [
        ServiceProvider(code='gerrit', name='review.compscicenter.ru', is_readonly=True),
        ServiceProvider(code='gitlab-manytask', name='gitlab.manytask.org'),
        # ServiceProvider(code='github', name='Github'),
        # ServiceProvider(code='ya', name='Yandex.Login'),
    ]
