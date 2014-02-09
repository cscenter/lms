from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import FormView, View

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('username', placeholder="username"),
            Field('password', placeholder="password"),
            Submit('submit', 'Submit'))

# TODO: rename all XXXView to just XXX?
class LoginView(FormView):
    form_class = LoginForm
    template_name = "login.html"

    def form_valid(self, form):
        # TODO: redirect on user-specific page?
        redirect_to = settings.LOGIN_REDIRECT_URL
        auth_login(self.request, form.get_user())
        if self.request.session.test_cookie_worked():
            self.request.session.delete_test_cookie()
        return HttpResponseRedirect(redirect_to)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    @method_decorator(sensitive_post_parameters('password'))
    def dispatch(self, request, *args, **kwargs):
        request.session.set_test_cookie()
        return super(LoginView, self).dispatch(request, *args, **kwargs)

class LogoutView(View):
    def get(self, request, *args, **kwargs):
        auth_logout(request)
        return HttpResponseRedirect(settings.LOGOUT_REDIRECT_URL)
