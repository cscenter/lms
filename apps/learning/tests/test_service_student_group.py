import pytest

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.tests.factories import BranchFactory, SiteFactory
from core.tests.settings import ANOTHER_DOMAIN, ANOTHER_DOMAIN_ID, TEST_DOMAIN
from courses.models import CourseBranch, CourseGroupModes, StudentGroupTypes
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from learning.models import StudentAssignment, StudentGroup, StudentGroupAssignee
from learning.services import EnrollmentService, StudentGroupService
from learning.services.student_group_service import (
    GroupEnrollmentKeyError, StudentGroupError
)
from learning.tests.factories import (
    EnrollmentFactory, InvitationFactory, StudentGroupAssigneeFactory,
    StudentGroupFactory
)
from users.models import StudentTypes
from users.tests.factories import StudentFactory, StudentProfileFactory


@pytest.mark.django_db
def test_student_group_service_create_no_groups_mode(settings):
    course = CourseFactory(group_mode=CourseGroupModes.NO_GROUPS)
    with pytest.raises(StudentGroupError) as e:
        StudentGroupService.create(course, group_type=StudentGroupTypes.BRANCH,
                                   branch=course.main_branch)


@pytest.mark.django_db
def test_student_group_service_create_with_branch_mode(settings):
    branch1, branch2 = BranchFactory.create_batch(2)
    course = CourseFactory(main_branch=branch1,
                           group_mode=CourseGroupModes.BRANCH)
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course, group_type=StudentGroupTypes.BRANCH)
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course, group_type=StudentGroupTypes.BRANCH, branch=branch2)
    assert e.value.code == 'malformed'
    student_group1 = StudentGroupService.create(course, group_type=StudentGroupTypes.BRANCH, branch=branch1)
    assert list(StudentGroup.objects.all()) == [student_group1]
    StudentGroupService.create(course, group_type=StudentGroupTypes.BRANCH, branch=branch1)  # repeat
    assert StudentGroup.objects.count() == 1


@pytest.mark.django_db
def test_student_group_service_create_manual_group(settings):
    course1, course2 = CourseFactory.create_batch(2, group_mode=CourseGroupModes.MANUAL)
    # Empty group name
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course1, group_type=StudentGroupTypes.MANUAL)
    assert e.value.code == 'required'
    student_group = StudentGroupService.create(course1, group_type=StudentGroupTypes.MANUAL, name='test')
    assert list(StudentGroup.objects.all()) == [student_group]
    # Non unique student group name for the course
    with pytest.raises(ValidationError) as e:
        StudentGroupService.create(course1, group_type=StudentGroupTypes.MANUAL, name='test')
    StudentGroupService.create(course2, group_type=StudentGroupTypes.MANUAL, name='test')


@pytest.mark.django_db
def test_student_group_service_resolve():
    branch_spb = BranchFactory(code="spb")
    branch_nsk = BranchFactory(code="nsk")
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=CourseGroupModes.BRANCH)
    assert StudentGroup.objects.filter(course=course).count() == 1
    student_spb_group = StudentGroup.objects.get(course=course)
    assert student_spb_group.type == StudentGroupTypes.BRANCH
    student_spb_profile = StudentProfileFactory(branch=branch_spb)
    student_nsk_profile = StudentProfileFactory(branch=branch_nsk)
    assert StudentGroupService.resolve(course, student_profile=student_spb_profile) == student_spb_group
    assert StudentGroupService.resolve(course, student_profile=student_spb_profile,
                                       enrollment_key='wrong_key') == student_spb_group
    sg_other = StudentGroupFactory(course=course)
    found = StudentGroupService.resolve(
        course, student_profile=student_spb_profile,
        enrollment_key=sg_other.enrollment_key)
    assert found == student_spb_group
    student_spb_group = StudentGroupService.resolve(course, student_profile=student_nsk_profile)
    assert student_spb_group.type == StudentGroupTypes.SYSTEM
    course.group_mode = CourseGroupModes.MANUAL
    assert StudentGroupService.resolve(
        course, student_profile=student_spb_profile,
        enrollment_key=sg_other.enrollment_key) == sg_other
    with pytest.raises(GroupEnrollmentKeyError):
        StudentGroupService.resolve(course, student_profile=student_spb_profile, enrollment_key='wrong')
    student_spb_group = StudentGroupService.resolve(course, student_profile=student_spb_profile, enrollment_key=None)
    assert student_spb_group.type == StudentGroupTypes.SYSTEM
    course.group_mode = 'unknown'
    with pytest.raises(StudentGroupError):
        StudentGroupService.resolve(course, student_profile=student_spb_profile, enrollment_key='wrong')


@pytest.mark.django_db
def test_student_group_service_resolve_invitation():
    branch_spb = BranchFactory(code="spb")
    student_spb_profile = StudentProfileFactory(branch=branch_spb)
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=CourseGroupModes.BRANCH)
    student_spb_group = StudentGroup.objects.get(course=course)
    assert student_spb_group.type == StudentGroupTypes.BRANCH
    invitation = InvitationFactory(semester=course.semester, courses=[course])
    resolved_group = StudentGroupService.resolve(course, student_profile=student_spb_profile,
                                                 invitation=invitation)
    assert resolved_group == student_spb_group
    assert not StudentGroup.objects.filter(course=course, type=StudentGroupTypes.INVITE).exists()
    # Manually create student group associated with an invitation
    invitation_group = StudentGroupService.create(course, group_type=StudentGroupTypes.INVITE,
                                                  invitation=invitation)
    resolved_group = StudentGroupService.resolve(course, student_profile=student_spb_profile,
                                                 invitation=invitation)
    # Regular students still go to the group-branch
    assert resolved_group == student_spb_group
    student_spb_profile.type = StudentTypes.INVITED
    resolved_group = StudentGroupService.resolve(course, student_profile=student_spb_profile,
                                                 invitation=invitation)
    assert resolved_group == invitation_group
    # Test creating invitation group on the fly
    invitation_group.delete()
    course.group_mode = CourseGroupModes.INVITE_AND_BRANCH
    resolved_group = StudentGroupService.resolve(course, student_profile=student_spb_profile,
                                                 invitation=invitation)
    assert resolved_group.type == StudentGroupTypes.INVITE
    assert resolved_group.invitation == invitation
    resolved_group2 = StudentGroupService.resolve(course, student_profile=student_spb_profile,
                                                  invitation=invitation)
    assert resolved_group == resolved_group2


@pytest.mark.django_db
def test_student_group_service_get_choices(settings):
    branch_spb = BranchFactory(code="spb")
    course = CourseFactory(main_branch=branch_spb,
                           group_mode=StudentGroupTypes.BRANCH)
    assert StudentGroup.objects.filter(course=course).count() == 1
    groups = list(StudentGroup.objects.filter(course=course).order_by('name', 'pk'))
    choices = StudentGroupService.get_choices(course)
    assert len(choices) == 1
    assert choices[0] == (groups[0].pk, groups[0].name)
    branch_nsk = BranchFactory(code="nsk",
                               site=SiteFactory(domain=ANOTHER_DOMAIN))
    assert branch_nsk.site_id == ANOTHER_DOMAIN_ID
    CourseBranch(course=course, branch=branch_nsk).save()
    assert StudentGroup.objects.filter(course=course).count() == 2
    sg1, sg2 = list(StudentGroup.objects.filter(course=course).order_by('pk'))
    choices = StudentGroupService.get_choices(course)
    assert (sg1.pk, f"{sg1.name} [{TEST_DOMAIN}]") in choices
    assert (sg2.pk, f"{sg2.name} [{ANOTHER_DOMAIN}]") in choices


@pytest.mark.django_db
def test_student_group_service_get_enrollments():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)
    enrollments = EnrollmentFactory.create_batch(3, course=course, student_group=student_group1)
    enrollment1, enrollment2, enrollment3 = enrollments
    in_group = StudentGroupService.get_enrollments(student_group2)
    assert len(in_group) == 0
    EnrollmentFactory(course=course, student_group=student_group2)
    in_group = StudentGroupService.get_enrollments(student_group1)
    assert len(in_group) == 3
    EnrollmentService.leave(enrollment1, reason_leave='cause')
    in_group = StudentGroupService.get_enrollments(student_group1)
    assert len(in_group) == 2
    assert enrollment2 in in_group
    assert enrollment3 in in_group


@pytest.mark.django_db
def test_student_group_service_get_groups_available_for_student_transfer():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2, student_group3 = StudentGroupFactory.create_batch(3, course=course)
    student_group_another_course = StudentGroupFactory(course__group_mode=StudentGroupTypes.MANUAL)
    student_groups = StudentGroupService.get_groups_for_safe_transfer(student_group1)
    assert len(student_groups) == 2
    assert student_group2 in student_groups
    assert student_group3 in student_groups
    student_groups = StudentGroupService.get_groups_for_safe_transfer(student_group_another_course)
    assert len(student_groups) == 0
    assignment1, assignment2 = AssignmentFactory.create_batch(2, course=course)
    # No assignment visibility restrictions
    student_groups = StudentGroupService.get_groups_for_safe_transfer(student_group1)
    assert len(student_groups) == 2
    # Assignment 1 is not available for student group 1 but we could transfer
    # students from group1 to group2 or group3 by adding missing assignments
    assignment1.restricted_to.add(student_group2, student_group3)
    student_groups = StudentGroupService.get_groups_for_safe_transfer(student_group1)
    assert len(student_groups) == 2
    # Assignment 1 is not available for student group 3 and we must delete
    # personal assignment on transferring student from group1 to group3.
    # Make sure this transition is prohibited.
    assignment1.restricted_to.clear()
    assignment1.restricted_to.add(student_group1, student_group2)
    student_groups = StudentGroupService.get_groups_for_safe_transfer(student_group1)
    assert len(student_groups) == 1
    assert student_group2 in student_groups
    # Assignment 1 is available for group1/group2, Assignment 2 is restricted to group2
    assignment2.restricted_to.add(student_group2)
    student_groups = StudentGroupService.get_groups_for_safe_transfer(student_group1)
    assert len(student_groups) == 1
    assert student_group2 in student_groups
    assignment2.restricted_to.add(student_group3)
    student_groups = StudentGroupService.get_groups_for_safe_transfer(student_group1)
    assert len(student_groups) == 1
    assert student_group2 in student_groups
    assignment2.restricted_to.clear()
    assignment2.restricted_to.add(student_group1)
    student_groups = StudentGroupService.get_groups_for_safe_transfer(student_group1)
    assert len(student_groups) == 0


@pytest.mark.django_db
def test_student_group_service_transfer_students():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2, student_group3, student_group4 = StudentGroupFactory.create_batch(4, course=course)
    assignment1, assignment2 = AssignmentFactory.create_batch(2, course=course)
    assignment1.restricted_to.add(student_group2)
    assignment2.restricted_to.add(student_group3)
    enrollment = EnrollmentFactory(course=course, student_group=student_group2)
    assert StudentAssignment.objects.filter(assignment=assignment1, student=enrollment.student_profile.user).exists()
    assert not StudentAssignment.objects.filter(assignment=assignment2, student=enrollment.student_profile.user).exists()
    enrollment1 = EnrollmentFactory(course=course, student_group=student_group2)
    student_profile1 = enrollment1.student_profile
    assert StudentAssignment.objects.filter(assignment=assignment1, student=student_profile1.user).exists()
    # Assignment 1 is available for group 2, assignment 2 for group 3
    with pytest.raises(ValidationError) as e:
        StudentGroupService.transfer_students(source=student_group2,
                                              destination=student_group3,
                                              enrollments=[enrollment1.pk])
    assert e.value.code == 'unsafe'
    # Assignment 1 is available both for group 2 and group 3, assignment 2 for group 3 only
    assignment1.restricted_to.add(student_group3)
    with pytest.raises(ValidationError) as e:
        StudentGroupService.transfer_students(source=student_group3,
                                              destination=student_group2,
                                              enrollments=[enrollment1.pk])
    assert e.value.code == 'unsafe'
    assert StudentAssignment.objects.filter(assignment=assignment1, student=student_profile1.user).exists()
    assert not StudentAssignment.objects.filter(assignment=assignment2, student=student_profile1.user).exists()
    StudentGroupService.transfer_students(source=student_group2,
                                          destination=student_group3,
                                          enrollments=[enrollment1.pk])
    enrollment1.refresh_from_db()
    assert enrollment1.student_group == student_group3
    assert StudentAssignment.objects.filter(assignment=assignment1, student=student_profile1.user).exists()
    # Make sure missing personal assignments were created on transfer group2 -> group3
    assert StudentAssignment.objects.filter(assignment=assignment2, student=student_profile1.user).exists()
    # But another student from group 2 keeps untouched
    assert StudentAssignment.objects.filter(assignment=assignment1, student=enrollment.student_profile.user).exists()
    assert not StudentAssignment.objects.filter(assignment=assignment2, student=enrollment.student_profile.user).exists()
    enrollment2 = EnrollmentFactory(course=course, student_group=student_group1)
    student_profile2 = enrollment2.student_profile
    # Student 2 is not in a source group.
    with pytest.raises(IntegrityError) as e:
        StudentGroupService.transfer_students(source=student_group4,
                                              destination=student_group2,
                                              enrollments=[enrollment2.pk])
    enrollment2.refresh_from_db()
    assert enrollment2.student_group == student_group1
    StudentGroupService.transfer_students(source=student_group1,
                                          destination=student_group4,
                                          enrollments=[enrollment2.pk])
    assert not StudentAssignment.objects.filter(assignment=assignment2, student=student_profile2.user).exists()
    assert not StudentAssignment.objects.filter(assignment=assignment1, student=student_profile2.user).exists()
    StudentGroupService.transfer_students(source=student_group4,
                                          destination=student_group2,
                                          enrollments=[enrollment2.pk])
    enrollment2.refresh_from_db()
    assert enrollment2.student_group == student_group2
    assert StudentAssignment.objects.filter(assignment=assignment1, student=student_profile2.user).exists()
    assert not StudentAssignment.objects.filter(assignment=assignment2, student=student_profile2.user).exists()


@pytest.mark.django_db
def test_student_group_service_transfer_students_unsafe():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)
    assignment1, assignment2, assignment3 = AssignmentFactory.create_batch(3, course=course)
    assignment1.restricted_to.add(student_group1)
    assignment2.restricted_to.add(student_group2)
    enrollment1 = EnrollmentFactory(course=course, student_group=student_group1)
    enrollment2 = EnrollmentFactory(course=course, student_group=student_group2)
    assert StudentAssignment.objects.filter(assignment=assignment1, student=enrollment1.student_profile.user).exists()
    assert not StudentAssignment.objects.filter(assignment=assignment2,
                                                student=enrollment1.student_profile.user).exists()
    # Other courses
    course_other = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group_other = StudentGroupFactory(course=course_other)
    assignment_other = AssignmentFactory(course=course_other)
    enrollment_other = EnrollmentFactory(course=course_other, student_group=student_group_other)
    assert StudentAssignment.objects.filter(assignment=assignment_other,
                                            student=enrollment_other.student_profile.user).exists()
    # Student transfer group1 -> group2 is unsafe since we must delete
    # personal assignment from group1
    with pytest.raises(ValidationError) as e:
        StudentGroupService.transfer_students(source=student_group1,
                                              destination=student_group2,
                                              enrollments=[enrollment1.pk])
    assert e.value.code == 'unsafe'
    assert enrollment1.student_group == student_group1
    StudentGroupService.transfer_students(source=student_group1,
                                          destination=student_group2,
                                          enrollments=[enrollment1.pk],
                                          safe=False)
    enrollment1.refresh_from_db()
    assert enrollment1.student_group == student_group2
    assert not StudentAssignment.objects.filter(assignment=assignment1, student=enrollment1.student_profile.user).exists()
    assert StudentAssignment.objects.filter(assignment=assignment2, student=enrollment1.student_profile.user).exists()
    assert StudentAssignment.objects.filter(assignment=assignment3, student=enrollment1.student_profile.user).exists()
    assert not StudentAssignment.objects.filter(assignment=assignment1, student=enrollment2.student_profile.user).exists()
    assert StudentAssignment.objects.filter(assignment=assignment2, student=enrollment2.student_profile.user).exists()
    assert StudentAssignment.objects.filter(assignment=assignment3, student=enrollment2.student_profile.user).exists()
    enrollment2.refresh_from_db()
    assert enrollment2.student_group == student_group2
    assert StudentAssignment.objects.filter(assignment=assignment_other, student=enrollment_other.student_profile.user).exists()
    # Student1 not in a group1 anymore
    with pytest.raises(IntegrityError) as e:
        StudentGroupService.transfer_students(source=student_group1,
                                              destination=student_group2,
                                              enrollments=[enrollment1.pk],
                                              safe=False)


@pytest.mark.django_db
def test_student_group_service_available_assignments():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1, student_group2, student_group3 = StudentGroupFactory.create_batch(3, course=course)
    assignment1, assignment2, assignment3 = AssignmentFactory.create_batch(3, course=course)
    assert len(StudentGroupService.available_assignments(student_group1)) == 3
    assignment1.restricted_to.add(student_group1)
    assert len(StudentGroupService.available_assignments(student_group1)) == 3
    assert len(StudentGroupService.available_assignments(student_group2)) == 2
    assert assignment2 in StudentGroupService.available_assignments(student_group2)
    assert assignment3 in StudentGroupService.available_assignments(student_group2)
    assignment2.restricted_to.add(student_group2)
    assert len(StudentGroupService.available_assignments(student_group3)) == 1
    assert assignment3 in StudentGroupService.available_assignments(student_group3)


@pytest.mark.django_db
def test_student_group_add_assignees(settings):
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1 = StudentGroupFactory(course=course)
    student_group2 = StudentGroupFactory()
    course_teacher1, course_teacher2 = CourseTeacherFactory.create_batch(2, course=course)
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assigned = StudentGroupAssignee.objects.get()
    assert assigned.assignee_id == course_teacher1.pk
    # Student group does not match course of the course teacher
    with pytest.raises(ValidationError):
        StudentGroupService.add_assignees(student_group2, teachers=[course_teacher1])
    # Can't add the same course teacher twice
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assignment = AssignmentFactory(course=course)
    # Customize list of responsible teachers for the assignment
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)
    assert StudentGroupAssignee.objects.count() == 2
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)


@pytest.mark.django_db
def test_student_group_update_assignees(settings):
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    student_group1 = StudentGroupFactory(course=course)
    course_teacher1, course_teacher2, course_teacher3 = CourseTeacherFactory.create_batch(3, course=course)
    student_group2 = StudentGroupFactory()
    course_teacher2_1 = CourseTeacherFactory(course=student_group2.course)
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assigned = StudentGroupAssignee.objects.get()
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.count() == 1
    assert StudentGroupAssignee.objects.get() == assigned
    StudentGroupService.update_assignees(student_group2, teachers=[course_teacher2_1])
    assert StudentGroupAssignee.objects.count() == 2
    assert assigned in StudentGroupAssignee.objects.all()
    # Add the second course teacher and try to update list of responsible
    # teachers again
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher2])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 1
    assert StudentGroupAssignee.objects.count() == 2
    # Assign responsible teachers for the assignment
    assignment = AssignmentFactory(course=course)
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher2], assignment=assignment)
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    assert StudentGroupService.get_assignees(student_group1) == [course_teacher1]
    assert StudentGroupService.get_assignees(student_group1, assignment=assignment) == [course_teacher2]
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1], assignment=assignment)
    assert StudentGroupService.get_assignees(student_group1, assignment=assignment) == [course_teacher1]
    # Reset list of teachers
    StudentGroupService.update_assignees(student_group1, teachers=[], assignment=assignment)
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 1
    assert StudentGroupAssignee.objects.filter(student_group=student_group1, assignment=assignment).count() == 0
    assert assigned in StudentGroupAssignee.objects.filter(student_group=student_group1).all()
    # Add and delete at the same time
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher3])
    StudentGroupService.update_assignees(student_group1, teachers=[course_teacher1, course_teacher2])
    assert StudentGroupAssignee.objects.filter(student_group=student_group1).count() == 2
    assigned_teachers = [sga.assignee for sga in StudentGroupAssignee.objects.filter(student_group=student_group1)]
    assert course_teacher1 in assigned_teachers
    assert course_teacher2 in assigned_teachers
    assert StudentGroupAssignee.objects.filter(student_group=student_group2).count() == 1


@pytest.mark.django_db
def test_student_group_get_assignees():
    course = CourseFactory(group_mode=StudentGroupTypes.MANUAL)
    assignment1 = AssignmentFactory(course=course)
    assignment2 = AssignmentFactory(course=course)
    assert StudentGroup.objects.filter(course=course).count() == 0
    student_group1 = StudentGroupFactory(course=course)
    student_group2 = StudentGroupFactory(course=course)
    sga1 = StudentGroupAssigneeFactory(student_group=student_group1)
    sga2 = StudentGroupAssigneeFactory(student_group=student_group1)
    sga3 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment1)
    sga4 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment1)
    sga5 = StudentGroupAssigneeFactory(student_group=student_group1,
                                       assignment=assignment2)
    assert StudentGroupService.get_assignees(student_group2) == []
    assignees = StudentGroupService.get_assignees(student_group1)
    assert len(assignees) == 2
    assert sga1.assignee in assignees
    assert sga2.assignee in assignees
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment1)
    assert len(assignees) == 2
    assert sga3.assignee in assignees
    assert sga4.assignee in assignees
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga5.assignee == assignees[0]
    sga6 = StudentGroupAssigneeFactory(student_group=student_group2,
                                       assignment=assignment2)
    assignees = StudentGroupService.get_assignees(student_group1,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga5.assignee == assignees[0]
    assignees = StudentGroupService.get_assignees(student_group2,
                                                  assignment=assignment2)
    assert len(assignees) == 1
    assert sga6.assignee == assignees[0]
