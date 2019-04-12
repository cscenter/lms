import factory
import pytest
from django.forms import model_to_dict
from django.utils.encoding import smart_bytes

from core.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.urls import reverse
from courses.models import Assignment
from courses.tests.factories import CourseFactory, AssignmentFactory
from users.tests.factories import TeacherCenterFactory, CuratorFactory


@pytest.mark.django_db
def test_course_assignment_create_security(client, assert_login_redirect):
    teacher = TeacherCenterFactory()
    teacher_other = TeacherCenterFactory()
    co = CourseFactory.create(teachers=[teacher])
    create_url = co.get_create_assignment_url()
    form = factory.build(dict, FACTORY_CLASS=AssignmentFactory)
    form.update({
        'course': co.pk,
        # 'attached_file': None
    })
    # Anonymous
    client.logout()
    assert_login_redirect(create_url, method='get')
    assert_login_redirect(create_url, form, method='post')
    client.login(teacher_other)
    assert_login_redirect(create_url, method='get')
    assert_login_redirect(create_url, form, method='post')
    client.login(teacher)
    response = client.get(create_url)
    assert response.status_code == 200
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(create_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_course_assignment_create(client):
    teacher = TeacherCenterFactory()
    CourseFactory.create_batch(3, teachers=[teacher])
    co = CourseFactory.create(teachers=[teacher])
    form = factory.build(dict, FACTORY_CLASS=AssignmentFactory)
    deadline_date = form['deadline_at'].strftime(DATE_FORMAT_RU)
    deadline_time = form['deadline_at'].strftime(TIME_FORMAT_RU)
    form.update({'course': co.pk,
                 # 'attached_file': None,
                 'deadline_at_0': deadline_date,
                 'deadline_at_1': deadline_time})
    url = co.get_create_assignment_url()
    client.login(teacher)
    response = client.post(url, form)
    assert response.status_code == 302
    assert Assignment.objects.count() == 1


@pytest.mark.django_db
def test_course_assignment_update_security(client, assert_login_redirect):
    teacher = TeacherCenterFactory()
    teacher_other = TeacherCenterFactory()
    co = CourseFactory(teachers=[teacher])
    a = AssignmentFactory(course=co)
    update_url = a.get_update_url()
    form = factory.build(dict, FACTORY_CLASS=AssignmentFactory)
    form.update({
        'course': co.pk,
        # 'attached_file': None
    })
    # Anonymous
    assert_login_redirect(update_url, method='get')
    assert_login_redirect(update_url, form, method='post')
    client.login(teacher_other)
    assert_login_redirect(update_url, method='get')
    assert_login_redirect(update_url, form, method='post')
    client.logout()
    client.login(teacher)
    response = client.get(update_url)
    assert response.status_code == 200
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(update_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_course_assignment_update(client, assert_redirect):
    teacher = TeacherCenterFactory()
    co = CourseFactory.create(teachers=[teacher])
    a = AssignmentFactory.create(course=co)
    form = model_to_dict(a)
    deadline_date = form['deadline_at'].strftime(DATE_FORMAT_RU)
    deadline_time = form['deadline_at'].strftime(TIME_FORMAT_RU)
    new_title = a.title + " foo42bar"
    form.update({'title': new_title,
                 'course': co.pk,
                 # 'attached_file': None,
                 'deadline_at_0': deadline_date,
                 'deadline_at_1': deadline_time})
    update_url = a.get_update_url()
    client.login(teacher)
    # Make sure new title is not presented on /teaching/assignments/
    list_url = reverse('teaching:assignment_list')
    response = client.get(list_url)
    assert response.status_code == 200
    assert smart_bytes(form['title']) not in response.content
    assert_redirect(client.post(update_url, form),
                    a.get_teacher_url())
    a.refresh_from_db()
    assert a.title == new_title


# TODO: test fail on updating `course` attribute?


@pytest.mark.django_db
def test_course_assignment_delete_security(client, assert_login_redirect):
    teacher = TeacherCenterFactory()
    teacher_other = TeacherCenterFactory()
    co = CourseFactory(teachers=[teacher])
    a = AssignmentFactory(course=co)
    delete_url = a.get_delete_url()
    # Anonymous
    assert_login_redirect(delete_url, method='get')
    assert_login_redirect(delete_url, {}, method='post')
    client.login(teacher_other)
    assert_login_redirect(delete_url, method='get')
    assert_login_redirect(delete_url, {}, method='post')
    client.logout()
    client.login(teacher)
    response = client.get(delete_url)
    assert response.status_code == 200
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(delete_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_course_assignment_delete(client, assert_redirect):
    teacher = TeacherCenterFactory()
    co = CourseFactory.create(teachers=[teacher])
    a = AssignmentFactory.create(course=co)
    delete_url = a.get_delete_url()
    client.login(teacher)
    response = client.get(delete_url)
    assert response.status_code == 200
    assert smart_bytes(a.title) in response.content
    teaching_assignment_list = reverse('teaching:assignment_list')
    assert_redirect(client.post(delete_url), teaching_assignment_list)
    response = client.get(teaching_assignment_list)
    assert response.status_code == 200
    assert smart_bytes(a.title) not in response.content
