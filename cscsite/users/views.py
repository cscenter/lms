from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import auth
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import FormView, View, RedirectView
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden
from crispy_forms.bootstrap import FormActions
import floppyforms as forms

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        required=True,
        label=_("Username"),
        widget=forms.TextInput(attrs={'autofocus': 'autofocus'}))
    password = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Password"))

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-xs-2'
        self.helper.field_class = 'col-xs-7'
        self.helper.layout = Layout(
            'username',
            'password',
            FormActions(Submit('submit', _("Submit"))),
            # TODO: test if "next" is working
            Hidden('next', ''))

# inspired by https://raw2.github.com/concentricsky/django-sky-visitor/
# TODO: rename all XXXView to just XXX?
class LoginView(FormView):
    redirect_field_name = auth.REDIRECT_FIELD_NAME
    form_class = LoginForm
    template_name = "login.html"

    @method_decorator(never_cache)
    @method_decorator(sensitive_post_parameters('password'))
    def dispatch(self, *args, **kwargs):
        return super(LoginView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        # credentials were checked in AuthenticationForm.is_valid()
        auth.login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    # TODO: redirect on user-specific page?
    def get_success_url(self):
        redirect_to = settings.LOGOUT_REDIRECT_URL

        if self.redirect_field_name in self.request.REQUEST:
            maybe_redirect_to = self.request.REQUEST[self.redirect_field_name]
            if is_safe_url(url=maybe_redirect_to,
                           host=self.request.get_host()):
                redirect_to = maybe_redirect_to

        return redirect_to

    def check_and_delete_test_cookie(self):
        if self.request.session.test_cookie_worked():
            self.request.session.delete_test_cookie()
            return True
        return False

    def get(self, request, *args, **kwargs):
        self.request.session.set_test_cookie()
        return super(LoginView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            self.check_and_delete_test_cookie()
            return self.form_valid(form)
        else:
            self.request.session.set_test_cookie()
            return self.form_invalid(form)

class LogoutView(RedirectView):
    redirect_field_name = auth.REDIRECT_FIELD_NAME

    def get(self, request, *args, **kwargs):
        auth.logout(request)
        return super(LogoutView, self).get(request, *args, **kwargs)

    def get_redirect_url(self, **kwargs):
        redirect_to = settings.LOGOUT_REDIRECT_URL

        if self.redirect_field_name in self.request.REQUEST:
            maybe_redirect_to = self.request.REQUEST[self.redirect_field_name]
            if is_safe_url(url=maybe_redirect_to,
                           host=self.request.get_host()):
                redirect_to = maybe_redirect_to

        return redirect_to
