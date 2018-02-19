from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from social_core.actions import do_auth
from social_core.exceptions import MissingBackend
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


class AdmissionTestApplicantCreateView(CreateView):
    model = AdmissionTestApplicant
    form_class = AdmissionTestApplicationForm

    def get_template_names(self):
        if self.request.session.get(f"{BACKEND_PREFIX}_login"):
            return ["learning/admission/test_2018_application_form.html"]
        else:
            return ["learning/admission/test_2018_application_form_welcome.html"]


@never_cache
def auth(request):
    request.social_strategy = get_strategy(STRATEGY, STORAGE, request)
    if not hasattr(request, 'strategy'):
        request.strategy = request.social_strategy
    redirect_uri = reverse('admission_test:auth_complete')
    try:
        # TODO: после редиректа к нам, pipeline должен в уже имеющейся сессии сохранить login, в форму подсавить ФИ, если указаны
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

    partial = partial_pipeline_data(backend, user, *args, **kwargs)
    if partial:
        # FIXME: UB
        user = backend.continue_pipeline(partial)
    else:
        auth_data = backend.complete(user=user, *args, **kwargs)
    for field_name in ["first_name", "second_name", "login", "sex"]:
        key = f"{BACKEND_PREFIX}_{field_name}"
        backend.strategy.session_set(key, auth_data.get(field_name))

    # pop redirect value before the session is trashed on login(), but after
    # the pipeline so that the pipeline can change the redirect if needed
    redirect_value = backend.strategy.session_get(redirect_name, '') or \
                     data.get(redirect_name, '')
    print(auth_data)
    return redirect('admission_test:admission_2018_testing')
