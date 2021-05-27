from rest_framework import exceptions, status
from rest_framework.settings import api_settings

from django.utils.translation import gettext_lazy as _


class TokenError(Exception):
    pass


class AuthenticationFailed(exceptions.AuthenticationFailed):
    pass


class InvalidToken(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _('Token is invalid or expired')
    default_code = 'token_not_valid'


# FIXME: add tests https://www.django-rest-framework.org/api-guide/exceptions/#exception-handling-in-rest-framework-views
class ErrorsFormatter:
    """
    The formatter parses errors to the following format
    inspired by https://github.com/HackSoftware/Django-Styleguide:
    {
        "errors": [
            {
                "message": "Error message",
                "code": "Some code",
                "field": "field_name"
            },
            {
                "message": "Error message",
                "code": "Some code",
                "field": "nested.field_name"
            },
            ...
        ]
    }
    """
    FIELD = 'field'
    MESSAGE = 'message'
    CODE = 'code'

    def __init__(self, exception):
        self.exception = exception

    def format(self):
        if hasattr(self.exception, 'get_full_details'):
            errors = self._convert_drf_errors(serializer_errors=self.exception.get_full_details())
        else:
            errors = self._convert_error_message(message=str(self.exception))
        return {
            "errors": errors
        }

    def _convert_drf_errors(self, serializer_errors=None):
        if serializer_errors is None:
            serializer_errors = {}
        if isinstance(serializer_errors, list):
            serializer_errors = {
                api_settings.NON_FIELD_ERRORS_KEY: serializer_errors
            }
        return self._get_list_of_errors(errors_dict=serializer_errors)

    def _convert_error_message(self, *, message='', code='error'):
        return [
            {
                self.MESSAGE: message,
                self.CODE: code
            }
        ]

    def _get_list_of_errors(self, field_path='', errors_dict=None):
        """
        `errors_dict` is in the following format:
        {
            'field1': {
                'message': 'some message'
                'code' 'some code'
            },
            'field2: ...'
        }
        """
        if errors_dict is None:
            return []

        # If 'message' is name of a field we don't want to stop the recursion here
        message_value = errors_dict.get(self.MESSAGE, None)
        if message_value is not None and isinstance(message_value, (str, exceptions.ErrorDetail)):
            if field_path:
                errors_dict[self.FIELD] = field_path
            return [errors_dict]

        errors_list = []
        for key, value in errors_dict.items():
            new_field_path = '{0}.{1}'.format(field_path, key) if field_path else key
            key_is_non_field_errors = key == api_settings.NON_FIELD_ERRORS_KEY
            if isinstance(value, list):
                current_level_error_list = []
                for field_error in value:
                    # If the type of `field_error` is a list we need to unpack it
                    if isinstance(field_error, list) and len(field_error) == 1:
                        field_error = field_error[0]
                    if not key_is_non_field_errors:
                        field_error[self.FIELD] = new_field_path
                    current_level_error_list.append(field_error)
            else:
                path = field_path if key_is_non_field_errors else new_field_path
                current_level_error_list = self._get_list_of_errors(field_path=path, errors_dict=value)
            errors_list += current_level_error_list
        return errors_list
