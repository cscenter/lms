import datetime
import os
import re

import factory
import pytest
import pytz
from bs4 import BeautifulSoup

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import model_to_dict
from django.utils.encoding import smart_bytes
from django.utils.timezone import now

from auth.mixins import PermissionRequiredMixin
from core.tests.factories import BranchFactory, LocationFactory
from core.timezone import now_local
from core.urls import reverse
from courses.constants import MaterialVisibilityTypes
from courses.forms import CourseClassForm
from courses.models import CourseClass, CourseGroupModes, CourseTeacher
from courses.permissions import CreateCourseClass
from courses.tests.factories import (
    CourseClassAttachmentFactory, CourseClassFactory, CourseFactory,
    CourseTeacherFactory, LearningSpaceFactory, SemesterFactory
)
from learning.models import StudentGroup
from learning.services import EnrollmentService, StudentGroupService
from learning.tests.factories import EnrollmentFactory, StudentGroupFactory
from users.tests.factories import (
    CuratorFactory, StudentFactory, StudentProfileFactory, TeacherFactory
)


@pytest.mark.django_db
def test_manager_for_student(settings):
    student_profile = StudentProfileFactory()
    student = student_profile.user
    teacher = TeacherFactory()
    course = CourseFactory(group_mode=CourseGroupModes.MANUAL)
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)
    # Active enrollment
    enrollment = EnrollmentService.enroll(student_profile, course, student_group=student_group1)
    assert CourseClass.objects.for_student(student).count() == 0
    assert CourseClass.objects.for_student(teacher).count() == 0
    cc = CourseClassFactory(course=course)
    assert CourseClass.objects.for_student(student).count() == 1
    assert CourseClass.objects.for_student(teacher).count() == 0
    # Student has left the course
    EnrollmentService.leave(enrollment)
    assert CourseClass.objects.for_student(student).count() == 0
    assert CourseClass.objects.for_student(teacher).count() == 0
    # Course class is visible to the student_group1
    cc = CourseClassFactory(course=course,
                            restricted_to=[student_group1])
    EnrollmentService.enroll(student_profile, course, student_group=student_group1)
    assert CourseClass.objects.for_student(student).count() == 2
    assert CourseClass.objects.for_student(teacher).count() == 0
    # This one is hidden for the student_group1
    cc = CourseClassFactory(course=course,
                            restricted_to=[student_group2])
    assert CourseClass.objects.for_student(student).count() == 2
    assert CourseClass.objects.for_student(teacher).count() == 0
    # Student is not enrolled in the course
    course2 = CourseFactory(main_branch=student_profile.branch)
    CourseClassFactory(course=course2)
    assert CourseClass.objects.for_student(student).count() == 2
    EnrollmentFactory(student=student, course=course2)
    assert CourseClass.objects.for_student(student).count() == 3
    CourseClassFactory(course=course,
                       restricted_to=[student_group1, student_group2])
    assert CourseClass.objects.for_student(student).count() == 4

@pytest.mark.django_db
def test_draft_course(client):
    student = StudentFactory()
    course = CourseFactory()
    teacher = TeacherFactory()
    curator = CuratorFactory()
    cc = CourseClassFactory(course=course)
    client.login(student)
    response = client.get(cc.get_absolute_url())
    assert response.status_code == 200
    client.login(teacher)
    response = client.get(cc.get_absolute_url())
    assert response.status_code == 200
    client.login(curator)
    response = client.get(cc.get_absolute_url())
    assert response.status_code == 200
    course.is_draft = True
    course.save()
    client.login(student)
    response = client.get(cc.get_absolute_url())
    assert response.status_code == 403
    client.login(teacher)
    response = client.get(cc.get_absolute_url())
    assert response.status_code == 200
    client.login(curator)
    response = client.get(cc.get_absolute_url())
    assert response.status_code == 200

@pytest.mark.django_db
def test_course_class_detail_security(client, assert_login_redirect):
    teacher = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
    form.update({'venue': LocationFactory.create().pk})
    url = co.get_create_class_url()
    assert_login_redirect(url, method='get')
    assert_login_redirect(url, form, method='post')


@pytest.mark.django_db
def test_view_course_class_create(client, lms_resolver, assert_login_redirect):
    curator = CuratorFactory()
    teacher, spectator, teacher_other = TeacherFactory.create_batch(3)
    student = StudentFactory()
    s = SemesterFactory.create_current()
    course = CourseFactory.create(teachers=[teacher], semester=s)
    co_other = CourseFactory.create(semester=s)
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    EnrollmentFactory(course=course, student=student)
    form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
    venue = LearningSpaceFactory(branch=course.main_branch)
    form.update({'venue': venue.pk})

    url = course.get_create_class_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == CreateCourseClass.name

    assert_login_redirect(url=url, method='post')
    client.login(student)
    assert client.get(url).status_code == 403
    assert client.post(url, form).status_code == 403
    client.login(spectator)
    assert client.get(url).status_code == 403
    assert client.post(url, form).status_code == 403
    client.login(teacher_other)
    assert client.get(url).status_code == 403
    assert client.post(url, form).status_code == 403

    client.login(teacher)
    # should save with course = co
    assert client.post(url, form).status_code == 302
    assert CourseClass.objects.filter(course=course).count() == 1
    assert CourseClass.objects.filter(course=co_other).count() == 0
    assert CourseClass.objects.filter(course=form['course']).count() == 0
    assert form['name'] == CourseClass.objects.get(course=course).name
    form.update({'course': course.pk})
    assert client.post(url, form).status_code == 302
    assert CourseClass.objects.filter(course=course).count() == 2

    client.login(curator)
    assert client.post(url, form).status_code == 302
    assert CourseClass.objects.filter(course=course).count() == 3


@pytest.mark.django_db
def test_course_class_create_and_add(client, assert_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current()
    course = CourseFactory.create(teachers=[teacher], semester=s)
    course_other = CourseFactory.create(semester=s)
    form = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
    location = LearningSpaceFactory(branch=course.main_branch)
    form.update({'venue': location.pk, '_addanother': True})
    client.login(teacher)
    url = course.get_create_class_url()
    # should save with course = co
    response = client.post(url, form)
    expected_url = course.get_create_class_url()
    assert response.status_code == 302
    assert_redirect(response, expected_url)
    assert CourseClass.objects.filter(course=course).count() == 1
    assert CourseClass.objects.filter(course=course_other).count() == 0
    assert CourseClass.objects.filter(course=form['course']).count() == 0
    assert form['name'] == CourseClass.objects.get(course=course).name
    form.update({'course': course.pk})
    assert client.post(url, form).status_code == 302
    del form['_addanother']
    response = client.post(url, form)
    assert CourseClass.objects.filter(course=course).count() == 3
    last_added_class = CourseClass.objects.order_by("-id").first()
    assert_redirect(response, last_added_class.get_absolute_url())


@pytest.mark.django_db
def test_view_course_class_update(client, assert_login_redirect, assert_redirect):
    curator = CuratorFactory()
    student = StudentFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    s = SemesterFactory.create_current()
    co = CourseFactory.create(teachers=[teacher], semester=s)
    CourseTeacherFactory(course=co, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    EnrollmentFactory(course=co, student=student)
    cc = CourseClassFactory.create(course=co)
    url = cc.get_update_url()

    assert_login_redirect(url=url, method='post')

    form = model_to_dict(cc)
    del form['slides']
    form['name'] += " changes"
    client.login(student)
    assert client.get(url).status_code == 403
    assert client.post(url, form).status_code == 403
    client.login(teacher_other)
    assert client.get(url).status_code == 403
    assert client.post(url, form).status_code == 403
    client.login(spectator)
    assert client.get(url).status_code == 403
    assert client.post(url, form).status_code == 403

    client.login(teacher)
    assert_redirect(client.post(url, form), cc.get_absolute_url())
    response = client.get(cc.get_absolute_url())
    assert form['name'] == response.context_data['object'].name

    client.login(curator)
    form['name'] += " changes 2"
    assert_redirect(client.post(url, form), cc.get_absolute_url())
    response = client.get(cc.get_absolute_url())
    assert form['name'] == response.context_data['object'].name


@pytest.mark.django_db
def test_course_class_update_and_add(client, assert_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current()
    co = CourseFactory.create(teachers=[teacher], semester=s)
    cc = CourseClassFactory.create(course=co)
    url = cc.get_update_url()
    client.login(teacher)
    form = model_to_dict(cc)
    form['name'] += " foobar"
    del form['slides']
    assert_redirect(client.post(url, form),
                    cc.get_absolute_url())
    response = client.get(cc.get_absolute_url())
    assert form['name'] == response.context_data['object'].name
    form.update({'_addanother': True})
    expected_url = co.get_create_class_url()
    assert_redirect(client.post(url, form), expected_url)


@pytest.mark.django_db
def test_view_course_class_delete(client, assert_redirect, assert_login_redirect):
    curator = CuratorFactory()
    student = StudentFactory()
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    s = SemesterFactory.create_current()
    co = CourseFactory.create(teachers=[teacher], semester=s)
    cc_1 = CourseClassFactory.create(course=co)
    cc_2 = CourseClassFactory.create(course=co)
    EnrollmentFactory(course=co, student=student)

    class_delete_url = cc_1.get_delete_url()
    assert_login_redirect(class_delete_url)
    assert_login_redirect(class_delete_url, {}, method='post')

    client.login(student)
    assert client.get(class_delete_url).status_code == 403
    assert client.post(class_delete_url).status_code == 403
    client.login(teacher_other)
    assert client.get(class_delete_url).status_code == 403
    assert client.post(class_delete_url).status_code == 403
    client.login(spectator)
    assert client.get(class_delete_url).status_code == 403
    assert client.post(class_delete_url).status_code == 403

    client.login(teacher)
    response = client.get(class_delete_url)
    assert response.status_code == 200
    assert smart_bytes(cc_1) in response.content
    assert_redirect(client.post(class_delete_url),
                    reverse('teaching:timetable'))
    assert not CourseClass.objects.filter(pk=cc_1.pk).exists()

    client.login(curator)
    class_delete_url = cc_2.get_delete_url()
    response = client.get(class_delete_url)
    assert response.status_code == 200
    assert smart_bytes(cc_2) in response.content
    assert_redirect(client.post(class_delete_url),
                    reverse('teaching:timetable'))
    assert not CourseClass.objects.filter(pk=cc_2.pk).exists()


@pytest.mark.django_db
def test_course_class_back_variable(client, assert_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current()
    course = CourseFactory.create(teachers=[teacher], semester=s)
    cc = CourseClassFactory(course=course)
    class_update_url = cc.get_update_url()
    client.login(teacher)
    form = model_to_dict(cc)
    del form['slides']
    form['name'] += " foobar"
    response = client.post(class_update_url, form)
    assert_redirect(response, cc.get_absolute_url())
    url = "{}?back=course".format(class_update_url)
    assert_redirect(client.post(url, form),
                    course.get_absolute_url())


@pytest.mark.django_db
def test_course_class_attachment_links(client, assert_login_redirect):
    teacher = TeacherFactory()
    s = SemesterFactory.create_current()
    co = CourseFactory.create(teachers=[teacher], semester=s)
    cc = CourseClassFactory.create(course=co)
    cca1 = CourseClassAttachmentFactory.create(
        course_class=cc, material__filename="foobar1.pdf")
    cca2 = CourseClassAttachmentFactory.create(
        course_class=cc, material__filename="foobar2.zip")
    assert_login_redirect(cc.get_absolute_url())
    client.login(teacher)
    response = client.get(cc.get_absolute_url())
    assert response.status_code == 200
    assert smart_bytes(cca1.get_download_url()) in response.content
    assert smart_bytes(cca1.material_file_name) in response.content
    assert smart_bytes(cca2.get_download_url()) in response.content
    assert smart_bytes(cca2.material_file_name) in response.content
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
    teacher = TeacherFactory()
    client.login(teacher)
    s = SemesterFactory.create_current()
    co = CourseFactory(teachers=[teacher], semester=s)
    cc = CourseClassFactory(course=co, slides=None)
    f1 = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
    f2 = SimpleUploadedFile("attachment2.txt", b"attachment2_content")
    form = model_to_dict(cc)
    del form['slides']
    form['attachments'] = [f1, f2]
    url = cc.get_update_url()
    response = client.post(url, form)
    assert_redirect(response, cc.get_absolute_url())
    # check that files are available from course class page
    response = client.get(cc.get_absolute_url())
    spans = (BeautifulSoup(response.content, "html.parser")
             .find_all('span', class_='assignment-attachment'))
    assert len(spans) == 2
    cca_files = sorted(a.material.path
                       for a in response.context_data['attachments'])
    # we will delete attachment2.txt
    cca_to_delete = [a for a in response.context_data['attachments']
                     if a.material.path == cca_files[1]][0]
    as_ = sorted(span.a.contents[0].strip() for span in spans)
    assert re.match("attachment1(_[0-9a-zA-Z]+)?.txt", as_[0])
    assert re.match("attachment2(_[0-9a-zA-Z]+)?.txt", as_[1])
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


@pytest.mark.django_db
def test_course_class_form_available(client, curator, settings):
    """Test form availability based on `is_completed` value"""
    # XXX: Date widget depends on locale
    settings.LANGUAGE_CODE = 'ru'
    teacher = TeacherFactory()
    semester = SemesterFactory.create_current()
    course = CourseFactory(semester=semester, teachers=[teacher])
    course_class_add_url = course.get_create_class_url()
    response = client.get(course_class_add_url)
    assert response.status_code == 302
    client.login(teacher)
    response = client.get(course_class_add_url)
    assert response.status_code == 200
    # Check form visible
    assert smart_bytes("submit-id-save") in response.content
    # Course completed, form invisible for teacher
    course.completed_at = now().date()
    course.save()
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
    today = now_local(teacher.time_zone).date()
    next_day = today + datetime.timedelta(days=1)
    course.completed_at = next_day
    course.save()
    venue = LearningSpaceFactory(branch=course.main_branch)
    date_format = CourseClassForm.base_fields['date'].widget.format
    form = {
        "type": "lecture",
        "venue": venue.pk,
        "name": "Test class",
        "date": next_day.strftime(date_format),
        "starts_at": "17:20",
        "ends_at": "18:50",
        "recording_link": "https://record.com",
        "translation_link": "https://translate.com",
        "is_conducted_by_invited": 'on',
        "time_zone": course.main_branch.get_timezone(),
        "materials_visibility": MaterialVisibilityTypes.PUBLIC
    }
    response = client.post(course_class_add_url, form)
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert 'success' in messages[0].tags
    # FIXME: добавить тест на is_form_available и посмотреть, можно ли удалить эту часть, по-моему это лишняя логика


@pytest.mark.django_db
def test_course_class_detail_view_timezone(client, settings):
    settings.LANGUAGE_CODE = 'ru'
    curator = CuratorFactory(time_zone=pytz.timezone('Europe/Moscow'))
    client.login(curator)
    course_class = CourseClassFactory(
        date=datetime.date(year=2020, month=1, day=1),
        starts_at=datetime.time(hour=20, minute=0),
        ends_at=datetime.time(hour=23, minute=0),
        time_zone=pytz.timezone('Europe/Moscow'))
    response = client.get(course_class.get_absolute_url())
    assert smart_bytes("01 января 2020, 20:00–23:00") in response.content
    curator.time_zone = pytz.timezone('Asia/Novosibirsk')
    curator.save()
    response = client.get(course_class.get_absolute_url())
    assert smart_bytes("02 января 2020, 00:00–03:00") in response.content


@pytest.mark.django_db
def test_view_course_add_class_btn_visibility(client):
    """
    The button for creating new class should
    only be displayed if the user has permissions to do so.
    """
    teacher, spectator = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)

    def has_create_news_btn(user):
        client.login(user)
        url = course.get_absolute_url()
        html = client.get(url).content.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        client.logout()
        return soup.find('a', {
            "href": course.get_create_class_url()
        }) is not None

    assert has_create_news_btn(teacher)
    assert not has_create_news_btn(spectator)
