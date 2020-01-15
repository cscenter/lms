import pytest

from courses.permissions import EditCourseClass
from courses.tests.factories import CourseClassFactory, CourseTeacherFactory
from users.tests.factories import UserFactory, TeacherFactory, CuratorFactory, \
    StudentFactory


@pytest.mark.django_db
def test_can_edit_course_class(client):
    user = UserFactory()
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    curator = CuratorFactory()
    student = StudentFactory()
    course_class = CourseClassFactory()
    cc_other = CourseClassFactory()
    assert not user.has_perm(EditCourseClass.name, course_class)
    assert not teacher.has_perm(EditCourseClass.name, course_class)
    assert not student.has_perm(EditCourseClass.name, course_class)
    assert curator.has_perm(EditCourseClass.name, course_class)
    CourseTeacherFactory(course=cc_other.course, teacher=teacher)
    assert teacher.has_perm(EditCourseClass.name, cc_other)
    assert not teacher_other.has_perm(EditCourseClass.name, cc_other)
    assert not teacher.has_perm(EditCourseClass.name, course_class)
