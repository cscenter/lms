import pytest

from courses.constants import AssignmentStatus
from courses.models import Assignment
from courses.tests.factories import AssignmentFactory
from learning.models import Enrollment, StudentAssignment
from learning.settings import EnrollmentTypes, GradeTypes
from learning.tests.factories import EnrollmentFactory, StudentAssignmentFactory

@pytest.mark.django_db
def test_enrollment_can_submit_assignments_manager():
    EnrollmentFactory()
    EnrollmentFactory.can_not_submit_assignments()
    assert Enrollment.objects.all().count() == 4
    assert Enrollment.objects.can_submit_assignments().count() == 1
    
@pytest.mark.django_db
def test_student_assignment_can_be_submitted_manager():
    EnrollmentFactory()
    EnrollmentFactory(is_deleted=True)
    EnrollmentFactory.can_not_submit_assignments()
    assert Enrollment.objects.all().count() == 5
    for enrollment in Enrollment.objects.all():
        sa = AssignmentFactory(course=enrollment.course)
    assert Enrollment.objects.all().count() == 5
    assert StudentAssignment.objects.all().count() == 4
    deleted_enrollment = Enrollment.objects.get(is_deleted=True)
    deleted_student_assignment = StudentAssignmentFactory(assignment=Assignment.objects.get(course=deleted_enrollment.course), 
                             student=deleted_enrollment.student)
    assert StudentAssignment.objects.all().count() == 5
    assert StudentAssignment.objects.can_be_submitted().count() == 1
    sa = StudentAssignment.objects.exclude(
        pk__in=[*StudentAssignment.objects.can_be_submitted().values_list("pk", flat=True), 
                deleted_student_assignment.pk]).first()
    sa.status = AssignmentStatus.COMPLETED
    sa.save()
    assert StudentAssignment.objects.can_be_submitted().count() == 2
    sa.status = AssignmentStatus.NEED_FIXES
    sa.save()
    assert StudentAssignment.objects.can_be_submitted().count() == 2
    sa.status = AssignmentStatus.ON_CHECKING
    sa.save()
    assert StudentAssignment.objects.can_be_submitted().count() == 1
    deleted_student_assignment.status = AssignmentStatus.COMPLETED
    deleted_student_assignment.save()
    assert StudentAssignment.objects.can_be_submitted().count() == 2
