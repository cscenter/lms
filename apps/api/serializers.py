from rest_framework import serializers

from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext_lazy as _

from .services import TokenService

UserModel = get_user_model()


class TokenObtainSerializer(serializers.Serializer):
    login_field_name: str = UserModel.USERNAME_FIELD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #
        self.fields['login'] = serializers.CharField()
        self.fields['password'] = serializers.CharField(
            style={'input_type': 'password'},
            write_only=True)

    def validate(self, attrs):
        authenticate_kwargs = {
            self.login_field_name: attrs['login'],
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
            'secret_token': self.get_token(self.user)
        }

    @classmethod
    def get_token(cls, user):
        _, token = TokenService.create(user)
        return token


class TokenRevokeSerializer(serializers.Serializer):
    pass
