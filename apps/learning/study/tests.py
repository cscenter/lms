import datetime

import pytest

from courses.tests.factories import *
from learning.permissions import course_access_role, CourseRole
from learning.settings import GradeTypes, StudentStatuses
from learning.tests.factories import *
from users.tests.factories import *


@pytest.mark.django_db
def test_access_student_assignment_curator(client, assert_login_redirect):
    """learning/assignments/<id>/ always visible to the curator"""
    teacher = TeacherCenterFactory()
    curator = CuratorFactory()
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    course = CourseFactory(city_id='spb', teachers=[teacher],
                           semester=past_semester)
    enrollment = EnrollmentFactory(course=course,
                                   grade=GradeTypes.UNSATISFACTORY)
    student_assignment = StudentAssignmentFactory(assignment__course=course,
                                                  score=None)
    client.login(curator)
    student_url = student_assignment.get_student_url()
    response = client.get(student_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_access_student_assignment_teacher(client, assert_login_redirect):
    """
    Redirects course teacher to the appropriate teaching/ section.
    """
    teacher = TeacherCenterFactory()
    other_teacher = TeacherCenterFactory()
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    course = CourseFactory(city_id='spb', teachers=[teacher],
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
    assert_login_redirect(student_url)


@pytest.mark.django_db
def test_access_student_assignment_regular_student(client, assert_login_redirect):
    teacher = TeacherCenterFactory()
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    course = CourseFactory(city_id='spb', teachers=[teacher],
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
    student_other = StudentCenterFactory()
    assert course_access_role(course=course, user=student_other) == CourseRole.NO_ROLE
    client.login(student_other)
    assert student_other.is_active_student
    assert_login_redirect(student_url)
    # Test access for the active course
    current_semester = SemesterFactory.create_current()
    active_course = CourseFactory(city_id='spb', semester=current_semester)
    EnrollmentFactory(course=active_course, student=student,
                      grade=GradeTypes.NOT_GRADED)
    new_assignment = AssignmentFactory(course=active_course)
    new_student_assignment = StudentAssignment.objects.get(assignment=new_assignment)
    assert course_access_role(course=active_course, user=student) == CourseRole.STUDENT_REGULAR
    client.login(student)
    response = client.get(new_student_assignment.get_student_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_access_student_assignment_failed_course(client, assert_login_redirect):
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    teacher = TeacherCenterFactory()
    course = CourseFactory(city_id='spb', teachers=[teacher],
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
    assert_login_redirect(student_url)
    # Now add some comment history from the course teacher.
    AssignmentCommentFactory(student_assignment=student_assignment, author=teacher)
    response = client.get(student_url)
    # Access denied since only student comment could be treated as `submission`
    assert response.status_code == 302
    AssignmentCommentFactory(student_assignment=student_assignment, author=active_student)
    response = client.get(student_url)
    assert response.status_code == 200
    # Remove all comments and test access if student has any mark on assignment
    AssignmentComment.objects.all().delete()
    response = client.get(student_url)
    assert response.status_code == 302
    student_assignment.score = 10
    student_assignment.save()
    response = client.get(student_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_access_student_assignment_expelled_student(client, assert_login_redirect):
    """
    Expelled student could see student assignment only if he has any
    submission or score, no matter course was failed/passed/still active
    """
    current_semester = SemesterFactory.create_current()
    active_course = CourseFactory(city_id='spb', semester=current_semester)
    student_assignment = StudentAssignmentFactory(assignment__course=active_course,
                                                  assignment__maximum_score=80,
                                                  score=None)
    student = student_assignment.student
    EnrollmentFactory(course=active_course, student=student, grade=GradeTypes.GOOD)
    assert course_access_role(course=active_course, user=student) == CourseRole.STUDENT_REGULAR
    student.status = StudentStatuses.EXPELLED
    student.save()
    assert course_access_role(course=active_course, user=student) == CourseRole.STUDENT_RESTRICT
    client.login(student)
    student_url = student_assignment.get_student_url()
    response = client.get(student_url)
    assert response.status_code == 302
    # Add `submission` from the student
    AssignmentCommentFactory(student_assignment=student_assignment, author=student)
    response = client.get(student_url)
    assert response.status_code == 200
    # The same for the past course
    past_semester = SemesterFactory.create_prev(current_semester)
    past_course = CourseFactory(city_id='spb', semester=past_semester)
    student_assignment = StudentAssignmentFactory(
        student=student,
        assignment__course=past_course,
        assignment__maximum_score=80,
        score=None)
    student_url = student_assignment.get_student_url()
    EnrollmentFactory(course=past_course, student=student, grade=GradeTypes.GOOD)
    assert course_access_role(course=past_course, user=student) == CourseRole.STUDENT_RESTRICT
    assert_login_redirect(student_url)
    student_assignment.score = 10
    student_assignment.save()
    assert course_access_role(course=past_course, user=student) == CourseRole.STUDENT_RESTRICT
    response = client.get(student_assignment.get_student_url())
    assert response.status_code == 200
