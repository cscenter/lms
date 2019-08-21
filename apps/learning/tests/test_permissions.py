import datetime

import pytest

from core.models import Branch
from core.tests.utils import now_for_branch
from core.timezone import now_local
from courses.models import Course
from courses.tests.factories import CourseFactory, SemesterFactory
from learning.permissions import course_access_role, CourseRole
from learning.settings import StudentStatuses, GradeTypes, Branches
from core.settings.base import DEFAULT_BRANCH_CODE
from learning.tests.factories import EnrollmentFactory, CourseInvitationFactory
from users.constants import Roles
from users.models import ExtendedAnonymousUser, User
from users.tests.factories import CuratorFactory, TeacherFactory, \
    StudentFactory


def delete_enrollment_cache(user: User, course: Course):
    cache_attr_name = user.ENROLLMENT_CACHE_KEY.format(course.pk)
    if hasattr(user, cache_attr_name):
        delattr(user, cache_attr_name)


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
    # Teacher for the same meta course has access to all readings
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
    teacher2.add_group(Roles.STUDENT)
    role = course_access_role(course=course, user=teacher2)
    assert role == CourseRole.TEACHER
    delete_enrollment_cache(teacher2, course)
    teacher2.status = StudentStatuses.EXPELLED
    teacher2.save()
    role = course_access_role(course=course, user=teacher2)
    assert role == CourseRole.TEACHER
    EnrollmentFactory(student=teacher2, course=course,
                      grade=GradeTypes.UNSATISFACTORY)
    delete_enrollment_cache(teacher2, course)
    assert course_access_role(course=course, user=teacher2) == CourseRole.TEACHER


@pytest.mark.django_db
def test_course_access_role_student():
    semester = SemesterFactory.create_current()
    prev_semester = SemesterFactory.create_prev(semester)
    course = CourseFactory(semester=semester, is_open=False)
    prev_course = CourseFactory(semester=prev_semester, is_open=False)
    student = StudentFactory(status='')  # not expelled
    role = course_access_role(course=course, user=student)
    assert role == CourseRole.NO_ROLE
    delete_enrollment_cache(student, course)
    e = EnrollmentFactory(student=student, course=course,
                          grade=GradeTypes.NOT_GRADED)
    # The course from the current semester and student has no grade.
    # It means to us that course is not failed by enrolled student
    role = course_access_role(course=course, user=student)
    assert role == CourseRole.STUDENT_REGULAR
    # Failed course enrollment
    EnrollmentFactory(student=student, course=prev_course,
                      grade=GradeTypes.UNSATISFACTORY)
    role = course_access_role(course=prev_course, user=student)
    assert role == CourseRole.STUDENT_RESTRICT
    # Expelled student has restricted access to all courses they enrolled in
    delete_enrollment_cache(student, course)
    delete_enrollment_cache(student, prev_course)
    student.status = StudentStatuses.EXPELLED
    student.save()
    role = course_access_role(course=prev_course, user=student)
    assert role == CourseRole.STUDENT_RESTRICT
    role = course_access_role(course=course, user=student)
    assert role == CourseRole.STUDENT_RESTRICT


@pytest.mark.django_db
def test_enroll_in_course():
    today_local = now_for_branch(Branches.SPB)
    yesterday = today_local - datetime.timedelta(days=1)
    tomorrow = today_local + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(for_branch=DEFAULT_BRANCH_CODE,
                                          enrollment_end_at=tomorrow.date())
    course = CourseFactory(semester=term, is_open=False,
                           is_correspondence=False,
                           capacity=0)
    assert course.enrollment_is_open
    student = StudentFactory(branch__code=Branches.SPB)
    assert student.status != StudentStatuses.EXPELLED
    assert student.has_perm("learning.enroll_in_course", course)
    # Enrollment is closed
    course.semester.enrollment_end_at = yesterday.date()
    assert not student.has_perm("learning.enroll_in_course", course)
    course.semester.enrollment_end_at = tomorrow.date()
    assert student.has_perm("learning.enroll_in_course", course)
    # Student was expelled
    student.status = StudentStatuses.EXPELLED
    assert not student.has_perm("learning.enroll_in_course", course)
    student.status = ''
    assert student.has_perm("learning.enroll_in_course", course)
    # Full course capacity
    course.capacity = 1
    course.learners_count = 1
    assert not student.has_perm("learning.enroll_in_course", course)
    course.learners_count = 0
    assert student.has_perm("learning.enroll_in_course", course)
    # Compare student and course cities
    course.branch = Branch.objects.filter(code=Branches.NSK).first()
    assert not student.has_perm("learning.enroll_in_course", course)
    course.is_correspondence = True
    assert student.has_perm("learning.enroll_in_course", course)


@pytest.mark.django_db
def test_leave_course():
    today = now_for_branch(Branches.SPB)
    yesterday = today - datetime.timedelta(days=1)
    future = today + datetime.timedelta(days=3)
    term = SemesterFactory.create_current(enrollment_end_at=future.date())
    enrollment = EnrollmentFactory(course__semester=term, course__is_open=False)
    course = enrollment.course
    student = enrollment.student
    assert course.enrollment_is_open
    assert student.has_perm("learning.leave_course", course)
    course.semester.enrollment_end_at = yesterday.date()
    assert not student.has_perm("learning.leave_course", course)
    course.semester.enrollment_end_at = future.date()
    assert student.has_perm("learning.leave_course", course)
    # Student couldn't leave abandoned course
    enrollment.is_deleted = True
    enrollment.save()
    student = User.objects.get(pk=student.pk)  # avoid cache
    assert not student.has_perm("learning.leave_course", course)


@pytest.mark.django_db
def test_enroll_in_course_by_invitation():
    today = now_for_branch(Branches.SPB)
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    term = SemesterFactory.create_current(for_branch=DEFAULT_BRANCH_CODE,
                                          enrollment_end_at=tomorrow.date())
    course = CourseFactory(semester=term, is_open=False,
                           is_correspondence=False,
                           capacity=0)
    assert course.enrollment_is_open
    student = StudentFactory(branch=course.branch)
    assert student.has_perm("learning.enroll_in_course", course)
    course_invitation = CourseInvitationFactory(course=course)
    assert student.has_perm("learning.enroll_in_course_by_invitation",
                            course_invitation)
    # Invitation activity depends on semester settings.
    # Also this condition checked internally in `learning.enroll_in_course`
    # predicate
    course.semester.enrollment_end_at = yesterday.date()
    course.semester.save()
    assert not course.enrollment_is_open
    assert not student.has_perm("learning.enroll_in_course_by_invitation",
                                course_invitation)
