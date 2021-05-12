
from registration import signals
from registration.backends.default.views import ActivationView, RegistrationView
from vanilla import TemplateView, UpdateView

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from auth.tasks import ActivationEmailContext, send_activation_email
from auth.views import LoginView
from core.urls import reverse
from courses.utils import date_to_term_pair, get_current_term_pair
from learning.invitation.forms import (
    CompleteAccountForm, InvitationLoginForm, InvitationRegistrationForm
)
from learning.models import Invitation
from learning.services import create_student_profile
from users.models import StudentProfile, StudentTypes, User


def student_profile_is_valid(user: User, site: Site, invitation):
    profile = user.get_student_profile(site)
    if not profile or not profile.is_active:
        return False
    if profile.type == StudentTypes.INVITED:
        created_on_term = date_to_term_pair(profile.created)
        if created_on_term != get_current_term_pair():
            return False
    return user.first_name and user.last_name


def complete_student_profile(user: User, site: Site, invitation: Invitation):
    update_fields = list(CompleteAccountForm.Meta.fields)
    with transaction.atomic():
        user.save(update_fields=update_fields)
        invitation_year = invitation.semester.academic_year
        # Account info should be valid at this point but the most recent
        # profile still can be invalid due to inactive state
        if not student_profile_is_valid(user, site, invitation):
            create_student_profile(user=user,
                                   branch=invitation.branch,
                                   profile_type=StudentTypes.INVITED,
                                   year_of_admission=invitation_year,
                                   invitation=invitation)


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

    # FIXME: What if log in as an expelled student?
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("invitation:login",
                                kwargs={"token": self.invitation.token},
                                subdomain=settings.LMS_SUBDOMAIN)
            return HttpResponseRedirect(redirect_to=login_url)
        if not student_profile_is_valid(request.user, request.site,
                                        self.invitation):
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
        new_student_profile = StudentProfile(
            user=new_user,
            branch=self.invitation.branch,
            type=StudentTypes.INVITED,
            year_of_admission=self.invitation.semester.academic_year)
        new_student_profile.save()
        activation_url = reverse("invitation:activate", kwargs={
            "token": self.invitation.token,
            "activation_key": new_user.registrationprofile.activation_key
        }, subdomain=settings.LMS_SUBDOMAIN)
        context = ActivationEmailContext(
            site_name=site.name,
            activation_url=self.request.build_absolute_uri(activation_url),
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


class InvitationCompleteProfileView(InvitationURLParamsMixin,
                                    LoginRequiredMixin,
                                    UpdateView):
    form_class = CompleteAccountForm
    template_name = "learning/invitation/complete_profile.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if student_profile_is_valid(request.user, request.site, self.invitation):
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
        complete_student_profile(self.object, self.request.site, self.invitation)
        return HttpResponseRedirect(self.invitation.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact_email'] = settings.LMS_CURATOR_EMAIL
        context['invitation'] = self.invitation
        return context
