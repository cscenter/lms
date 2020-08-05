import logging

from django.contrib.auth import get_user_model
from social_core.backends.oauth import BaseOAuth2
from social_core.utils import handle_http_errors

from .registry import role_registry

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class RBACPermissions:
    """
    Backend uses RBAC model approach allowing to check permissions
    both on model and object level.

    Default roles and permissions are not supported.

    Implementation uses `UserModel.roles` attribute which should return
    set of available roles for the user.
    """
    def authenticate(self, *args, **kwargs):
        return None

    def has_perm(self, user, perm, obj=None):
        if not user.is_active and not user.is_anonymous:
            return False
        default_role = role_registry.default_role
        if user.is_anonymous:
            return self._has_perm(user, perm, {default_role}, obj)
        elif hasattr(user, 'roles'):
            roles = [default_role]
            for role_code in user.roles:
                if role_code not in role_registry:
                    logger.warning(f'Role with a code {role_code} is not '
                                   f'registered but assigned to the user {user}')
                    continue
                role = role_registry[role_code]
                roles.append(role)
            roles.sort(key=lambda r: r.priority)
            return self._has_perm(user, perm, roles, obj)
        return False

    def _has_perm(self, user, perm_name, roles, obj):
        for role in roles:
            if role.permissions.rule_exists(perm_name):
                return role.permissions[perm_name].test(user, obj)
            # Case when using base permission name, e.g.,
            # `.has_perm('update_comment', obj)` and expecting
            # .has_perm('update_own_comment', obj) will be in a call chain
            # if relation exists
            if perm_name in role.relations:
                # Related `Permission.rule` checks only object level
                # permission
                if obj is None:
                    continue
                for rel_perm_name in role.relations[perm_name]:
                    if self._has_perm(user, rel_perm_name, {role}, obj):
                        return True
        return False

    def has_module_perms(self, user, app_label):
        return self.has_perm(user, app_label)


class RBACModelBackend(RBACPermissions):
    """
    Authenticates against `users.models.User` like
    `django.contrib.auth.backends.ModelBackend`. Uses own implementation of
    permissions verification based on `django-rules` which
    allows to check permissions on object level
    """
    # FIXME: maintain compatibility with `django.contrib.auth.models.User` permissions verification
    # FIXME: Implement the verification of permissions based on django-rules first (could be used as separated backend for permissions verification)
    # FIXME: Then return migrate back to default `User.groups` implementation to support built-in permissions and `get_user_model()` instead of custom user model
    def authenticate(self, request, username=None, password=None, **kwargs):
        # XXX this is fine, since @ is not allowed in usernames.
        field = "email" if "@" in username else "username"
        try:
            user = UserModel.objects.get(**{field: username})
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            # See comment in 'ModelBackend#authenticate'.
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            UserModel().set_password(password)

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None


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
