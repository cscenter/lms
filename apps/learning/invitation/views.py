
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from registration import signals
from registration.backends.default.views import RegistrationView, ActivationView
from vanilla import TemplateView, UpdateView

from auth.tasks import send_activation_email, ActivationEmailContext
from auth.views import LoginView
from core.urls import reverse
from learning.invitation.forms import InvitationLoginForm, \
    InvitationRegistrationForm, CompleteProfileForm
from learning.models import Invitation
from learning.roles import Roles


def student_profile_is_valid(user, invitation):
    if invitation.branch_id != user.branch_id:
        return False
    if not user.enrollment_year:
        return False
    if not user.roles.intersection({Roles.INVITED, Roles.STUDENT,
                                    Roles.VOLUNTEER}):
        return False
    return user.first_name and user.last_name


class InvitationURLParamsMixin:
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        qs = (Invitation.objects
              .filter(token=kwargs['token'])
              .select_related("branch"))
        self.invitation = get_object_or_404(qs)
        if not self.invitation.is_active:
            raise Http404


class InvitationView(InvitationURLParamsMixin, TemplateView):
    template_name = "learning/invitation/invitation_courses.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("invitation:login",
                                kwargs={"token": self.invitation.token},
                                subdomain=settings.LMS_SUBDOMAIN)
            return HttpResponseRedirect(redirect_to=login_url)
        if not student_profile_is_valid(request.user, self.invitation):
            redirect_to = reverse("invitation:complete_profile",
                                  kwargs={"token": self.invitation.token},
                                  subdomain=settings.LMS_SUBDOMAIN)
            return HttpResponseRedirect(redirect_to=redirect_to)
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        course_invitations = (self.invitation.courseinvitation_set
                              .select_related('course',
                                              'course__meta_course',
                                              'course__semester'))
        return {
            'view': self,
            'course_invitation_list': course_invitations,
        }


class InvitationLoginView(InvitationURLParamsMixin, LoginView):
    form_class = InvitationLoginForm
    template_name = "learning/invitation/auth.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            url = self.invitation.get_absolute_url()
            return HttpResponseRedirect(redirect_to=url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        register_url = reverse("invitation:registration",
                               kwargs={"token": self.invitation.token},
                               subdomain=settings.LMS_SUBDOMAIN)
        context["register_url"] = register_url
        return context

    def get_success_url(self):
        return self.invitation.get_absolute_url()


class InvitationRegisterView(InvitationURLParamsMixin, RegistrationView):
    form_class = InvitationRegistrationForm
    template_name = "learning/invitation/registration.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            url = self.invitation.get_absolute_url()
            return HttpResponseRedirect(redirect_to=url)
        context = self.get_context_data()
        return self.render_to_response(context)

    def register(self, form):
        site = get_current_site(self.request)
        new_user_instance = form.save(commit=False)
        new_user_instance.enrollment_year = timezone.now().year
        new_user_instance.branch = self.invitation.branch
        new_user = self.registration_profile.objects.create_inactive_user(
            new_user=new_user_instance,
            site=site,
            send_email=False,
            request=self.request,
        )
        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=self.request)
        new_user.add_group(Roles.INVITED)
        activation_url = reverse("invitation:activate", kwargs={
            "token": self.invitation.token,
            "activation_key": new_user.registrationprofile.activation_key
        }, subdomain=settings.LMS_SUBDOMAIN)
        context = ActivationEmailContext(
            site_name=site.name,
            activation_url=activation_url,
            language_code=self.request.LANGUAGE_CODE)
        send_activation_email.delay(context, new_user.registrationprofile.pk)
        return new_user

    def registration_allowed(self):
        return True

    def get_success_url(self, user=None):
        return reverse("invitation:registration_complete",
                       subdomain=settings.LMS_SUBDOMAIN)


class InvitationRegisterCompleteView(TemplateView):
    template_name = 'learning/invitation/registration_complete.html'


class InvitationActivationCompleteView(TemplateView):
    template_name = 'learning/invitation/activation_complete.html'


class InvitationActivationView(InvitationURLParamsMixin, ActivationView):
    template_name = 'learning/invitation/activation_fail.html'

    def get_success_url(self, user):
        messages.success(self.request, _("Учетная запись активирована."),
                         extra_tags='timeout')
        return self.invitation.get_absolute_url()


def complete_student_profile(user, invitation):
    update_fields = list(CompleteProfileForm.Meta.fields)
    if not user.enrollment_year:
        user.enrollment_year = timezone.now().year
        update_fields.append('enrollment_year')
    if user.branch_id != invitation.branch_id:
        update_fields.append('branch')
        user.branch = invitation.branch
    with transaction.atomic():
        user.save(update_fields=update_fields)
        if Roles.INVITED not in user.roles:
            user.add_group(Roles.INVITED)


class InvitationCompleteProfileView(InvitationURLParamsMixin,
                                    LoginRequiredMixin,
                                    UpdateView):
    form_class = CompleteProfileForm
    template_name = "learning/invitation/complete_profile.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if student_profile_is_valid(request.user, self.invitation):
            return HttpResponseRedirect(self.invitation.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_login_url(self):
        return reverse("invitation:login",
                       kwargs={"token": self.invitation.token},
                       subdomain=settings.LMS_SUBDOMAIN)

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        self.object = form.save(commit=False)
        complete_student_profile(self.object, self.invitation)
        return HttpResponseRedirect(self.invitation.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invitation'] = self.invitation
        return context
