import datetime

import pytest

from django.utils import timezone
from django.utils.encoding import smart_bytes

from courses.models import CourseNews, CourseReview
from courses.services import CourseService
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseNewsFactory, CourseReviewFactory,
    MetaCourseFactory, SemesterFactory
)
from learning.models import EnrollmentPeriod
from learning.settings import Branches, GradeTypes
from learning.tabs import CourseReviewsTab
from learning.tests.factories import EnrollmentFactory
from users.tests.factories import (
    CuratorFactory, StudentFactory, TeacherFactory, VolunteerFactory
)

# TODO: тест для видимости таб из под разных ролей. (прятать табу во вьюхе, если нет содержимого)


@pytest.mark.django_db
def test_course_news_tab_permissions_student(client, assert_login_redirect):
    current_semester = SemesterFactory.create_current()
    prev_term = SemesterFactory.create_prev(current_semester)
    news: CourseNews = CourseNewsFactory(course__main_branch__code=Branches.SPB,
                                         course__semester=current_semester)
    course = news.course
    news_prev: CourseNews = CourseNewsFactory(course__main_branch__code=Branches.SPB,
                                              course__meta_course=course.meta_course,
                                              course__semester=prev_term)
    co_prev = news_prev.course
    assert_login_redirect(course.get_absolute_url())
    # By default student can't see the news until enroll in the course
    student_spb = StudentFactory(branch__code=Branches.SPB)
    client.login(student_spb)
    response = client.get(course.get_absolute_url())
    assert "news" not in response.context_data['course_tabs']
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context_data['course_tabs']
    e_current = EnrollmentFactory(course=course, student=student_spb)
    response = client.get(course.get_absolute_url())
    assert "news" in response.context_data['course_tabs']
    # To see the news for completed course student should successfully pass it.
    e_prev = EnrollmentFactory(course=co_prev, student=student_spb)
    response = client.get(co_prev.get_absolute_url())
    assert "news" not in response.context_data['course_tabs']
    e_prev.grade = GradeTypes.GOOD
    e_prev.save()
    response = client.get(co_prev.get_absolute_url())
    assert "news" in response.context_data['course_tabs']


@pytest.mark.django_db
def test_course_news_tab_permissions_teacher_and_curator(client):
    course_teacher = TeacherFactory()
    other_teacher = TeacherFactory()
    course = CourseFactory(semester=SemesterFactory.create_current(),
                           teachers=[course_teacher])
    news = CourseNewsFactory(course=course)
    client.login(other_teacher)
    response = client.get(course.get_absolute_url())
    assert "news" not in response.context_data['course_tabs']
    client.login(course_teacher)
    response = client.get(course.get_absolute_url())
    assert "news" in response.context_data['course_tabs']
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(course.get_absolute_url())
    assert "news" in response.context_data['course_tabs']


@pytest.mark.django_db
def test_course_assignments_tab_permissions(client, assert_login_redirect):
    current_term = SemesterFactory.create_current()
    prev_term = SemesterFactory.create_prev(current_term)
    teacher = TeacherFactory()
    course = CourseFactory(semester=current_term,
                           teachers=[teacher])
    course_prev = CourseFactory(meta_course=course.meta_course,
                                semester=prev_term)
    assert_login_redirect(course_prev.get_absolute_url())
    client.login(teacher)
    response = client.get(course.get_absolute_url())
    assert "assignments" not in response.context_data['course_tabs']
    a = AssignmentFactory(course=course)
    response = client.get(course.get_absolute_url())
    assert "assignments" in response.context_data['course_tabs']
    assert smart_bytes(a.get_teacher_url()) in response.content
    # Show links only if a teacher is an actual teacher of the course
    a_prev = AssignmentFactory(course=course_prev)
    response = client.get(course_prev.get_absolute_url())
    assert "assignments" in response.context_data['course_tabs']
    assert smart_bytes(a_prev.get_teacher_url()) not in response.content
    student = StudentFactory()
    client.login(student)
    response = client.get(course_prev.get_absolute_url())
    assert "assignments" in response.context_data['course_tabs']
    tab = response.context_data['course_tabs']['assignments']
    assert len(tab.tab_panel.context["items"]) == 1
    assert smart_bytes(a_prev.get_teacher_url()) not in response.content


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
    assert "reviews" in response.context_data['course_tabs']
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
