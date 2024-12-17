import datetime

import factory
import pytest
from bs4 import BeautifulSoup

from django.forms import model_to_dict
from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from auth.permissions import perm_registry
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.urls import reverse
from courses.constants import AssigneeMode, AssignmentFormat
from courses.forms import AssignmentStudentGroupTeachersBucketFormSetFactory, AssignmentForm
from courses.models import Assignment, AssignmentAttachment, CourseTeacher
from courses.permissions import (
    CreateAssignment, DeleteAssignmentAttachment, DeleteAssignmentAttachmentAsTeacher,
    EditAssignment
)
from courses.tests.factories import (
    AssignmentAttachmentFactory, AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from learning.models import StudentGroup, StudentGroupTeacherBucket
from learning.tests.factories import StudentAssignmentFactory, StudentGroupFactory
from users.tests.factories import CuratorFactory, StudentFactory, TeacherFactory


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
def test_draft_course(client):
    future = datetime.datetime.now() + datetime.timedelta(days=3)
    student = StudentFactory()
    teacher = TeacherFactory()
    curator = CuratorFactory()
    course = CourseFactory(completed_at=future, teachers=[teacher])
    ca = StudentAssignmentFactory(assignment__course=course,
                                  student=student)
    client.login(student)
    response = client.get(ca.get_student_url())
    assert response.status_code == 200
    client.login(teacher)
    response = client.get(ca.assignment.get_teacher_url())
    assert response.status_code == 200
    client.login(curator)
    response = client.get(ca.assignment.get_teacher_url())
    assert response.status_code == 200
    course.is_draft = True
    course.save()
    client.login(student)
    response = client.get(ca.get_student_url())
    assert response.status_code == 200
    client.login(teacher)
    response = client.get(ca.assignment.get_teacher_url())
    assert response.status_code == 200
    client.login(curator)
    response = client.get(ca.assignment.get_teacher_url())
    assert response.status_code == 200

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


def create_assignment_form():
    future = datetime.date.today() + datetime.timedelta(3)
    form = {
        'title': 'Assignment title',
        'submission_type': AssignmentFormat.ONLINE,
        'text': 'some text',
        'passing_score': 2,
        'maximum_score': 5,
        'weight': 1,
        'time_zone': 'Europe/Moscow',
        'deadline_at_0': future.strftime(DATE_FORMAT_RU),
        'deadline_at_1': '00:00',
        'assignee_mode': AssigneeMode.STUDENT_GROUP_BALANCED
    }
    return prefixed_form(form, "assignment")


def get_assignment_course_models():
    course = CourseFactory()
    ct1, ct2 = CourseTeacherFactory.create_batch(2, course=course)
    sg0 = StudentGroup.objects.first()
    sg1, sg2 = StudentGroupFactory.create_batch(2, course=course)
    url = course.get_create_assignment_url()
    return course, url, ct1, ct2, sg0, sg1, sg2


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_one_bucket(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 1,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk, sg2.pk],
        '0-teachers': ct1.pk,
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    a = Assignment.objects.first()
    assert a.assignee_mode == AssigneeMode.STUDENT_GROUP_BALANCED
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 1
    bucket = buckets.first()
    assert set(bucket.groups.all()) == {sg0, sg1, sg2}
    assert set(bucket.teachers.all()) == {ct1}


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_few_buckets(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg2.pk],
        '1-teachers': [ct2.pk, ct1.pk]
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    a = Assignment.objects.first()
    assert a.assignee_mode == AssigneeMode.STUDENT_GROUP_BALANCED
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket_1 = buckets.first()
    bucket_2 = buckets.last()
    assert set(bucket_1.groups.all()) == {sg0, sg1}
    assert set(bucket_1.teachers.all()) == {ct1}
    assert set(bucket_2.groups.all()) == {sg2}
    assert set(bucket_2.teachers.all()) == {ct1, ct2}


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_delete_bucket(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 3,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '0-teachers': [ct1.pk, ct2.pk],
        '1-student_groups': [sg2.pk],
        '1-teachers': ct2.pk,
        '2-student_groups': [sg0.pk, sg1.pk],
        '2-teachers': ct1.pk,
        '2-DELETE': 'on'
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    a = Assignment.objects.first()
    assert a.assignee_mode == AssigneeMode.STUDENT_GROUP_BALANCED
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket_1 = buckets.first()
    bucket_2 = buckets.last()
    assert set(bucket_1.groups.all()) == {sg0, sg1}
    assert set(bucket_1.teachers.all()) == {ct1, ct2}
    assert set(bucket_2.groups.all()) == {sg2}
    assert set(bucket_2.teachers.all()) == {ct2}


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_no_buckets_error(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 0,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    assert not Assignment.objects.exists()
    assert not StudentGroupTeacherBucket.objects.exists()
    assert 'Добавьте следующие студенческие группы в бакеты' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_delete_empty_bucket_required(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 1,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    assert not Assignment.objects.exists()
    assert not StudentGroupTeacherBucket.objects.exists()
    content = response.content.decode('utf-8')
    assert 'Удалите пустую форму №1' in content


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_all_buckets_deleted_error(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 3,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '0-teachers': [ct1.pk, ct2.pk],
        '0-DELETE': 'on',
        '1-student_groups': [sg2.pk],
        '1-teachers': ct2.pk,
        '1-DELETE': 'on',
        '2-student_groups': [sg0.pk, sg1.pk],
        '2-teachers': ct1.pk,
        '2-DELETE': 'on'
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    assert not Assignment.objects.exists()
    assert not StudentGroupTeacherBucket.objects.exists()
    assert 'Добавьте следующие студенческие группы в бакеты' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_teacher_required(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '1-student_groups': [sg2.pk],
        '1-teachers': ct2.pk,
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    assert not Assignment.objects.exists()
    assert not StudentGroupTeacherBucket.objects.exists()
    form_data['bucket-0-teachers'] = ct2.pk
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    a = Assignment.objects.first()
    assert a.assignee_mode == AssigneeMode.STUDENT_GROUP_BALANCED
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_all_students_groups_in_buckets_required(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg2.pk],
        '1-teachers': ct2.pk,
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    assert not Assignment.objects.exists()
    assert not StudentGroupTeacherBucket.objects.exists()
    form_data['bucket-0-student_groups'].append(sg1.pk)
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    a = Assignment.objects.first()
    assert a.assignee_mode == AssigneeMode.STUDENT_GROUP_BALANCED
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2


@pytest.mark.django_db
def test_course_assignment_create_balanced_mode_buckets_student_groups_intersection_error(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg1.pk, sg2.pk],
        '1-teachers': ct2.pk,
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    assert not Assignment.objects.exists()
    assert not StudentGroupTeacherBucket.objects.exists()
    assert f"Студенческая группа {sg1.name} уже добавлена в бакет №1" in response.content.decode('utf-8')
    form_data['bucket-1-student_groups'].pop(0)
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    a = Assignment.objects.first()
    assert a.assignee_mode == AssigneeMode.STUDENT_GROUP_BALANCED
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2


@pytest.mark.django_db
def test_course_assignment_update_balanced_mode_add_bucket(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 1,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk, sg2.pk],
        '0-teachers': ct1.pk,
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    client.post(url, form_data, follow=True)
    a = Assignment.objects.first()
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 1
    url = a.get_update_url()
    form_data['bucket-TOTAL_FORMS'] = 2
    form_data['bucket-0-student_groups'].pop(2)
    form_data['bucket-1-student_groups'] = sg2.pk
    form_data['bucket-1-teachers'] = ct2.pk

    client.post(url, form_data, follow=True)
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket1 = buckets.first()
    bucket2 = buckets.last()
    assert set(bucket1.groups.all()) == {sg0, sg1}
    assert set(bucket1.teachers.all()) == {ct1}
    assert set(bucket2.groups.all()) == {sg2}
    assert set(bucket2.teachers.all()) == {ct2}


@pytest.mark.django_db
def test_course_assignment_update_balanced_mode_remembers_bucket_appointment(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    course2 = CourseFactory()
    # Check that these groups are not in options.
    sg11, sg12 = StudentGroupFactory.create_batch(2, course=course2)
    ct11, ct12 = CourseTeacherFactory.create_batch(2, course=course2)
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg2.pk],
        '1-teachers': ct2.pk
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    client.post(url, form_data, follow=True)
    a = Assignment.objects.first()
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    url = a.get_update_url()
    response = client.get(url)
    formset = response.context['buckets_formset']
    assert len(formset.forms) == 2
    form1, form2 = formset.forms
    assert form1.initial == {
        'student_groups': [sg0.pk, sg1.pk],
        'teachers': [ct1.pk]
    }
    assert form2.initial == {
        'student_groups': [sg2.pk],
        'teachers': [ct2.pk]
    }


@pytest.mark.django_db
def test_course_assignment_update_balanced_mode_restricted_to_student_groups(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg1.pk],
        '1-teachers': ct2.pk
    }
    # Actually allowed to. So sg2 is restricted
    form_data['assignment-restricted_to'] = [sg0.pk, sg1.pk]
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    client.post(url, form_data, follow=True)
    a = Assignment.objects.first()
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket1 = buckets.first()
    bucket2 = buckets.last()
    assert set(bucket1.groups.all()) == {sg0}
    assert set(bucket1.teachers.all()) == {ct1}
    assert set(bucket2.groups.all()) == {sg1}
    assert set(bucket2.teachers.all()) == {ct2}

    url = a.get_update_url()
    response = client.get(url)
    formset = response.context['buckets_formset']
    assert len(formset.forms) == 2
    form1, form2 = formset.forms
    student_groups = form1.fields['student_groups'].choices
    # sg2 is restricted but should be possible to choice, because the sg2 can become allowed
    assert set(sg[0] for sg in student_groups) == {sg0.pk, sg1.pk, sg2.pk}

    form_data['bucket-1-student_groups'].append(sg2.pk)
    response = client.post(url, form_data)
    error_msg = f"Студенческая группа {sg2.name} не находится" \
                " в списке &quot;Доступно для групп&quot; задания."
    assert error_msg in response.content.decode('utf-8')
    del form_data['assignment-restricted_to']

    response = client.post(url, form_data)
    assert error_msg not in response.content.decode('utf-8')
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket1 = buckets.first()
    bucket2 = buckets.last()
    assert set(bucket1.groups.all()) == {sg0}
    assert set(bucket1.teachers.all()) == {ct1}
    assert set(bucket2.groups.all()) == {sg1, sg2}
    assert set(bucket2.teachers.all()) == {ct2}


@pytest.mark.django_db
def test_course_assignment_update_balanced_mode_teachers_list(client):
    course1, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    course2 = CourseFactory()
    # Check that teachers of another course are not in options.
    ct11, ct12 = CourseTeacherFactory.create_batch(2, course=course2)
    sg11, sg12 = StudentGroupFactory.create_batch(2, course=course2)
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg1.pk, sg2.pk],
        '1-teachers': ct2.pk
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    client.post(url, form_data, follow=True)
    a = Assignment.objects.first()
    url = a.get_update_url()
    response = client.get(url)

    formset = response.context['buckets_formset']
    assert len(formset.forms) == 2
    form1, form2 = formset.forms
    teachers = form1.fields['teachers'].choices
    assert set(ct[0] for ct in teachers) == {ct1.pk, ct2.pk}


@pytest.mark.django_db
def test_course_assignment_update_balanced_mode_swap_buckets(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg2.pk],
        '1-teachers': ct2.pk
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    client.post(url, form_data, follow=True)

    a = Assignment.objects.first()
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket1 = buckets.first()
    bucket2 = buckets.last()
    assert set(bucket1.groups.all()) == {sg0, sg1}
    assert set(bucket1.teachers.all()) == {ct1}
    assert set(bucket2.groups.all()) == {sg2}
    assert set(bucket2.teachers.all()) == {ct2}


    url = a.get_update_url()
    form_data['bucket-TOTAL_FORMS'] = 2
    form_data['bucket-0-student_groups'] = sg2.pk
    form_data['bucket-0-teachers'] = ct2.pk
    form_data['bucket-1-student_groups'] = [sg0.pk, sg1.pk]
    form_data['bucket-1-teachers'] = ct1.pk
    client.post(url, form_data, follow=True)

    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket1 = buckets.first()
    bucket2 = buckets.last()
    assert set(bucket1.groups.all()) == {sg2}
    assert set(bucket1.teachers.all()) == {ct2}
    assert set(bucket2.groups.all()) == {sg0, sg1}
    assert set(bucket2.teachers.all()) == {ct1}


@pytest.mark.django_db
def test_course_assignment_update_balanced_mode_delete_bucket(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg2.pk],
        '1-teachers': ct2.pk
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    client.post(url, form_data, follow=True)

    a = Assignment.objects.first()
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket1 = buckets.first()
    bucket2 = buckets.last()
    assert set(bucket1.groups.all()) == {sg0, sg1}
    assert set(bucket1.teachers.all()) == {ct1}
    assert set(bucket2.groups.all()) == {sg2}
    assert set(bucket2.teachers.all()) == {ct2}

    url = a.get_update_url()
    form_data['bucket-TOTAL_FORMS'] = 2
    form_data['bucket-0-student_groups'].append(sg2.pk)
    form_data['bucket-1-DELETE'] = 'on'
    client.post(url, form_data, follow=True)

    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 1
    bucket1 = buckets.first()
    assert set(bucket1.groups.all()) == {sg0, sg1, sg2}
    assert set(bucket1.teachers.all()) == {ct1}


@pytest.mark.django_db
def test_course_assignment_update_balanced_mode_validation_error_doesnt_change_state(client):
    course, url, ct1, ct2, sg0, sg1, sg2 = get_assignment_course_models()
    client.login(ct1.teacher)
    form_data = create_assignment_form()
    assignment_formset = {
        'TOTAL_FORMS': 2,
        'INITIAL_FORMS': 0,
        'MIN_NUM_FORMS': 0,
        'MAX_NUM_FORMS': 1000,
        '0-student_groups': [sg0.pk, sg1.pk],
        '0-teachers': ct1.pk,
        '1-student_groups': [sg2.pk],
        '1-teachers': ct2.pk,
    }
    form_data.update(prefixed_form(assignment_formset, 'bucket'))
    client.post(url, form_data, follow=True)

    a = Assignment.objects.first()
    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket1 = buckets.first()
    bucket2 = buckets.last()
    assert set(bucket1.groups.all()) == {sg0, sg1}
    assert set(bucket1.teachers.all()) == {ct1}
    assert set(bucket2.groups.all()) == {sg2}
    assert set(bucket2.teachers.all()) == {ct2}

    url = a.get_update_url()
    form_data.pop('bucket-1-teachers')
    form_data['bucket-2-student_groups'] = sg1.pk
    form_data['bucket-2-teachers'] = ct2.pk
    form_data['bucket-TOTAL_FORMS'] = 3
    client.post(url, form_data, follow=True)

    buckets = StudentGroupTeacherBucket.objects.all()
    assert buckets.count() == 2
    bucket1 = buckets.first()
    bucket2 = buckets.last()
    assert set(bucket1.groups.all()) == {sg0, sg1}
    assert set(bucket1.teachers.all()) == {ct1}
    assert set(bucket2.groups.all()) == {sg2}
    assert set(bucket2.teachers.all()) == {ct2}


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


