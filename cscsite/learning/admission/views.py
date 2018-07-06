# -*- coding: utf-8 -*-

import datetime
import json
import re
import uuid
from collections import Counter
from functools import wraps
from itertools import groupby

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.db import transaction, IntegrityError
from django.db.models import Q, Avg, Value, Prefetch
from django.db.models.functions import Coalesce
from django.db.transaction import atomic
from django.http import HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponseForbidden, HttpResponseBadRequest, \
    Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone, formats
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateResponseMixin, RedirectView
from django.views.generic.edit import BaseCreateView, \
    ModelFormMixin
from django_filters.views import BaseFilterView, FilterMixin
from extra_views.formsets import BaseModelFormSetView
from formtools.wizard.views import NamedUrlSessionWizardView
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView
from social_core.actions import do_auth
from social_core.exceptions import MissingBackend, SocialAuthBaseException
from social_core.storage import UserMixin
from social_core.utils import user_is_authenticated
from social_django.models import DjangoStorage
from social_django.strategy import DjangoStrategy

from api.permissions import CuratorAccessPermission
from core.api.yandex_oauth import YandexRuOAuth2Backend
from core.exceptions import Redirect
from core.settings.base import DEFAULT_CITY_CODE, LANGUAGE_CODE
from core.utils import render_markdown
from learning.admission.filters import ApplicantFilter, InterviewsFilter, \
    InterviewsCuratorFilter, InterviewStatusFilter, ResultsFilter
from learning.admission.forms import InterviewCommentForm, \
    ApplicantReadOnlyForm, InterviewForm, ApplicantStatusForm, \
    ResultsModelForm, ApplicationFormStep1, ApplicationInSpbForm, \
    ApplicationInNskForm, InterviewAssignmentsForm, InterviewFromStreamForm
from learning.admission.models import Interview, Comment, Contest, Test, Exam, \
    Applicant, Campaign, InterviewAssignment, InterviewSlot, \
    InterviewInvitation, InterviewStream
from learning.admission.serializers import InterviewSlotSerializer
from learning.admission.services import create_invitation
from learning.admission.utils import generate_interview_reminder, \
    calculate_time
from learning.settings import DATE_FORMAT_RU
from learning.utils import now_local
from learning.viewmixins import InterviewerOnlyMixin, CuratorOnlyMixin
from learning.views import get_user_city_code
from tasks.models import Task
from users.models import CSCUser
from .tasks import register_in_yandex_contest, import_testing_results

ADMISSION_SETTINGS = apps.get_app_config("admission")
STRATEGY = 'social_django.strategy.DjangoStrategy'
# Override `user` attribute to prevent accidental user creation
STORAGE = __name__ + '.DjangoStorageCustom'
BACKEND_PREFIX = 'application_ya'
SESSION_LOGIN_KEY = f"{BACKEND_PREFIX}_login"

date_re = re.compile(
    r'(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{4})$'
)


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
@redirect_to("admission:auth_complete")
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
@redirect_to("admission:auth_complete")
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


# FIXME: Don't allow to save duplicates.
class ApplicantFormWizardView(NamedUrlSessionWizardView):
    template_name = "admission/application_form.html"
    form_list = [
        ('welcome', ApplicationFormStep1),
        ('spb', ApplicationInSpbForm),
        ('nsk', ApplicationInNskForm),
    ]
    initial_dict = {
        'spb': {'has_job': 'Нет'},
        'nsk': {'has_job': 'Нет'},
    }

    def create_new_applicant(self, cleaned_data):
        cleaned_data['where_did_you_learn'] = ",".join(
            cleaned_data['where_did_you_learn'])
        cleaned_data['preferred_study_programs'] = ",".join(
            cleaned_data['preferred_study_programs'])
        if cleaned_data['has_job'] == 'no':
            del cleaned_data['workplace']
            del cleaned_data['position']
        applicant = Applicant(**cleaned_data)
        applicant.clean()  # normalize yandex login
        applicant.save()
        if applicant.pk:
            register_in_yandex_contest.delay(applicant.pk, LANGUAGE_CODE)
        else:
            print("SOMETHING WRONG?")

    def done(self, form_list, **kwargs):
        cleaned_data = {}
        for form in form_list:
            cleaned_data.update(form.cleaned_data)
        self.create_new_applicant(cleaned_data)
        # Remove yandex login data from session
        self.request.session.pop(SESSION_LOGIN_KEY, None)
        return HttpResponseRedirect(reverse("admission:application_complete"))

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        # Customize yandex login button widget based on stored value
        yandex_login = self.request.session.get(SESSION_LOGIN_KEY, None)
        if yandex_login:
            kwargs["yandex_passport_access_allowed"] = True
        if step == "welcome":
            # Validate we have any active campaign with ongoing application
            # period
            today = timezone.now()
            campaigns_qs = (Campaign.objects
                            .filter(current=True, year=today.year,
                                    application_ends_at__gt=today)
                            .select_related('city'))
            if not len(campaigns_qs):
                raise Redirect(to=reverse("admission:application_closed"))
            kwargs["campaigns_qs"] = campaigns_qs
        return kwargs

    def get_form(self, step=None, data=None, files=None):
        if step is None:
            step = self.steps.current
        # Append yandex login to data if session value was found
        if step == "welcome":
            yandex_login = self.request.session.get(SESSION_LOGIN_KEY, None)
            if yandex_login and data and "yandex_id" not in data:
                data = data.copy()
                form_prefix = self.get_form_prefix(step)
                data[f"{form_prefix}-yandex_id"] = yandex_login
        return super().get_form(step, data, files)

    @staticmethod
    def show_spb_form(wizard):
        saved_data = wizard.storage.get_step_data('welcome')
        return saved_data and saved_data.get("city") == "spb"

    @staticmethod
    def show_nsk_form(wizard):
        saved_data = wizard.storage.get_step_data('welcome')
        return saved_data and saved_data.get("city") == "nsk"

    def process_step(self, form):
        """
        This method is used to postprocess the form data. By default, it
        returns the raw `form.data` dictionary.
        """
        data = super().process_step(form)
        if self.steps.current == "welcome":
            # Additionally save city code for easier step recognition
            data["city"] = form.cleaned_data['campaign'].city_id
        return data


ApplicantFormWizardView.condition_dict = {
    'spb': ApplicantFormWizardView.show_spb_form,
    'nsk': ApplicantFormWizardView.show_nsk_form,
}


class ApplicationCompleteView(generic.TemplateView):
    template_name = "admission/application_form_done.html"


class ApplicantContextMixin(object):
    @staticmethod
    def get_applicant_context(applicant_id):
        context = {}
        applicant = get_object_or_404(
            Applicant.objects
                     .select_related("exam", "campaign", "campaign__city",
                                     "online_test", "university")
                     .filter(pk=applicant_id))
        context["applicant"] = applicant
        context["applicant_form"] = ApplicantReadOnlyForm(instance=applicant)
        context["campaign"] = applicant.campaign
        contest_ids = []
        try:
            context["online_test"] = applicant.online_test
            contest_ids.append(context["online_test"].yandex_contest_id)
        except Test.DoesNotExist:
            pass
        try:
            context["exam"] = applicant.exam
            contest_ids.append(context["exam"].yandex_contest_id)
        except Exam.DoesNotExist:
            pass
        # get contests description
        contests = {}
        contest_ids = [c for c in contest_ids if c]
        if contest_ids:
            contests_query = Contest.objects.filter(contest_id__in=contest_ids)
            for c in contests_query:
                if c.contest_id == context["online_test"].yandex_contest_id:
                    contests["test"] = c
                elif c.contest_id == context["exam"].yandex_contest_id:
                    contests["exam"] = c
        context["contests"] = contests
        # Similar applicants
        conditions = [
            Q(email=applicant.email),
            (
                Q(first_name__iexact=applicant.first_name) &
                Q(surname__iexact=applicant.surname) &
                Q(patronymic__iexact=applicant.patronymic)
            ),
        ]
        if applicant.phone:
            conditions.append(Q(phone=applicant.phone))
        if applicant.stepic_id:
            conditions.append(Q(stepic_id=applicant.stepic_id))
        if applicant.yandex_id_normalize:
            conditions.append(Q(yandex_id_normalize=applicant.yandex_id_normalize))
        query = conditions.pop()
        for c in conditions:
            query |= c

        similar_applicants = Applicant.objects.filter(query)
        similar_applicants = filter(lambda a: a != applicant,
                                    similar_applicants)
        context["similar_applicants"] = similar_applicants
        return context


def applicant_testing_new_task(request):
    """
    Creates new task for importing testing results from yandex contests.
    Make sure `current` campaigns are already exists in DB before add new task.
    """
    if request.method == "POST" and request.user.is_curator:
        task = Task.build(
            task_name="learning.admission.tasks.import_testing_results",
            creator=request.user)
        # Not really atomic, just trying to avoid useless rows in DB
        try:
            # FIXME: Deal with deadlocks (locked tasks which were started
            # processing by rqworker but did fail during the processing)
            # Without it this try-block looks useless
            Task.objects.get(locked_by__isnull=True,
                             processed_at__isnull=True,
                             task_name=task.task_name,
                             task_hash=task.task_hash)
        except Task.MultipleObjectsReturned:
            # Even more than 1 job in Task.MAX_RUN_TIME seconds
            pass
        except Task.DoesNotExist:
            task.save()
            import_testing_results.delay(task_id=task.pk)
        return HttpResponse(status=201)
    return HttpResponseForbidden()


class ApplicantTestingResultsTask(APIView):
    """
    Returns interview slots for requested venue and date.
    """
    http_method_names = ['post']
    permission_classes = [CuratorAccessPermission]

    def post(self, request, format=None):
        slots = []
        if "stream" in request.GET:
            try:
                stream = int(self.request.GET["stream"])
            except ValueError:
                raise ParseError()
            slots = InterviewSlot.objects.filter(stream_id=stream)
        serializer = InterviewSlotSerializer(slots, many=True)
        return Response(serializer.data)


class ApplicantListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
    context_object_name = 'applicants'
    model = Applicant
    template_name = "admission/applicant_list.html"
    filterset_class = ApplicantFilter
    paginate_by = 50

    def get_queryset(self):
        return (
            Applicant.objects
            .select_related("exam", "online_test", "campaign", "university",
                            "campaign__city")
            .prefetch_related("interview")
            .annotate(exam__score_coalesce=Coalesce('exam__score', Value(-1)),
                      test__score_coalesce=Coalesce('online_test__score',
                                                    Value(-1)))
            .order_by("-exam__score_coalesce", "-test__score_coalesce", "-pk"))

    def get(self, request, *args, **kwargs):
        """Sets filter defaults and redirects"""
        user = self.request.user
        if user.is_curator and "campaign" not in self.request.GET:
            # Try to find user preferred current campaign id
            current = list(Campaign.objects
                           .filter(current=True)
                           .only("pk", "city_id"))
            try:
                c = next(c.pk for c in current if c.city_id == user.city_id)
            except StopIteration:
                # We didn't find active campaign for user city. Try to get
                # any current campaign or show all if no active at all.
                c = next((c.pk for c in current), "")
            url = reverse("admission:applicants")
            url = f"{url}?campaign={c}&status="
            return HttpResponseRedirect(redirect_to=url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = context['filter'].form.cleaned_data.get('campaign')
        import_testing_results_btn_state = None
        if campaign and campaign.current and self.request.user.is_curator:
            task_name = "learning.admission.tasks.import_testing_results"
            task = (Task.objects
                    .get_task(task_name)
                    .filter(processed_at__isnull=False)
                    .order_by("-id")
                    .first())
            if task:
                dt = task.processed_at
                city_code = get_user_city_code(self.request)
                if city_code:
                    tz = settings.TIME_ZONES[city_code]
                    dt = timezone.localtime(dt, timezone=tz)
                import_testing_results_btn_state = {
                    "date": formats.date_format(dt, "SHORT_DATETIME_FORMAT"),
                    "status": "Успешно" if not task.is_failed() else "Ошибка"
                }
            else:
                import_testing_results_btn_state = {}
        context["import_testing_results"] = import_testing_results_btn_state
        return context


class ApplicantDetailView(InterviewerOnlyMixin, ApplicantContextMixin,
                          TemplateResponseMixin, BaseCreateView):

    form_class = InterviewForm
    template_name = "admission/applicant_detail.html"

    def get_queryset(self):
        applicant_id = self.kwargs.get(self.pk_url_kwarg, None)
        return (Applicant.objects
                .select_related("exam", "online_test", "campaign",
                                "campaign__city")
                .get(pk=applicant_id))

    def get_context_data(self, **kwargs):
        applicant_id = self.kwargs[self.pk_url_kwarg]
        context = kwargs
        context.update(self.get_applicant_context(applicant_id))
        applicant = context["applicant"]
        context["status_form"] = ApplicantStatusForm(instance=applicant)
        if 'form' not in kwargs:
            invitation = InterviewInvitation.objects.for_applicant(applicant)
            if not invitation:
                city_code = applicant.campaign.city_id
                context["form"] = InterviewFromStreamForm(city_code=city_code)
            else:
                context["invitation"] = invitation
        return context

    def get(self, request, *args, **kwargs):
        applicant_id = self.kwargs[self.pk_url_kwarg]
        try:
            interview = Interview.objects.get(applicant_id=applicant_id)
            return HttpResponseRedirect(reverse("admission:interview_detail",
                                                args=[interview.pk]))
        except Interview.DoesNotExist:
            return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Get data for interview from stream form"""
        if not request.user.is_curator:
            return self.handle_no_permission(request)
        applicant_id = self.kwargs.get(self.pk_url_kwarg)
        applicant = get_object_or_404(
            Applicant.objects
            .filter(pk=applicant_id)
            .select_related("campaign"))
        self.object = None
        stream_form = InterviewFromStreamForm(
            city_code=applicant.campaign.city_id,
            data=self.request.POST)
        if not stream_form.is_valid():
            msg = "Действие было отменено"
            messages.error(self.request, msg, extra_tags='timeout')
            return self.form_invalid(stream_form)
        slot = stream_form.cleaned_data.get('slot')
        if slot:
            response = self.create_interview_from_slot(applicant, stream_form,
                                                       slot)
        else:
            response = self.create_invitation(applicant, stream_form)
        return response

    def get_success_url(self):
        messages.success(self.request, "Собеседование успешно добавлено",
                         extra_tags='timeout')
        return reverse("admission:interview_detail", args=[self.object.pk])

    def create_interview_from_slot(self, applicant, stream_form, slot):
        data = InterviewForm.build_data(applicant, slot)
        form = InterviewForm(data=data)
        if form.is_valid():
            with transaction.atomic():
                sid = transaction.savepoint()
                interview = self.object = form.save()
                slot_has_taken = InterviewSlot.objects.lock(slot, interview)
                generate_interview_reminder(interview, slot)
                if not slot_has_taken:
                    transaction.savepoint_rollback(sid)
                    messages.error(
                        self.request,
                        "Cлот уже был занят другим участником! Нужно вручную "
                        "разобраться в ситуации.<br><a target='_blank' "
                        "href='{}'>Перейти в админ-панель</a>".format(
                            reverse("admin:admission_interviewstream_change",
                                    args=[slot.stream.pk])))
                    return self.form_invalid(stream_form)
                else:
                    transaction.savepoint_commit(sid)
            return super(ModelFormMixin, self).form_valid(form)
        else:
            # It never happens until user trying to change data by hand.
            messages.error(self.request, "Unknown error. Repeat your "
                                         "request or tell everyone about "
                                         "this disaster.")
            return self.form_invalid(stream_form)

    def create_invitation(self, applicant, stream_form):
        streams = stream_form.cleaned_data['streams']
        try:
            create_invitation(streams, applicant,
                              uri_builder=self.request.build_absolute_uri)
            messages.success(
                self.request,
                "Приглашение успешно создано и должно быть отправлено в "
                "течение 5 минут.",
                extra_tags='timeout')
        except IntegrityError:
            messages.error(self.request, "Приглашение не было создано.")
        url = applicant.get_absolute_url()
        return HttpResponseRedirect("{}#create".format(url))


class ApplicantStatusUpdateView(CuratorOnlyMixin, generic.UpdateView):
    form_class = ApplicantStatusForm
    model = Applicant

    def get_success_url(self):
        messages.success(self.request, "Статус успешно обновлён",
                         extra_tags='timeout')
        return reverse("admission:applicant_detail", args=[self.object.pk])


# FIXME: rewrite with rest framework
class InterviewAssignmentDetailView(CuratorOnlyMixin, generic.DetailView):
    def get(self, request, **kwargs):
        assignment_id = self.kwargs['pk']
        assignment = get_object_or_404(
            InterviewAssignment.objects.filter(pk=assignment_id))
        rendered_text = render_markdown(assignment.description)
        return JsonResponse({
            'id': assignment_id,
            'name': assignment.name,
            'description': rendered_text
        })


class InterviewListView(InterviewerOnlyMixin, BaseFilterView, generic.ListView):
    context_object_name = 'interviews'
    model = Interview
    paginate_by = 50
    template_name = "admission/interview_list.html"

    def get(self, request, *args, **kwargs):
        """
        Redirects curator to appropriate campaign if no any provided.
        """
        user = self.request.user
        if user.is_curator and "campaign" not in self.request.GET:
            # Try to find user preferred current campaign id
            current = list(Campaign.objects.filter(current=True)
                           .only("pk", "city_id"))
            try:
                current_campaign = next(c for c in current
                                        if c.city_id == user.city_id)
            except StopIteration:
                # We didn't find active campaign for user city. Try to get
                # any current campaign or show all if no active at all.
                current_campaign = next((c for c in current), None)
            if not current_campaign:
                messages.error(self.request, "Нет активных кампаний по набору.")
                today_local = timezone.now()  # stub
            else:
                today_local = now_local(current_campaign.get_city_timezone())
            # Duplicate initial values from filterset
            statuses = "&".join(f"status={s}" for s in
                                [Interview.COMPLETED, Interview.APPROVED])
            date = formats.date_format(today_local, "SHORT_DATE_FORMAT")
            url = "{}?campaign={}&{statuses}&date_from={date_from}&date_to={date_to}".format(
                reverse("admission:interviews"), current_campaign.pk,
                statuses=statuses, date_from=date, date_to=date)
            return HttpResponseRedirect(redirect_to=url)
        return super().get(request, *args, **kwargs)

    def get_filterset_class(self):
        if self.request.user.is_curator:
            return InterviewsCuratorFilter
        return InterviewsFilter

    def get_filterset_kwargs(self, filterset_class):
        # Note: With django-filter 1.0.4 the best way to define initial value
        # for form without magic is to put it in the view.
        kwargs = super().get_filterset_kwargs(filterset_class)
        if not kwargs["data"]:
            today = formats.date_format(timezone.now(), "SHORT_DATE_FORMAT")
            kwargs["data"] = {
                "status": [Interview.COMPLETED, Interview.APPROVED],
                "date_from": today,
                "date_to": today
            }
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset
        # Choose results list title for selected campaign
        context["results_title"] = _("Current campaign")
        # TODO: Move to appropriate place?
        if "campaign" in self.filterset.form.declared_fields:
            try:
                campaign_filter_value = int(self.filterset.data.get("campaign"))
                campaign_field = self.filterset.form.declared_fields["campaign"]
                for campaign_id, name in campaign_field.choices:
                    if campaign_id == campaign_filter_value:
                        context["results_title"] = name
            except ValueError:
                context["results_title"] = _("All campaigns")
        return context

    def get_queryset(self):
        q = (Interview.objects
             .select_related("applicant", "applicant__campaign")
             .prefetch_related("interviewers")
             .annotate(average=Coalesce(Avg('comments__score'), Value(0)))
             .order_by("date", "pk"))
        if not self.request.user.is_curator:
            # Show interviewers only interviews from current campaigns where
            # they participate.
            try:
                current_campaigns = list(Campaign.objects.filter(current=True)
                                         .values_list("pk", flat=True))
            except Campaign.DoesNotExist:
                messages.error(self.request, "Нет активных кампаний по набору.")
                return Interview.objects.none()
            q = q.filter(applicant__campaign_id__in=current_campaigns,
                         interviewers=self.request.user)
        return q


class InterviewDetailView(InterviewerOnlyMixin, ApplicantContextMixin,
                          generic.TemplateView):
    template_name = "admission/interview_detail.html"

    def get_context_data(self, **kwargs):
        interview_id = self.kwargs['pk']
        interview = get_object_or_404(
            Interview.objects
                .filter(pk=interview_id)
                .prefetch_related(
                    "interviewers",
                    "assignments",
                    Prefetch("comments",
                             queryset=(Comment.objects
                                       .select_related("interviewer")))))
        context = self.get_applicant_context(interview.applicant_id)
        # Activate timezone for the whole detail view
        timezone.activate(context['applicant'].get_city_timezone())
        context.update({
            "interview": interview,
            "assignments_form": InterviewAssignmentsForm(instance=interview),
        })
        show_all_comments = self.request.user.is_curator
        form_kwargs = {
            "interview_id": interview.pk,
            "interviewer": self.request.user.pk
        }
        for comment in interview.comments.all():
            if comment.interviewer == self.request.user:
                show_all_comments = True
                form_kwargs["instance"] = comment
        context["show_all_comments"] = show_all_comments
        context["comment_form"] = InterviewCommentForm(**form_kwargs)
        return context

    def post(self, request, *args, **kwargs):
        """Update list of assignments"""
        if not request.user.is_curator:
            return HttpResponseForbidden()
        interview = get_object_or_404(Interview.objects
                                      .filter(pk=self.kwargs["pk"]))
        form = InterviewAssignmentsForm(instance=interview,
                                        data=self.request.POST)
        if form.is_valid():
            form.save()
            messages.success(self.request, "Список заданий успешно обновлён",
                             extra_tags='timeout')
        url = "{}#assignments".format(interview.get_absolute_url())
        return HttpResponseRedirect(url)


class InterviewCommentView(InterviewerOnlyMixin, generic.UpdateView):
    """Update/Insert view for interview comment"""
    form_class = InterviewCommentForm
    http_method_names = ['post', 'put']

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        try:
            obj = queryset.get()
            return obj
        except (AttributeError, queryset.model.DoesNotExist):
            return None

    def get_queryset(self):
        return Comment.objects.filter(interview=self.kwargs["pk"],
                                      interviewer=self.request.user)

    @transaction.atomic
    def form_valid(self, form):
        if self.request.is_ajax():
            _ = form.save()
            return JsonResponse({"success": "true"})
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Комментарий успешно сохранён",
                         extra_tags='timeout')
        return reverse("admission:interview_detail",
                       args=[self.object.interview_id])

    def form_invalid(self, form):
        if self.request.is_ajax():
            # TODO: return 400 status code?
            msg = "<br>".join(m for ms in form.errors.values() for m in ms)
            r = JsonResponse({"errors": msg})
            r.status_code = 400
            return r
        return super().form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            "interviewer": self._get_interviewer(),
            "interview_id": self.kwargs["pk"]
        })
        return kwargs

    def _get_interviewer(self):
        interview_id = self.kwargs["pk"]
        interview = get_object_or_404(Interview.objects
                                      .filter(pk=interview_id)
                                      .prefetch_related("interviewers"))
        if self.request.user.is_curator:
            return self.request.user
        for i in interview.interviewers.all():
            if i.pk == self.request.user.pk:
                return i
        return None


class InterviewResultsDispatchView(CuratorOnlyMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        """Based on user settings, get preferred page address and redirect"""
        cs = (Campaign.objects
              .filter(current=True)
              .values_list("city_id", flat=True))
        preferred_city = self.request.user.city_id
        if preferred_city in cs:
            city_redirect_to = preferred_city
        else:
            city_redirect_to = next(cs.iterator(), DEFAULT_CITY_CODE)
        return reverse("admission:interview_results_by_city", kwargs={
            "city_code": city_redirect_to
        })


class InterviewResultsView(CuratorOnlyMixin, FilterMixin, TemplateResponseMixin,
                           BaseModelFormSetView):
    """
    We can have multiple interviews for applicant
    """
    context_object_name = 'interviews'
    template_name = "admission/interview_results.html"
    model = Applicant
    form_class = ResultsModelForm
    filterset_class = ResultsFilter
    extra = 0

    def dispatch(self, request, *args, **kwargs):
        self.active_campaigns = (Campaign.objects
                                 .filter(current=True)
                                 .select_related("city"))
        try:
            city_code = self.kwargs["city_code"]
            self.selected_campaign = next(c for c in self.active_campaigns
                                          if c.city.code == city_code)
        except StopIteration:
            messages.error(self.request,
                           "Активная кампания по набору не найдена")
            return HttpResponseRedirect(reverse("admission:applicants"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        formset = self.construct_formset()
        context = self.get_context_data(filter=self.filterset,
                                        formset=formset)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        formset = self.construct_formset()
        if formset.is_valid():
            return self.formset_valid(formset)
        else:
            return self.formset_invalid(formset)

    def get_formset_kwargs(self):
        """Overrides queryset for instantiating the formset."""
        kwargs = super().get_formset_kwargs()
        kwargs['queryset'] = self.filterset.qs
        return kwargs

    def get_queryset(self):
        """Sort data by average interview score"""
        return (
            Applicant.objects
            # TODO: Carefully restrict by status to optimize query
            .filter(campaign=self.selected_campaign)
            .exclude(interview__isnull=True)
            .select_related("exam", "online_test", "university")
            .prefetch_related(
                Prefetch(
                    'interview',
                    queryset=(Interview.objects
                              .annotate(_average_score=Avg('comments__score'))),
                ),
            ))

    def get_context_data(self, filter, formset, **kwargs):

        def cpm_interview_best_score(form):
            if form.instance.interview.average_score is None:
                return Comment.UNREACHABLE_COMMENT_SCORE
            else:
                return form.instance.interview.average_score

        formset.forms.sort(key=cpm_interview_best_score, reverse=True)
        stats = Counter()
        received_statuses = {
            Applicant.ACCEPT,
            Applicant.ACCEPT_IF,
            Applicant.VOLUNTEER
        }
        received = 0
        for form in formset.forms:
            # Select the highest interview score to sort by
            applicant = form.instance
            stats.update((applicant.status,))
            if applicant.status in received_statuses:
                received += 1

        stats = [(Applicant.get_name_by_status_code(s), cnt) for
                 s, cnt in stats.items()]
        if received:
            stats.append(("Планируем принять всего", received))
        context = {
            "filter": filter,
            "formset": formset,
            "stats": stats,
            "active_campaigns": self.active_campaigns,
            "selected_campaign": self.selected_campaign
        }
        return context


class ApplicantCreateUserView(CuratorOnlyMixin, generic.View):
    http_method_names = ['post']

    @atomic
    def post(self, request, *args, **kwargs):
        # TODO: add tests
        applicant_pk = kwargs.get("pk")
        back_url = reverse("admission:applicants")
        try:
            applicant = Applicant.objects.get(pk=applicant_pk)
        except Applicant.DoesNotExist:
            messages.error(self.request, "Анкета не найдена",
                           extra_tags='timeout')
            return HttpResponseRedirect(reverse("admission:applicants"))
        try:
            user = CSCUser.create_student_from_applicant(applicant)
        except CSCUser.MultipleObjectsReturned:
            messages.error(
                self.request,
                "Всё плохо. Найдено несколько пользователей "
                "с email {}".format(applicant.email))
            return HttpResponseRedirect(back_url)
        except RuntimeError as e:
            # username already taken, failed to create the new unique one
            messages.error(self.request, e.args[0])
            return HttpResponseRedirect(back_url)
        # Link applicant and user
        applicant.user = user
        applicant.save()
        url = reverse("admin:users_cscuser_change", args=[user.pk])
        return HttpResponseRedirect(url)


class InterviewAppointmentView(generic.TemplateView):
    template_name = "admission/interview_appointment.html"

    def get_invitation(self):
        try:
            # FIXME: если кампания закончилась? тупо 404 или показывать страницу об окончании?
            secret_code = uuid.UUID(self.kwargs['secret_code'], version=4)
            return (InterviewInvitation.objects
                    .select_related("applicant")
                    .prefetch_related("streams")
                    .get(secret_code=secret_code,
                         # FIXME: инфу о годе из ссылки использовать?
                         applicant__campaign__current=True))
        except (ValueError, InterviewInvitation.DoesNotExist):
            raise Http404

    def get_context_data(self, **kwargs):
        invitation = self.get_invitation()
        context = {
            "invitation": invitation,
            "interview": None,
            "slots": None
        }
        if invitation.is_accepted:
            # No any locked slot if applicant interview was created manually
            slot = (InterviewSlot.objects
                    .filter(interview_id=invitation.interview_id,
                            interview__applicant_id=invitation.applicant_id)
                    .select_related("interview",
                                    "stream",
                                    "interview__applicant__campaign"))
            slot = get_object_or_404(slot)
            if slot.interview.applicant_id != invitation.applicant_id:
                # Interview accepted by invitation could be reassigned
                # to another applicant
                # TODO: 404 or show relevant error?
                raise Http404
            interview = slot.interview
            if interview.slot.stream.with_assignments:
                interview.date -= InterviewStream.WITH_ASSIGNMENTS_TIMEDELTA
            context["interview"] = interview
        elif not invitation.is_expired:
            streams = [s.id for s in invitation.streams.all()]
            slots = (InterviewSlot.objects
                     .filter(stream_id__in=streams)
                     .select_related("stream")
                     .order_by("stream__date", "start_at"))
            time_diff = InterviewStream.WITH_ASSIGNMENTS_TIMEDELTA
            any_slot_is_empty = False
            for slot in slots:
                if slot.is_empty:
                    any_slot_is_empty = True
                if slot.stream.with_assignments:
                    slot.start_at = calculate_time(slot.start_at, time_diff)
            slots = groupby(slots, key=lambda s: s.stream.date)
            grouped_slots = []
            for stream_date, g in slots:
                grouped_slots.append((stream_date, list(g)))
            context["slots"] = grouped_slots
            context["show_dates"] = len(grouped_slots) > 1
            if not any_slot_is_empty:
                # TODO: Do something bad
                pass
        return context

    def post(self, request, *args, **kwargs):
        invitation = self.get_invitation()
        if "time" not in request.POST:
            messages.error(self.request, "Вы забыли указать время",
                           extra_tags="timeout")
            return HttpResponseRedirect(invitation.get_absolute_url())
        slot_id = int(request.POST['time'])
        slot = get_object_or_404(InterviewSlot.objects.filter(pk=slot_id))
        # Check that slot is consistent with one of invitation streams
        if slot.stream_id not in [s.id for s in invitation.streams.all()]:
            return HttpResponseBadRequest()
        interview_data = InterviewForm.build_data(invitation.applicant, slot)
        form = InterviewForm(data=interview_data)
        if form.is_valid():
            with transaction.atomic():
                sid = transaction.savepoint()
                interview = form.save()
                slot_has_taken = InterviewSlot.objects.lock(slot, interview)
                generate_interview_reminder(interview, slot)
                # Mark invitation as accepted
                (InterviewInvitation.objects
                 .filter(pk=invitation.pk)
                 .update(interview_id=interview.id))
                if not slot_has_taken:
                    transaction.savepoint_rollback(sid)
                    messages.error(
                        self.request,
                        "Извините, но слот уже был занят другим участником. "
                        "Выберите другое время и повторите попытку.")
                else:
                    transaction.savepoint_commit(sid)
            return HttpResponseRedirect(invitation.get_absolute_url())
        else:
            print(form.errors)
        return HttpResponseBadRequest()


class InterviewSlots(APIView):
    """
    Returns all slots for requested interview streams
    """
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, format=None):
        slots = []
        if "streams[]" in request.GET:
            try:
                streams = [int(v) for v in self.request.GET.getlist("streams[]")]
            except ValueError:
                raise ParseError()
            slots = (InterviewSlot.objects
                     .filter(stream_id__in=streams)
                     .select_related("stream")
                     .order_by("stream__date", "start_at"))
        serializer = InterviewSlotSerializer(slots, many=True)
        return Response(serializer.data)
