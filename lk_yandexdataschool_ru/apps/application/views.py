from typing import List, Dict

from django.views.generic import TemplateView

from admission.constants import WHERE_DID_YOU_LEARN
from admission.models import Campaign
from auth.views import YANDEX_OAUTH_BACKEND_PREFIX

from core.urls import reverse
from django.db.models import F
from django.middleware.csrf import get_token

from learning.settings import AcademicDegreeLevels

from django.conf import settings

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
        active_campaigns = (Campaign.with_open_registration()
                            .filter(branch__site_id=settings.SITE_ID)
                            .annotate(value=F('branch__code'),
                                      label=F('branch__name'))
                            .values('value', 'label', 'id')
                            .order_by('order'))
        show_form = len(active_campaigns) > 0
        context["show_form"] = show_form
        utm_params = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]
        utm = {param: self.request.GET.get(param) for param in utm_params}
        sources = [{"value": k, "label": v} for k, v in WHERE_DID_YOU_LEARN]
        if show_form:
            levels_of_education = [{"value": k, "label": str(v).lower()} for k, v in
                                   AcademicDegreeLevels.values.items()]

            yandex_passport_access = self.request.session.get(SESSION_LOGIN_KEY)
            context['app'] = {
                'props': {
                    'utm': utm,
                    'endpoint': reverse('applicant_create'),
                    'csrfToken': get_token(self.request),
                    'authCompleteUrl': reverse('auth:application:complete'),
                    'authBeginUrl': reverse('auth:application:begin'),
                    'endpointCities': reverse('universities:v1:cities'),
                    'endpointUniversities': reverse('universities:v1:universities'),
                    'campaigns': list(active_campaigns),
                    'educationLevelOptions': levels_of_education,
                    'sourceOptions': sources,
                    'partners': get_partners(),
                },
                'state': {
                    'isYandexPassportAccessAllowed': bool(yandex_passport_access),
                }
            }
        return context
