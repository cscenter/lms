from typing import Optional, Type

from social_django.storage import (
    DjangoAssociationMixin, DjangoCodeMixin, DjangoNonceMixin, DjangoPartialMixin,
    DjangoUserMixin
)

from django.db import models

from core.models import TimestampedModel
from users.models import User


class OpenIDNonce(DjangoNonceMixin, models.Model):
    """
    This is a helper class for OpenID mechanism that stores a one-use number.

    Shouldn’t be used by the project since it’s for `social_auth` internal
    use only.
    """
    server_url = models.CharField(max_length=255)
    timestamp = models.IntegerField()
    salt = models.CharField(max_length=65)

    class Meta:
        db_table = 'auth_social_openid_nonces'
        constraints = [
            models.UniqueConstraint(
                fields=('server_url', 'timestamp', 'salt'),
                name='unique_salt_per_timestamp_per_server_url'
            ),
        ]


class OpenIDAssociation(DjangoAssociationMixin, models.Model):
    """
    Another OpenID helper class, it stores basic data to keep the OpenID
    association. Like Nonce this is for `social_auth` internal use only.
    """
    server_url = models.CharField(max_length=255)
    handle = models.CharField(max_length=255)
    secret = models.CharField(max_length=255)  # Stored base64 encoded
    issued = models.IntegerField()
    lifetime = models.IntegerField()
    assoc_type = models.CharField(max_length=64)

    class Meta:
        db_table = 'auth_social_openid_associations'
        constraints = [
            models.UniqueConstraint(
                fields=('server_url', 'handle'),
                name='unique_handle_per_server_url'
            ),
        ]


class EmailValidationCode(DjangoCodeMixin, models.Model):
    """
    This class is used to keep track of email validations codes following
    the usual email validation mechanism of sending an email to the user
    with a unique code.

    This model is used by the partial pipeline `social_core.pipeline.mail.mail_validation`.
    """
    email = models.EmailField(max_length=254)
    code = models.CharField(max_length=32, db_index=True)
    verified = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'auth_social_email_validation'
        constraints = [
            models.UniqueConstraint(
                fields=('email', 'code'),
                name='unique_code_per_email'
            ),
        ]


class Partial(DjangoPartialMixin, models.Model):
    token = models.CharField(max_length=32, db_index=True)
    next_step = models.PositiveSmallIntegerField(default=0)
    backend = models.CharField(max_length=32)
    data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'auth_social_partial'


class ConnectedAuthService(TimestampedModel, DjangoUserMixin):
    """
    Difference with social_django.models.UserSocialAuth:
        * `created_at` and `modified_at` field names instead of created/modified
        * UserSocialAuthManager was removed
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
    def allowed_to_disconnect(cls, user: User, backend_name: str,
                              association_id: Optional[int] = None) -> bool:
        return backend_name != "gerrit"

    @classmethod
    def disconnect(cls, entry: 'ConnectedAuthService'):
        entry.delete()

    @classmethod
    def username_max_length(cls) -> int:
        username_field = cls.username_field()
        field = cls.user_model()._meta.get_field(username_field)
        return field.max_length

    @property
    def login(self) -> Optional[str]:
        if self.provider == "gerrit":
            return self.uid
        elif isinstance(self.extra_data, dict):
            if "login" in self.extra_data:
                return self.extra_data["login"]
            return self.extra_data.get("username", None)
        return None
