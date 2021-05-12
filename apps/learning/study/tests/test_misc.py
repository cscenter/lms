import datetime

import pytest
import pytz
from bs4 import BeautifulSoup

from django.utils import formats, timezone
from django.utils.encoding import smart_bytes
from django.utils.timezone import now

from auth.mixins import PermissionRequiredMixin
from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.tests.factories import AssignmentFactory, CourseFactory, SemesterFactory
from courses.utils import get_current_term_pair
from learning.permissions import ViewOwnStudentAssignments
from learning.services import CourseRole, course_access_role, get_student_profile
from learning.settings import Branches, GradeTypes, StudentStatuses
from learning.tests.factories import *
from learning.tests.factories import EnrollmentFactory, StudentAssignmentFactory
from projects.constants import ProjectTypes
from projects.tests.factories import (
    ProjectFactory, ProjectStudentFactory, ReportingPeriodFactory
)
from users.tests.factories import *
from users.tests.factories import StudentFactory, StudentProfileFactory


@pytest.mark.django_db
def test_access_student_assignment_teacher(client, assert_login_redirect):
    """
    Redirects course teacher to the appropriate teaching/ section.
    """
    teacher = TeacherFactory()
    other_teacher = TeacherFactory()
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    course = CourseFactory(main_branch__code=Branches.SPB, teachers=[teacher],
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
    course = CourseFactory(main_branch__code=Branches.SPB, teachers=[teacher],
                           semester=past_semester)
    student_assignment = StudentAssignmentFactory(assignment__course=course,
                                                  score=None)
    student_url = student_assignment.get_student_url()
    student = student_assignment.student
    # Course didn't failed by the student so he has full access to
    # the student assignment page.
    enrollment = Enrollment.objects.get(course=course, student=student)
    enrollment.grade = GradeTypes.GOOD
    enrollment.save()
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
    active_course = CourseFactory(main_branch__code=Branches.SPB,
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
    course = CourseFactory(main_branch__code=Branches.SPB, teachers=[teacher],
                           semester=past_semester)
    student_assignment = StudentAssignmentFactory(assignment__course=course,
                                                  assignment__maximum_score=80,
                                                  score=None)
    student_url = student_assignment.get_student_url()
    active_student = student_assignment.student
    assert active_student.is_active_student
    enrollment = Enrollment.objects.get(course=course, student=active_student)
    enrollment.grade = GradeTypes.UNSATISFACTORY
    enrollment.save()
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
def test_access_student_assignment_inactive_student(inactive_status, client,
                                                    settings):
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
    enrollment = Enrollment.objects.get(course=active_course, student=student)
    enrollment.grade = GradeTypes.GOOD
    enrollment.save()
    assert course_access_role(course=active_course, user=student) == CourseRole.STUDENT_REGULAR
    student_profile = get_student_profile(student, settings.SITE_ID)
    assert student_profile.branch == active_course.main_branch
    student_profile.status = inactive_status
    student_profile.save()
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
    enrollment = Enrollment.objects.get(course=past_course, student=student)
    enrollment.grade = GradeTypes.GOOD
    enrollment.save()
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
    student_profile = StudentProfileFactory(branch__code=Branches.SPB)
    client.login(student_profile.user)
    s = SemesterFactory.create_current()
    course_spb = CourseFactory(semester=s, main_branch__code=Branches.SPB)
    course_nsk = CourseFactory(semester=s, main_branch__code=Branches.NSK)
    response = client.get(reverse('study:course_list'))
    assert len(response.context_data['ongoing_rest']) == 1


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
def test_assignment_list_view_permissions(client, lms_resolver,
                                          assert_login_redirect):
    from auth.permissions import perm_registry
    url = reverse('study:assignment_list')
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    # TODO: test ViewOwnAssignments in test_permissions.py
    assert resolver.func.view_class.permission_required == ViewOwnStudentAssignments.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(url, method='get')
    teacher = TeacherFactory()
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_assignment_list_view(client):
    url = reverse('study:assignment_list')
    student = StudentFactory()
    s = SemesterFactory.create_current(for_branch=Branches.SPB)
    course = CourseFactory(semester=s)
    as1 = AssignmentFactory.create_batch(2, course=course)
    client.login(student)
    # no assignments yet
    response = client.get(url)
    assert len(response.context_data['assignment_list_open']) == 0
    assert len(response.context_data['assignment_list_archive']) == 0
    # enroll at course offering, assignments are shown
    EnrollmentFactory(student=student, course=course)
    response = client.get(url)
    assert len(response.context_data['assignment_list_open']) == 2
    assert len(response.context_data['assignment_list_archive']) == 0
    # add a few assignments, they should show up
    as2 = AssignmentFactory.create_batch(3, course=course)
    response = client.get(url)
    assert {(StudentAssignment.objects.get(assignment=a, student=student))
            for a in (as1 + as2)} == set(response.context_data['assignment_list_open'])
    assert len(as1) + len(as2) == len(response.context_data['assignment_list_open'])
    # Add few old assignments from current semester with expired deadline
    deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                   - datetime.timedelta(days=1))
    as_olds = AssignmentFactory.create_batch(2, course=course,
                                             deadline_at=deadline_at)
    response = client.get(url)
    for a in as1 + as2 + as_olds:
        assert smart_bytes(a.title) in response.content
    for a in as_olds:
        assert smart_bytes(a.title) in response.content
    assert {StudentAssignment.objects.get(assignment=a, student=student)
            for a in (as1 + as2)} == set(response.context_data['assignment_list_open'])
    assert {StudentAssignment.objects.get(assignment=a, student=student)
            for a in as_olds} == set(response.context_data['assignment_list_archive'])
    # Now add assignment from the past semester
    old_s = SemesterFactory.create_prev(s)
    old_co = CourseFactory.create(semester=old_s)
    as_past = AssignmentFactory(course=old_co)
    response = client.get(url)
    assert as_past not in response.context_data['assignment_list_archive']


@pytest.mark.django_db
def test_assignment_list_view_context_unenrolled_course(client):
    """
    Course assignments (even with future deadline) must be placed under archive
    if student left the course
    """
    url = reverse('study:assignment_list')
    student = StudentFactory()
    future = now() + datetime.timedelta(days=2)
    s = SemesterFactory.create_current(for_branch=Branches.SPB,
                                       enrollment_period__ends_on=future)
    # Create open co to pass enrollment limit
    course = CourseFactory(semester=s)
    as1 = AssignmentFactory.create_batch(2, course=course)
    client.login(student)
    # Enroll in course
    EnrollmentFactory(student=student, course=course)
    response = client.get(url)
    assert len(response.context_data['assignment_list_open']) == 2
    assert len(response.context_data['assignment_list_archive']) == 0
    # Now unenroll from the course
    form = {'course_pk': course.pk}
    response = client.post(course.get_unenroll_url(), form)
    response = client.get(url)
    assert len(response.context_data['assignment_list_open']) == 0
    assert len(response.context_data['assignment_list_archive']) == 2


@pytest.mark.django_db
@pytest.mark.parametrize("learner_factory", [StudentFactory, VolunteerFactory])
def test_deadline_l10n_on_student_assignment_list_page(learner_factory,
                                                       settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    FORMAT_DATE_PART = 'd E Y'
    FORMAT_TIME_PART = 'H:i'
    # This day will be in archive block (1 jan 2017 15:00 in UTC)
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    # Assignment will be created with the past date, but we will see it on
    # assignments page since course offering semester set to current
    current_term = SemesterFactory.create_current()
    assignment = AssignmentFactory(deadline_at=dt,
                                   time_zone=pytz.timezone('Europe/Moscow'),
                                   course__main_branch__code=Branches.SPB,
                                   course__semester_id=current_term.pk)
    student = learner_factory(branch__code=Branches.SPB)
    sa = StudentAssignmentFactory(assignment=assignment, student=student)
    client.login(student)
    url_learning_assignments = reverse('study:assignment_list')
    response = client.get(url_learning_assignments)
    html = BeautifulSoup(response.content, "html.parser")
    # Note: On this page used `naturalday` filter, so use passed datetime
    year_part = formats.date_format(assignment.deadline_at_local(),
                                    FORMAT_DATE_PART)
    assert year_part == "01 января 2017"
    time_part = formats.date_format(assignment.deadline_at_local(),
                                    FORMAT_TIME_PART)
    assert time_part == "18:00"
    assert any(year_part in s.text and time_part in s.text for s in
               html.find_all('div', {'class': 'assignment-date'}))
    # Test `upcoming` block
    now_year = get_current_term_pair(branch_spb.get_timezone()).year
    dt = dt.replace(year=now_year + 1, month=2, hour=14)
    assignment.deadline_at = dt
    assignment.save()
    year_part = formats.date_format(assignment.deadline_at_local(),
                                    FORMAT_DATE_PART)
    assert year_part == "01 февраля {}".format(now_year + 1)
    time_part = formats.date_format(assignment.deadline_at_local(),
                                    FORMAT_TIME_PART)
    assert time_part == "17:00"
    response = client.get(url_learning_assignments)
    html = BeautifulSoup(response.content, "html.parser")
    assert any(year_part in s.text and time_part in s.text for s in
               html.find_all('div', {'class': 'assignment-date'}))
    # Deadlines depends on authenticated user timezone
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    assignment_nsk = AssignmentFactory(deadline_at=dt,
                                       course__main_branch=branch_nsk,
                                       course__semester=current_term)
    StudentAssignmentFactory(assignment=assignment_nsk, student=student)
    client.login(student)
    response = client.get(url_learning_assignments)
    assert response.context_data["tz_override"] == branch_spb.get_timezone()
    year_part = formats.date_format(assignment_nsk.deadline_at_local(),
                                    FORMAT_DATE_PART)
    assert year_part == "01 января 2017"
    time_part = formats.date_format(
        assignment_nsk.deadline_at_local(tz=branch_spb.get_timezone()),
        FORMAT_TIME_PART)
    assert time_part == "18:00"
    html = BeautifulSoup(response.content, "html.parser")
    assert any(year_part in s.text and time_part in s.text for s in
               html.find_all('div', {'class': 'assignment-date'}))
    # Users without learner permission role has no access to the page
    user = UserFactory()
    client.login(user)
    response = client.get(url_learning_assignments)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("inactive_status", StudentStatuses.inactive_statuses)
def test_course_list_student_with_inactive_status(inactive_status, client):
    inactive_student = StudentFactory(student_profile__status=inactive_status)
    client.login(inactive_student)
    url = reverse('study:course_list')
    response = client.get(url)
    assert response.status_code == 403
    active_student = StudentFactory()
    client.login(active_student)
    response = client.get(url)
    assert response.status_code == 200
