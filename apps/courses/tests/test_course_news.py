import factory
import pytest
from django.forms import model_to_dict

from courses.tests.factories import CourseFactory, CourseNewsFactory
from courses.models import CourseNews
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_course_news_create_security(client, settings, assert_login_redirect,
                                     assert_redirect):
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher])
    url = course.get_create_news_url()
    form = factory.build(dict, FACTORY_CLASS=CourseNewsFactory)
    form.update({'course': course})
    assert_login_redirect(url, form=form, method='post')
    client.login(teacher_other)
    assert_login_redirect(url, form=form, method='post')
    client.logout()
    client.login(teacher)
    response = client.post(url, form)
    assert response.status_code == 302
    assert CourseNews.objects.count() == 1


@pytest.mark.django_db
def test_course_news_create_data(client, assert_redirect):
    teacher = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher])
    url = course.get_create_news_url()
    form = factory.build(dict, FACTORY_CLASS=CourseNewsFactory)
    form.update({'course': course})
    news_tab_url = course.get_url_for_tab("news")
    client.login(teacher)
    assert_redirect(client.post(url, form), news_tab_url)
    response = client.get(news_tab_url)
    assert response.status_code == 200
    assert form['text'].encode() in response.content
    course_news = response.context['course'].coursenews_set.all()[0]
    assert teacher == course_news.author


@pytest.mark.django_db
def test_course_news_update(client, assert_login_redirect, assert_redirect):
    """Tests permissions and update action"""
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher])
    course_news = CourseNewsFactory.create(course=course, author=teacher)
    url = course_news.get_update_url()
    form = model_to_dict(course_news)
    form.update({'text': "foobar text"})
    assert_login_redirect(url, form=form, method='post')
    client.login(teacher_other)
    assert_login_redirect(url, form=form, method='post')
    client.logout()
    client.login(teacher)
    response = client.post(url, form)
    assert response.status_code == 302
    assert_redirect(response, course.get_url_for_tab("news"))
    response = client.get(course.get_url_for_tab("news"))
    assert response.status_code == 200
    assert form['text'].encode() in response.content


@pytest.mark.django_db
def test_course_news_delete(client, assert_login_redirect, assert_redirect):
    """Tests permissions and delete action"""
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher])
    course_news = CourseNewsFactory.create(course=course, author=teacher)
    url = course_news.get_delete_url()
    assert_login_redirect(url, form={}, method='post')
    client.login(teacher_other)
    assert_login_redirect(url, form={}, method='post')
    client.logout()
    client.login(teacher)
    response = client.post(url)
    assert response.status_code == 302
    assert_redirect(response, course.get_absolute_url())
    response = client.get(course.get_absolute_url())
    assert course_news.text.encode() not in response.content
