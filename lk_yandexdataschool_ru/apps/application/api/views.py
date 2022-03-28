import json

from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.status import HTTP_201_CREATED
from rest_framework.views import APIView
from rest_framework.response import Response

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse

from application.api.serializers import ApplicationYDSFormSerializer
from application.views import SESSION_LOGIN_KEY
from lk_yandexdataschool_ru.apps.application.tasks import register_new_application_form


class ApplicationFormCreateTaskView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        try:
            json_data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest()
        is_jsonrpc2 = json_data.get('jsonrpc', '') == '2.0'
        if not is_jsonrpc2 or not isinstance(json_data.get('params'), dict) or not json_data.get('id'):
            return HttpResponseBadRequest()
        # Check request permissions
        if json_data['params'].get('SecretToken') != settings.APPLICATION_FORM_SECRET_TOKEN:
            return HttpResponseForbidden()

        form_data = json_data['params']
        del form_data['SecretToken']
        answer_id = form_data.get('id')
        if not answer_id:
            return HttpResponseBadRequest()
        delayed_job = register_new_application_form.delay(answer_id=answer_id,
                                                          language_code=request.LANGUAGE_CODE,
                                                          form_data=form_data)
        payload = {
            "jsonrpc": "2.0",
            "id": answer_id,
            "result": delayed_job.id,
        }
        return JsonResponse(payload, status=HTTP_201_CREATED)


class ApplicantCreateFromYDSFormAPIView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ApplicationYDSFormSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        # Insert yandex login if session value were found, otherwise remove it
        if data:
            data = data.copy()
            yandex_login = self.request.session.get(SESSION_LOGIN_KEY, None)
            if yandex_login:
                data["yandex_login"] = yandex_login
            elif "yandex_login" in data:
                del data["yandex_login"]
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # Remove yandex login data from session
        self.request.session.pop(SESSION_LOGIN_KEY, None)
        return Response(serializer.data, status=status.HTTP_201_CREATED,
                        headers=headers)
