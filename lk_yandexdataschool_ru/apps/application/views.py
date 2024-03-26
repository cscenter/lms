from typing import List, Dict

from django.utils import timezone
from django.views.generic import TemplateView

from admission.constants import WHERE_DID_YOU_LEARN, DiplomaDegrees
from admission.models import Campaign, CampaignCity
from auth.views import YANDEX_OAUTH_BACKEND_PREFIX

from core.urls import reverse
from django.db.models import F
from django.middleware.csrf import get_token

from learning.settings import AcademicDegreeLevels

from django.conf import settings

from users.constants import GenderTypes
from users.models import PartnerTag

SESSION_LOGIN_KEY = f"{YANDEX_OAUTH_BACKEND_PREFIX}_login"


def get_partners() -> List[Dict]:
    partners = [
        {
            "id": partner.id,
            "value": partner.slug,
            "label": f"Да, {partner.name}"
        } for partner in PartnerTag.objects.all()
    ]
    return partners


class ApplicationFormView(TemplateView):
    template_name = "lk_yandexdataschool_ru/application_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now()
        always_allow_campaigns = (
            CampaignCity.objects
                .filter(city__isnull=True,
                        campaign__current=True,
                        campaign__application_starts_at__lte=today,
                        campaign__application_ends_at__gt=today,
                        campaign__branch__site_id=settings.SITE_ID
                        )
                .annotate(value=F('campaign__branch__code'),
                          label=F('campaign__branch__name'),
                )
                .select_related('campaign', 'campaign__branch')
                .order_by('campaign__order')
                .values('value', 'label', 'campaign_id')
        )

        show_form = len(always_allow_campaigns) > 0
        context["show_form"] = show_form
        utm_params = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]
        utm = {param: self.request.GET.get(param) for param in utm_params}
        sources = [{"value": k, "label": v} for k, v in WHERE_DID_YOU_LEARN]
        if show_form:
            levels_of_education = [{"value": k, "label": str(v)} for k, v in
                                   AcademicDegreeLevels.values.items()]
            diploma_degrees = [{"value": k, "label": str(v)} for k, v in
                                   DiplomaDegrees.values.items()]
            genders = [{"value": k, "label": str(v)} for k, v in
                                   GenderTypes.values.items()]
            self.request.session.pop(SESSION_LOGIN_KEY, None)
            yandex_passport_access = False
            # yandex_passport_access = self.request.session.get(SESSION_LOGIN_KEY)
            context['app'] = {
                'props': {
                    'utm': utm,
                    'endpoint': reverse('applicant_create'),
                    'csrfToken': get_token(self.request),
                    'authCompleteUrl': reverse('auth:application:complete'),
                    'authBeginUrl': reverse('auth:application:begin'),
                    'endpointUniversitiesCities': reverse('universities:v1:cities'),
                    'endpointUniversities': reverse('universities:v1:universities'),
                    'endpointResidenceCities': reverse('admission-api:v2:residence_cities'),
                    'endpointResidenceCampaigns': reverse('admission-api:v2:residence_city_campaigns'),
                    'alwaysAllowCampaigns': list(always_allow_campaigns),
                    'educationLevelOptions': levels_of_education,
                    'diplomaDegreeOptions': diploma_degrees,
                    'genderOptions': genders,
                    'sourceOptions': sources,
                    'partners': get_partners(),
                },
                'state': {
                    'isYandexPassportAccessAllowed': bool(yandex_passport_access),
                }
            }
        return context
