from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseRedirect, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views import generic
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _

from braces.views import LoginRequiredMixin

from .models import CSCUser
from .forms import LoginForm, UserProfileForm


# inspired by https://raw2.github.com/concentricsky/django-sky-visitor/
class LoginView(generic.FormView):
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
        redirect_to = self.request.REQUEST.get(self.redirect_field_name)

        if not is_safe_url(redirect_to, self.request.get_host()):
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


class LogoutView(LoginRequiredMixin,
                 generic.RedirectView):
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


class TeacherDetailView(generic.DetailView):
    template_name = "teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        return (auth.get_user_model()
                ._default_manager
                .all()
                .prefetch_related('teaching_set',
                                  'teaching_set__semester',
                                  'teaching_set__course'))

    def get_object(self, *args, **kwargs):
        teacher = super(TeacherDetailView, self).get_object(*args, **kwargs)
        if not teacher.is_teacher:
            raise Http404
        return teacher


class UserDetailView(generic.DetailView):
    template_name = "user_detail.html"
    context_object_name = 'user_object'

    def get_queryset(self, *args, **kwargs):
        return (auth.get_user_model()
                ._default_manager
                .all()
                .select_related('overall_grade')
                .prefetch_related('teaching_set',
                                  'teaching_set__semester',
                                  'teaching_set__course',
                                  'enrollment_set',
                                  'enrollment_set__course_offering',
                                  'enrollment_set__course_offering__semester',
                                  'enrollment_set__course_offering__course'))

    def get_context_data(self, *args, **kwargs):
        context = (super(UserDetailView, self)
                   .get_context_data(*args, **kwargs))
        context['is_extended_profile_available'] = \
            (self.request.user == self.object or
             self.request.user.is_superuser)
        context['is_editing_allowed'] = \
            context['is_extended_profile_available']
        return context


class UserUpdateView(generic.UpdateView):
    model = CSCUser
    template_name = "learning/simple_crispy_form.html"
    form_class = UserProfileForm

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, *args, **kwargs):
        context = (super(UserUpdateView, self)
                   .get_context_data(*args, **kwargs))
        return context
