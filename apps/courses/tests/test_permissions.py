import pytest

from courses.constants import MaterialVisibilityTypes
from courses.permissions import EditCourseClass, CreateAssignment, \
    EditAssignment, ViewCourseClassMaterials
from courses.tests.factories import CourseClassFactory, CourseTeacherFactory, \
    CourseFactory
from learning.settings import GradeTypes
from learning.tests.factories import EnrollmentFactory
from users.tests.factories import UserFactory, TeacherFactory, CuratorFactory, \
    StudentFactory, InvitedStudentFactory


@pytest.mark.django_db
@pytest.mark.parametrize("permission_name", [CreateAssignment.name,
                                             EditAssignment.name])
def test_can_create_course_assignment(permission_name, client):
    """
    Curators and actual teachers have permissions to create/edit assignment
    """
    teacher = TeacherFactory()
    curator = CuratorFactory()
    user = UserFactory()
    student = StudentFactory()
    invited_student = InvitedStudentFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    assert teacher.has_perm(permission_name, course)
    assert curator.has_perm(permission_name, course)
    assert not user.has_perm(permission_name, course)
    assert not student.has_perm(permission_name, course)
    assert not invited_student.has_perm(permission_name, course)
    assert not teacher_other.has_perm(permission_name, course)


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


@pytest.mark.django_db
def test_course_class_materials_visibility(client):
    user = UserFactory()
    student = StudentFactory()
    enrolled_student = StudentFactory()
    course = CourseFactory()
    EnrollmentFactory(student=enrolled_student, course=course,
                      grade=GradeTypes.GOOD)
    course_class = CourseClassFactory(
        course=course,
        materials_visibility=MaterialVisibilityTypes.PUBLIC)
    assert user.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.PARTICIPANTS
    assert not user.has_perm(ViewCourseClassMaterials.name, course_class)
    assert student.has_perm(ViewCourseClassMaterials.name, course_class)
    assert enrolled_student.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.COURSE_PARTICIPANTS
    assert not student.has_perm(ViewCourseClassMaterials.name, course_class)
    assert enrolled_student.has_perm(ViewCourseClassMaterials.name, course_class)


