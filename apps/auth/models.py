from typing import Optional, Type

from social_django.storage import DjangoUserMixin

from django.db import models

from core.models import TimestampedModel
from users.models import User


class ConnectedAuthService(TimestampedModel, DjangoUserMixin):
    """
    Difference with social_django.models.UserSocialAuth:
        * `created_at` and `modified_at` field names instead of created/modified
        * UserSocialAuthManager was removed
        * Disconnecting provider with class method is prohibited
        * Creating user with class method is prohibited

    Some partials like `.create_user` from the social_django app may not work
    because of the changes above.
    """
    user = models.ForeignKey(User, related_name='social_auth',
                             on_delete=models.CASCADE)
    provider = models.CharField(max_length=32)
    uid = models.CharField(max_length=255, db_index=True)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'auth_connected_service_providers'
        constraints = [
            models.UniqueConstraint(fields=('provider', 'uid'),
                                    name='unique_uid_per_provider')
        ]

    def __str__(self):
        return str(self.user)

    @classmethod
    def get_social_auth(cls, provider: str, uid: str) -> Optional['ConnectedAuthService']:
        return (cls.objects
                .select_related('user')
                .filter(provider=provider, uid=uid)
                .first())

    @classmethod
    def user_model(cls) -> Type[models.Model]:
        return cls._meta.get_field('user').remote_field.model

    @classmethod
    def create_user(cls, *args, **kwargs):
        return False

    @classmethod
    def allowed_to_disconnect(cls, user, backend_name, association_id=None) -> bool:
        return False

    @classmethod
    def disconnect(cls, entry):
        return False

    @classmethod
    def username_max_length(cls) -> int:
        username_field = cls.username_field()
        field = cls.user_model()._meta.get_field(username_field)
        return field.max_length
