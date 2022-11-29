# -*- coding: utf-8 -*-


from django.conf import settings
from django.db.models import F

from django.middleware.csrf import get_token

from django.views.generic.base import TemplateView

from admission.constants import WHERE_DID_YOU_LEARN
from admission.models import Applicant, Campaign
from auth.views import YANDEX_OAUTH_BACKEND_PREFIX

from core.models import University
from core.urls import reverse
from learning.settings import AcademicDegreeLevels

STRATEGY = 'social_django.strategy.DjangoStrategy'
# Override `user` attribute to prevent accidental user creation
STORAGE = __name__ + '.DjangoStorageCustom'
SESSION_LOGIN_KEY = f"{YANDEX_OAUTH_BACKEND_PREFIX}_login"


class ApplicationFormView(TemplateView):
    template_name = "compscicenter_ru/admission/application_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_campaigns = (Campaign.with_open_registration()
                            .filter(branch__site_id=settings.SITE_ID)
                            .annotate(value=F('branch__code'),
                                      label=F('branch__name'))
                            .values('value', 'label', 'id'))
        show_form = len(active_campaigns) > 0
        context["show_form"] = show_form
        if show_form:
            universities = (University.objects
                            .exclude(abbr='other')
                            .annotate(value=F('id'), label=F('name'))
                            .values('value', 'label', 'city_id')
                            .order_by("name"))
            levels_of_education = [{"value": k, "label": str(v).lower()} for k, v in
                                   AcademicDegreeLevels.values.items()]
            study_programs = [{"value": k, "label": v} for k, v in
                              Applicant.STUDY_PROGRAMS]
            sources = [{"value": k, "label": v} for k, v in WHERE_DID_YOU_LEARN]

            yandex_passport_access = self.request.session.get(SESSION_LOGIN_KEY)
            context['app'] = {
                'props': {
                    'endpoint': reverse('public-api:v2:applicant_create'),
                    'csrfToken': get_token(self.request),
                    'authCompleteUrl': reverse('auth:application:complete'),
                    'authBeginUrl': reverse('auth:application:begin'),
                    'campaigns': list(active_campaigns),
                    'universities': list(universities),
                    'educationLevelOptions': levels_of_education,
                    'studyProgramOptions': study_programs,
                    'sourceOptions': sources
                },
                'state': {
                    'isYandexPassportAccessAllowed': bool(yandex_passport_access),
                }
            }
        return context
