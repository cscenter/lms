import pytest
from django.utils.encoding import smart_bytes

from courses.factories import SemesterFactory, CourseNewsFactory, \
    CourseTeacherFactory, CourseFactory, MetaCourseFactory, AssignmentFactory
from courses.models import CourseNews
from learning.factories import EnrollmentFactory
from learning.settings import GradeTypes
from users.factories import StudentCenterFactory, TeacherCenterFactory

# TODO: тест для видимости таб из под разных ролей. (прятать табу во вьюхе, если нет содержимого)


@pytest.mark.django_db
def test_course_news_tab_permissions(client):
    current_semester = SemesterFactory.create_current()
    prev_term = SemesterFactory.create_prev(current_semester)
    news: CourseNews = CourseNewsFactory(course__city_id='spb',
                                         course__semester=current_semester)
    co = news.course
    news_prev: CourseNews = CourseNewsFactory(course__city_id='spb',
                                              course__meta_course=co.meta_course,
                                              course__semester=prev_term)
    co_prev = news_prev.course
    response = client.get(co.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    # By default student can't see the news until enroll in the course
    student_spb = StudentCenterFactory(city_id='spb')
    client.login(student_spb)
    response = client.get(co.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    e_current = EnrollmentFactory(course=co, student=student_spb)
    response = client.get(co.get_absolute_url())
    assert "news" in response.context['course_tabs']
    # Prev courses should be successfully passed to see the news
    e_prev = EnrollmentFactory(course=co_prev, student=student_spb)
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    e_prev.grade = GradeTypes.GOOD
    e_prev.save()
    response = client.get(co_prev.get_absolute_url())
    assert "news" in response.context['course_tabs']
    # Teacher from the same course can view news from other offerings
    teacher = TeacherCenterFactory()
    client.login(teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    response = client.get(co.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    CourseTeacherFactory(course=co_prev, teacher=teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "news" in response.context['course_tabs']
    response = client.get(co.get_absolute_url())
    assert "news" in response.context['course_tabs']
    co_other = CourseFactory(semester=current_semester)
    response = client.get(co_other.get_absolute_url())
    assert "news" not in response.context['course_tabs']


@pytest.mark.django_db
def test_course_assignments_tab_permissions(client):
    current_semester = SemesterFactory.create_current()
    prev_term = SemesterFactory.create_prev(current_semester)
    meta_course = MetaCourseFactory()
    a = AssignmentFactory(course__semester=prev_term,
                          course__meta_course=meta_course)
    co_prev = a.course
    co = CourseFactory(meta_course=meta_course,
                       semester=current_semester)
    teacher = TeacherCenterFactory()
    CourseTeacherFactory(teacher=teacher, course=co)
    # Unauthenticated user can't see tab at all
    response = client.get(co_prev.get_absolute_url())
    assert "assignments" not in response.context['course_tabs']
    # Teacher can see links to assignments from other course sessions
    client.login(teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "assignments" in response.context['course_tabs']
    assert smart_bytes(a.get_teacher_url()) in response.content
    student = StudentCenterFactory()
    client.login(student)
    response = client.get(co_prev.get_absolute_url())
    assert "assignments" in response.context['course_tabs']
    tab = response.context['course_tabs']['assignments']
    assert len(tab.tab_panel.context["items"]) == 1
    assert smart_bytes(a.get_teacher_url()) not in response.content
