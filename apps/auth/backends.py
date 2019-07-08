from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from social_core.backends.oauth import BaseOAuth2
from social_core.utils import handle_http_errors


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # XXX this is fine, since @ is not allowed in usernames.
        field = "email" if "@" in username else "username"
        user_model = get_user_model()
        try:
            user = user_model.objects.get(**{field: username})
            if user.check_password(password):
                return user
        except user_model.DoesNotExist:
            # See comment in 'ModelBackend#authenticate'.
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            user_model().set_password(password)


class YandexRuOAuth2Backend(BaseOAuth2):
    name = 'yandexru'
    AUTHORIZATION_URL = 'https://oauth.yandex.ru/authorize'
    ACCESS_TOKEN_URL = 'https://oauth.yandex.ru/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REDIRECT_STATE = False

    def auth_extra_arguments(self):
        extra_arguments = super().auth_extra_arguments()
        extra_arguments["force_confirm"] = "yes"
        return extra_arguments

    @handle_http_errors
    def auth_complete(self, *args, **kwargs):
        """
        Completes process, preventing user authentication and pipeline running
        """
        self.process_error(self.data)
        state = self.validate_state()
        response = self.request_access_token(
            self.access_token_url(),
            data=self.auth_complete_params(state),
            headers=self.auth_headers(),
            auth=self.auth_complete_credentials(),
            method=self.ACCESS_TOKEN_METHOD
        )
        self.process_error(response)
        data = self.user_data(response['access_token'], *args, **kwargs)
        response.update(data or {})
        return response

    def get_user_details(self, response):
        fullname, first_name, last_name = self.get_user_names(
            response.get('real_name') or response.get('display_name') or ''
        )
        email = response.get('default_email')
        if not email:
            emails = response.get('emails')
            email = emails[0] if emails else ''
        return {'username': response.get('login'),
                'email': email,
                'fullname': fullname,
                'first_name': first_name,
                'last_name': last_name}

    def user_data(self, access_token, *args, **kwargs):
        return self.get_json('https://login.yandex.ru/info',
                             params={'oauth_token': access_token,
                                     'format': 'json'})
