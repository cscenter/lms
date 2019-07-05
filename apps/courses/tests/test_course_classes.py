import datetime
import os
import re

import factory
import pytest
from bs4 import BeautifulSoup
from django.conf import settings
from django.conf.urls.static import static
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import model_to_dict
from django.utils.encoding import smart_bytes
from django.utils.timezone import now

from core.timezone import now_local
from core.urls import reverse
from courses.forms import CourseClassForm
from courses.models import CourseClass
from courses.tests.factories import CourseClassFactory, CourseTeacherFactory, \
    CourseFactory, VenueFactory, SemesterFactory, CourseClassAttachmentFactory
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_course_class_detail_is_actual_teacher(client):
    teacher = TeacherFactory()
    cc = CourseClassFactory.create()
    cc_other = CourseClassFactory.create()
    url = cc.get_absolute_url()
    assert not client.get(url).context['is_actual_teacher']
    client.login(teacher)
    assert not client.get(url).context['is_actual_teacher']
    CourseTeacherFactory(course=cc_other.course, teacher=teacher)
    assert not client.get(url).context['is_actual_teacher']
    CourseTeacherFactory(course=cc.course, teacher=teacher)
    assert client.get(url).context['is_actual_teacher']


@pytest.mark.django_db
def test_course_class_detail_security(client, assert_login_redirect):
    teacher = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
    form.update({'venue': VenueFactory.create().pk})
    del form['slides']
    url = co.get_create_class_url()
    assert_login_redirect(url, method='get')
    assert_login_redirect(url, form, method='post')


@pytest.mark.django_db
def test_course_class_create(client):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher], semester=s)
    co_other = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                    semester=s)
    form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
    venue = VenueFactory.create(city_id=settings.DEFAULT_CITY_CODE)
    form.update({'venue': venue.pk})
    del form['slides']
    url = co.get_create_class_url()
    client.login(teacher)
    # should save with course = co
    assert client.post(url, form).status_code == 302
    assert CourseClass.objects.filter(course=co).count() == 1
    assert CourseClass.objects.filter(course=co_other).count() == 0
    assert CourseClass.objects.filter(course=form['course']).count() == 0
    assert form['name'] == CourseClass.objects.get(course=co).name
    form.update({'course': co.pk})
    assert client.post(url, form).status_code == 302


@pytest.mark.django_db
def test_course_class_create_and_add(client, assert_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher], semester=s)
    co_other = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                                    semester=s)
    form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
    venue = VenueFactory.create(city_id=settings.DEFAULT_CITY_CODE)
    form.update({'venue': venue.pk, '_addanother': True})
    del form['slides']
    client.login(teacher)
    url = co.get_create_class_url()
    # should save with course = co
    response = client.post(url, form)
    expected_url = co.get_create_class_url()
    assert response.status_code == 302
    assert_redirect(response, expected_url)
    assert CourseClass.objects.filter(course=co).count() == 1
    assert CourseClass.objects.filter(course=co_other).count() == 0
    assert CourseClass.objects.filter(course=form['course']).count() == 0
    assert form['name'] == CourseClass.objects.get(course=co).name
    form.update({'course': co.pk})
    assert client.post(url, form).status_code == 302
    del form['_addanother']
    response = client.post(url, form)
    assert CourseClass.objects.filter(course=co).count() == 3
    last_added_class = CourseClass.objects.order_by("-id").first()
    assert_redirect(response, last_added_class.get_absolute_url())


@pytest.mark.django_db
def test_course_class_update(client, assert_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher], semester=s)
    cc = CourseClassFactory.create(course=co)
    url = cc.get_update_url()
    client.login(teacher)
    form = model_to_dict(cc)
    del form['slides']
    form['name'] += " foobar"
    assert_redirect(client.post(url, form), cc.get_absolute_url())
    response = client.get(cc.get_absolute_url())
    assert form['name'] == response.context['object'].name


@pytest.mark.django_db
def test_course_class_update_and_add(client, assert_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher], semester=s)
    cc = CourseClassFactory.create(course=co)
    url = cc.get_update_url()
    client.login(teacher)
    form = model_to_dict(cc)
    del form['slides']
    form['name'] += " foobar"
    assert_redirect(client.post(url, form),
                    cc.get_absolute_url())
    response = client.get(cc.get_absolute_url())
    assert form['name'] == response.context['object'].name
    form.update({'_addanother': True})
    expected_url = co.get_create_class_url()
    assert_redirect(client.post(url, form), expected_url)


@pytest.mark.django_db
def test_course_class_delete(client, assert_redirect, assert_login_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher], semester=s)
    cc = CourseClassFactory.create(course=co)
    class_delete_url = cc.get_delete_url()
    assert_login_redirect(class_delete_url)
    assert_login_redirect(class_delete_url, {}, method='post')
    client.login(teacher)
    response = client.get(class_delete_url)
    assert response.status_code == 200
    assert smart_bytes(cc) in response.content
    assert_redirect(client.post(class_delete_url),
                    reverse('teaching:timetable'))
    assert not CourseClass.objects.filter(pk=cc.pk).exists()


@pytest.mark.django_db
def test_course_class_back_variable(client, assert_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(teachers=[teacher], semester=s)
    cc = CourseClassFactory.create(course=co)
    class_update_url = cc.get_update_url()
    client.login(teacher)
    form = model_to_dict(cc)
    del form['slides']
    form['name'] += " foobar"
    assert_redirect(client.post(class_update_url, form),
                    cc.get_absolute_url())
    url = "{}?back=course".format(class_update_url)
    assert_redirect(client.post(url, form),
                    co.get_absolute_url())


@pytest.mark.django_db
def test_course_class_attachment_links(client, assert_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher], semester=s)
    cc = CourseClassFactory.create(course=co)
    cca1 = CourseClassAttachmentFactory.create(
        course_class=cc, material__filename="foobar1.pdf")
    cca2 = CourseClassAttachmentFactory.create(
        course_class=cc, material__filename="foobar2.zip")
    response = client.get(cc.get_absolute_url())
    assert response.status_code == 200
    assert smart_bytes(cca1.material.url) in response.content
    assert smart_bytes(cca1.material_file_name) in response.content
    assert smart_bytes(cca2.material.url) in response.content
    assert smart_bytes(cca2.material_file_name) in response.content
    client.login(teacher)
    class_update_url = cc.get_update_url()
    response = client.get(class_update_url)
    assert response.status_code == 200
    assert smart_bytes(cca1.get_delete_url()) in response.content
    assert smart_bytes(cca1.material_file_name) in response.content
    assert smart_bytes(cca2.get_delete_url()) in response.content
    assert smart_bytes(cca2.material_file_name) in response.content


@pytest.mark.django_db
def test_course_class_attachments(client, assert_redirect,
                                  assert_login_redirect):
    # Serving media enabled (TODO: rewrite with setup_module?)
    import compscicenter_ru.urls
    _original_urls = compscicenter_ru.urls.urlpatterns.copy()
    settings.DEBUG = True
    s = static(settings.MEDIA_URL,
               document_root=settings.MEDIA_ROOT)
    compscicenter_ru.urls.urlpatterns += s
    settings.DEBUG = False

    teacher = TeacherFactory()
    s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
    co = CourseFactory.create(city=settings.DEFAULT_CITY_CODE,
                              teachers=[teacher], semester=s)
    cc = CourseClassFactory.create(course=co)
    f1 = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
    f2 = SimpleUploadedFile("attachment2.txt", b"attachment2_content")
    client.login(teacher)
    form = model_to_dict(cc)
    del form['slides']
    form['attachments'] = [f1, f2]
    url = cc.get_update_url()
    assert_redirect(client.post(url, form),
                    cc.get_absolute_url())
    # check that files are available from course class page
    response = client.get(cc.get_absolute_url())
    spans = (BeautifulSoup(response.content, "html.parser")
             .find_all('span', class_='assignment-attachment'))
    assert len(spans) == 2
    cca_files = sorted(a.material.path
                       for a in response.context['attachments'])
    # we will delete attachment2.txt
    cca_to_delete = [a for a in response.context['attachments']
                     if a.material.path == cca_files[1]][0]
    as_ = sorted((span.a.contents[0].strip(),
                  b"".join(client.get(span.a['href']).streaming_content))
                 for span in spans)
    assert re.match("attachment1(_[0-9a-zA-Z]+)?.txt", as_[0][0])
    assert re.match("attachment2(_[0-9a-zA-Z]+)?.txt", as_[1][0])
    assert b"attachment1_content" == as_[0][1]
    assert b"attachment2_content" == as_[1][1]
    # delete one of the files, check that it's deleted and other isn't
    url = cca_to_delete.get_delete_url()
    # check security just in case
    client.logout()
    assert_login_redirect(url)
    assert_login_redirect(url, {}, method='post')
    client.login(teacher)
    response = client.get(url)
    assert response.status_code == 200
    assert smart_bytes(cca_to_delete.material_file_name) in response.content
    assert_redirect(client.post(url),
                    cc.get_update_url())
    response = client.get(cc.get_absolute_url())
    spans = (BeautifulSoup(response.content, "html.parser")
             .find_all('span', class_='assignment-attachment'))
    assert len(spans) == 1
    assert re.match("attachment1(_[0-9a-zA-Z]+)?.txt",
                    spans[0].a.contents[0].strip())
    assert not os.path.isfile(cca_files[1])
    # Disable Serving media
    compscicenter_ru.urls.urlpatterns = _original_urls


@pytest.mark.django_db
def test_course_class_form_available(client, curator, settings):
    """Test form availability based on `is_completed` value"""
    # XXX: Date widget depends on locale
    settings.LANGUAGE_CODE = 'ru'
    teacher = TeacherFactory(city_id='spb')
    semester = SemesterFactory.create_current()
    co = CourseFactory(semester=semester, teachers=[teacher])
    course_class_add_url = co.get_create_class_url()
    response = client.get(course_class_add_url)
    assert response.status_code == 302
    client.login(teacher)
    response = client.get(course_class_add_url)
    assert response.status_code == 200
    # Check form visible
    assert smart_bytes("submit-id-save") in response.content
    # Course completed, form invisible for teacher
    co.completed_at = now().date()
    co.save()
    response = client.get(course_class_add_url)
    assert smart_bytes("Курс завершён") in response.content
    client.login(curator)
    response = client.get(course_class_add_url)
    assert smart_bytes("Курс завершён") not in response.content
    # Try to send form directly by teacher
    client.login(teacher)
    form = {}
    response = client.post(course_class_add_url, form, follow=True)
    assert response.status_code == 403
    # Check we can post form if course is active
    today = now_local(teacher.city_code).date()
    next_day = today + datetime.timedelta(days=1)
    co.completed_at = next_day
    co.save()
    venue = VenueFactory(city=co.city)
    date_format = CourseClassForm.base_fields['date'].widget.format
    form = {
        "type": "lecture",
        "venue": venue.pk,
        "name": "Test class",
        "date": next_day.strftime(date_format),
        "starts_at": "17:20",
        "ends_at": "18:50"
    }
    response = client.post(course_class_add_url, form, follow=True)
    message = list(response.context['messages'])[0]
    assert 'success' in message.tags
    # FIXME: добавить тест на is_form_available и посмотреть, можно ли удалить эту часть, по-моему это лишняя логика