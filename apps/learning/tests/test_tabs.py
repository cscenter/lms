import datetime

import pytest
from django.utils import timezone
from django.utils.encoding import smart_bytes

from courses.models import CourseNews, CourseReview
from courses.services import CourseService
from courses.tests.factories import SemesterFactory, CourseNewsFactory, \
    CourseTeacherFactory, CourseFactory, MetaCourseFactory, AssignmentFactory, \
    CourseReviewFactory
from learning.models import EnrollmentPeriod
from learning.settings import GradeTypes, Branches
from learning.tabs import CourseReviewsTab
from learning.tests.factories import EnrollmentFactory
from users.tests.factories import StudentFactory, TeacherFactory, \
    VolunteerFactory


# TODO: тест для видимости таб из под разных ролей. (прятать табу во вьюхе, если нет содержимого)


@pytest.mark.django_db
def test_course_news_tab_permissions(client):
    current_semester = SemesterFactory.create_current()
    prev_term = SemesterFactory.create_prev(current_semester)
    news: CourseNews = CourseNewsFactory(course__main_branch__code=Branches.SPB,
                                         course__semester=current_semester)
    course = news.course
    news_prev: CourseNews = CourseNewsFactory(course__main_branch__code=Branches.SPB,
                                              course__meta_course=course.meta_course,
                                              course__semester=prev_term)
    co_prev = news_prev.course
    response = client.get(course.get_absolute_url())
    assert response.status_code == 200
    # By default student can't see the news until enroll in the course
    student_spb = StudentFactory(branch__code=Branches.SPB)
    client.login(student_spb)
    response = client.get(course.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    e_current = EnrollmentFactory(course=course, student=student_spb)
    response = client.get(course.get_absolute_url())
    assert "news" in response.context['course_tabs']
    # To see the news for completed course student should successfully pass it.
    e_prev = EnrollmentFactory(course=co_prev, student=student_spb)
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    e_prev.grade = GradeTypes.GOOD
    e_prev.save()
    response = client.get(co_prev.get_absolute_url())
    assert "news" in response.context['course_tabs']
    # Teacher from the same course can view news from other offerings
    teacher = TeacherFactory()
    client.login(teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    response = client.get(course.get_absolute_url())
    assert "news" not in response.context['course_tabs']
    CourseTeacherFactory(course=co_prev, teacher=teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "news" in response.context['course_tabs']
    response = client.get(course.get_absolute_url())
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
    course = CourseFactory(meta_course=meta_course, semester=current_semester)
    teacher = TeacherFactory()
    CourseTeacherFactory(teacher=teacher, course=course)
    response = client.get(co_prev.get_absolute_url())
    assert response.status_code == 200
    # Teacher can see links to assignments from other course sessions
    client.login(teacher)
    response = client.get(co_prev.get_absolute_url())
    assert "assignments" in response.context['course_tabs']
    assert smart_bytes(a.get_teacher_url()) in response.content
    student = StudentFactory()
    client.login(student)
    response = client.get(co_prev.get_absolute_url())
    assert "assignments" in response.context['course_tabs']
    tab = response.context['course_tabs']['assignments']
    assert len(tab.tab_panel.context["items"]) == 1
    assert smart_bytes(a.get_teacher_url()) not in response.content


@pytest.mark.django_db
def test_course_reviews_tab_permissions(client, curator, settings):
    today = timezone.now()
    next_week = today + datetime.timedelta(weeks=1)
    yesterday = today - datetime.timedelta(days=1)
    current_term = SemesterFactory.create_current(
        enrollment_period__ends_on=next_week.date())
    prev_term = SemesterFactory.create_prev(current_term)
    course = CourseFactory(semester=current_term)
    prev_course = CourseFactory(semester=prev_term,
                                meta_course=course.meta_course)
    CourseReview(course=prev_course, text='Very good').save()
    assert course.enrollment_is_open
    student = StudentFactory()
    client.login(student)
    response = client.get(course.get_absolute_url())
    assert CourseReviewsTab.is_enabled(course, student)
    assert "reviews" in response.context['course_tabs']
    volunteer = VolunteerFactory()
    assert CourseReviewsTab.is_enabled(course, volunteer)
    assert CourseReviewsTab.is_enabled(course, curator)
    ep = EnrollmentPeriod.objects.get(semester=current_term,
                                      site_id=settings.SITE_ID)
    ep.ends_on = yesterday.date()
    ep.save()
    assert not course.enrollment_is_open
    assert not CourseReviewsTab.is_enabled(course, curator)


@pytest.mark.django_db
def test_get_course_reviews(settings):
    meta_course1, meta_course2 = MetaCourseFactory.create_batch(2)
    c1 = CourseFactory(meta_course=meta_course1, main_branch__code=Branches.SPB,
                       semester__year=2015)
    c2 = CourseFactory(meta_course=meta_course1, main_branch__code=Branches.SPB,
                       semester__year=2016)
    cr1 = CourseReviewFactory(course=c1)
    cr2 = CourseReviewFactory(course=c2)
    c3 = CourseFactory(meta_course=meta_course1, main_branch__code=Branches.NSK,
                       semester__year=2016)
    c4 = CourseFactory(meta_course=meta_course2, main_branch__code=Branches.SPB,
                       semester__year=2015)
    cr3 = CourseReviewFactory(course=c3)
    CourseReview(course=c4, text='zzz').save()
    assert len(CourseService.get_reviews(c1)) == 3
    assert set(CourseService.get_reviews(c1)) == {cr1, cr2, cr3}
