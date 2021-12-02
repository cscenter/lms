from typing import Iterable

from braces.views import LoginRequiredMixin
from social_core.actions import do_auth, do_disconnect
from social_core.utils import partial_pipeline_data, setting_url
from social_django.strategy import DjangoStrategy
from social_django.utils import psa

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import REDIRECT_FIELD_NAME, views
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import generic
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST

from auth.forms import AsyncPasswordResetForm, LoginForm
from auth.storage import SocialServiceStorage
from core.urls import reverse, reverse_lazy
from users.constants import Roles


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
        user = backend.complete(user=user, *args, **kwargs)

    # pop redirect value before the session is trashed on login(), but after
    # the pipeline so that the pipeline can change the redirect if needed
    redirect_value = (backend.strategy.session_get(REDIRECT_FIELD_NAME, '') or
                      data.get(REDIRECT_FIELD_NAME, ''))

    # check if the output value is something else than a user and just
    # return it to the client
    user_model = backend.strategy.storage.user.user_model()
    if user and not isinstance(user, user_model):
        return user

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
