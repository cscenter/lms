from typing import List, Union

from auth.models import ConnectedAuthService
from users.models import User


def get_connected_accounts(*, user: Union[User, int]) -> List[ConnectedAuthService]:
    connected_accounts = (ConnectedAuthService.objects
                          .filter(user=user))
    return list(connected_accounts)
