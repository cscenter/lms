# -*- coding: utf-8 -*-

from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.db.models import F
from django.http.response import Http404
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView
from social_core.actions import do_auth
from social_core.exceptions import MissingBackend, SocialAuthBaseException
from social_core.storage import UserMixin
from social_core.utils import user_is_authenticated
from social_django.models import DjangoStorage
from social_django.strategy import DjangoStrategy

from admission.constants import WHERE_DID_YOU_LEARN
from admission.models import Applicant, Campaign, University
from auth.backends import YandexRuOAuth2Backend
from core.urls import reverse
from learning.settings import AcademicDegreeLevels

STRATEGY = 'social_django.strategy.DjangoStrategy'
# Override `user` attribute to prevent accidental user creation
STORAGE = __name__ + '.DjangoStorageCustom'
BACKEND_PREFIX = 'application_ya'
SESSION_LOGIN_KEY = f"{BACKEND_PREFIX}_login"


class DjangoStorageCustom(DjangoStorage):
    user = UserMixin


def redirect_to(redirect_url):
    """Used for yandex oauth view to pass redirect url pattern name"""
    def _wrapper(f):
        @wraps(f)
        def _inner(*args, **kwargs):
            return f(*args, redirect_url=redirect_url, **kwargs)
        return _inner
    return _wrapper


@never_cache
@redirect_to("application:auth_complete")
def yandex_login_access(request, *args, **kwargs):
    redirect_url = reverse(kwargs.pop("redirect_url"))
    request.social_strategy = DjangoStrategy(DjangoStorageCustom, request,
                                             *args, **kwargs)
    if not hasattr(request, 'strategy'):
        request.strategy = request.social_strategy
    try:
        request.backend = YandexRuOAuth2Backend(request.social_strategy, redirect_url)
    except MissingBackend:
        raise Http404('Backend not found')
    return do_auth(request.backend, redirect_name=REDIRECT_FIELD_NAME)


@never_cache
@csrf_exempt
@redirect_to("application:auth_complete")
def yandex_login_access_complete(request, *args, **kwargs):
    """
    Authentication complete view. Our main goal - to retrieve user yandex login.
    """
    redirect_url = reverse(kwargs.pop("redirect_url"))
    request.social_strategy = DjangoStrategy(DjangoStorageCustom, request,
                                             *args, **kwargs)
    if not hasattr(request, 'strategy'):
        request.strategy = request.social_strategy
    try:
        request.backend = YandexRuOAuth2Backend(request.social_strategy,
                                                redirect_url)
    except MissingBackend:
        raise Http404('Backend not found')

    user = request.user
    backend = request.backend

    is_authenticated = user_is_authenticated(user)
    user = user if is_authenticated else None

    # Note: Pipeline is never called since we prevent user authentication
    try:
        auth_data = backend.complete(user=user, *args, **kwargs)
        for field_name in ["login", "sex"]:
            key = f"{BACKEND_PREFIX}_{field_name}"
            backend.strategy.session_set(key, auth_data.get(field_name))
        context = {"yandex_login": auth_data.get("login", "")}
    except SocialAuthBaseException as e:
        context = {"error": str(e)}
    return render(request, 'admission/social_close_popup.html', context=context)


class ApplicationFormView(TemplateView):
    template_name = "compscicenter_ru/admission/application_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_campaigns = (Campaign.with_open_registration()
                            .annotate(value=F('branch__code'),
                                      label=F('branch__name'))
                            .values('value', 'label', 'id'))
        show_form = len(active_campaigns) > 0
        context["show_form"] = show_form
        if show_form:
            universities = (University.objects
                            .exclude(abbr='other')
                            .annotate(value=F('id'), label=F('name'))
                            .values('value', 'label', 'branch_id')
                            .order_by("name"))
            levels_of_education = [{"value": k, "label": str(v)} for k, v in
                                   AcademicDegreeLevels.values.items()]
            study_programs = [{"value": k, "label": v} for k, v in
                              Applicant.STUDY_PROGRAMS]
            sources = [{"value": k, "label": v} for k, v in WHERE_DID_YOU_LEARN]

            yandex_passport_access = self.request.session.get(SESSION_LOGIN_KEY)
            context['app'] = {
                'props': {
                    'endpoint': reverse('public-api:v2:applicant_create'),
                    'csrfToken': get_token(self.request),
                    'authCompleteUrl': reverse('application:auth_complete'),
                    'authBeginUrl': reverse('application:auth_begin'),
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
