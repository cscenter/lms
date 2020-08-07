import datetime

import pytest

from auth.permissions import perm_registry
from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.utils import instance_memoize
from courses.models import Course, CourseBranch
from courses.services import CourseService
from courses.tests.factories import CourseFactory, SemesterFactory, \
    AssignmentFactory
from learning.models import StudentAssignment, EnrollmentPeriod
from learning.permissions import CreateAssignmentComment, \
    CreateAssignmentCommentAsTeacher, \
    CreateAssignmentCommentAsLearner, ViewRelatedStudentAssignment, \
    ViewStudentAssignment, EditOwnStudentAssignment, \
    EditOwnAssignmentExecutionTime, EnrollInCourse, EnrollPermissionObject, \
    InvitationEnrollPermissionObject
from learning.services import get_student_profile, CourseRole, \
    course_access_role
from learning.settings import StudentStatuses, GradeTypes, Branches
from learning.tests.factories import EnrollmentFactory, CourseInvitationFactory, \
    AssignmentCommentFactory, StudentAssignmentFactory
from users.constants import Roles
from users.models import ExtendedAnonymousUser, User, StudentTypes
from users.tests.factories import CuratorFactory, TeacherFactory, \
    StudentFactory, UserFactory, StudentProfileFactory


def delete_enrollment_cache(user: User, course: Course):
    instance_memoize.delete_cache(user)


@pytest.mark.django_db
def test_course_access_role_for_anon_and_curator():
    course = CourseFactory()
    anonymous_user = ExtendedAnonymousUser()
    role = course_access_role(course=course, user=anonymous_user)
    assert role == CourseRole.NO_ROLE
    curator = CuratorFactory()
    role = course_access_role(course=course, user=curator)
    assert role == CourseRole.CURATOR
    curator.status = StudentStatuses.EXPELLED
    curator.save()
    delete_enrollment_cache(curator, course)
    role = course_access_role(course=course, user=curator)
    assert role == CourseRole.CURATOR


@pytest.mark.django_db
def test_course_access_role_teacher():
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    role = course_access_role(course=course, user=teacher)
    assert role == CourseRole.TEACHER
    role = course_access_role(course=course, user=teacher_other)
    assert role == CourseRole.NO_ROLE
    # Teacher of the same meta course has access to all readings
    meta_course = course.meta_course
    teacher2 = TeacherFactory()
    course2 = CourseFactory(meta_course=meta_course, teachers=[teacher2])
    role = course_access_role(course=course2, user=teacher2)
    assert role == CourseRole.TEACHER
    # Make sure student `expelled` status doesn't affect on teacher role
    teacher2.status = StudentStatuses.EXPELLED
    teacher2.save()
    role = course_access_role(course=course2, user=teacher2)
    assert role == CourseRole.TEACHER
    # Now make sure that teacher role is prevailed on any student role
    student_profile = StudentProfileFactory(user=teacher2,
                                            branch=course.main_branch)
    role = course_access_role(course=course, user=teacher2)
    assert role == CourseRole.TEACHER
    delete_enrollment_cache(teacher2, course)
    student_profile.status = StudentStatuses.EXPELLED
    student_profile.save()
    role = course_access_role(course=course, user=teacher2)
    assert role == CourseRole.TEACHER
    EnrollmentFactory(student=teacher2, course=course,
                      grade=GradeTypes.UNSATISFACTORY)
    delete_enrollment_cache(teacher2, course)
    assert course_access_role(course=course, user=teacher2) == CourseRole.TEACHER


@pytest.mark.django_db
@pytest.mark.parametrize("inactive_status", StudentStatuses.inactive_statuses)
def test_course_access_role_student(inactive_status, settings):
    semester = SemesterFactory.create_current()
    prev_semester = SemesterFactory.create_prev(semester)
    course = CourseFactory(semester=semester, is_open=False)
    prev_course = CourseFactory(semester=prev_semester, is_open=False)
    student = StudentFactory(status='')  # not expelled
    role = course_access_role(course=course, user=student)
    assert role == CourseRole.NO_ROLE
    delete_enrollment_cache(student, course)
    student_profile = student.get_student_profile(settings.SITE_ID)
    e = EnrollmentFactory(student=student, course=course,
                          grade=GradeTypes.NOT_GRADED)
    # The course from the current semester and student has no grade.
    # It means to us that course is not failed by enrolled student
    role = course_access_role(course=course, user=student)
    assert role == CourseRole.STUDENT_REGULAR
    # Failed course enrollment
    e2 = EnrollmentFactory(student=student, course=prev_course,
                           grade=GradeTypes.UNSATISFACTORY)
    role = course_access_role(course=prev_course, user=student)
    assert role == CourseRole.STUDENT_RESTRICT
    # Inactive student has restricted access to all courses they enrolled in
    delete_enrollment_cache(student, course)
    delete_enrollment_cache(student, prev_course)
    assert student_profile == e.student_profile
    student_profile.status = inactive_status
    student_profile.save()
    role = course_access_role(course=prev_course, user=student)
    assert role == CourseRole.STUDENT_RESTRICT
    role = course_access_role(course=course, user=student)
    assert role == CourseRole.STUDENT_RESTRICT


@pytest.mark.django_db
@pytest.mark.parametrize("inactive_status", StudentStatuses.inactive_statuses)
def test_enroll_in_course(inactive_status, settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    today_local = now_local(branch_spb.get_timezone())
    yesterday = today_local - datetime.timedelta(days=1)
    tomorrow = today_local + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(
        for_branch=settings.DEFAULT_BRANCH_CODE,
        enrollment_period__ends_on=tomorrow.date())
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    course = CourseFactory(
        semester=term, is_open=False,
        completed_at=(today_local + datetime.timedelta(days=10)).date(),
        capacity=0, main_branch=branch_spb)
    assert course.enrollment_is_open
    student_spb = StudentFactory(branch=branch_spb, status="")
    student_spb_profile = student_spb.get_student_profile(settings.SITE_ID)
    perm_obj = EnrollPermissionObject(course, student_spb_profile)
    assert student_spb.has_perm(EnrollInCourse.name, perm_obj)
    # Enrollment is closed
    ep = EnrollmentPeriod.objects.get(semester=course.semester,
                                      site_id=settings.SITE_ID)
    ep.ends_on = yesterday.date()
    ep.save()
    assert not student_spb.has_perm(EnrollInCourse.name, perm_obj)
    ep.ends_on = tomorrow.date()
    ep.save()
    assert student_spb.has_perm(EnrollInCourse.name, perm_obj)
    # Student with inactive status
    student_spb_profile.status = inactive_status
    student_spb_profile.save()
    assert not student_spb.has_perm(EnrollInCourse.name, perm_obj)
    student_spb_profile.status = ''
    student_spb_profile.save()
    assert student_spb.has_perm(EnrollInCourse.name, perm_obj)
    # Full course capacity
    course.capacity = 1
    course.learners_count = 1
    assert not student_spb.has_perm(EnrollInCourse.name, perm_obj)
    course.learners_count = 0
    assert student_spb.has_perm(EnrollInCourse.name, perm_obj)
    # Compare student and course branches
    course.main_branch = branch_nsk
    course.save()
    CourseService.sync_branches(course)
    assert not student_spb.has_perm(EnrollInCourse.name, perm_obj)
    CourseBranch(course=course, branch=branch_spb).save()
    course.refresh_from_db()
    assert student_spb.has_perm(EnrollInCourse.name, perm_obj)


@pytest.mark.django_db
def test_leave_course(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    today = now_local(branch_spb.get_timezone())
    yesterday = today - datetime.timedelta(days=1)
    future = today + datetime.timedelta(days=3)
    term = SemesterFactory.create_current(
        enrollment_period__ends_on=future.date())
    enrollment = EnrollmentFactory(course__semester=term, course__is_open=False)
    course = enrollment.course
    student = enrollment.student
    assert course.enrollment_is_open
    assert student.has_perm("learning.leave_course", course)
    ep = EnrollmentPeriod.objects.get(semester=term, site_id=settings.SITE_ID)
    ep.ends_on = yesterday.date()
    ep.save()
    assert not student.has_perm("learning.leave_course", course)
    ep.ends_on = future.date()
    ep.save()
    assert student.has_perm("learning.leave_course", course)
    # Student couldn't leave abandoned course
    enrollment.is_deleted = True
    enrollment.save()
    student = User.objects.get(pk=student.pk)  # avoid cache
    assert not student.has_perm("learning.leave_course", course)


@pytest.mark.django_db
def test_enroll_in_course_by_invitation(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    today = now_local(branch_spb.get_timezone())
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    branch_spb = BranchFactory(code=Branches.SPB)
    term = SemesterFactory.create_current(
        for_branch=branch_spb.code,
        enrollment_period__ends_on=tomorrow.date())
    course = CourseFactory(main_branch=branch_spb, semester=term, is_open=False,
                           capacity=0)
    assert course.enrollment_is_open
    student = StudentFactory(branch=course.main_branch)
    student_profile = student.get_student_profile(settings.SITE_ID)
    assert student.has_perm(EnrollInCourse.name,
                            EnrollPermissionObject(course, student_profile))
    course_invitation = CourseInvitationFactory(course=course)
    perm_obj = InvitationEnrollPermissionObject(course_invitation,
                                                student_profile)
    assert student.has_perm("learning.enroll_in_course_by_invitation",
                            perm_obj)
    # Invitation activity depends on semester settings.
    # Also this condition checked internally in `learning.enroll_in_course`
    # predicate
    ep = EnrollmentPeriod.objects.get(site_id=settings.SITE_ID,
                                      semester=course.semester)
    ep.ends_on = yesterday.date()
    ep.save()
    assert not course.enrollment_is_open
    assert not student.has_perm("learning.enroll_in_course_by_invitation",
                                perm_obj)


@pytest.mark.django_db
def test_create_assignment_comment():
    user = UserFactory()
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    curator = CuratorFactory()
    student_other = StudentFactory()
    course = CourseFactory(teachers=[teacher])
    assert CreateAssignmentComment.name in perm_registry
    assert CreateAssignmentCommentAsTeacher in perm_registry
    assert CreateAssignmentCommentAsLearner in perm_registry
    e = EnrollmentFactory(course=course)
    student = e.student
    AssignmentFactory(course=course)
    assert StudentAssignment.objects.count() == 1
    sa = StudentAssignment.objects.first()
    assert teacher.has_perm(CreateAssignmentCommentAsTeacher.name, sa)
    assert not teacher_other.has_perm(CreateAssignmentCommentAsTeacher.name, sa)
    assert not curator.has_perm(CreateAssignmentCommentAsTeacher.name, sa)
    assert not user.has_perm(CreateAssignmentCommentAsTeacher.name, sa)
    assert curator.has_perm(CreateAssignmentComment.name, sa)
    # Now check relation
    assert teacher.has_perm(CreateAssignmentComment.name, sa)
    assert not teacher_other.has_perm(CreateAssignmentComment.name, sa)
    assert not student_other.has_perm(CreateAssignmentComment.name, sa)
    assert student.has_perm(CreateAssignmentComment.name, sa)
    assert not user.has_perm(CreateAssignmentComment.name, sa)
    # User is teacher and volunteer
    StudentProfileFactory(type=StudentTypes.VOLUNTEER, user=teacher)
    teacher.refresh_from_db()
    assert teacher.has_perm(CreateAssignmentComment.name, sa)
    assert teacher.has_perm(CreateAssignmentCommentAsTeacher.name, sa)
    assert not teacher.has_perm(CreateAssignmentCommentAsLearner.name, sa)


@pytest.mark.django_db
def test_view_related_student_assignment():
    curator = CuratorFactory()
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course)
    assert not ViewRelatedStudentAssignment.rule(UserFactory(), sa)
    assert ViewRelatedStudentAssignment.rule(teacher, sa)
    assert not ViewRelatedStudentAssignment.rule(teacher_other, sa)
    assert not ViewRelatedStudentAssignment.rule(curator, sa)
    # Teacher for the same meta course has access to all readings
    meta_course = course.meta_course
    teacher2 = TeacherFactory()
    course2 = CourseFactory(meta_course=meta_course, teachers=[teacher2])
    sa2 = StudentAssignmentFactory(assignment__course=course2)
    assert ViewRelatedStudentAssignment.rule(teacher2, sa)
    # Make sure student `expelled` status doesn't affect on teacher role
    teacher2.status = StudentStatuses.EXPELLED
    teacher2.save()
    assert ViewRelatedStudentAssignment.rule(teacher2, sa)


@pytest.mark.django_db
def test_view_student_assignment_role_relation():
    """
    Tests call chain `teacher.has_perm(ViewStudentAssignment.name, sa)` ->
    `teacher.has_perm(ViewRelatedStudentAssignment.name, sa)`
    """
    curator = CuratorFactory()
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course)
    assert not UserFactory().has_perm(ViewStudentAssignment.name, sa)
    assert teacher.has_perm(ViewStudentAssignment.name, sa)
    assert not teacher_other.has_perm(ViewStudentAssignment.name, sa)
    assert curator.has_perm(ViewStudentAssignment.name, sa)


@pytest.mark.django_db
def test_edit_own_student_assignment():
    curator = CuratorFactory()
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    sa = StudentAssignmentFactory(assignment__course=course)
    assert not EditOwnStudentAssignment.rule(UserFactory(), sa)
    assert EditOwnStudentAssignment.rule(teacher, sa)
    assert not EditOwnStudentAssignment.rule(teacher_other, sa)
    assert not EditOwnStudentAssignment.rule(curator, sa)
    # Teacher of the same meta course can't edit assignments where he's
    # not participated
    meta_course = course.meta_course
    teacher2 = TeacherFactory()
    course2 = CourseFactory(meta_course=meta_course, teachers=[teacher2])
    sa2 = StudentAssignmentFactory(assignment__course=course2)
    assert EditOwnStudentAssignment.rule(teacher2, sa2)
    assert not EditOwnStudentAssignment.rule(teacher2, sa)


@pytest.mark.django_db
def test_update_assignment_execution_time():
    """
    Available to the student only after course teacher assessed student work
    """
    permission_name = EditOwnAssignmentExecutionTime.name
    sa = StudentAssignmentFactory(score=None)
    curator = CuratorFactory()
    student = sa.student
    student_other = StudentFactory()
    teacher = TeacherFactory()
    user = UserFactory()
    no_permission = [teacher, user, student_other, curator]
    for u in no_permission:
        assert not u.has_perm(permission_name, sa)
    # Permission denied until student assignment without a score
    assert not student.has_perm(permission_name, sa)
    sa.score = 0
    assert student.has_perm(permission_name, sa)
    for u in no_permission:
        assert not u.has_perm(permission_name, sa)


