from social_core.utils import handle_http_errors
from social_django.strategy import DjangoStrategy


class DjangoStrategyCustom(DjangoStrategy):
    """
    Retrieves login from social app without trying to login user
    """
    def authenticate(self, backend, *args, **kwargs):
        raise NotImplementedError()
