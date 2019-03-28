from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from admission.api.serializers import ApplicantSerializer
from admission.views import SESSION_LOGIN_KEY


class ApplicantCreateAPIView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ApplicantSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        # Insert yandex login if session value were found, otherwise remove it
        if data:
            data = data.copy()
            yandex_login = self.request.session.get(SESSION_LOGIN_KEY, None)
            if yandex_login:
                data["yandex_id"] = yandex_login
            elif "yandex_id" in data:
                del data["yandex_id"]
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # Remove yandex login data from session
        self.request.session.pop(SESSION_LOGIN_KEY, None)
        return Response(serializer.data, status=status.HTTP_201_CREATED,
                        headers=headers)
