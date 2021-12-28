import pytest
from bs4 import BeautifulSoup

from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from auth.permissions import perm_registry
from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.urls import reverse
from courses.models import (
    CourseBranch, CourseGroupModes, CourseTeacher, StudentGroupTypes
)
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory, SemesterFactory
)
from learning.models import Enrollment, StudentAssignment, StudentGroup
from learning.permissions import DeleteStudentGroup, ViewStudentGroup
from learning.services import EnrollmentService, StudentGroupService
from learning.settings import Branches, GradeTypes
from learning.teaching.forms import StudentGroupForm
from learning.teaching.utils import get_student_groups_url
from learning.tests.factories import (
    CourseInvitationFactory, EnrollmentFactory, StudentGroupAssigneeFactory,
    StudentGroupFactory
)
from users.tests.factories import (
    CuratorFactory, InvitedStudentFactory, StudentFactory, StudentProfileFactory,
    TeacherFactory
)


@pytest.mark.django_db
def test_create_student_group_from_main_branch(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH)
    student_groups = StudentGroup.objects.filter(course=course).all()
    assert len(student_groups) == 1
    sg = student_groups[0]
    assert sg.branch_id == branch_spb.pk
    assert sg.type == StudentGroupTypes.BRANCH
    for lang, _ in settings.LANGUAGES:
        field_name = f"name_{lang}"
        assert getattr(sg, field_name) == getattr(branch_spb, field_name)


@pytest.mark.django_db
def test_upsert_student_group_from_additional_branch(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH)
    assert StudentGroup.objects.filter(course=course).count() == 1
    CourseBranch(course=course, branch=branch_nsk).save()
    groups = StudentGroup.objects.filter(course=course)
    assert len(groups) == 2
    sg1, sg2 = groups
    if sg1.branch != branch_spb:
        sg1, sg2 = sg2, sg1
    assert sg2.type == StudentGroupTypes.BRANCH
    assert sg2.branch_id is not None
    assert sg2.branch_id == branch_nsk.pk
    for lang, _ in settings.LANGUAGES:
        field_name = f"name_{lang}"
        assert getattr(sg2, field_name) == getattr(branch_nsk, field_name)
    assert {sg1.branch_id, sg2.branch_id} == {branch_spb.pk, branch_nsk.pk}
    # Remove course branch and add the new one
    course.branches.remove(branch_nsk)
    groups = StudentGroup.objects.filter(course=course)
    assert groups.count() == 2
    assert StudentGroupService.get_or_create_default_group(course) in groups
    branch = BranchFactory()
    CourseBranch(course=course, branch=branch).save()
    groups = StudentGroup.objects.filter(course=course)
    assert len(groups) == 3
    group_branches = [sg.branch for sg in groups]
    assert branch_spb in group_branches
    assert branch in group_branches


@pytest.mark.django_db
def test_student_group_resolving_on_enrollment(client):
    """
    Prevent enrollment ff it's impossible to resolve student group by
    student's root branch.
    """
    student_profile1 = StudentProfileFactory()
    student_profile2 = StudentProfileFactory(branch=BranchFactory())
    today = now_local(student_profile1.user.time_zone).date()
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=today)
    course = CourseFactory(main_branch=student_profile1.branch,
                           semester=current_semester)
    student_groups = StudentGroup.objects.filter(course=course).all()
    assert len(student_groups) == 1
    student_group = student_groups[0]
    enroll_url = course.get_enroll_url()
    form = {'course_pk': course.pk}
    client.login(student_profile1.user)
    response = client.post(enroll_url, form)
    assert response.status_code == 302
    enrollments = Enrollment.active.filter(student_profile=student_profile1,
                                           course=course).all()
    assert len(enrollments) == 1
    enrollment = enrollments[0]
    assert enrollment.student_group == student_group
    # No permission through public interface
    client.login(student_profile2.user)
    response = client.post(enroll_url, form)
    assert response.status_code == 403


@pytest.mark.django_db
def test_student_group_resolving_on_enrollment_admin(client, settings):
    """
    Admin interface doesn't check all the requirements to enroll student.
    If it's impossible to resolve student group - add student to the
    special group `Others`.
    """
    student, student2 = StudentFactory.create_batch(2, branch=BranchFactory())
    today = now_local(student.time_zone).date()
    current_semester = SemesterFactory.create_current(
        enrollment_period__ends_on=today)
    course = CourseFactory(main_branch=BranchFactory(),
                           semester=current_semester)
    post_data = {
        'course': course.pk,
        'student': student.pk,
        'student_profile': student.get_student_profile(settings.SITE_ID).pk,
        'grade': GradeTypes.NOT_GRADED
    }
    curator = CuratorFactory()
    client.login(curator)
    response = client.post(reverse('admin:learning_enrollment_add'), post_data)
    enrollments = Enrollment.active.filter(student=student, course=course)
    assert len(enrollments) == 1
    e = enrollments[0]
    assert e.student_group_id is not None
    assert e.student_group.name_en == 'Others'
    assert e.student_group.type == StudentGroupTypes.SYSTEM
    # Enroll the second student
    post_data['student'] = student2.pk
    post_data['student_profile'] = student2.get_student_profile().pk
    response = client.post(reverse('admin:learning_enrollment_add'), post_data)
    e2 = Enrollment.active.filter(student=student2, course=course)
    assert e2.exists()
    assert e2.get().student_group == e.student_group


@pytest.mark.django_db
def test_student_group_resolving_enrollment_by_invitation(settings, client):
    branch_spb = BranchFactory(code=Branches.SPB)
    invited = InvitedStudentFactory(branch=branch_spb)
    today = now_local(invited.time_zone).date()
    term = SemesterFactory.create_current(enrollment_period__ends_on=today)
    course = CourseFactory(main_branch=branch_spb, semester=term)
    student_groups = StudentGroup.objects.filter(course=course).all()
    assert len(student_groups) == 1
    student_group = student_groups[0]
    course_invitation = CourseInvitationFactory(course=course)
    enroll_url = course_invitation.get_absolute_url()
    client.login(invited)
    response = client.post(enroll_url, {})
    assert response.status_code == 302
    enrollments = Enrollment.active.filter(student=invited, course=course).all()
    assert len(enrollments) == 1
    enrollment = enrollments[0]
    assert enrollment.student_group == student_group


@pytest.mark.django_db
def test_assignment_restricted_to(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH,
                           branches=[branch_nsk])
    assert StudentGroup.objects.filter(course=course).count() == 2
    sg_spb, sg_nsk = StudentGroup.objects.filter(course=course).all()
    if sg_spb.branch != branch_spb:
        sg_spb, sg_nsk = sg_nsk, sg_spb
    student_profile_spb = StudentProfileFactory(branch=branch_spb)
    student_profile_nsk = StudentProfileFactory(branch=branch_nsk)
    EnrollmentFactory(course=course, student_profile=student_profile_spb,
                      student=student_profile_spb.user)
    EnrollmentFactory(course=course, student_profile=student_profile_nsk,
                      student=student_profile_nsk.user)
    a = AssignmentFactory(course=course, restricted_to=[sg_spb])
    student_assignments = StudentAssignment.objects.filter(assignment=a)
    assert len(student_assignments) == 1
    assert student_assignments[0].student == student_profile_spb.user


@pytest.mark.django_db
def test_view_student_group_list_permissions(client, lms_resolver):
    teacher = TeacherFactory()
    student = StudentFactory()
    course = CourseFactory(teachers=[teacher])
    url = get_student_groups_url(course)
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewStudentGroup.name
    assert resolver.func.view_class.permission_required in perm_registry
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_view_student_group_list_smoke(client, lms_resolver):
    teacher = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher],
                                  group_mode=CourseGroupModes.MANUAL)
    student_group1 = StudentGroupFactory(course=course)
    student_group2 = StudentGroupFactory(course=course)

    client.login(teacher)
    url = get_student_groups_url(course)
    response = client.get(url)
    assert smart_bytes(student_group1.name) in response.content
    assert smart_bytes(student_group2.name) in response.content


@pytest.mark.django_db
def test_view_student_group_detail_permissions(client, lms_resolver):
    teacher = TeacherFactory()
    student = StudentFactory()
    course = CourseFactory(teachers=[teacher])
    student_group = StudentGroupFactory(course=course)
    student_group_other = StudentGroupFactory()
    url = student_group.get_absolute_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewStudentGroup.name
    assert resolver.func.view_class.permission_required in perm_registry
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200
    # Student group PK is not associated with the course from friendly URL
    url = reverse("teaching:student_groups:detail", kwargs={
        "pk": student_group_other.pk,
        **course.url_kwargs
    })
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_view_student_group_detail_smoke(client):
    teacher = TeacherFactory()
    student1, student2 = StudentFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher], group_mode=CourseGroupModes.MANUAL)
    student_group1 = StudentGroupFactory(course=course)
    EnrollmentFactory(student=student1, course=course, student_group=student_group1)
    course_teacher = CourseTeacher.objects.filter(course=course).first()
    StudentGroupAssigneeFactory(assignee=course_teacher, student_group=student_group1)
    client.login(teacher)
    url = student_group1.get_absolute_url()
    response = client.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    assert student_group1.name in soup.find('h2').text
    assert smart_bytes(student1.last_name) in response.content
    assert smart_bytes(student2.last_name) not in response.content
    assert smart_bytes(teacher.last_name) in response.content


@pytest.mark.django_db
def test_view_student_group_delete(settings):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher], group_mode=CourseGroupModes.MANUAL)
    student_group = StudentGroupFactory(course=course)
    assert teacher.has_perm(DeleteStudentGroup.name, student_group)
    enrollment = EnrollmentFactory(course=course, student_group=student_group)
    EnrollmentService.leave(enrollment)
    assert Enrollment.active.filter(course=course).count() == 0
    assert Enrollment.objects.filter(course=course).count() == 1
    # Student must be moved to the default student group if student's group
    # was deleted after student left the course
    StudentGroupService.remove(student_group)
    enrollment.refresh_from_db()
    assert enrollment.student_group == StudentGroupService.get_or_create_default_group(course)
    # Re-enter the course
    student_group = StudentGroupService.resolve(course, enrollment.student, site=settings.SITE_ID)
    EnrollmentService.enroll(enrollment.student_profile, course, student_group=student_group)
    enrollment.refresh_from_db()
    assert Enrollment.active.filter(course=course).count() == 1
    default_sg = StudentGroup.objects.get(course=course, type=StudentGroupTypes.SYSTEM)
    assert enrollment.student_group == default_sg


@pytest.mark.django_db
def test_form_student_group_assignee_update_doesnt_propose_spectators(settings):
    teacher_1, teacher_2, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(group_mode=CourseGroupModes.MANUAL)
    ct_1 = CourseTeacherFactory(course=course, teacher=teacher_1,
                                roles=CourseTeacher.roles.lecturer)
    ct_2 = CourseTeacherFactory(course=course, teacher=teacher_2,
                                roles=CourseTeacher.roles.organizer)
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    sg_form = StudentGroupForm(course)
    possible_assignees = sg_form.fields['assignee'].queryset
    assert len(possible_assignees) == 2
    assert {ct_1, ct_2} == set(possible_assignees)
