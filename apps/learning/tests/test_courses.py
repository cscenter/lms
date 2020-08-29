import datetime

import pytest
import pytz

from core.tests.factories import BranchFactory
from courses.models import CourseBranch
from courses.tests.factories import CourseTeacherFactory, AssignmentFactory, \
    CourseFactory
from learning.settings import Branches
from users.tests.factories import TeacherFactory, StudentFactory


@pytest.mark.django_db
def test_course_detail_view_timezone(settings, client):
    """Test `tz_override` based on user role"""
    # 12 january 2017 23:59 (UTC)
    deadline_at = datetime.datetime(2017, 1, 12, 23, 59, 0, 0,
                                    tzinfo=pytz.UTC)
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    course_spb = CourseFactory(main_branch=branch_spb)
    assignment = AssignmentFactory(deadline_at=deadline_at,
                                   course=course_spb)
    teacher_nsk = TeacherFactory(branch=branch_nsk)
    student_spb = StudentFactory(branch=branch_spb)
    student_nsk = StudentFactory(branch=branch_nsk)
    # Anonymous user doesn't see tab
    assignments_tab_url = course_spb.get_url_for_tab("assignments")
    response = client.get(assignments_tab_url)
    assert response.status_code == 302
    # Show assignments in the timezone of the course if authenticated user
    # is not participated in a course as a teacher/student/etc and course
    # is available in one branch only
    for u in [student_spb, student_nsk, teacher_nsk]:
        client.login(u)
        response = client.get(assignments_tab_url)
        assert response.status_code == 200
        assert response.context_data["tz_override"] is None
    CourseBranch(course=course_spb, branch=branch_nsk).save()
    client.logout()
    # Any authenticated user (this teacher is not actual teacher of the course)
    client.login(teacher_nsk)
    response = client.get(assignments_tab_url)
    assert response.status_code == 200
    assert response.context_data["tz_override"] == branch_nsk.get_timezone()
    client.login(student_nsk)
    response = client.get(assignments_tab_url)
    assert response.status_code == 200
    assert response.context_data["tz_override"] == branch_nsk.get_timezone()
    client.login(student_spb)
    response = client.get(assignments_tab_url)
    assert response.status_code == 200
    assert response.context_data["tz_override"] == branch_spb.get_timezone()
    # Actual teacher of the course
    CourseTeacherFactory(course=course_spb, teacher=teacher_nsk)
    client.login(teacher_nsk)
    response = client.get(assignments_tab_url)
    assert response.status_code == 200
    assert response.context_data["tz_override"] is None
