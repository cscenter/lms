from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.views import exception_handler as drf_exception_handler

from . import serializers
from .errors import ErrorsFormatter, InvalidToken, TokenError


class TokenViewBase(APIView):
    permission_classes = ()
    authentication_classes = ()

    serializer_class = None

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class TokenObtainView(TokenViewBase):
    """
    Takes a set of user credentials and returns an access token
    to prove the authentication of those credentials.
    """
    serializer_class = serializers.TokenObtainSerializer


class TokenRevokeView(TokenViewBase):
    serializer_class = serializers.TokenRevokeSerializer


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    # Unexpected errors (e.g. 5xx server error)
    if response is None:
        return response
    response.data = ErrorsFormatter(exc).format()
    return response
