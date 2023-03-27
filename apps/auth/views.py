from typing import Iterable

from braces.views import LoginRequiredMixin
from django.db import IntegrityError
from social_core.actions import do_disconnect
from social_core.exceptions import AuthException
from social_core.utils import partial_pipeline_data, setting_url
from social_django.utils import psa

from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth import views
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from auth.forms import AsyncPasswordResetForm, LoginForm
from auth.storage import SocialServiceStorage
from core.urls import reverse, reverse_lazy
from users.constants import Roles

from functools import wraps

from social_core.actions import do_auth
from social_core.exceptions import MissingBackend, SocialAuthBaseException
from social_core.storage import UserMixin
from social_core.utils import user_is_authenticated
from social_django.models import DjangoStorage
from social_django.strategy import DjangoStrategy
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http.response import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from auth.backends import YandexRuOAuth2Backend
from users.models import YandexUserData

YANDEX_OAUTH_BACKEND_PREFIX = 'application_ya'


class LoginView(generic.FormView):
    redirect_field_name = auth.REDIRECT_FIELD_NAME
    form_class = LoginForm
    template_name = "login.html"

    @method_decorator(never_cache)
    @method_decorator(sensitive_post_parameters('password'))
    def dispatch(self, *args, **kwargs):
        return super(LoginView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        auth.login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_next"] = (self.redirect_field_name in self.request.POST
                               or self.redirect_field_name in self.request.GET)
        return context

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name)

        if not redirect_to:
            user_roles = self.request.user.roles
            if user_roles == {Roles.STUDENT}:
                redirect_to = reverse("study:assignment_list")
            elif user_roles == {Roles.TEACHER}:
                redirect_to = reverse("teaching:assignments_check_queue")

        hosts = {self.request.get_host()}
        if not url_has_allowed_host_and_scheme(redirect_to, allowed_hosts=hosts):
            redirect_to = settings.LOGOUT_REDIRECT_URL

        return redirect_to

    def get(self, request, *args, **kwargs):
        self.request.session.set_test_cookie()
        return super(LoginView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            if self.request.session.test_cookie_worked():
                self.request.session.delete_test_cookie()
            return self.form_valid(form)
        else:
            self.request.session.set_test_cookie()
            return self.form_invalid(form)


class LogoutView(LoginRequiredMixin, generic.RedirectView):
    redirect_field_name = auth.REDIRECT_FIELD_NAME

    def get(self, request, *args, **kwargs):
        # FIXME: enable after bugfix in django-loginas
        # restore_original_login(request)
        auth.logout(request)
        return super(LogoutView, self).get(request, *args, **kwargs)

    def get_redirect_url(self, **kwargs):
        redirect_to = settings.LOGOUT_REDIRECT_URL

        if self.redirect_field_name in self.request.GET:
            maybe_redirect_to = self.request.GET[self.redirect_field_name]
            hosts = {self.request.get_host()}
            if url_has_allowed_host_and_scheme(maybe_redirect_to,
                                               allowed_hosts=hosts):
                redirect_to = maybe_redirect_to

        return redirect_to


pass_reset_view = views.PasswordResetView.as_view(
    form_class=AsyncPasswordResetForm,
    success_url=reverse_lazy('auth:password_reset_done'),
    email_template_name=None,
    html_email_template_name=None,
    subject_template_name=None)


pass_reset_confirm_view = views.PasswordResetConfirmView.as_view(
    success_url=reverse_lazy('auth:password_reset_complete')
)


class ConnectServiceStrategy(DjangoStrategy):
    def get_backends(self) -> Iterable[str]:
        return [
            'auth.backends.GitLabManyTaskOAuth2',
            'social_core.backends.github.GithubOAuth2'
        ]

    def authenticate(self, backend, *args, **kwargs):
        """
        Instead of trying to authenticate user with the default Django's
        mechanism (see settings.AUTHENTICATION_BACKENDS), let's directly
        run the pipeline. The purpose of this strategy is to associate user
        account with the service, not the authentication.
        """
        kwargs['strategy'] = self
        kwargs['storage'] = self.storage
        kwargs['backend'] = backend
        kwargs.setdefault('request', None)
        args, kwargs = self.clean_authenticate_args(*args, **kwargs)
        return backend.authenticate(*args, **kwargs)

    def get_pipeline(self, backend=None) -> Iterable[str]:
        return (
            'social_core.pipeline.social_auth.social_details',
            'social_core.pipeline.social_auth.social_uid',
            'social_core.pipeline.social_auth.auth_allowed',
            # Checks if the current service is already associated with the user
            'social_core.pipeline.social_auth.social_user',
            # Create the record that associated the service with this user
            'social_core.pipeline.social_auth.associate_user',
            # Populate the extra_data field in the social record with the values
            # specified by settings (and the default ones like access_token, etc).
            'social_core.pipeline.social_auth.load_extra_data',
        )

    def get_disconnect_pipeline(self, backend=None) -> Iterable[str]:
        return [
            'social_core.pipeline.disconnect.allowed_to_disconnect',
            'social_core.pipeline.disconnect.get_entries',
            'social_core.pipeline.disconnect.revoke_tokens',
            'social_core.pipeline.disconnect.disconnect'
        ]


def connect_service_strategy(request=None):
    return ConnectServiceStrategy(SocialServiceStorage, request=request)


@never_cache
@login_required
@psa(redirect_uri=f'auth:social:complete', load_strategy=connect_service_strategy)
def connect_service_begin(request, backend: str):
    return do_auth(request.backend, redirect_name=REDIRECT_FIELD_NAME)


@never_cache
@csrf_exempt
@login_required
@psa(redirect_uri=f'auth:social:complete', load_strategy=connect_service_strategy)
def connect_service_complete(request, backend: str, *args, **kwargs):
    backend = request.backend
    data = backend.strategy.request_data()

    user = request.user if request.user.is_authenticated else None

    partial = partial_pipeline_data(backend, user, *args, **kwargs)
    if partial:
        user = backend.continue_pipeline(partial)
        # clean partial data after usage
        backend.strategy.clean_partial_pipeline(partial.token)
    else:
        # Runs authentication process through the chain:
        # ... -> strategy.authenticate -> ... backend.authenticate -> ... -> pipeline
        try:
            user = backend.complete(user=user, *args, **kwargs)
        except AuthException as e:
            messages.error(request, str(e))
            url = user.get_absolute_url()
            return HttpResponseRedirect(redirect_to=f"{url}#connected-accounts")

    # pop redirect value before the session is trashed on login(), but after
    # the pipeline so that the pipeline can change the redirect if needed
    redirect_value = (backend.strategy.session_get(REDIRECT_FIELD_NAME, '') or
                      data.get(REDIRECT_FIELD_NAME, ''))

    # check if the output value is something else than a user and just
    # return it to the client
    user_model = backend.strategy.storage.user.user_model()
    if user and not isinstance(user, user_model):
        return user

    messages.success(request, "Аккаунт успешно подключен")
    redirect_url = reverse('user_detail', subdomain=settings.LMS_SUBDOMAIN, kwargs={
        "pk": user.pk
    })
    url = setting_url(backend, redirect_value, f'{redirect_url}#connected-accounts')
    return backend.strategy.redirect(url)


@never_cache
@login_required
@psa(load_strategy=connect_service_strategy)
@require_POST
@csrf_protect
def disconnect_service(request, backend: str):
    return do_disconnect(request.backend, request.user, association_id=None,
                         redirect_name=REDIRECT_FIELD_NAME)


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


def connect_yandexru_oauth_backend(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
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
        return view(request, *args, **kwargs)
    return wrapper


@never_cache
@redirect_to("auth:application:complete")
@connect_yandexru_oauth_backend
def yandex_login_access_admission(request, *args, **kwargs):
    return do_auth(request.backend, redirect_name=REDIRECT_FIELD_NAME)


@never_cache
@csrf_exempt
@redirect_to("auth:application:complete")
@connect_yandexru_oauth_backend
def yandex_login_access_admission_complete(request, *args, **kwargs):
    """
    Authentication complete view. Our main goal - to retrieve user yandex login.
    """

    user = request.user
    backend = request.backend

    is_authenticated = user_is_authenticated(user)
    user = user if is_authenticated else None

    # Note: Pipeline is never called since we prevent user authentication
    try:
        auth_data = backend.complete(user=user, *args, **kwargs)
        for field_name in ["id", "login", "display_name", "real_name", "first_name", "last_name"]:
            key = f"{YANDEX_OAUTH_BACKEND_PREFIX}_{field_name}"
            backend.strategy.session_set(key, auth_data.get(field_name))
        context = {"yandex_login": auth_data.get("login", "")}
    except SocialAuthBaseException as e:
        context = {"error": str(e)}
    return render(request, 'admission/social_close_popup.html', context=context)


@never_cache
@redirect_to("auth:users:yandex_complete")
@connect_yandexru_oauth_backend
def yandex_profile_oauth_data_access(request, *args, **kwargs):
    return do_auth(request.backend, redirect_name=REDIRECT_FIELD_NAME)


@never_cache
@csrf_exempt
@redirect_to("auth:users:yandex_complete")
@connect_yandexru_oauth_backend
def yandex_profile_oauth_data_complete(request, *args, **kwargs):
    """
    Authentication complete view. Our main goal - to retrieve user yandex login.
    """

    user = request.user
    backend = request.backend

    if not user_is_authenticated(user):
        return HttpResponse('401 Unauthorized', status=401)
    # Note: Pipeline is never called since we prevent user authentication
    try:
        auth_data = backend.complete(user=user, *args, **kwargs)
        fields = ["id", "login", "display_name", "real_name", "first_name", "last_name"]
        yandex_data = {field_name: auth_data.get(field_name) for field_name in fields}
        yandex_data["uid"] = yandex_data.pop("id")
        obj, created = YandexUserData.objects.get_or_create(user=user)
        for field_name, value in yandex_data.items():
            # Be careful, don't let 'id' appear here
            setattr(obj, field_name, value)
        obj.changed_by = None
        obj.save()
        messages.success(request, 'Ваш профиль был успешно подключён!')
    except IntegrityError:
        messages.error(request, "Данный аккаунт уже подключен к другому профилю, обратитесь к кураторам!",
                       extra_tags='timeout')
        YandexUserData.objects.filter(user=user).delete()
    except Exception as e:
        messages.error(request, str(e), extra_tags='timeout')
    url = reverse('user_detail', args=[request.user.pk],
                  subdomain=settings.LMS_SUBDOMAIN)
    return HttpResponseRedirect(redirect_to=url)

