import logging
from typing import List, Optional

from django.db.models import Prefetch
from django.utils.translation import gettext_noop

from courses.models import Assignment
from courses.services import CourseService
from courses.tabs import CourseTab, CourseTabPanel
from courses.tabs_registry import register
from learning.permissions import ViewCourseNews, ViewCourseReviews
from learning.services import CourseRole, course_access_role

logger = logging.getLogger(__name__)


@register
class CourseContactsTab(CourseTab):
    type = 'contacts'
    title = gettext_noop("CourseTab|Contacts")
    priority = 20
    is_hidden = False

    @classmethod
    def is_enabled(cls, course, user):
        return user.get_enrollment(course.pk) or user.is_curator

    def get_tab_panel(self, *, course, user) -> Optional[CourseTabPanel]:
        return CourseTabPanel(context={
            "items": CourseService.get_contacts(course)
        })


@register
class CourseNewsTab(CourseTab):
    type = 'news'
    title = gettext_noop("CourseTab|News")
    priority = 60

    @classmethod
    def is_enabled(cls, course, user):
        return user.has_perm(ViewCourseNews.name, course)

    def get_tab_panel(self, *, course, user) -> Optional[CourseTabPanel]:
        return CourseTabPanel(context={"items": CourseService.get_news(course)})


@register
class CourseReviewsTab(CourseTab):
    type = 'reviews'
    title = gettext_noop("CourseTab|Reviews")
    priority = 30
    is_hidden = False

    @classmethod
    def is_enabled(cls, course, user):
        return user.has_perm(ViewCourseReviews.name, course)

    def get_tab_panel(self, *, course, user) -> Optional[CourseTabPanel]:
        return CourseTabPanel(context={
            "items": CourseService.get_reviews(course)
        })


@register
class CourseAssignmentsTab(CourseTab):
    type = 'assignments'
    title = gettext_noop("CourseTab|Assignments")
    priority = 50

    @classmethod
    def is_enabled(cls, course, user):
        return (user.is_curator or user.is_student or user.is_graduate or
                user.is_teacher or user.get_enrollment(course.pk))

    def get_tab_panel(self, *, course, user) -> Optional[CourseTabPanel]:
        return CourseTabPanel(context={
            "items": get_course_assignments(course=course, user=user)
        })


def get_course_assignments(course, user, user_role=None) -> List[Assignment]:
    """
    Returns
    For enrolled students show links to there submissions.
    Course teachers (among all terms) see links to assignment details.
    Others can see only assignment names.
    """
    if user_role is None:
        user_role = course_access_role(course=course, user=user)
    Assignment = course.assignment_set.field.model
    AssignmentAttachment = Assignment.assignmentattachment_set.field.model
    attachments = Prefetch("assignmentattachment_set",
                           queryset=AssignmentAttachment.objects.order_by())
    assignments = (course.assignment_set
                   .only("title", "course_id", "submission_type", "deadline_at", "time_zone")
                   .prefetch_related(attachments)
                   .order_by('deadline_at', 'title'))
    student_roles = (CourseRole.STUDENT_REGULAR,
                     CourseRole.STUDENT_RESTRICT)
    if user_role in student_roles:
        assignments = assignments.prefetch_student_scores(user)
    assignments = assignments.all()  # enable query caching
    for assignment in assignments:
        to_details = None
        if user_role in student_roles:
            student_assignment = assignment.studentassignment_set.first()
            if student_assignment is not None:
                if user_role == CourseRole.STUDENT_RESTRICT:
                    # Hide details if the student didn't post any solution
                    if not (student_assignment.score or student_assignment.solutions_total):
                        continue
                to_details = student_assignment.get_student_url()
            else:
                logger.info(f"no StudentAssignment for student ID "
                            f"{user.pk}, assignment ID {assignment.pk}")
        elif user_role in [CourseRole.TEACHER, CourseRole.CURATOR]:
            to_details = assignment.get_teacher_url()
        setattr(assignment, 'magic_link', to_details)
    return assignments
