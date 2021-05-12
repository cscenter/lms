import json

from rest_framework.permissions import AllowAny
from rest_framework.status import HTTP_201_CREATED
from rest_framework.views import APIView

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse

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
