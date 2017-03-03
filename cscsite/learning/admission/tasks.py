import logging

from django.apps import apps
from django.utils import translation
from django_rq import job
from post_office import mail

from core.settings.base import CENTER_SITE_ID

logger = logging.getLogger(__name__)


@job('high')
def application_form_send_email(applicant_id, language_code):
    """Send email with summary after application form processed"""
    Site = apps.get_model('sites', 'Site')
    site = Site.objects.get(pk=CENTER_SITE_ID)
    translation.activate(language_code)
    Applicant = apps.get_model('admission', 'Applicant')
    applicant = (Applicant.objects
                 .filter(pk=applicant_id)
                 .select_related("campaign", "campaign__city")
                 .first())
    if applicant:
        mail.send(
            [applicant.email],
            sender='info@compscicenter.ru',
            template="admission-application-form-complete",
            context={
                'FIRST_NAME': applicant.first_name,
                'SECOND_NAME': applicant.second_name,
                'LAST_NAME': applicant.last_name,
                'EMAIL': applicant.email,
                'CITY': applicant.campaign.city.name,
                'PHONE': applicant.phone,
                'YANDEX_LOGIN': applicant.yandex_id,
            },
            backend='ses',
        )
    else:
        logger.error("Applicant with id={} not found".format(applicant_id))
