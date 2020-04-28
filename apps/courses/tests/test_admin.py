import pytest
from bs4 import BeautifulSoup
from django.forms import inlineformset_factory

from core.admin import get_admin_url
from core.models import Branch
from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.admin import CourseTeacherInline, CourseBranchInline
from courses.constants import MaterialVisibilityTypes
from courses.models import Assignment, AssignmentSubmissionTypes, Course, \
    CourseTeacher, CourseBranch
from courses.tests.factories import CourseFactory, SemesterFactory, \
    MetaCourseFactory
from learning.settings import Branches, GradingSystems
from users.tests.factories import CuratorFactory, TeacherFactory


def _get_course_post_data(course=None):
    if course is None:
        branch = BranchFactory(code=Branches.SPB)
        meta_course = MetaCourseFactory()
        term = SemesterFactory.create_current()
    else:
        branch = course.main_branch
        meta_course = course.meta_course
        term = course.semester
    form_data = {
        "meta_course": meta_course.pk,
        "main_branch": branch.pk,
        "semester": term.pk,
        "grading_type": GradingSystems.BASE,
        "capacity": 0,
        "language": "ru",
        "materials_visibility": MaterialVisibilityTypes.VISIBLE,
    }
    return form_data


def _get_course_teachers_post_data(course=None):
    """Returns POST-data for inline formset"""
    prefix = 'course_teachers'
    if course is not None:
        course_teachers = CourseTeacher.objects.filter(course=course)
        initial_forms = len(course_teachers)
    else:
        initial_forms = 0
        teacher = TeacherFactory()
        course_teachers = [CourseTeacher(teacher=teacher,
                                         course=course,
                                         roles=CourseTeacher.roles.lecturer)]
    form_data = {
        f'{prefix}-INITIAL_FORMS': initial_forms,
        f'{prefix}-MIN_NUM_FORMS': 1,
        f'{prefix}-TOTAL_FORMS': len(course_teachers),
        f'{prefix}-MAX_NUM_FORMS': 1000,
    }
    for i, course_teacher in enumerate(course_teachers):
        roles = [v for v, has_role in course_teacher.roles.items() if has_role]
        data = {
            f'{prefix}-{i}-teacher': course_teacher.teacher_id,
            f'{prefix}-{i}-roles': roles,
            f'{prefix}-{i}-notify_by_default': course_teacher.notify_by_default,
        }
        if course is not None:
            data[f'{prefix}-{i}-id'] = course_teacher.pk
            data[f'{prefix}-{i}-course'] = course.pk
        form_data.update(data)
    return form_data


def _get_course_branch_post_data(course=None):
    prefix = 'coursebranch_set'
    if course is not None:
        course_branches = CourseBranch.objects.filter(course=course)
        initial_forms = len(course_branches)
    else:
        initial_forms = 0
        course_branches = []
    form_data = {
        f'{prefix}-INITIAL_FORMS': initial_forms,
        f'{prefix}-MIN_NUM_FORMS': 0,
        f'{prefix}-TOTAL_FORMS': len(course_branches),
        f'{prefix}-MAX_NUM_FORMS': 1000,
    }
    for i, course_branch in enumerate(course_branches):
        data = {
            f'{prefix}-{i}-branch': course_branch.branch_id,
            f'{prefix}-{i}-is_main': course_branch.is_main,
        }
        if course is not None:
            data[f'{prefix}-{i}-id'] = course_branch.pk
            data[f'{prefix}-{i}-course'] = course.pk
        form_data.update(data)
    return form_data


@pytest.mark.django_db
def test_course_teacher_inline_formset():
    teacher = TeacherFactory()
    CourseTeacherInlineFormSet = inlineformset_factory(
        Course, CourseTeacher, formset=CourseTeacherInline.formset,
        fields=['teacher', 'roles', 'notify_by_default'])
    data = {
        'course_teachers-INITIAL_FORMS': 0,
        'course_teachers-MIN_NUM_FORMS': 1,
        'course_teachers-MAX_NUM_FORMS': 1000,
        'course_teachers-TOTAL_FORMS': 1,
        'course_teachers-0-teacher': teacher.pk,
        'course_teachers-0-roles': ['lecturer'],
    }
    form_set = CourseTeacherInlineFormSet(data, instance=CourseFactory())
    assert form_set.is_valid()
    course = CourseFactory()
    data = _get_course_teachers_post_data(course)
    form_set = CourseTeacherInlineFormSet(data, instance=course)
    assert form_set.is_valid()


@pytest.mark.django_db
def test_course_branches_inline_formset():
    CourseBranchInlineFormSet = inlineformset_factory(
        Course, CourseBranch, formset=CourseBranchInline.formset,
        fields=['branch', 'is_main'])
    data = {
        'coursebranch_set-INITIAL_FORMS': 0,
        'coursebranch_set-MIN_NUM_FORMS': 0,
        'coursebranch_set-MAX_NUM_FORMS': 1000,
        'coursebranch_set-TOTAL_FORMS': 0,
    }
    form_set = CourseBranchInlineFormSet(data, instance=CourseFactory())
    assert form_set.is_valid()
    course = CourseFactory()
    CourseBranch(course=course, branch=BranchFactory()).save()
    data = _get_course_branch_post_data(course)
    form_set = CourseBranchInlineFormSet(data, instance=course)
    assert form_set.is_valid()


@pytest.mark.django_db
def test_course_branches_main_branch(client):
    """Create course with main branch only"""
    curator = CuratorFactory()
    client.login(curator)
    form_data = _get_course_post_data(course=None)
    branch = Branch.objects.get(pk=form_data["main_branch"])
    course_teachers_form_data = _get_course_teachers_post_data()
    form_data.update(course_teachers_form_data)
    branches_form_data = _get_course_branch_post_data()
    form_data.update(branches_form_data)
    add_url = reverse('admin:courses_course_add')
    response = client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    message = list(response.context['messages'])[0]
    assert 'success' in message.tags
    assert Course.objects.count() == 1
    course = Course.objects.get()
    assert course.branches.count() == 1
    assert course.branches.get() == branch
    assert CourseBranch.objects.get(course=course).is_main


@pytest.mark.django_db
def test_course_branches_invalid(client):
    """
    Create course with one additional branch != main branch but marked
    as main (.is_main=True)
    """
    client.login(CuratorFactory())
    form_data = _get_course_post_data(course=None)
    course_teachers_form_data = _get_course_teachers_post_data(course=None)
    form_data.update(course_teachers_form_data)
    branches_form_data = _get_course_branch_post_data(course=None)
    branch = BranchFactory()
    branches_form_data.update({
        'coursebranch_set-TOTAL_FORMS': 1,
        'coursebranch_set-0-branch': branch.pk,
        'coursebranch_set-0-is_main': True,
    })
    form_data.update(branches_form_data)
    add_url = reverse('admin:courses_course_add')
    response = client.post(add_url, form_data)
    assert response.status_code == 200
    # Check error message about additional branch is marked as main
    assert "additional branch as main" in response.context_data['errors'].as_text()


@pytest.mark.django_db
def test_course_branches_main_branch_and_additional(client):
    """Create course with one additional branch != main branch"""
    client.login(CuratorFactory())
    form_data = _get_course_post_data(course=None)
    course_teachers_form_data = _get_course_teachers_post_data(course=None)
    form_data.update(course_teachers_form_data)
    branches_form_data = _get_course_branch_post_data(course=None)
    branch = BranchFactory()
    branches_form_data.update({
        'coursebranch_set-TOTAL_FORMS': 1,
        'coursebranch_set-0-branch': branch.pk,
        'coursebranch_set-0-is_main': False,
    })
    form_data.update(branches_form_data)
    add_url = reverse('admin:courses_course_add')
    response = client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    assert Course.objects.count() == 1
    course = Course.objects.get()
    assert course.branches.count() == 2
    assert CourseBranch.objects.count() == 2
    # Additional branch will be saved first
    cb1, cb2 = CourseBranch.objects.order_by('pk')
    assert cb1.branch == branch
    assert not cb1.is_main
    assert cb2.branch == course.main_branch
    assert cb2.is_main


@pytest.mark.django_db
def test_course_branches_main_branch_and_additional2(client):
    """Create course with one additional branch == main branch"""
    client.login(CuratorFactory())
    form_data = _get_course_post_data(course=None)
    course_teachers_form_data = _get_course_teachers_post_data(course=None)
    form_data.update(course_teachers_form_data)
    branches_form_data = _get_course_branch_post_data(course=None)
    branches_form_data.update({
        'coursebranch_set-TOTAL_FORMS': 1,
        'coursebranch_set-0-branch': form_data['main_branch'],
        'coursebranch_set-0-is_main': True,
    })
    form_data.update(branches_form_data)
    add_url = reverse('admin:courses_course_add')
    response = client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    assert Course.objects.count() == 1
    course = Course.objects.get()
    assert course.branches.count() == 1
    assert CourseBranch.objects.count() == 1
    cb = CourseBranch.objects.get()
    assert cb.branch_id == course.main_branch_id
    assert cb.is_main


@pytest.mark.django_db
def test_course_branches_update_main_branch(client):
    client.login(CuratorFactory())
    main_branch = BranchFactory()
    course = CourseFactory(main_branch=main_branch,
                           teachers=[TeacherFactory()])
    cb1 = CourseBranch.objects.get(course=course, branch=main_branch)
    branch = BranchFactory()
    cb2 = CourseBranch(course=course, branch=branch, is_main=False)
    cb2.save()
    form_data = _get_course_post_data(course)
    course_teachers_form_data = _get_course_teachers_post_data(course)
    form_data.update(course_teachers_form_data)
    branches_form_data = _get_course_branch_post_data(course)
    form_data.update(branches_form_data)
    form_data['main_branch'] = branch.pk
    update_url = reverse('admin:courses_course_change', args=[course.pk])
    # Validation error
    response = client.post(update_url, form_data)
    assert response.status_code == 200
    assert "additional branch as main" in response.context_data['errors'].as_text()
    if branches_form_data['coursebranch_set-0-branch'] == cb1.branch_id:
        prev_main_branch_index = 0
    else:
        prev_main_branch_index = 1
    branches_form_data[f'coursebranch_set-{prev_main_branch_index}-is_main'] = False
    form_data.update(branches_form_data)
    response = client.post(update_url, form_data)
    assert response.status_code == 302
    assert CourseBranch.objects.count() == 2
    course_branch1, course_branch2 = CourseBranch.objects.order_by('pk')
    assert cb1 == course_branch1
    assert not course_branch1.is_main
    assert cb2 == course_branch2
    assert course_branch2.is_main


@pytest.mark.django_db
def test_assignment_admin_view(settings, client):
    curator = CuratorFactory()
    client.login(curator)
    # Datetime widget formatting depends on locale, change it
    settings.LANGUAGE_CODE = 'ru'
    co_in_spb = CourseFactory(main_branch__code=Branches.SPB)
    co_in_nsk = CourseFactory(main_branch__code=Branches.NSK)
    form_data = {
        "course": "",
        "submission_type": AssignmentSubmissionTypes.ONLINE,
        "deadline_at_0": "29.06.2017",
        "deadline_at_1": "00:00:00",
        "title": "title",
        "text": "text",
        "passing_score": "3",
        "maximum_score": "5",
        "weight": "1.00",
        "_continue": "save_and_continue"
    }
    # Test with empty branch aware field
    add_url = reverse('admin:courses_assignment_add')
    response = client.post(add_url, form_data)
    assert response.status_code == 200
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    # Send valid data
    form_data["course"] = co_in_spb.pk
    response = client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    message = list(response.context['messages'])[0]
    assert 'success' in message.tags
    assert Assignment.objects.count() == 1
    assignment = Assignment.objects.first()
    # In SPB we have msk timezone (UTC +3)
    # In DB we store datetime values in UTC
    assert assignment.deadline_at.day == 28
    assert assignment.deadline_at.hour == 21
    assert assignment.deadline_at.minute == 0
    # Admin widget shows localized time
    change_url = get_admin_url(assignment)
    response = client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    date_input = widget.find('input', {"name": 'deadline_at_0'})
    assert date_input.get('value') == '29.06.2017'
    # We can't update course offering through admin interface
    response = client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    assert assignment.course_id == co_in_spb.pk
    # But do it manually to test widget
    assignment.course = co_in_nsk
    assignment.save()
    form_data["deadline_at_1"] = "00:00:00"
    response = client.post(change_url, form_data)
    assignment.refresh_from_db()
    response = client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    assert assignment.deadline_at.hour == 17  # UTC +7 in nsk
    assert assignment.deadline_at.minute == 0
    # Update course and deadline time
    assignment.course = co_in_spb
    assignment.save()
    form_data["deadline_at_1"] = "06:00:00"
    response = client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    response = client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '06:00:00'
    assert assignment.deadline_at.hour == 3
    assert assignment.deadline_at.minute == 0
    # Update course offering and deadline, but choose values when
    # UTC time shouldn't change
    assignment.course = co_in_nsk
    assignment.save()
    form_data["deadline_at_1"] = "10:00:00"
    response = client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    response = client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '10:00:00'
    assert assignment.deadline_at.hour == 3
    assert assignment.deadline_at.minute == 0
    assert assignment.course_id == co_in_nsk.pk