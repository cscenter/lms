from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .services import TokenService

UserModel = get_user_model()


class TokenObtainSerializer(serializers.Serializer):
    username_field = UserModel.USERNAME_FIELD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[self.username_field] = serializers.CharField()
        self.fields['password'] = serializers.CharField(
            style={'input_type': 'password'},
            write_only=True)

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            'password': attrs['password'],
        }
        try:
            authenticate_kwargs['request'] = self.context['request']
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)

        if self.user is None or not self.user.is_active:
            raise serializers.ValidationError(_('No active account found'))
        return {
            'secret_key': self.get_token(self.user)
        }

    @classmethod
    def get_token(cls, user):
        _, token = TokenService.create(user)
        return token


class TokenRevokeSerializer(serializers.Serializer):
    pass
