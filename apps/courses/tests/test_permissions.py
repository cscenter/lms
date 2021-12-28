import pytest

from auth.mixins import PermissionRequiredMixin
from core.utils import instance_memoize
from courses.constants import MaterialVisibilityTypes
from courses.models import CourseTeacher
from courses.permissions import (
    CreateAssignment, DeleteAssignment, DeleteAssignmentAttachment, EditAssignment,
    CreateCourseClass, DeleteCourseClass, EditCourseClass, EditCourseDescription,
    ViewCourseClassMaterials, ViewCourseInternalDescription
)
from courses.tests.factories import (
    AssignmentAttachmentFactory, AssignmentFactory, CourseClassFactory, CourseFactory,
    CourseNewsFactory, CourseTeacherFactory
)
from learning.permissions import CreateCourseNews, DeleteCourseNews, EditCourseNews
from learning.settings import GradeTypes, StudentStatuses
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


@pytest.mark.parametrize("permission_name", [
    EditCourseNews.name,
    DeleteCourseNews.name
])
@pytest.mark.django_db
def test_course_news_edit_delete_permissions(client, permission_name):
    user = UserFactory()
    student = StudentFactory()
    invited_student = InvitedStudentFactory()
    curator = CuratorFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    news = CourseNewsFactory(course=course)

    assert curator.has_perm(permission_name)
    assert teacher.has_perm(permission_name, news)
    assert not spectator.has_perm(permission_name, news)
    assert not user.has_perm(permission_name, news)
    assert not student.has_perm(permission_name, news)
    assert not invited_student.has_perm(permission_name, news)
    assert not teacher_other.has_perm(permission_name, news)

@pytest.mark.django_db
def test_course_news_create_permission(client):
    permission_name = CreateCourseNews.name
    user = UserFactory()
    student = StudentFactory()
    curator = CuratorFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    invited_student = InvitedStudentFactory()
    assert curator.has_perm(permission_name)
    assert teacher.has_perm(permission_name, course)
    assert not spectator.has_perm(permission_name, course)
    assert not user.has_perm(permission_name, course)
    assert not student.has_perm(permission_name, course)
    assert not invited_student.has_perm(permission_name, course)
    assert not teacher_other.has_perm(permission_name, course)


@pytest.mark.django_db
def test_permission_create_course_class(client):
    user = UserFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    curator = CuratorFactory()
    student = StudentFactory()

    course = CourseFactory()
    co_other = CourseFactory()

    assert not user.has_perm(CreateCourseClass.name, course)
    assert not teacher.has_perm(CreateCourseClass.name, course)
    assert not student.has_perm(CreateCourseClass.name, course)
    assert curator.has_perm(CreateCourseClass.name, course)

    CourseTeacherFactory(course=co_other, teacher=teacher)
    CourseTeacherFactory(course=co_other, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)

    assert teacher.has_perm(CreateCourseClass.name, co_other)
    assert not spectator.has_perm(CreateCourseClass.name, co_other)
    assert not teacher_other.has_perm(CreateCourseClass.name, co_other)
    assert not teacher.has_perm(CreateCourseClass.name, course)


@pytest.mark.django_db
def test_permission_edit_course_class(client, lms_resolver):
    user = UserFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    curator = CuratorFactory()
    student = StudentFactory()
    course_class = CourseClassFactory()
    cc_other = CourseClassFactory()

    url = course_class.get_update_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == EditCourseClass.name

    assert not user.has_perm(EditCourseClass.name, course_class)
    assert not teacher.has_perm(EditCourseClass.name, course_class)
    assert not student.has_perm(EditCourseClass.name, course_class)
    assert curator.has_perm(EditCourseClass.name, course_class)

    CourseTeacherFactory(course=cc_other.course, teacher=teacher)
    CourseTeacherFactory(course=cc_other.course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    assert teacher.has_perm(EditCourseClass.name, cc_other)
    assert not spectator.has_perm(EditCourseClass.name, cc_other)
    assert not teacher_other.has_perm(EditCourseClass.name, cc_other)
    assert not teacher.has_perm(EditCourseClass.name, course_class)


@pytest.mark.django_db
def test_permission_delete_course_class(client, lms_resolver):
    user = UserFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    curator = CuratorFactory()
    student = StudentFactory()
    course_class = CourseClassFactory()
    cc_other = CourseClassFactory()

    url = course_class.get_delete_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == DeleteCourseClass.name

    assert not user.has_perm(DeleteCourseClass.name, course_class)
    assert not teacher.has_perm(DeleteCourseClass.name, course_class)
    assert not student.has_perm(DeleteCourseClass.name, course_class)
    assert curator.has_perm(DeleteCourseClass.name, course_class)

    CourseTeacherFactory(course=cc_other.course, teacher=teacher)
    CourseTeacherFactory(course=cc_other.course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    assert teacher.has_perm(DeleteCourseClass.name, cc_other)
    assert not spectator.has_perm(DeleteCourseClass.name, cc_other)
    assert not teacher_other.has_perm(DeleteCourseClass.name, cc_other)
    assert not teacher.has_perm(DeleteCourseClass.name, course_class)


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
    teacher, course_teacher, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[course_teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    course_class = CourseClassFactory(
        course=course,
        materials_visibility=MaterialVisibilityTypes.PUBLIC)
    assert teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    assert spectator.has_perm(ViewCourseClassMaterials.name, course_class)
    assert course_teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.PARTICIPANTS
    instance_memoize.delete_cache(teacher)
    instance_memoize.delete_cache(course_teacher)
    assert teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    assert spectator.has_perm(ViewCourseClassMaterials.name, course_class)
    assert course_teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    course_class.materials_visibility = MaterialVisibilityTypes.COURSE_PARTICIPANTS
    instance_memoize.delete_cache(teacher)
    instance_memoize.delete_cache(course_teacher)
    assert not teacher.has_perm(ViewCourseClassMaterials.name, course_class)
    assert spectator.has_perm(ViewCourseClassMaterials.name, course_class)
    assert course_teacher.has_perm(ViewCourseClassMaterials.name, course_class)


@pytest.mark.django_db
def test_view_course_internal_description():
    permission_name = ViewCourseInternalDescription.name
    curator = CuratorFactory()
    teacher1, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher1])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    assert curator.has_perm(permission_name)
    assert curator.has_perm(permission_name, course)
    assert teacher1.has_perm(permission_name, course)
    assert spectator.has_perm(permission_name, course)
    assert not teacher1.has_perm(permission_name)
    assert not teacher_other.has_perm(permission_name, course)
    assert not teacher_other.has_perm(permission_name)
    enrollment1 = EnrollmentFactory(course=course, grade=GradeTypes.GOOD)
    student = enrollment1.student_profile.user
    assert not student.has_perm(permission_name)
    assert student.has_perm(permission_name, course)
    # Failed the course
    enrollment1.grade = GradeTypes.UNSATISFACTORY
    enrollment1.save()
    instance_memoize.delete_cache(student)
    assert not student.has_perm(permission_name, course)
    # Inactive profile
    enrollment1.grade = GradeTypes.GOOD
    enrollment1.save()
    instance_memoize.delete_cache(student)
    assert student.has_perm(permission_name, course)
    enrollment1.student_profile.status = StudentStatuses.EXPELLED
    enrollment1.student_profile.save()
    instance_memoize.delete_cache(student)
    assert not student.has_perm(permission_name, course)
    enrollment2 = EnrollmentFactory(grade=GradeTypes.GOOD)
    student2 = enrollment2.student_profile.user
    assert not student2.has_perm(permission_name)
    assert not student2.has_perm(permission_name, course)


@pytest.mark.django_db
def test_permission_edit_course_description(client):
    permission_name = EditCourseDescription.name
    user = UserFactory()
    student = StudentFactory()
    curator = CuratorFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    invited_student = InvitedStudentFactory()
    assert curator.has_perm(permission_name)
    assert teacher.has_perm(permission_name, course)
    assert not spectator.has_perm(permission_name, course)
    assert not user.has_perm(permission_name, course)
    assert not student.has_perm(permission_name, course)
    assert not invited_student.has_perm(permission_name, course)
    assert not teacher_other.has_perm(permission_name, course)

