import pytest

from courses.models import Course
from courses.tests.factories import CourseFactory, SemesterFactory
from learning.permissions import course_access_role, CourseRole, \
    has_master_degree
from learning.settings import StudentStatuses, GradeTypes
from learning.tests.factories import EnrollmentFactory
from users.constants import AcademicRoles
from users.models import ExtendedAnonymousUser, User
from users.tests.factories import CuratorFactory, TeacherCenterFactory, \
    StudentFactory, StudentCenterFactory


def delete_enrollment_cache(user: User, course: Course):
    cache_attr_name = user.ENROLLMENT_CACHE_KEY.format(course.pk)
    if hasattr(user, cache_attr_name):
        delattr(user, cache_attr_name)


@pytest.mark.django_db
def test_user_permissions():
    """
    Tests properties based on groups:
        * is_student
        * is_volunteer
        * is_graduate
        * is_teacher
    """
    user = User(username="foo", email="foo@localhost.ru")
    user.save()
    assert not user.is_student
    assert not user.is_volunteer
    assert not user.is_teacher
    assert not user.is_graduate
    user = User(username="bar", email="bar@localhost.ru")
    user.save()
    user.add_group(AcademicRoles.STUDENT)
    assert user.is_student
    assert not user.is_volunteer
    assert not user.is_teacher
    assert not user.is_graduate
    user = User(username="baz", email="baz@localhost.ru")
    user.save()
    user.add_group(AcademicRoles.STUDENT)
    user.add_group(AcademicRoles.TEACHER)
    assert user.is_student
    assert not user.is_volunteer
    assert user.is_teacher
    assert not user.is_graduate
    user = User(username="baq", email="baq@localhost.ru")
    user.save()
    user.add_group(AcademicRoles.STUDENT)
    user.add_group(AcademicRoles.TEACHER)
    user.add_group(AcademicRoles.GRADUATE_CENTER)
    assert user.is_student
    assert not user.is_volunteer
    assert user.is_teacher
    assert user.is_graduate
    user = User(username="zoo", email="zoo@localhost.ru")
    user.save()
    user.add_group(AcademicRoles.STUDENT)
    user.add_group(AcademicRoles.TEACHER)
    user.add_group(AcademicRoles.GRADUATE_CENTER)
    user.add_group(AcademicRoles.VOLUNTEER)
    assert user.is_student
    assert user.is_volunteer
    assert user.is_teacher
    assert user.is_graduate


@pytest.mark.django_db
def test_anonymous_user_permissions(client):
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert not request_user.is_authenticated
    assert not request_user.is_student
    assert not request_user.is_volunteer
    assert not has_master_degree(request_user)
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_interviewer


@pytest.mark.django_db
def test_request_user_permissions(client):
    # Active student
    student = StudentCenterFactory(status='')
    client.login(student)
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert request_user.is_authenticated
    assert request_user.is_student
    assert not request_user.is_volunteer
    assert request_user.is_active_student
    assert not has_master_degree(request_user)
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_interviewer
    # Expelled student
    student.status = StudentStatuses.EXPELLED
    student.save()
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert request_user.is_authenticated
    assert request_user.is_student
    assert not request_user.is_volunteer
    assert not request_user.is_active_student
    assert not has_master_degree(request_user)
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_interviewer


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
    teacher = TeacherCenterFactory()
    teacher_other = TeacherCenterFactory()
    course = CourseFactory(teachers=[teacher])
    role = course_access_role(course=course, user=teacher)
    assert role == CourseRole.TEACHER
    role = course_access_role(course=course, user=teacher_other)
    assert role == CourseRole.NO_ROLE
    # Teacher for the same meta course has access to all readings
    meta_course = course.meta_course
    teacher2 = TeacherCenterFactory()
    course2 = CourseFactory(meta_course=meta_course, teachers=[teacher2])
    role = course_access_role(course=course2, user=teacher2)
    assert role == CourseRole.TEACHER
    # Make sure student `expelled` status doesn't affect on teacher role
    teacher2.status = StudentStatuses.EXPELLED
    teacher2.save()
    role = course_access_role(course=course2, user=teacher2)
    assert role == CourseRole.TEACHER
    # Now make sure that teacher role is prevailed on any student role
    teacher2.add_group(AcademicRoles.STUDENT)
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
