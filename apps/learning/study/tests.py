import datetime

import pytest

from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.tests.factories import *
from courses.tests.factories import SemesterFactory, CourseFactory
from learning.permissions import course_access_role, CourseRole
from learning.services import EnrollmentService
from learning.settings import GradeTypes, StudentStatuses, Branches
from learning.tests.factories import *
from projects.constants import ProjectTypes
from projects.models import ReportingPeriodKey
from projects.tests.factories import ReportingPeriodFactory, \
    ProjectStudentFactory, ProjectFactory
from users.tests.factories import *
from users.tests.factories import StudentFactory


@pytest.mark.django_db
def test_access_student_assignment_teacher(client, assert_login_redirect):
    """
    Redirects course teacher to the appropriate teaching/ section.
    """
    teacher = TeacherFactory()
    other_teacher = TeacherFactory()
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    course = CourseFactory(branch__code=Branches.SPB, teachers=[teacher],
                           semester=past_semester)
    enrollment = EnrollmentFactory(course=course,
                                   grade=GradeTypes.UNSATISFACTORY)
    student_assignment = StudentAssignmentFactory(assignment__course=course,
                                                  score=None)
    client.login(teacher)
    student_url = student_assignment.get_student_url()
    response = client.get(student_url)
    assert response.status_code == 302
    assert response.url == student_assignment.get_teacher_url()
    client.login(other_teacher)
    response = client.get(student_url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_access_student_assignment_regular_student(client):
    teacher = TeacherFactory()
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    course = CourseFactory(branch__code=Branches.SPB, teachers=[teacher],
                           semester=past_semester)
    student_assignment = StudentAssignmentFactory(assignment__course=course,
                                                  score=None)
    student_url = student_assignment.get_student_url()
    student = student_assignment.student
    # Course didn't failed by the student so he has full access to
    # the student assignment page.
    enrollment = EnrollmentFactory(course=course, student=student,
                                   grade=GradeTypes.GOOD)
    assert course_access_role(course=course, user=student) == CourseRole.STUDENT_REGULAR
    client.login(student)
    response = client.get(student_url)
    assert response.status_code == 200
    # Access student assignment by student who wasn't enrolled in
    student_other = StudentFactory()
    assert course_access_role(course=course, user=student_other) == CourseRole.NO_ROLE
    client.login(student_other)
    assert student_other.is_active_student
    response = client.get(student_url)
    assert response.status_code == 403
    # Test access for the active course
    current_semester = SemesterFactory.create_current()
    active_course = CourseFactory(branch__code=Branches.SPB,
                                  semester=current_semester)
    EnrollmentFactory(course=active_course, student=student,
                      grade=GradeTypes.NOT_GRADED)
    new_assignment = AssignmentFactory(course=active_course)
    new_student_assignment = StudentAssignment.objects.get(assignment=new_assignment)
    assert course_access_role(course=active_course, user=student) == CourseRole.STUDENT_REGULAR
    client.login(student)
    response = client.get(new_student_assignment.get_student_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_access_student_assignment_failed_course(client):
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    teacher = TeacherFactory()
    course = CourseFactory(branch__code=Branches.SPB, teachers=[teacher],
                           semester=past_semester)
    student_assignment = StudentAssignmentFactory(assignment__course=course,
                                                  assignment__maximum_score=80,
                                                  score=None)
    student_url = student_assignment.get_student_url()
    active_student = student_assignment.student
    assert active_student.is_active_student
    enrollment = EnrollmentFactory(course=course, student=active_student,
                                   grade=GradeTypes.UNSATISFACTORY)
    assert course_access_role(course=course, user=active_student) == CourseRole.STUDENT_RESTRICT
    # Student failed the course and has no positive grade on target assignment
    client.login(active_student)
    response = client.get(student_url)
    assert response.status_code == 403
    # Now add some comment history from the course teacher.
    AssignmentCommentFactory(student_assignment=student_assignment, author=teacher)
    response = client.get(student_url)
    # Access denied since only student comment could be treated as `submission`
    assert response.status_code == 403
    AssignmentCommentFactory(student_assignment=student_assignment, author=active_student)
    response = client.get(student_url)
    assert response.status_code == 200
    # Remove all comments and test access if student has any mark on assignment
    AssignmentComment.published.all().delete()
    response = client.get(student_url)
    assert response.status_code == 403
    student_assignment.score = 10
    student_assignment.save()
    response = client.get(student_url)
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("inactive_status", StudentStatuses.inactive_statuses)
def test_access_student_assignment_inactive_student(inactive_status, client):
    """
    Inactive student could see student assignment only if he has any
    submission or score, no matter course was failed/passed/still active
    """
    current_semester = SemesterFactory.create_current()
    active_course = CourseFactory(semester=current_semester)
    student_assignment = StudentAssignmentFactory(assignment__course=active_course,
                                                  assignment__maximum_score=80,
                                                  score=None)
    student = student_assignment.student
    EnrollmentFactory(course=active_course, student=student, grade=GradeTypes.GOOD)
    assert course_access_role(course=active_course, user=student) == CourseRole.STUDENT_REGULAR
    student.status = inactive_status
    student.save()
    assert course_access_role(course=active_course, user=student) == CourseRole.STUDENT_RESTRICT
    client.login(student)
    student_url = student_assignment.get_student_url()
    response = client.get(student_url)
    assert response.status_code == 403
    # Add `submission` from the student
    AssignmentCommentFactory(student_assignment=student_assignment, author=student)
    response = client.get(student_url)
    assert response.status_code == 200
    # The same for the past course
    past_semester = SemesterFactory.create_prev(current_semester)
    past_course = CourseFactory(semester=past_semester)
    student_assignment = StudentAssignmentFactory(
        student=student,
        assignment__course=past_course,
        assignment__maximum_score=80,
        score=None)
    student_url = student_assignment.get_student_url()
    EnrollmentFactory(course=past_course, student=student, grade=GradeTypes.GOOD)
    assert course_access_role(course=past_course, user=student) == CourseRole.STUDENT_RESTRICT
    response = client.get(student_url)
    assert response.status_code == 403
    student_assignment.score = 10
    student_assignment.save()
    assert course_access_role(course=past_course, user=student) == CourseRole.STUDENT_RESTRICT
    response = client.get(student_assignment.get_student_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_course_list(client, settings):
    student = StudentFactory(branch__code=Branches.SPB)
    client.login(student)
    s = SemesterFactory.create_current()
    course_spb = CourseFactory(semester=s, branch__code=Branches.SPB)
    course_nsk = CourseFactory(semester=s, branch__code=Branches.NSK)
    response = client.get(reverse('study:course_list'))
    assert len(response.context['ongoing_rest']) == 1


@pytest.mark.django_db
def test_projects_on_assignment_list_page(client):
    url = reverse("study:assignment_list")
    branch_spb = BranchFactory(code=Branches.SPB)
    current_term = SemesterFactory.create_current()
    student = StudentFactory(branch=branch_spb)
    sa = StudentAssignmentFactory(assignment__course__semester=current_term,
                                  student=student)
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
    assert "reporting_periods" in response.context_data
    assert not response.context_data["reporting_periods"]
    # Assign project to the student and add reporting period
    start_on = current_term.starts_at.date()
    end_on = start_on + datetime.timedelta(days=3)
    rp_all = ReportingPeriodFactory(term=current_term,
                                    start_on=start_on,
                                    end_on=end_on,
                                    project_type=None)
    project = ProjectFactory(branch=branch_spb,
                             semester=current_term,
                             project_type=ProjectTypes.practice)
    ps = ProjectStudentFactory(student=student, project=project)
    ProjectStudentFactory(project=project)  # another random student
    response = client.get(url)
    assert response.status_code == 200
    periods = response.context_data["reporting_periods"]
    assert len(periods) == 1
    assert ps in periods
    assert len(periods[ps]) == 1
    assert rp_all in periods[ps]
    # Make sure projects from the prev term is not listed
    prev_term = SemesterFactory.create_prev(current_term)
    ps_old = ProjectStudentFactory(student=student,
                                   project__branch=branch_spb,
                                   project__semester=prev_term)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context_data["reporting_periods"]) == 1
    # Add another reporting period
    rp_practice = ReportingPeriodFactory(term=current_term,
                                         start_on=end_on + datetime.timedelta(days=1),
                                         end_on=end_on + datetime.timedelta(days=3),
                                         project_type=project.project_type)
    response = client.get(url)
    assert response.status_code == 200
    periods = response.context_data["reporting_periods"]
    assert len(periods) == 1
    assert len(periods[ps]) == 2


@pytest.mark.django_db
def test_student_assignment_execution_time_form(client, assert_redirect):
    """
    Execution time form is unavailable until student get score on assignment
    """
    term = SemesterFactory.create_current()
    assignment = AssignmentFactory(course__semester=term, maximum_score=10)
    student = StudentFactory()
    EnrollmentService.enroll(student, assignment.course)
    sa = StudentAssignment.objects.get(assignment=assignment, student=student)
    assert sa.execution_time is None
    update_url = reverse('study:student_assignment_execution_time_update',
                         args=[sa.pk])
    client.login(student)
    form_data = {'execution_time': '2:45'}
    response = client.post(update_url, form_data)
    assert response.status_code == 403
    sa.score = 4
    sa.save()
    response = client.post(update_url, form_data)
    assert_redirect(response, sa.get_student_url())
