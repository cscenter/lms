from django.conf import settings
from django.utils import translation
from django_rq import job

from admission.tasks import register_in_yandex_contest
from lk_yandexdataschool_ru.apps.application.api.serializers import ApplicantYandexFormSerializer


@job('high')
def register_new_application_form(*, answer_id, language_code, form_data):
    translation.activate(language_code)
    serializer = ApplicantYandexFormSerializer(data=form_data)
    serializer.is_valid(raise_exception=True)
    # Registration by the same email is prohibited by form settings
    new_applicant = serializer.save(meta={"answer_id": answer_id})
    if new_applicant.pk:
        register_in_yandex_contest.delay(new_applicant.pk, settings.LANGUAGE_CODE)
