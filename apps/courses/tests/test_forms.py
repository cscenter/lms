import factory
import pytest

from courses.constants import AssigneeMode, ClassTypes, MaterialVisibilityTypes
from courses.forms import (
    AssignmentResponsibleTeachersForm, AssignmentResponsibleTeachersFormFactory, CourseClassForm,
    StudentGroupAssigneeForm, StudentGroupAssigneeFormFactory
)
from courses.models import CourseGroupModes, CourseTeacher
from courses.tests.factories import (
    AssignmentFactory, CourseClassFactory, CourseFactory, CourseTeacherFactory, LearningSpaceFactory, SemesterFactory
)
from learning.services import StudentGroupService
from learning.tests.factories import StudentGroupFactory
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_assignment_responsible_teachers_form_factory():
    course = CourseFactory(teachers=TeacherFactory.create_batch(3))
    course_teachers = list(course.course_teachers.all())
    course_teacher1, course_teacher2, course_teacher3 = course_teachers
    course_teacher1.roles = CourseTeacher.roles.reviewer
    course_teacher1.save()
    course_teacher2.roles = CourseTeacher.roles.reviewer
    course_teacher2.save()
    initial = AssignmentResponsibleTeachersFormFactory.to_initial_state(course)
    assert len(initial) == 2

    def get_field_name(id):
        return f"{AssignmentResponsibleTeachersForm.field_prefix}-{id}-active"

    assert get_field_name(course_teacher1.pk) in initial
    assert initial[get_field_name(course_teacher1.pk)]
    assert get_field_name(course_teacher2.pk) in initial
    assert initial[get_field_name(course_teacher2.pk)]
    # Build form class
    form_class = AssignmentResponsibleTeachersFormFactory.build_form_class(course)
    assert form_class.prefix == AssignmentResponsibleTeachersForm.prefix
    assert len(form_class.declared_fields) == 3
    assert get_field_name(course_teacher1.pk) in form_class.declared_fields
    assert get_field_name(course_teacher2.pk) in form_class.declared_fields
    assert get_field_name(course_teacher3.pk) in form_class.declared_fields


@pytest.mark.django_db
def test_assignment_responsible_teachers_form_to_internal():
    course = CourseFactory(teachers=TeacherFactory.create_batch(3))
    course_teacher1, course_teacher2, course_teacher3 = course.course_teachers.all()
    form_class = AssignmentResponsibleTeachersFormFactory.build_form_class(course)
    data = {
        f"teacher-{course_teacher1.pk}-active": 'True',
        f"teacher-{course_teacher2.pk}-active": '1',
        f"teacher-{course_teacher3.pk}-active": 'false',
    }
    data_prefixed = {f"{AssignmentResponsibleTeachersForm.prefix}-{k}": v for k, v
                     in data.items()}
    form = form_class(data=data_prefixed)
    assert form.is_valid()
    exported = form.to_internal()
    assert "responsible_teachers" in exported
    responsible_teachers = exported['responsible_teachers']
    assert len(responsible_teachers) == 2
    assert course_teacher1.pk in responsible_teachers
    assert course_teacher2.pk in responsible_teachers


@pytest.mark.django_db
def test_get_responsible_teachers_form():
    course = CourseFactory(teachers=TeacherFactory.create_batch(3))
    course_teacher1, course_teacher2, course_teacher3 = course.course_teachers.all()
    course_teacher1.roles = CourseTeacher.roles.reviewer
    course_teacher1.save()
    form = AssignmentResponsibleTeachersFormFactory.build_form(course)
    assert not form.is_bound

    def get_field_name(id):
        return f"{AssignmentResponsibleTeachersForm.field_prefix}-{id}-active"

    assert len(form.initial) == 1
    assert get_field_name(course_teacher1.pk) in form.initial


@pytest.mark.django_db
def test_student_group_assignee_form_factory_get_initial_state():
    course = CourseFactory(teachers=TeacherFactory.create_batch(3),
                           group_mode=CourseGroupModes.MANUAL)
    course_teacher1, course_teacher2, course_teacher3 = course.course_teachers.all()
    initial = StudentGroupAssigneeFormFactory.get_initial_state(course)
    # Do not fallback to the course group assignees
    assert not initial
    assignment = AssignmentFactory(course=course, assignee_mode=AssigneeMode.DISABLED)
    initial = StudentGroupAssigneeFormFactory.get_initial_state(course)
    # No course groups at all
    assert not initial
    # Set default responsible teachers
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)
    StudentGroupService.add_assignees(student_group1, teachers=[course_teacher1])
    StudentGroupService.add_assignees(student_group2, teachers=[course_teacher2, course_teacher3])
    initial = StudentGroupAssigneeFormFactory.get_initial_state(course)
    assert not initial
    # Customize responsible teachers
    assignment.assignee_mode = AssigneeMode.STUDENT_GROUP_CUSTOM
    assignment.save()
    StudentGroupService.set_custom_assignees_for_assignment(assignment=assignment, data={
        student_group1.pk: [course_teacher1.pk],
        student_group2.pk: [course_teacher1.pk, course_teacher2.pk],
    })
    initial = StudentGroupAssigneeFormFactory.get_initial_state(course, assignment=assignment)
    assert len(initial) == 1
    assert f"assignee-{student_group1.pk}-teacher" in initial


@pytest.mark.django_db
def test_student_group_assignee_form_factory_build_form_class():
    course = CourseFactory(teachers=TeacherFactory.create_batch(3),
                           group_mode=CourseGroupModes.MANUAL)
    form_class = StudentGroupAssigneeFormFactory.build_form_class(course)
    assert len(form_class.base_fields) == 0
    StudentGroupFactory.create_batch(2, course=course)
    form_class = StudentGroupAssigneeFormFactory.build_form_class(course)
    # `name` read-only field + `teacher` select field for each student group
    assert len(form_class.base_fields) == 4


@pytest.mark.django_db
def test_student_group_assignee_form_factory_form_is_valid():
    course = CourseFactory(teachers=TeacherFactory.create_batch(3),
                           group_mode=CourseGroupModes.MANUAL)
    course_teacher1, course_teacher2, course_teacher3 = course.course_teachers.all()
    course_teacher_other = CourseTeacherFactory()
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)
    # Incomplete data
    data = {
        f"assignee-{student_group1.pk}-teacher": course_teacher1.pk,
    }

    def get_prefixed(form_data):
        return {f"{StudentGroupAssigneeForm.prefix}-{k}": v for k, v in form_data.items()}

    form = StudentGroupAssigneeFormFactory.build_form(course, data=get_prefixed(data))
    assert not form.is_valid()
    form = StudentGroupAssigneeFormFactory.build_form(course, is_required=False, data=get_prefixed(data))
    assert form.is_valid()
    # Invalid data
    data = {
        f"assignee-{student_group1.pk}-teacher": course_teacher1.pk,
        f"assignee-{student_group2.pk}-teacher": course_teacher_other.pk,
    }
    form = StudentGroupAssigneeFormFactory.build_form(course, data=get_prefixed(data))
    assert not form.is_valid()
    form = StudentGroupAssigneeFormFactory.build_form(course, is_required=False, data=get_prefixed(data))
    assert not form.is_valid()
    data = {
        f"assignee-{student_group1.pk}-teacher": course_teacher1.pk,
        f"assignee-{student_group2.pk}-teacher": 'wrong type',
    }
    form = StudentGroupAssigneeFormFactory.build_form(course, data=get_prefixed(data))
    assert not form.is_valid()
    # Valid data
    data = {
        f"assignee-{student_group1.pk}-teacher": course_teacher1.pk,
        f"assignee-{student_group2.pk}-teacher": course_teacher2.pk,
    }
    form = StudentGroupAssigneeFormFactory.build_form(course, data=get_prefixed(data))
    assert form.is_valid()


@pytest.mark.django_db
def test_student_group_assignee_form_to_internal():
    course = CourseFactory(teachers=TeacherFactory.create_batch(3),
                           group_mode=CourseGroupModes.MANUAL)
    course_teacher1, course_teacher2, course_teacher3 = course.course_teachers.all()
    student_group1, student_group2 = StudentGroupFactory.create_batch(2, course=course)

    def get_prefixed(form_data):
        return {f"{StudentGroupAssigneeForm.prefix}-{k}": v for k, v in form_data.items()}

    form = StudentGroupAssigneeFormFactory.build_form(course)
    assert not form.to_internal()
    # Invalid data
    data = {
        f"assignee-{student_group1.pk}-teacher": course_teacher1.pk,
    }
    form = StudentGroupAssigneeFormFactory.build_form(course, data=get_prefixed(data))
    assert not form.is_valid()
    assert not form.to_internal()
    # Valid
    data = {
        f"assignee-{student_group1.pk}-teacher": course_teacher1.pk,
        f"assignee-{student_group2.pk}-teacher": course_teacher2.pk,
    }
    form = StudentGroupAssigneeFormFactory.build_form(course, data=get_prefixed(data))
    assert form.is_valid()
    output = form.to_internal()
    assert len(output) == 2
    assert output[student_group1.pk] == [course_teacher1.pk]
    assert output[student_group2.pk] == [course_teacher2.pk]

@pytest.mark.django_db
def test_courseclassform_is_repeated_create_update_mods():
    course_class = CourseClassFactory(course__semester=SemesterFactory.create_current())
    data = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
    data.update({
        'venue': LearningSpaceFactory(branch=course_class.course.main_branch),
        'is_repeated': True,
        'number_of_repeats': 3
    })
    
    create_form = CourseClassForm(course=course_class.course, data=data)
    update_form = CourseClassForm(instance=course_class, course=course_class.course, data=data)
    assert 'is_repeated' in create_form.fields
    assert 'number_of_repeats' in create_form.fields
    assert create_form.is_valid()
    assert 'is_repeated' in create_form.data
    assert 'number_of_repeats' in create_form.data
    assert 'is_repeated' in create_form.cleaned_data
    assert 'number_of_repeats' in create_form.cleaned_data
    
    assert 'is_repeated' not in update_form.fields
    assert 'number_of_repeats' not in update_form.fields
    assert update_form.is_valid()
    assert 'is_repeated' in update_form.data
    assert 'number_of_repeats' in update_form.data
    assert 'is_repeated' not in update_form.cleaned_data
    assert 'number_of_repeats' not in update_form.cleaned_data

@pytest.mark.django_db
def test_courseclassform_number_of_repeats_validation():
    course = CourseFactory(semester=SemesterFactory.create_current())
    data = factory.build(dict, FACTORY_CLASS=CourseClassFactory)
    data.update({
        'venue': LearningSpaceFactory(branch=course.main_branch),
        'is_repeated': True,
        'number_of_repeats': 1,
        'date': course.semester.starts_at
    })
    
    assert CourseClassForm(course=course, data=data).is_valid(), CourseClassForm(course=course, data=data).errors
    max_days = (course.semester.ends_at.date() - course.semester.starts_at.date()).days
    max_repeats = max_days // 7 + 1
    data["number_of_repeats"] = max_repeats
    assert CourseClassForm(course=course, data=data).is_valid(), CourseClassForm(course=course, data=data).errors
    data["number_of_repeats"] = max_repeats + 1
    assert not CourseClassForm(course=course, data=data).is_valid()
