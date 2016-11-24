# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Case, BooleanField, Prefetch, Count, Value, When, \
    IntegerField, Sum
from django.http import Http404, HttpResponse, HttpResponseForbidden, \
    HttpResponsePermanentRedirect, HttpResponseRedirect

from django.http.response import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.generic.edit import FormMixin, BaseUpdateView
from django_filters.views import BaseFilterView, FilterMixin

from core import comment_persistence
from core.utils import hashids
from core.views import LoginRequiredMixin
from learning.models import Semester
from learning.projects.filters import ProjectsFilter, CurrentTermProjectsFilter
from learning.projects.forms import ReportCommentForm, ReportReviewForm, \
    ReportStatusForm, ReportSummarizeForm, ReportForm, \
    ReportCuratorAssessmentForm
from learning.projects.models import Project, ProjectStudent, Report, \
    ReportComment, Review
from learning.settings import PARTICIPANT_GROUPS
from learning.utils import get_current_semester_pair, get_term_index
from learning.viewmixins import ProjectReviewerGroupOnlyMixin, CuratorOnlyMixin, \
    StudentOnlyMixin
from notifications import types
from notifications.signals import notify
from users.models import CSCUser

logger = logging.getLogger(__name__)


class RaiseRedirect(Exception):
    pass


class ReportListViewMixin(object):
    context_object_name = "projects"
    template_name = "learning/projects/reports.html"

    def get_queryset(self):
        current_year, term_type = get_current_semester_pair()
        current_term_index = get_term_index(current_year, term_type)
        queryset = (Project.objects
                    .select_related("semester")
                    .filter(semester__index=current_term_index,
                            canceled=False)
                    .prefetch_related(
                        Prefetch(
                            "projectstudent_set",
                            queryset=ProjectStudent.objects.select_related(
                                "report", "student")
                        )
                    ))
        return queryset

    def get_context_data(self, **kwargs):
        context = super(ReportListViewMixin, self).get_context_data(**kwargs)
        context["current_term"] = Semester.get_current()
        return context


class ReportListReviewerView(ProjectReviewerGroupOnlyMixin,
                             ReportListViewMixin,
                             generic.ListView):
    def get_queryset(self):
        qs = super(ReportListReviewerView, self).get_queryset()
        return qs.filter(reviewers=self.request.user).order_by("name", "pk")

    def get_context_data(self, **kwargs):
        context = super(ReportListReviewerView, self).get_context_data(**kwargs)
        if not context[self.context_object_name] and self.request.user.is_curator:
            raise RaiseRedirect
        return context

    def get(self, request, *args, **kwargs):
        """
        If you are not subscribed on any project and has curator permissions,
        you will be redirected to curator reports view
        """
        try:
            response = super(ReportListViewMixin, self).get(request, *args,
                                                            **kwargs)
            return response
        except RaiseRedirect:
            msg = ("Вы были перенаправлены на список всех отчетов "
                   "текущего семестра")
            messages.info(request, msg, extra_tags="timeout")
            redirect_to = reverse("projects:report_list_curators")
            return HttpResponseRedirect(redirect_to=redirect_to)


class ReportListCuratorView(CuratorOnlyMixin, ReportListViewMixin,
                            generic.ListView):

    def get_context_data(self, **kwargs):
        context = super(ReportListCuratorView, self).get_context_data(**kwargs)
        projects = list(context[self.context_object_name])
        projects.sort(key=self.cmp_projects)
        context[self.context_object_name] = projects
        return context

    @staticmethod
    def cmp_projects(project):
        """
        Немного сумасшедшая сортировка:
        1. отправлены отчёты всех участников, проверка ещё не у всех
        2. подведение итогов куратором у кого-то из участников
        3. отправлены не у всех
        4. не отправлены у всех
        5. на проверке у всех
        6. у кого-то на проверке
        """
        if not hasattr(project, "__cmp__num_order"):
            reports_cnt = 0
            participants_cnt = 0
            any_has_sent_status = False
            any_has_review_status = False
            any_has_summary_status = False
            all_has_review_status = True
            for ps in project.projectstudent_set.all():
                try:
                    report = ps.report
                    if report.status == Report.SENT:
                        any_has_sent_status = True
                    elif report.status == Report.SUMMARY:
                        any_has_summary_status = True
                    elif report.status == Report.REVIEW:
                        any_has_review_status = True
                    else:
                        all_has_review_status = False
                    reports_cnt += 1
                    participants_cnt += 1
                except (AttributeError, Report.DoesNotExist):
                    if ps.final_grade == ProjectStudent.GRADES.not_graded:
                        participants_cnt += 1
            all_sent_report = (participants_cnt == reports_cnt)
            if all_sent_report and any_has_sent_status:
                num_order = 1
            elif all_sent_report and any_has_summary_status:
                num_order = 2
            elif reports_cnt == 0:
                # Subset of next condition, check in the first place
                num_order = 4
            elif not all_sent_report:
                num_order = 3
            elif all_sent_report and all_has_review_status:
                num_order = 5
            elif all_sent_report and any_has_review_status:
                num_order = 6
            else:
                num_order = 7
            project.__cmp__num_order = num_order
        else:
            num_order = project.__cmp__num_order
        return num_order, project.name


class CurrentTermProjectsView(ProjectReviewerGroupOnlyMixin, FilterMixin,
                              generic.ListView):
    paginate_by = 50
    filterset_class = CurrentTermProjectsFilter
    context_object_name = "projects"
    template_name = "learning/projects/available.html"

    def get_queryset(self):
        current_year, term_type = get_current_semester_pair()
        current_term_index = get_term_index(current_year, term_type)
        queryset = (Project.objects
                    .filter(semester__index=current_term_index,
                            canceled=False)
                    .select_related("semester")
                    .prefetch_related("students", "reviewers")
                    .annotate(reviewers_cnt=Count("reviewers"))
                    .annotate(
                        have_reviewers=Case(
                            When(reviewers_cnt__gt=0, then=Value(1)),
                            default=Value(0),
                            output_field=BooleanField()))
                    .order_by("have_reviewers", "name", "pk"))
        return queryset

    def get_context_data(self, **kwargs):
        context = super(CurrentTermProjectsView,
                        self).get_context_data(**kwargs)
        context["current_term"] = Semester.get_current()
        if self.request.user.is_curator:
            context["filter"] = self.filterset
        else:
            context["filter"] = ""
        return context

    def get(self, request, *args, **kwargs):
        if not request.user.is_curator:
            return super().get(request, *args, **kwargs)
        filterset_class = self.get_filterset_class()
        self.filterset = self.get_filterset(filterset_class)
        self.object_list = self.filterset.qs
        context = self.get_context_data(filter=self.filterset,
                                        object_list=self.object_list)
        return self.render_to_response(context)


class ProjectListView(CuratorOnlyMixin, BaseFilterView, generic.ListView):
    paginate_by = 50
    filterset_class = ProjectsFilter
    context_object_name = "projects"
    template_name = "learning/projects/all.html"

    def get_queryset(self):
        queryset = (Project.objects
                    .select_related("semester")
                    .prefetch_related("students", "reviewers")
                    .order_by("-semester__index", "name", "pk"))
        return queryset

    def get_context_data(self, **kwargs):
        context = super(ProjectListView, self).get_context_data(**kwargs)
        context["filter"] = self.filterset
        return context


class StudentProjectsView(StudentOnlyMixin, generic.ListView):
    context_object_name = "projects"
    template_name = "learning/projects/student_projects.html"

    def get_queryset(self):
        return (ProjectStudent.objects
                .filter(student=self.request.user)
                .select_related("project", "project__semester", "student")
                .order_by("-project__semester__index", "project__name"))


class ProjectDetailView(generic.CreateView):
    model = Report
    form_class = ReportForm
    context_object_name = "report"
    template_name = "learning/projects/project_detail.html"

    def get_project(self):
        queryset = Project.objects.select_related("semester").prefetch_related(
            Prefetch(
                "projectstudent_set",
                queryset=(ProjectStudent
                          .objects
                          .select_related("report", "student"))
            ),
            "reviewers"
        )
        pk = self.kwargs.get(self.pk_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(pk=pk)
        if pk is None:
            raise AttributeError("Create view %s must be called with "
                                 "either an object pk."
                                 % self.__class__.__name__)
        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

    def get_authenticated_project_student(self, project):
        """
        Returns related student_project instance if authenticated user
        is student participant of current project
        """
        for ps in project.projectstudent_set.all():
            if ps.student == self.request.user:
                return ps
        return None

    def get(self, request, *args, **kwargs):
        self.object = None
        self.project = self.get_project()
        # Redirect student participant to report page if report exists
        project_student = self.get_authenticated_project_student(self.project)
        try:
            _ = project_student.report
            return self.response_redirect_to_report(project_student)
        except (AttributeError, Report.DoesNotExist):
            pass
        context = self.get_context_data()
        return self.render_to_response(context)

    @staticmethod
    def response_redirect_to_report(project_student):
        return HttpResponseRedirect(
            reverse(
                "projects:student_project_report",
                kwargs={
                    "project_pk": project_student.project.pk,
                    "student_pk": project_student.student.pk
                }
            )
        )

    def post(self, request, *args, **kwargs):
        """Check user permissions before create new report"""
        self.object = None
        self.project = self.get_project()
        project_student = self.get_authenticated_project_student(self.project)
        try:
            _ = project_student.report
            return self.response_redirect_to_report(project_student)
        except Report.DoesNotExist:
            # DoesNotExist is subclass of AttributeError
            pass
        except AttributeError as e:
            # It is not student participant
            return HttpResponseForbidden()
        # Prevent action if reporting period not started yet or stale or
        # student already has some grade
        if (not self.project.is_active() or
                not self.project.report_period_started() or
                not project_student.can_send_report()):
            # TODO: redirect with appropriate message?
            return HttpResponseForbidden()
        form_kwargs = self.get_form_kwargs()
        form_kwargs["project_student"] = project_student
        form = self.form_class(**form_kwargs)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        messages.success(self.request,
                         _("Report successfully sended"),
                         extra_tags="timeout")
        report = self.object
        return reverse(
            "projects:project_report",
            kwargs={
                "project_pk": report.project_student.project.pk,
                "student_pk": report.project_student.student.pk
            }
        )

    def get_context_data(self, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        # Permissions block
        user = self.request.user
        context["project"] = self.project
        project_student = self.get_authenticated_project_student(self.project)
        # Student participant should already have been redirected to
        # report page if his report exists
        context["has_sending_report_permissions"] = (
            self.project.is_active() and
            user in self.project.students.all() and
            project_student.can_send_report()
        )
        context["you_enrolled"] = user in self.project.reviewers.all()
        context["has_enroll_permissions"] = (
            (user.is_project_reviewer or user.is_curator)
            and self.project.is_active())
        context["can_view_report"] = user.is_curator or (
            user.is_project_reviewer and context["you_enrolled"])
        return context


class ProjectPrevNextView(generic.RedirectView):
    """
    Based on `direction` get prev or next project relative to passed project id
    """
    direction = None
    # TODO: add tests
    def get_queryset(self):
        current_year, term_type = get_current_semester_pair()
        current_term_index = get_term_index(current_year, term_type)
        queryset = (Project.objects
                    .filter(semester__index=current_term_index,
                            canceled=False)
                    .annotate(reviewers_cnt=Count("reviewers"))
                    .annotate(
                        have_reviewers=Case(
                            When(reviewers_cnt__gt=0, then=Value(1)),
                            default=Value(0),
                            output_field=BooleanField())
                    )
                    .values_list("pk", flat=True)
                    .order_by("have_reviewers", "name", "pk"))
        return queryset

    def get_redirect_url(self, *args, **kwargs):
        project_id = int(self.kwargs.get("project_id"))
        # Not so many projects to care about performance
        qs = self.get_queryset()
        if self.direction == "prev":
            qs = qs.reverse()
        next_project_id, first, prev_id = (None,) * 3
        for p in qs:
            if prev_id == project_id:
                next_project_id = p
                break
            if first is None:
                # Rotate if we didn't find next project
                next_project_id = p
                first = p
            prev_id = p
        return reverse("projects:project_detail", args=[next_project_id])


class ProjectEnrollView(ProjectReviewerGroupOnlyMixin, generic.View):
    http_method_names = ['post']
    raise_exception = True  # raise if not in project_reviewer group

    def post(self, request, *args, **kwargs):
        project_pk = kwargs.get("pk")
        project = get_object_or_404(
            Project.objects
                   .select_related("semester")
                   .filter(pk=project_pk)
        )
        if not project.is_active():
            return HttpResponseForbidden()

        project.reviewers.add(request.user.pk)
        project.save()
        # TODO: add notification when user unsubscribed?
        notify.send(
            request.user,  # actor
            type=types.PROJECT_REVIEWER_ENROLLED,
            verb='enrolled in',
            action_object=project,
            public=False,
            recipient="")
        messages.success(self.request,
                         _("You successfully enrolled on the project"),
                         extra_tags='timeout')
        url = reverse("projects:project_detail", args=[project.pk])
        return HttpResponseRedirect(url)


class ReportView(FormMixin, generic.DetailView):
    model = Report
    http_method_names = ["get", "post", "put"]
    context_object_name = "report"
    template_name = "learning/projects/report.html"

    def __init__(self, **kwargs):
        super(ReportView, self).__init__(**kwargs)
        self.is_author = None
        self.is_project_reviewer = None
        self.is_curator = None

    def get_object(self, queryset=None):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        report = get_object_or_404(
            Report.objects
            .filter(
                project_student__student=student_pk,
                project_student__project=project_pk)
            .select_related(
                "project_student",
                "project_student__student",
                "project_student__project",
                "project_student__project__semester")
        )
        return report

    def set_roles(self, report):
        """Cache roles of authenticated user in current project """
        user = self.request.user
        self.is_author = report.project_student.student_id == user.pk
        self.is_project_reviewer = (
            user in report.project_student.project.reviewers.all())
        self.is_curator = user.is_curator

    def has_permissions(self, report):
        """Check authenticated user has access to GET- or POST-actions"""
        is_author = self.is_author
        is_project_reviewer = self.is_project_reviewer
        is_curator = self.request.user.is_curator
        is_project_participant = is_author or is_project_reviewer or is_curator
        add_comment_action = ReportCommentForm.prefix in self.request.POST
        send_review_action = ReportReviewForm.prefix in self.request.POST
        # Additional check for curators on send review action
        if send_review_action and (not is_project_reviewer or
                                   report.is_completed()):
            return False
        if is_curator:
            return True
        # Restrict send comment for all except curators if review is completed
        if add_comment_action and report.status in [report.COMPLETED,
                                                    report.SUMMARY]:
            return False
        # Hide view for reviewers until report status is `SENT`.
        if is_project_reviewer and report.status == Report.SENT:
            return False
        return is_project_participant

    def send_notification_to_curators(self, review):
        """Reviewer complete assessment"""
        curators = (CSCUser.objects.filter(
            is_superuser=True,
            is_staff=True,
            groups=PARTICIPANT_GROUPS.CURATOR_PROJECTS))
        report = (Report.objects
                  .select_related("project_student",
                                  "project_student__project",
                                  "project_student__student")
                  .get(pk=review.report_id))
        other_reports = (Report.objects
            .filter(project_student__project=report.project_student.project)
            .exclude(project_student=report.project_student)
            .values_list("pk", flat=True))
        student = report.project_student.student
        student_declension = ""
        if student.gender == CSCUser.GENDER_FEMALE:
            student_declension = "a"
        context = {
            "student_pk": student.pk,
            "student": student.get_short_name(),
            "student_declension": student_declension,
            "project_pk": report.project_student.project.pk,
            "project_name": report.project_student.project.name,
            "other_reports": other_reports
        }
        for recipient in curators:
            notify.send(
                self.request.user,  # Reviewer
                type=types.PROJECT_REPORT_REVIEW_COMPLETED,
                verb='changed',
                action_object=review,
                target=report,
                recipient=recipient,
                data=context
            )

    def form_valid(self, form):
        model = form.save()
        if form.prefix == ReportReviewForm.prefix and model.is_completed:
            self.send_notification_to_curators(model)
        return super(ReportView, self).form_valid(form)

    def form_invalid(self, **kwargs):
        messages.error(self.request, _("Data not saved. Fix errors."))
        context = self.get_context_data(**kwargs)
        context["has_errors"] = True
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # skip FormMixin.get_context_data() here
        context = super(FormMixin, self).get_context_data(**kwargs)
        report = context[self.context_object_name]
        form_kwargs = {
            "report": report,
            "author": self.request.user
        }
        if report.summarize_state() and self.request.user.is_curator:
            report.calculate_mean_scores()
            context[ReportSummarizeForm.prefix] = ReportSummarizeForm(
                instance=report)
        if ReportStatusForm.prefix not in context:
            context[ReportStatusForm.prefix] = ReportStatusForm(
                instance=report)
        if ReportCuratorAssessmentForm.prefix not in context:
            context[ReportCuratorAssessmentForm.prefix] = \
                ReportCuratorAssessmentForm(instance=report)
        if ReportCommentForm.prefix not in context:
            context[ReportCommentForm.prefix] = ReportCommentForm(**form_kwargs)
        own_review = self.get_review_object(report)
        if ReportReviewForm.prefix not in context:
            form_kwargs["instance"] = own_review
            context[ReportReviewForm.prefix] = ReportReviewForm(**form_kwargs)
        comments = (ReportComment.objects
                    .filter(report=report)
                    .order_by('created')
                    .select_related('author'))
        context["comments"] = comments
        context['clean_comments_json'] = comment_persistence.get_hashes_json()
        context["can_comment"] = self.can_comment(report, own_review)
        context["can_assess"] = (report.status == report.SENT and
                                 self.request.user.is_curator)
        context["is_reviewer"] = self.is_project_reviewer
        context["is_author"] = self.is_author
        context["reviewers"] = report.project_student.project.reviewers.all()
        # Preliminary scores
        if self.request.user.is_curator:
            context['reviews'] = report.review_set.all()
            # Collect those who without report at all
            has_reviews = [r.reviewer_id for r in context['reviews']]
            context["without_reviews"] = [r for r in context["reviewers"]
                                          if r.pk not in has_reviews]
        else:
            context['reviews'] = set()
            context["without_reviews"] = set()
        context['own_review'] = own_review
        return context

    def can_comment(self, report, review):
        # When report has sent, reviewers can't see the whole page until
        # next status
        if report.status == report.SENT:
            return True
        # On review stage reviewers can't comment after review was completed
        if report.status == report.REVIEW:
            if (self.is_project_reviewer and not self.is_curator and
                    review and review.is_completed):
                return False
            return True
        # On last 2 stages nobody can comment
        return False

    def get_review_object(self, report):
        if report.status == report.SENT:
            # No reviews at all on this stage
            return None
        try:
            review = Review.objects.get(
                report=report, reviewer=self.request.user)
        except Review.DoesNotExist:
            review = None
        return review

    def get(self, request, *args, **kwargs):
        report = self.object = self.get_object()
        self.set_roles(report)
        if not self.has_permissions(self.object):
            return redirect_to_login(request.get_full_path())
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        report = self.object = self.get_object()
        self.set_roles(report)
        if not self.has_permissions(self.object):
            return HttpResponseForbidden()

        form_kwargs = self.get_form_kwargs()
        if ReportCommentForm.prefix in request.POST:
            # TODO: Check `can_comment` permissions
            success_msg = _("Comment successfully added.")
            form_class = ReportCommentForm
            form_name = ReportCommentForm.prefix
        elif ReportReviewForm.prefix in request.POST:
            if ReportReviewForm.prefix + "-draft" in request.POST:
                success_msg = _("The draft successfully saved.")
            else:
                success_msg = _("The review successfully saved.")
            form_class = ReportReviewForm
            form_name = ReportReviewForm.prefix
            form_kwargs["instance"] = self.get_review_object(report)
        else:
            return HttpResponseBadRequest()
        form = form_class(**form_kwargs)
        if form.is_valid():
            response = self.form_valid(form)
            messages.success(self.request, success_msg, extra_tags='timeout')
            return response
        else:
            return self.form_invalid(**{form_name: form})

    def get_form_kwargs(self):
        form_kwargs = super(ReportView, self).get_form_kwargs()
        # Required fields for both models, not represented in form
        form_kwargs["report"] = self.object
        form_kwargs["author"] = self.request.user
        return form_kwargs

    def get_success_url(self):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        if self.is_author:
            url_name = "projects:student_project_report"
        else:
            url_name = "projects:project_report"
        return reverse_lazy(
            url_name,
            kwargs={
                "project_pk": project_pk,
                "student_pk": student_pk
            }
        )


class ReportUpdateViewMixin(CuratorOnlyMixin, BaseUpdateView):
    http_method_names = ["post", "put"]
    model = Report

    def get_object(self, queryset=None):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        report = get_object_or_404(
            Report.objects.filter(
                project_student__student=student_pk,
                project_student__project=project_pk,
            )
        )
        return report

    def get_success_url(self):
        project_pk = self.kwargs.get("project_pk")
        student_pk = self.kwargs.get("student_pk")
        messages.success(self.request,
                         self.get_success_msg(),
                         extra_tags='timeout')
        return reverse_lazy(
            "projects:project_report",
            kwargs={
                "project_pk": project_pk,
                "student_pk": student_pk
            }
        )

    @staticmethod
    def get_success_msg():
        return _("Report was successfully updated.")

    @staticmethod
    def get_error_msg(form):
        return _("Data not saved. Check errors.")

    def form_invalid(self, form):
        """
        Silently fail and redirect. Form will be invalid only if you fake data.
        """
        messages.error(self.request, self.get_error_msg(form))
        return HttpResponseRedirect(reverse(
            "projects:project_report",
            kwargs={
                "project_pk": self.kwargs.get("project_pk"),
                "student_pk": self.kwargs.get("student_pk")
            }
        ))


class ReportUpdateStatusView(ReportUpdateViewMixin):
    form_class = ReportStatusForm

    @staticmethod
    def get_success_msg():
        return _("Status was successfully updated.")

    @staticmethod
    def get_error_msg(form):
        msg = "<br>".join("<br>".join(errors) for errors in
                          form.errors.values())
        return "Статус не был обновлён.<br>" + msg

    def get_queryset(self):
        qs = super(ReportUpdateStatusView, self).get_queryset()
        return qs.select_related("project_student__project")

    def form_valid(self, form):
        response = super(ReportUpdateStatusView, self).form_valid(form)
        report = self.object
        project_id = report.project_student.project_id
        if "status" in form.changed_data and report.status == Report.REVIEW:
            project_students = (ProjectStudent.objects
                                .filter(project_id=project_id)
                                .select_related("student", "report"))
            all_reports_in_review_state = True
            for ps in project_students:
                try:
                    if ps.report.status != Report.REVIEW:
                        all_reports_in_review_state = False
                        break
                except ObjectDoesNotExist:
                    # Don't take into stats if student already has
                    # unsatisfactory grade. It means he left project.
                    if ps.final_grade == ProjectStudent.GRADES.unsatisfactory:
                        continue
                    all_reports_in_review_state = False
                    break
            if all_reports_in_review_state:
                self.send_email_notification(project_students)
            # For all reviews drop is_complete flag
            Review.objects.filter(report=report).update(is_completed=False)
        return response

    def send_email_notification(self, project_students):
        """
        All project reports in review state, send notification to reviewers
        about that fact.
        """
        reports = [(ps.student.pk, ps.student.get_short_name()) for ps
                   in project_students]
        context = {
            "project_pk": self.object.project_student.project.pk,
            "project_name": self.object.project_student.project.name,
            "reports": reports
        }
        reviewers = self.object.project_student.project.reviewers.all()
        for recipient in reviewers:
            notify.send(
                self.request.user,  # Curator who changed status
                type=types.PROJECT_REPORTS_IN_REVIEW_STATE,
                verb='changed',
                target=self.object,
                recipient=recipient,
                data=context
            )


class ReportCuratorAssessmentView(ReportUpdateViewMixin):
    form_class = ReportCuratorAssessmentForm

    @staticmethod
    def get_success_msg():
        return _("Grades successfully updated.")


class ReportCuratorSummarizeView(ReportUpdateViewMixin):
    form_class = ReportSummarizeForm

    @staticmethod
    def get_success_msg():
        return _("The report results are summed up successfully.")

    def form_valid(self, form):
        response = super(ReportCuratorSummarizeView, self).form_valid(form)

        # Send email notification to student participant
        if self.object.status == self.object.COMPLETED:
            self.send_email_notification()
        return response

    def send_email_notification(self):
        """Email notification with final results and comments for student"""
        # FIXME: test db hitting
        context = {
            "project_name": self.object.project_student.project.name,
            "final_score": self.object.final_score,
            "message": self.object.final_score_note
        }
        notify.send(
            self.request.user,  # Curator who complete reviewing
            type=types.PROJECT_REPORT_COMPLETED,
            verb='complete',
            # In this case action_object and target are the same
            target=self.object,
            recipient=self.object.project_student.student,
            data=context
        )


class ReportAttachmentDownloadView(LoginRequiredMixin, generic.View):

    def get(self, request, *args, **kwargs):
        try:
            attachment_type, pk = hashids.decode(kwargs['sid'])
        except IndexError:
            raise Http404
        projects_app = apps.get_app_config("projects")
        user = request.user
        if attachment_type == projects_app.REPORT_COMMENT_ATTACHMENT:
            qs = ReportComment.objects.filter(pk=pk)
            if not user.is_project_reviewer and not user.is_curator:
                qs = qs.filter(report__project_student__student=user)
            comment = get_object_or_404(qs)
            if not comment.attached_file:
                raise Http404
            file_name = comment.attached_file_name
            file_url = comment.attached_file.url
        elif attachment_type == projects_app.REPORT_ATTACHMENT:
            qs = Report.objects.filter(pk=pk)
            if not user.is_project_reviewer and not user.is_curator:
                qs = qs.filter(project_student__student=user)
            report = get_object_or_404(qs)
            if not report.file:
                raise Http404
            file_name = report.file_name
            file_url = report.file.url
        else:
            raise Http404

        response = HttpResponse()
        del response['Content-Type']
        response['Content-Disposition'] = "attachment; filename={}".format(
            file_name)
        response['X-Accel-Redirect'] = file_url
        return response

