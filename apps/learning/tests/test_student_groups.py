import pytest

from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.urls import reverse
from courses.models import CourseBranch, CourseTeacher, StudentGroupTypes
from courses.tests.factories import AssignmentFactory, CourseFactory, SemesterFactory
from learning.models import Enrollment, StudentAssignment, StudentGroup
from learning.settings import Branches, GradeTypes
from learning.tests.factories import (
    AssignmentCommentFactory, CourseInvitationFactory, EnrollmentFactory,
    StudentAssignmentFactory, StudentGroupAssigneeFactory
)
from users.tests.factories import (
    CuratorFactory, InvitedStudentFactory, StudentFactory, StudentProfileFactory,
    TeacherFactory
)


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
def test_auto_assign_teacher_to_student_assignment():
    student = StudentFactory()
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    student_assignment = StudentAssignmentFactory(assignment__course=course,
                                                  student=student)
    comment1 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=teacher)
    student_assignment.refresh_from_db()
    assert student_assignment.assignee is None
    assert student_assignment.trigger_auto_assign is True
    enrollment = Enrollment.objects.get(student=comment1.student_assignment.student)
    course_teacher = CourseTeacher.objects.get(course=course)
    StudentGroupAssigneeFactory(student_group=enrollment.student_group,
                                assignee=course_teacher)
    comment2 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=student)
    student_assignment.refresh_from_db()
    assert student_assignment.trigger_auto_assign is False
    assert student_assignment.assignee == course_teacher
    enrollment.is_deleted = True
    enrollment.save()
    student_assignment.trigger_auto_assign = True
    student_assignment.assignee = None
    student_assignment.save()
    comment3 = AssignmentCommentFactory(student_assignment=student_assignment,
                                        author=student)
