import pytest

from core.utils import instance_memoize
from courses.constants import MaterialVisibilityTypes
from courses.models import CourseTeacher
from courses.permissions import (
    CreateAssignment, EditAssignment, EditCourseClass, ViewCourseClassMaterials, DeleteAssignment,
    DeleteAssignmentAttachment
)
from courses.tests.factories import (
    AssignmentFactory, CourseClassFactory, CourseFactory, CourseTeacherFactory, AssignmentAttachmentFactory
)
from learning.settings import GradeTypes
from learning.tests.factories import EnrollmentFactory
from users.models import User
from users.tests.factories import (
    CuratorFactory, InvitedStudentFactory, StudentFactory, TeacherFactory, UserFactory,
    VolunteerFactory
)

# FIXME: test ViewOwnAssignment


@pytest.mark.django_db
def test_permission_create_course_assignment(client):
    """
    Curators and actual teachers have permissions to create course assignment
    """
    permission_name = CreateAssignment.name
    teacher, spectator = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher])
    curator = CuratorFactory()
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    user = UserFactory()
    student = StudentFactory()
    invited_student = InvitedStudentFactory()
    teacher_other = TeacherFactory()
    assert curator.has_perm(permission_name)
    assert teacher.has_perm(permission_name, course)
    assert not spectator.has_perm(permission_name, course)
    assert not user.has_perm(permission_name, course)
    assert not student.has_perm(permission_name, course)
    assert not invited_student.has_perm(permission_name, course)
    assert not teacher_other.has_perm(permission_name, course)


@pytest.mark.django_db
def test_permission_edit_course_assignment(client):
    permission_name = EditAssignment.name
    user = UserFactory()
    student = StudentFactory()
    curator = CuratorFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    invited_student = InvitedStudentFactory()
    assignment = AssignmentFactory(course=course)
    assert curator.has_perm(permission_name)
    assert teacher.has_perm(permission_name, assignment)
    assert not spectator.has_perm(permission_name, assignment)
    assert not user.has_perm(permission_name, assignment)
    assert not student.has_perm(permission_name, assignment)
    assert not invited_student.has_perm(permission_name, assignment)
    assert not teacher_other.has_perm(permission_name, assignment)


@pytest.mark.django_db
def test_permission_delete_course_assignment(client):
    permission_name = DeleteAssignment.name
    user = UserFactory()
    student = StudentFactory()
    curator = CuratorFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    invited_student = InvitedStudentFactory()
    assignment = AssignmentFactory(course=course)
    assert curator.has_perm(permission_name)
    assert teacher.has_perm(permission_name, assignment)
    assert not spectator.has_perm(permission_name, assignment)
    assert not user.has_perm(permission_name, assignment)
    assert not student.has_perm(permission_name, assignment)
    assert not invited_student.has_perm(permission_name, assignment)
    assert not teacher_other.has_perm(permission_name, assignment)


@pytest.mark.django_db
def test_permission_delete_assignment_attachment(client):
    permission_name = DeleteAssignmentAttachment.name
    user = UserFactory()
    student = StudentFactory()
    curator = CuratorFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    invited_student = InvitedStudentFactory()
    attachment = AssignmentAttachmentFactory(assignment__course=course)
    assert curator.has_perm(permission_name)
    assert teacher.has_perm(permission_name, attachment)
    assert not spectator.has_perm(permission_name, attachment)
    assert not user.has_perm(permission_name, attachment)
    assert not student.has_perm(permission_name, attachment)
    assert not invited_student.has_perm(permission_name, attachment)
    assert not teacher_other.has_perm(permission_name, attachment)


@pytest.mark.django_db
def test_permission_edit_course_class(client):
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
def test_course_class_materials_visibility_default(client):
    """Authenticated user can see only public course class materials"""
    user = UserFactory()
    course = CourseFactory()
    course_class = CourseClassFactory(
        course=course,
        materials_visibility=MaterialVisibilityTypes.PUBLIC)
    assert user.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.PARTICIPANTS
    instance_memoize.delete_cache(user)
    assert not user.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.COURSE_PARTICIPANTS
    instance_memoize.delete_cache(user)
    assert not user.has_perm(ViewCourseClassMaterials.name, course_class)


@pytest.mark.django_db
@pytest.mark.parametrize("participant_factory", [StudentFactory,
                                                 InvitedStudentFactory,
                                                 VolunteerFactory])
def test_course_class_materials_visibility_students(participant_factory,
                                                    client):
    course = CourseFactory()
    course_class = CourseClassFactory(
        course=course,
        materials_visibility=MaterialVisibilityTypes.PUBLIC)
    participant: User = participant_factory()
    assert participant.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.PARTICIPANTS
    instance_memoize.delete_cache(participant)
    assert participant.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.COURSE_PARTICIPANTS
    instance_memoize.delete_cache(participant)
    assert not participant.has_perm(ViewCourseClassMaterials.name, course_class)
    EnrollmentFactory(student=participant, course=course, grade=GradeTypes.GOOD)
    instance_memoize.delete_cache(participant)
    assert participant.has_perm(ViewCourseClassMaterials.name, course_class)


@pytest.mark.django_db
def test_course_class_materials_visibility_teachers(client):
    teacher = TeacherFactory()
    course_teacher = TeacherFactory()
    course = CourseFactory(teachers=[course_teacher])
    course_class = CourseClassFactory(
        course=course,
        materials_visibility=MaterialVisibilityTypes.PUBLIC)
    assert teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    assert course_teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.PARTICIPANTS
    instance_memoize.delete_cache(teacher)
    instance_memoize.delete_cache(course_teacher)
    assert teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    assert course_teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.COURSE_PARTICIPANTS
    instance_memoize.delete_cache(teacher)
    instance_memoize.delete_cache(course_teacher)
    assert not teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    assert course_teacher.has_perm(ViewCourseClassMaterials.name, course_class)

