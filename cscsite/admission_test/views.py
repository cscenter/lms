from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import Http404
from django.shortcuts import redirect, render_to_response, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from social_core.actions import do_auth
from social_core.exceptions import MissingBackend, AuthCanceled, \
    SocialAuthBaseException
from social_core.utils import get_strategy, user_is_authenticated, \
    partial_pipeline_data
from vanilla import CreateView

from admission_test.backends import YandexRuOAuth2
from admission_test.forms import AdmissionTestApplicationForm
from admission_test.models import AdmissionTestApplicant


NAMESPACE = 'admission_test'
STRATEGY = 'social_django.strategy.DjangoStrategy'
# Override `user` attribute to prevent accidental user creation
STORAGE = 'admission_test.models.DjangoStorageCustom'
BACKEND_PREFIX = 'ya'
SESSION_LOGIN_KEY = f"{BACKEND_PREFIX}_login"


class AdmissionTestApplicantCreateView(CreateView):
    model = AdmissionTestApplicant
    form_class = AdmissionTestApplicationForm
    template_name = "application_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check yandex login in current user session
        yandex_login = self.request.session.get(SESSION_LOGIN_KEY)
        if yandex_login:
            context["yandex_login"] = yandex_login
        return context

    def get_form(self, data=None, files=None, **kwargs):
        yandex_login = self.request.session.get(SESSION_LOGIN_KEY)
        if yandex_login:
            kwargs["yandex_passport_access_allowed"] = True
            if data:
                data = data.copy()
                data["yandex_id"] = yandex_login
        cls = self.get_form_class()
        return cls(data=data, files=files, **kwargs)

    def form_invalid(self, form):
        if 'yandex_id' in form.errors:
            messages.error(self.request, 'Нет доступа к данным на Яндексе')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('admission_test:registration_complete')


def registration_complete(request):
    request.session.pop(SESSION_LOGIN_KEY, None)
    return render(request, 'registration_complete.html', context={
    })


@never_cache
def auth(request):
    request.social_strategy = get_strategy(STRATEGY, STORAGE, request)
    if not hasattr(request, 'strategy'):
        request.strategy = request.social_strategy
    redirect_uri = reverse('admission_test:auth_complete')
    try:
        request.backend = YandexRuOAuth2(request.social_strategy, redirect_uri)
    except MissingBackend:
        raise Http404('Backend not found')
    return do_auth(request.backend, redirect_name=REDIRECT_FIELD_NAME)


@never_cache
@csrf_exempt
def auth_complete(request, *args, **kwargs):
    """Authentication complete view"""
    request.social_strategy = get_strategy(STRATEGY, STORAGE, request)
    if not hasattr(request, 'strategy'):
        request.strategy = request.social_strategy
    redirect_uri = reverse('admission_test:auth_complete')
    try:
        request.backend = YandexRuOAuth2(request.social_strategy, redirect_uri)
    except MissingBackend:
        raise Http404('Backend not found')

    user = request.user
    backend = request.backend
    redirect_name = REDIRECT_FIELD_NAME
    data = backend.strategy.request_data()

    is_authenticated = user_is_authenticated(user)
    user = user if is_authenticated else None

    try:
        partial = partial_pipeline_data(backend, user, *args, **kwargs)
        if partial:
            # FIXME: UB
            user = backend.continue_pipeline(partial)
        else:
            auth_data = backend.complete(user=user, *args, **kwargs)
        for field_name in ["login", "sex"]:
            key = f"{BACKEND_PREFIX}_{field_name}"
            backend.strategy.session_set(key, auth_data.get(field_name))
    except SocialAuthBaseException as e:
        return render(request, 'close_popup.html', context={"error": str(e)})

    # pop redirect value before the session is trashed on login(), but after
    # the pipeline so that the pipeline can change the redirect if needed
    redirect_value = backend.strategy.session_get(redirect_name, '') or \
                     data.get(redirect_name, '')
    return render(request, 'close_popup.html', context={
        "yandex_login": auth_data.get("login", "")
    })
