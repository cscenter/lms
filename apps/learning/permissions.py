import logging

import rules
from django.conf import settings

from auth.permissions import add_perm, Permission
from courses.models import Course, CourseTeacher
from learning.models import StudentAssignment, CourseInvitation
from learning.services import course_failed_by_student, CourseRole, \
    course_access_role
from learning.settings import StudentStatuses

logger = logging.getLogger(__name__)


@rules.predicate
def enroll_in_course(user, course: Course):
    if not course.enrollment_is_open:
        logger.debug("Enrollment is closed")
        return False
    if course.is_capacity_limited and not course.places_left:
        return False
    student_profile = user.get_student_profile(settings.SITE_ID)
    if not student_profile:
        return
    if not student_profile.is_active:
        logger.debug("Permissions for student with inactive profile "
                     "are restricted")
        return False
    if course.main_branch_id != student_profile.branch_id:  # avoid db hit
        if not any(b.pk == student_profile.branch_id for b in course.branches.all()):
            logger.debug("Student with branch %s could not enroll in the "
                         "course %s", user.branch_id, course)
            return False
    return True


# FIXME: перевесить на StudentProfile
@rules.predicate
def has_active_status(user):
    return user.status not in StudentStatuses.inactive_statuses


@add_perm
class ViewStudyMenu(Permission):
    name = "learning.view_study_menu"


@add_perm
class ViewTeachingMenu(Permission):
    name = "learning.view_teaching_menu"


@add_perm
class ViewCourseNews(Permission):
    name = "learning.view_course_news"

    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        role = course_access_role(course=course, user=user)
        return role != CourseRole.NO_ROLE and role != CourseRole.STUDENT_RESTRICT


@add_perm
class ViewCourseReviews(Permission):
    name = "learning.view_course_reviews"

    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        return course.enrollment_is_open


@add_perm
class ViewEnrollments(Permission):
    """
    User with this permission has access to view all course enrollments.

    Note:
        Related Permissions use `course` instance as a permission object.
    """
    name = "learning.view_enrollment"

    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        return True


@add_perm
class ViewRelatedEnrollments(Permission):
    name = "teaching.view_enrollment"

    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        # TODO: What about teachers from other related courses?
        return any(t.teacher_id == user.pk for t in
                   course.course_teachers.all())


@add_perm
class ViewLibrary(Permission):
    name = "study.view_library"
    rule = has_active_status


@add_perm
class ViewOwnEnrollments(Permission):
    name = "study.view_own_enrollments"
    rule = has_active_status


@add_perm
class ViewStudentAssignmentList(Permission):
    name = "learning.view_studentassignments"


@add_perm
class ViewStudentAssignment(Permission):
    name = "learning.view_studentassignment"


@add_perm
class ViewRelatedStudentAssignment(Permission):
    name = "teaching.view_studentassignment"

    @staticmethod
    @rules.predicate
    def rule(user, student_assignment: StudentAssignment):
        """
        Teacher permits to view all assignments related to the meta course
        where he participated in.
        """
        course = student_assignment.assignment.course
        all_teachers = (CourseTeacher.objects
                        .filter(course__meta_course_id=course.meta_course_id)
                        .values_list('teacher_id', flat=True))
        return user.pk in all_teachers


@add_perm
class EditStudentAssignment(Permission):
    name = "learning.change_studentassignment"


@add_perm
class EditOwnStudentAssignment(Permission):
    name = "teaching.change_studentassignment"

    @staticmethod
    @rules.predicate
    def rule(user, student_assignment: StudentAssignment):
        course = student_assignment.assignment.course
        return user in course.teachers.all()


# FIXME: возможно, view_assignments надо отдать куратору и преподавателю. А студенту явный view_own_assignments.
#  Но, блин, этот дурацкий случай для отчисленных студентов :< И own ничего не чекает, никакой бизнес-логики на самом деле не приаттачено(((((((((
@add_perm
class ViewOwnStudentAssignments(Permission):
    name = "study.view_own_assignments"
    rule = has_active_status


@add_perm
class ViewOwnStudentAssignment(Permission):
    name = "study.view_own_assignment"

    @staticmethod
    @rules.predicate
    def rule(user, student_assignment: StudentAssignment):
        if user.id != student_assignment.student_id:
            return False

        course = student_assignment.assignment.course
        is_inactive = user.status in StudentStatuses.inactive_statuses
        if not is_inactive and not course_failed_by_student(course, user):
            return True
        # If student failed the course or was expelled at all, deny
        # access only when he has no submissions or positive
        # grade on assignment
        # XXX: Take into account only student comments since only
        # they could be treated as `submission`.
        return student_assignment.has_comments(user) or student_assignment.score


@add_perm
class ViewSchedule(Permission):
    name = "study.view_schedule"
    rule = has_active_status


@add_perm
class ViewCourses(Permission):
    name = "study.view_courses"
    rule = has_active_status


@add_perm
class ViewInternships(Permission):
    name = "study.view_internships"
    rule = has_active_status


@add_perm
class ViewFAQ(Permission):
    name = "study.view_faq"
    rule = has_active_status


@add_perm
class ViewGradebook(Permission):
    name = "teaching.view_gradebook"


@add_perm
class ViewOwnGradebook(Permission):
    name = "teaching.view_own_gradebook"

    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        return user in course.teachers.all()


@add_perm
class CreateAssignmentComment(Permission):
    name = "learning.create_assignment_comment"


@add_perm
class CreateAssignmentCommentStudent(Permission):
    name = "study.create_assignment_comment"

    @staticmethod
    @rules.predicate
    def rule(user, student_assignment: StudentAssignment):
        if user.status in StudentStatuses.inactive_statuses:
            return False
        return student_assignment.student_id == user.id


@add_perm
class CreateAssignmentCommentTeacher(Permission):
    name = "teaching.create_assignment_comment"

    @staticmethod
    @rules.predicate
    def rule(user, sa: StudentAssignment):
        return user in sa.assignment.course.teachers.all()


@add_perm
class EditOwnAssignmentExecutionTime(Permission):
    """
    Access is granted to the student after course teacher assessed student work
    """
    name = "study.update_own_assignment_execution_time"

    @staticmethod
    @rules.predicate
    def rule(user, sa: StudentAssignment):
        return sa.student_id == user.id and sa.score is not None


@add_perm
class EnrollInCourse(Permission):
    name = "learning.enroll_in_course"
    rule = enroll_in_course


@add_perm
class EnrollInCourseByInvitation(Permission):
    name = "learning.enroll_in_course_by_invitation"

    @staticmethod
    @rules.predicate
    def rule(user, course_invitation: CourseInvitation):
        if not course_invitation or not course_invitation.is_active:
            return False
        return enroll_in_course(user, course_invitation.course)


@add_perm
class LeaveCourse(Permission):
    name = "learning.leave_course"

    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        # Student could unenroll before enrollment deadline
        if not course.enrollment_is_open:
            return False
        enrollment = user.get_enrollment(course)
        if not enrollment:
            return False
        return True
