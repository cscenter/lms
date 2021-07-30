import logging
from typing import NamedTuple

import rules

from django.conf import settings

from auth.permissions import Permission, add_perm
from courses.models import Assignment, AssignmentSubmissionFormats, Course
from learning.models import CourseInvitation, StudentAssignment, StudentGroup
from learning.services import CourseRole, course_access_role, course_failed_by_student
from learning.settings import StudentStatuses
from users.models import StudentProfile, User

logger = logging.getLogger(__name__)


class EnrollPermissionObject(NamedTuple):
    course: Course
    student_profile: StudentProfile


class InvitationEnrollPermissionObject(NamedTuple):
    course_invitation: CourseInvitation
    student_profile: StudentProfile


@rules.predicate
def enroll_in_course(user, permission_object: EnrollPermissionObject):
    course = permission_object.course
    student_profile = permission_object.student_profile
    if not course.enrollment_is_open:
        logger.debug("Enrollment is closed")
        return False
    if course.is_capacity_limited and not course.places_left:
        return False
    if not student_profile:
        return
    if not student_profile.is_active:
        logger.debug("Permissions for student with inactive profile "
                     "are restricted")
        return False
    if course.main_branch_id != student_profile.branch_id:  # avoid db hit
        if not any(b.pk == student_profile.branch_id for b in course.branches.all()):
            logger.debug("Student with branch %s could not enroll in the "
                         "course %s", student_profile.branch_id, course)
            return False
    return True


@rules.predicate
def has_active_status(user):
    if user.is_curator:
        return True
    student_profile = user.get_student_profile(settings.SITE_ID)
    if not student_profile:
        return False
    return not StudentStatuses.is_inactive(student_profile.status)


@rules.predicate
def learner_has_access_to_the_assignment(user: User,
                                         student_assignment: StudentAssignment):
    if user.id != student_assignment.student_id:
        return False
    course = student_assignment.assignment.course
    enrollment = user.get_enrollment(course.pk)
    if not enrollment:
        return False
    student_profile = enrollment.student_profile
    if student_profile.is_active and not course_failed_by_student(course, user):
        return True
    # If student failed the course or was expelled at all, deny
    # access only when he has no submissions or positive
    # grade on assignment
    # XXX: Take into account only student comments since only
    # they could be treated as `submission`.
    return student_assignment.has_comments(user) or student_assignment.score


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
        course = student_assignment.assignment.course
        return user in course.teachers.all()


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
        # FIXME: check is actual teacher?
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
    rule = learner_has_access_to_the_assignment


@add_perm
class ViewSchedule(Permission):
    name = "study.view_schedule"
    rule = has_active_status


@add_perm
class ViewCourses(Permission):
    name = "study.view_courses"
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
class EditGradebook(Permission):
    name = "teaching.edit_gradebook"


@add_perm
class EditOwnGradebook(Permission):
    name = "teaching.edit_own_gradebook"

    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        # FIXME: check course is ended
        return course.is_actual_teacher(user.pk)


@add_perm
class ViewAssignmentAttachment(Permission):
    name = "learning.view_assignment_attachment"


@add_perm
class ViewAssignmentAttachmentAsLearner(Permission):
    name = "study.view_assignment_attachment"

    @staticmethod
    @rules.predicate
    def rule(user, assignment: Assignment):
        try:
            student_assignment = (StudentAssignment.objects
                                  .get(student=user,
                                       assignment_id=assignment.pk))
            return learner_has_access_to_the_assignment(user, student_assignment)
        except StudentAssignment.DoesNotExist:
            return False


@add_perm
class ViewAssignmentAttachmentAsTeacher(Permission):
    name = "teaching.view_assignment_attachment"

    @staticmethod
    @rules.predicate
    def rule(user, assignment: Assignment):
        return user in assignment.course.teachers.all()


@add_perm
class CreateAssignmentComment(Permission):
    name = "learning.create_assignment_comment"


@add_perm
class CreateAssignmentCommentAsLearner(Permission):
    name = "study.create_assignment_comment"

    @staticmethod
    @rules.predicate
    def rule(user, student_assignment: StudentAssignment):
        student_profile = user.get_student_profile()
        if student_profile.status in StudentStatuses.inactive_statuses:
            return False
        return student_assignment.student_id == user.id


@add_perm
class CreateAssignmentCommentAsTeacher(Permission):
    name = "teaching.create_assignment_comment"

    @staticmethod
    @rules.predicate
    def rule(user, student_assignment: StudentAssignment):
        return user in student_assignment.assignment.course.teachers.all()


@add_perm
class CreateAssignmentSolution(Permission):
    name = "learning.create_assignment_solution"


@add_perm
class CreateOwnAssignmentSolution(Permission):
    name = "study.create_assignment_solution"

    @staticmethod
    @rules.predicate
    def rule(user, student_assignment: StudentAssignment):
        submission_format = student_assignment.assignment.submission_type
        if submission_format == AssignmentSubmissionFormats.NO_SUBMIT:
            return False
        student_profile = user.get_student_profile()
        if student_profile.status in StudentStatuses.inactive_statuses:
            return False
        return student_assignment.student_id == user.id


@add_perm
class ViewAssignmentCommentAttachment(Permission):
    name = "learning.view_assignment_comment_attachment"


@add_perm
class ViewAssignmentCommentAttachmentAsLearner(Permission):
    name = "study.view_assignment_comment_attachment"
    rule = learner_has_access_to_the_assignment


@add_perm
class ViewAssignmentCommentAttachmentAsTeacher(Permission):
    name = "teaching.view_assignment_comment_attachment"

    @staticmethod
    @rules.predicate
    def rule(user, student_assignment: StudentAssignment):
        return user in student_assignment.assignment.course.teachers.all()


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
    def rule(user, permission_object: InvitationEnrollPermissionObject):
        course_invitation = permission_object.course_invitation
        if not course_invitation or not course_invitation.is_active:
            return False
        perm_obj = EnrollPermissionObject(
            course_invitation.course,
            permission_object.student_profile)
        return enroll_in_course(user, perm_obj)


@add_perm
class LeaveCourse(Permission):
    name = "learning.leave_course"

    @staticmethod
    @rules.predicate
    def rule(user, course: Course):
        """Student could leave the course before enrollment deadline."""
        if not course.enrollment_is_open:
            return False
        enrollment = user.get_enrollment(course)
        if not enrollment:
            return False
        return True


@add_perm
class CreateStudentGroup(Permission):
    """Allows to create any student group."""
    name = "learning.create_student_group"


@add_perm
class CreateStudentGroupAsTeacher(Permission):
    """Allows course teacher to create student group of this course."""

    name = "teaching.create_student_group"

    @staticmethod
    @rules.predicate
    def rule(user: User, course: Course):
        return user in course.teachers.all()


@add_perm
class ViewStudentGroup(Permission):
    """Allows to view any student group."""

    name = "learning.view_student_group"


@add_perm
class ViewStudentGroupAsTeacher(Permission):
    """Allows course teacher to view student group of this course."""

    name = "teaching.view_student_group"

    @staticmethod
    @rules.predicate
    def rule(user: User, course: Course):
        return user in course.teachers.all()


@add_perm
class UpdateStudentGroup(Permission):
    """Allows to update any student group."""

    name = "learning.update_student_group"


@add_perm
class UpdateStudentGroupAsTeacher(Permission):
    """Allows course teacher to update student group of this course."""

    name = "teaching.update_student_group"

    @staticmethod
    @rules.predicate
    def rule(user: User, student_group: StudentGroup):
        return user in student_group.course.teachers.all()


@add_perm
class DeleteStudentGroup(Permission):
    """Allows to delete any student group."""

    name = "learning.delete_student_group"


@add_perm
class DeleteStudentGroupAsTeacher(Permission):
    """Allows course teacher to delete student group of this course."""

    name = "teaching.delete_student_group"

    @staticmethod
    @rules.predicate
    def rule(user: User, student_group: StudentGroup):
        return user in student_group.course.teachers.all()
