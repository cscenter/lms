import json

from django.conf import settings
from django.db.models import Q
from django.utils.timezone import now
from django.views import generic
from rest_framework.response import Response
from rest_framework.views import APIView

from admission.models import Campaign, Interview, Comment
from core.models import Branch
from core.utils import bucketize
from courses.constants import SemesterTypes
from courses.models import Course, Semester
from courses.utils import get_term_index
from learning.settings import StudentStatuses, GradeTypes
from projects.constants import ProjectGradeTypes
from users.constants import Roles
from users.managers import get_enrollments_progress, get_projects_progress
from users.mixins import CuratorOnlyMixin
from users.models import User, StudentProfile


class StatsIndexView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/index.html"


class StatsLearningView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/learning.html"

    def get_context_data(self, **kwargs):
        context = super(StatsLearningView, self).get_context_data(**kwargs)
        # Terms grouped by year
        branches = Branch.objects.for_site(site_id=self.request.site.pk)
        min_established = min(b.established for b in branches)
        term_start = get_term_index(min_established, SemesterTypes.AUTUMN)
        terms = (Semester.objects.only("pk", "type", "year")
                 .filter(index__gte=term_start)
                 .order_by("-index"))
        context["terms"] = bucketize(terms, key=lambda x: x.year)
        # TODO: Если прикрутить REST API, то можно эту логику перенести
        # на клиент и сразу не грузить весь список курсов
        # Courses grouped by term
        courses = (Course.objects
                   .filter(main_branch__site_id=settings.SITE_ID)
                   .values("pk", "semester_id", "meta_course__name")
                   .order_by("-semester_id", "meta_course__name"))
        courses = bucketize(courses, key=lambda x: x["semester_id"])
        # Find selected course and term
        course_id = self.request.GET.get("course_session_id")
        try:
            course_id = int(course_id)
        except TypeError:
            max_term_id = max(courses.keys())
            course_id = courses[max_term_id][0]["pk"]
        term_id = None
        for group in courses.values():
            for co in group:
                if co["pk"] == course_id:
                    term_id = co["semester_id"]
                    break
        if not term_id:
            # Replace with appropriate error
            raise Exception("{}".format(course_id))

        context["courses"] = courses
        context["data"] = {
            "selected": {
                "term_id": term_id,
                "course_session_id": course_id,
            },
        }

        context["json_data"] = json.dumps({
            "courses": courses,
            "course_session_id": course_id,
        })
        return context


class StatsAdmissionView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/admission.html"

    def get_context_data(self, **kwargs):
        campaigns, selected_campaign_id = self.get_campaigns()
        branches, selected_branch = self.get_branches(campaigns,
                                                      selected_campaign_id)
        interviewers, selected_interviewer = self.get_interviewers()
        interviewer_stats = selected_interviewer and (Comment.objects
             .filter(interviewer_id=selected_interviewer)
             .select_related("interview",
                             "interview__applicant",
                             "interview__applicant__campaign",
                             "interview__applicant__campaign__branch",
                             "interview__applicant__user")
             .prefetch_related("interview__applicant__user__groups"))
        context = {
            "branches": branches,
            "campaigns": campaigns,
            "interviewers": interviewers,
            "data": {
                "selected": {
                    "branch": selected_branch,
                    "campaign_id": selected_campaign_id,
                    "interviewer_id": selected_interviewer
                },
                "interviewer_stats": interviewer_stats
            },
            "json_data": json.dumps({
                "campaigns": {b.id: [{"id": c.id, "year": c.year} for c in cs] for b, cs in campaigns.items()},
                "campaignId": selected_campaign_id,
                "branchId": selected_branch.pk
            })
        }
        return context

    def get_campaigns(self):
        campaigns = list(Campaign.objects
                         .select_related('branch')
                         .order_by("-year", "branch__site", "branch__order"))
        campaigns = bucketize(campaigns, key=lambda c: c.branch)
        # Find selected campaign
        campaign_id = self.request.GET.get("campaign")
        try:
            campaign_id = int(campaign_id)
        except TypeError:
            branch = next(iter(campaigns))
            campaign_id = campaigns[branch][0].id
        return campaigns, campaign_id

    @staticmethod
    def get_branches(campaigns, selected_campaign_id):
        branches = {}
        selected_branch = None
        for by_branch in campaigns.values():
            for campaign in by_branch:
                branches[campaign.branch.id] = campaign.branch
                if campaign.id == selected_campaign_id:
                    selected_branch = campaign.branch
                    break
        return branches, selected_branch

    def get_interviewers(self):
        selected_interviewer = self.request.GET.get("interviewer", '')
        try:
            selected_interviewer = int(selected_interviewer)
        except ValueError:
            selected_interviewer = ''
        interviewers = (Interview.interviewers.through.objects
                        .distinct("user__last_name", "user_id")
                        .order_by("user__last_name")
                        .select_related("user"))
        return interviewers, selected_interviewer


# TODO: move to learning or users app
class AlumniStats(APIView):
    def get(self, request, graduation_year, format=None):
        filters = (Q(status=StudentStatuses.GRADUATE) &
                   Q(graduate_profile__graduation_year=graduation_year))
        if graduation_year == now().year and self.request.user.is_curator:
            filters = filters | Q(status=StudentStatuses.WILL_GRADUATE)
        exclude_grades = GradeTypes.unsatisfactory_grades
        exclude_project_grades = [ProjectGradeTypes.UNSATISFACTORY, ProjectGradeTypes.NOT_GRADED]
        enrollments_prefetch = get_enrollments_progress(
            lookup='user__enrollment_set',
            filters=[~Q(grade__in=exclude_grades)]
        )
        projects_prefetch = get_projects_progress(
            lookup='user__projectstudent_set',
            filters=[~Q(final_grade__in=exclude_project_grades)])
        student_profiles = (StudentProfile.objects
                            .filter(filters)
                            .select_related('user')
                            .prefetch_related(projects_prefetch,
                                              enrollments_prefetch)
                            .order_by('user__last_name',
                                      'user__first_name',
                                      'pk')
                            .distinct('user__last_name',
                                      'user__first_name',
                                      'pk'))
        unique_teachers = set()
        hours = 0
        enrollments_total = 0
        unique_projects = set()
        unique_courses = set()
        excellent_total = 0
        good_total = 0
        classes_total = {}
        for student_profile in student_profiles:
            user = student_profile.user
            for ps in user.projects_progress:
                unique_projects.add(ps.project_id)
            for enrollment in user.enrollments_progress:
                enrollments_total += 1
                if enrollment.grade in GradeTypes.excellent_grades:
                    excellent_total += 1
                elif enrollment.grade in GradeTypes.good_grades:
                    good_total += 1
                course = enrollment.course
                unique_courses.add(course.meta_course)
                if course.pk not in classes_total:
                    classes_total[course.pk] = course.courseclass_set.count()
                    for course_teacher in course.course_teachers.all():
                        unique_teachers.add(course_teacher.teacher_id)
                course_classes_total = classes_total[course.pk]
                hours += course_classes_total * 1.5
        stats = {
            "total": len(student_profiles),
            "teachers_total": len(unique_teachers),
            "hours": int(hours),
            "courses": {
                "total": len(unique_courses),
                "enrollments": enrollments_total
            },
            "marks": {
                "good": good_total,
                "excellent": excellent_total
            },
            "projects_total": len(unique_projects)
        }
        return Response(stats)
