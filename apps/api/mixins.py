from rest_framework import exceptions as rest_exceptions
from rest_framework.views import exception_handler as drf_exception_handler

from django.core.exceptions import ValidationError

from api.errors import ErrorsFormatter


def get_first_matching_attr(obj, *attrs, default=None):
    for attr in attrs:
        if hasattr(obj, attr):
            return getattr(obj, attr)
    return default


def get_error_message(exc):
    """
    Returns error message(s) from Django's' exceptions
    """
    if hasattr(exc, 'error_dict'):
        return exc.error_dict
    error_msg = get_first_matching_attr(exc, 'message', 'messages')

    if isinstance(error_msg, list):
        error_msg = ', '.join(error_msg)

    if error_msg is None:
        error_msg = str(exc)

    return error_msg


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    # Unexpected errors (e.g. 5xx server error)
    if response is None:
        return response
    response.data = ErrorsFormatter(exc).format()
    return response


class ApiErrorsMixin:
    """
    Converts known Django and Python exceptions into a DRF format.
    Without this cast a 500 error will be raised.

    Note:
        DRF exception handler knows how to handle Django's Http404 and
        PermissionDenied exceptions.
    """
    cast_exceptions = {
        ValidationError: rest_exceptions.ValidationError,
        ValueError: rest_exceptions.ValidationError
    }

    def handle_exception(self, exc):
        e = exc
        if isinstance(exc, tuple(self.cast_exceptions.keys())):
            drf_exception_class = self.cast_exceptions[exc.__class__]
            code = getattr(exc, "code", None)
            e = drf_exception_class(detail=get_error_message(exc), code=code)
        return super().handle_exception(e)

    def get_exception_handler(self):
        # TODO: remove when it will be safe to enable this handler globally
        #  in rest settings
        return exception_handler
