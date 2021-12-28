import factory
import pytest
from bs4 import BeautifulSoup

from django.forms import model_to_dict
from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from auth.permissions import perm_registry
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.urls import reverse
from courses.constants import AssigneeMode
from courses.models import Assignment, AssignmentAttachment, CourseTeacher
from courses.permissions import (
    CreateAssignment, DeleteAssignmentAttachment, DeleteAssignmentAttachmentAsTeacher,
    EditAssignment
)
from courses.tests.factories import (
    AssignmentAttachmentFactory, AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from users.tests.factories import CuratorFactory, TeacherFactory


def prefixed_form(form_data, prefix: str):
    return {f"{prefix}-{k}": v for k, v in form_data.items()}


@pytest.mark.django_db
def test_course_assignment_create_view_security(client, assert_login_redirect,
                                                lms_resolver):
    from auth.permissions import perm_registry
    course = CourseFactory()
    create_url = course.get_create_assignment_url()
    resolver = lms_resolver(create_url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == CreateAssignment.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(create_url, method='get')


@pytest.mark.django_db
def test_course_assignment_form_create(client):
    import datetime
    teacher = TeacherFactory()
    CourseFactory.create_batch(3, teachers=[teacher])
    course = CourseFactory(teachers=[teacher])
    form = factory.build(dict, FACTORY_CLASS=AssignmentFactory)
    deadline_date = form['deadline_at'].strftime(DATE_FORMAT_RU)
    deadline_time = form['deadline_at'].strftime(TIME_FORMAT_RU)
    form.update({
        'course': course.pk,
        'deadline_at_0': deadline_date,
        'deadline_at_1': deadline_time,
        'time_zone': 'Europe/Moscow',
        'assignee_mode': AssigneeMode.STUDENT_GROUP_DEFAULT
    })

    url = course.get_create_assignment_url()
    client.login(teacher)
    response = client.post(url, prefixed_form(form, "assignment"))
    assert response.status_code == 302
    assert Assignment.objects.count() == 1
    a = Assignment.objects.first()
    assert a.ttc is None
    form.update({'ttc': '2:42'})
    response = client.post(url, prefixed_form(form, "assignment"))
    assert response.status_code == 302
    assert Assignment.objects.count() == 2
    a2 = Assignment.objects.exclude(pk=a.pk).first()
    assert a2.ttc == datetime.timedelta(hours=2, minutes=42)


@pytest.mark.django_db
def test_course_assignment_update_view_security(client, assert_login_redirect,
                                                lms_resolver):
    from auth.permissions import perm_registry
    assignment = AssignmentFactory.create()
    course = CourseFactory()
    update_url = assignment.get_update_url()
    resolver = lms_resolver(update_url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == EditAssignment.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(update_url, method='get')


@pytest.mark.django_db
def test_course_assignment_update(client, assert_redirect):
    teacher = TeacherFactory()
    client.login(teacher)
    course = CourseFactory.create(teachers=[teacher])
    a = AssignmentFactory.create(course=course)
    form = model_to_dict(a)
    del form['ttc']
    del form['checker']
    deadline_date = form['deadline_at'].strftime(DATE_FORMAT_RU)
    deadline_time = form['deadline_at'].strftime(TIME_FORMAT_RU)
    new_title = a.title + " foo42bar"
    form.update({
        'assignee_mode': AssigneeMode.STUDENT_GROUP_DEFAULT,
        'title': new_title,
        'course': course.pk,
        'time_zone': 'Europe/Moscow',
        'deadline_at_0': deadline_date,
        'deadline_at_1': deadline_time,
    })
    # Make sure new title is not present on /teaching/assignments/
    list_url = reverse('teaching:assignments_check_queue')
    response = client.get(list_url)
    assert response.status_code == 200
    assert smart_bytes(form['title']) not in response.content
    response = client.post(a.get_update_url(), prefixed_form(form, "assignment"))
    assert_redirect(response, a.get_teacher_url())
    a.refresh_from_db()
    assert a.title == new_title


# TODO: test fail on updating `course` attribute?


@pytest.mark.django_db
def test_course_assignment_delete_security(client, assert_login_redirect):
    teacher, teacher_other, spectator = TeacherFactory.create_batch(3)
    co = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=co, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    a = AssignmentFactory(course=co)
    delete_url = a.get_delete_url()
    # Anonymous
    assert_login_redirect(delete_url, method='get')
    assert_login_redirect(delete_url, {}, method='post')

    client.login(teacher_other)
    response = client.get(delete_url)
    assert response.status_code == 403
    response = client.post(delete_url)
    assert response.status_code == 403
    client.logout()

    client.login(spectator)
    response = client.get(delete_url)
    assert response.status_code == 403
    response = client.post(delete_url)
    assert response.status_code == 403
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
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    assignment = AssignmentFactory(course=course)
    delete_url = assignment.get_delete_url()
    client.login(teacher)
    response = client.get(delete_url)
    assert response.status_code == 200
    assert smart_bytes(assignment.title) in response.content
    teaching_assignment_list = reverse('teaching:assignments_check_queue')
    assert_redirect(client.post(delete_url), teaching_assignment_list)
    response = client.get(teaching_assignment_list)
    assert response.status_code == 200
    assert smart_bytes(assignment.title) not in response.content


@pytest.mark.django_db
def test_view_course_assignment_attachment_delete_security(client,
                                                           lms_resolver,
                                                           assert_login_redirect):
    teacher, spectator = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    attachment = AssignmentAttachmentFactory(assignment__course=course)
    delete_url = attachment.get_delete_url()

    resolver = lms_resolver(delete_url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == DeleteAssignmentAttachment.name
    assert resolver.func.view_class.permission_required in perm_registry

    assert_login_redirect(delete_url)

    client.login(spectator)
    response = client.get(delete_url)
    assert response.status_code == 403
    response = client.post(delete_url)
    assert response.status_code == 403
    client.logout()

    client.login(teacher)
    response = client.get(delete_url)
    assert response.status_code == 200
    response = client.post(delete_url, follow=True)
    assert response.status_code == 200
    assert (not AssignmentAttachment.objects
            .filter(pk=attachment.pk)
            .count()
    )

    assert not AssignmentAttachment.objects.count()


@pytest.mark.django_db
def test_view_course_assignment_edit_delete_btn_visibility(client):
    """
    The buttons for editing and deleting an assignment should
    only be displayed if the user has permissions to do so.
    """
    teacher, spectator = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher])
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)
    assignment = AssignmentFactory(course=course)

    def has_elements(user):
        url = assignment.get_teacher_url()
        client.login(user)
        html = client.get(url).content.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        has_edit = soup.find("a", {
            "href": assignment.get_update_url()
        }) is not None
        has_delete = soup.find("a", {
            "href": assignment.get_delete_url()
        }) is not None
        client.logout()
        return has_edit + has_delete

    assert has_elements(teacher) == 2
    assert not has_elements(spectator)


