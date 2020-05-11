import pytest

from core.tests.factories import BranchFactory, SiteFactory
from core.timezone import now_local
from core.urls import reverse
from courses.models import StudentGroupTypes, CourseBranch
from courses.tests.factories import CourseFactory, AssignmentFactory, \
    SemesterFactory
from learning.models import StudentGroup, StudentAssignment, Enrollment
from learning.services import StudentGroupService
from learning.settings import Branches, GradeTypes
from learning.tests.factories import EnrollmentFactory, CourseInvitationFactory
from users.tests.factories import StudentFactory, CuratorFactory, \
    InvitedStudentFactory


@pytest.mark.django_db
def test_create_student_group_from_root_branch(settings):
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
    # Update by removing branch
    branch = BranchFactory()
    course.branches.remove(branch_nsk)
    CourseBranch(course=course, branch=branch).save()
    groups = StudentGroup.objects.filter(course=course)
    assert len(groups) == 2
    sg1, sg2 = groups
    if sg1.branch != branch_spb:
        sg1, sg2 = sg2, sg1
    assert sg1.branch == branch_spb
    assert sg2.branch == branch


@pytest.mark.django_db
def test_student_group_resolving_on_enrollment(client):
    """
    Prevent enrollment ff it's impossible to resolve student group by
    student's root branch.
    """
    student1 = StudentFactory()
    student2 = StudentFactory(branch=BranchFactory())
    today = now_local(student1.get_timezone()).date()
    current_semester = SemesterFactory.create_current(enrollment_end_at=today)
    course = CourseFactory(main_branch=student1.branch,
                           semester=current_semester)
    student_groups = StudentGroup.objects.filter(course=course).all()
    assert len(student_groups) == 1
    student_group = student_groups[0]
    enroll_url = course.get_enroll_url()
    form = {'course_pk': course.pk}
    client.login(student1)
    response = client.post(enroll_url, form)
    assert response.status_code == 302
    enrollments = Enrollment.active.filter(student=student1, course=course).all()
    assert len(enrollments) == 1
    enrollment = enrollments[0]
    assert enrollment.student_group == student_group
    # No permission through public interface
    client.login(student2)
    response = client.post(enroll_url, form)
    assert response.status_code == 403


@pytest.mark.django_db
def test_student_group_resolving_on_enrollment_admin(client):
    """
    Admin interface doesn't check all the requirements to enroll student.
    If it's impossible to resolve student group - add student to the
    special group `Others`.
    """
    student, student2 = StudentFactory.create_batch(2, branch=BranchFactory())
    today = now_local(student.get_timezone()).date()
    current_semester = SemesterFactory.create_current(enrollment_end_at=today)
    course = CourseFactory(main_branch=BranchFactory(),
                           semester=current_semester)
    post_data = {
        'course': course.pk,
        'student': student.pk,
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
    assert e.student_group.type == StudentGroupTypes.MANUAL
    # Enroll the second student
    post_data['student'] = student2.pk
    response = client.post(reverse('admin:learning_enrollment_add'), post_data)
    e2 = Enrollment.active.filter(student=student2, course=course)
    assert e2.exists()
    assert e2.get().student_group == e.student_group


@pytest.mark.django_db
def test_student_group_resolving_enrollment_by_invitation(settings, client):
    branch_spb = BranchFactory(code=Branches.SPB)
    invited = InvitedStudentFactory(branch=branch_spb)
    today = now_local(invited.get_timezone()).date()
    term = SemesterFactory.create_current(enrollment_end_at=today)
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
    student_spb = StudentFactory(branch=branch_spb)
    student_nsk = StudentFactory(branch=branch_nsk)
    EnrollmentFactory(course=course, student=student_spb)
    EnrollmentFactory(course=course, student=student_nsk)
    a = AssignmentFactory(course=course, restricted_to=[sg_spb])
    student_assignments = StudentAssignment.objects.filter(assignment=a)
    assert len(student_assignments) == 1
    assert student_assignments[0].student == student_spb


@pytest.mark.django_db
def test_student_group_service_get_choices(settings):
    branch_spb = BranchFactory(code=Branches.SPB)
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH)
    assert StudentGroup.objects.filter(course=course).count() == 1
    groups = list(StudentGroup.objects.filter(course=course).order_by('pk'))
    choices = StudentGroupService.get_choices(course)
    assert len(choices) == 1
    assert choices[0] == (str(groups[0].pk), groups[0].name)
    branch_nsk = BranchFactory(code=Branches.NSK,
                               site=SiteFactory(domain=settings.ANOTHER_DOMAIN))
    assert branch_nsk.site_id == settings.ANOTHER_DOMAIN_ID
    CourseBranch(course=course, branch=branch_nsk).save()
    assert StudentGroup.objects.filter(course=course).count() == 2
    sg1, sg2 = list(StudentGroup.objects.filter(course=course).order_by('pk'))
    choices = StudentGroupService.get_choices(course)
    assert choices[0] == (str(sg1.pk), f"{sg1.name} [{settings.TEST_DOMAIN}]")
    assert choices[1] == (str(sg2.pk), f"{sg2.name} [{settings.ANOTHER_DOMAIN}]")