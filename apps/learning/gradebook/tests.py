import csv
import datetime
import io
from decimal import Decimal
from io import StringIO, BytesIO

import pytest
import pytz
from bs4 import BeautifulSoup
from django.contrib import messages
from django.utils.encoding import smart_bytes, force_bytes

from auth.mixins import PermissionRequiredMixin
from auth.permissions import perm_registry
from core.urls import reverse
from courses.models import AssignmentSubmissionFormats
from courses.tests.factories import SemesterFactory, CourseFactory, \
    AssignmentFactory
from learning.gradebook import gradebook_data, BaseGradebookForm, \
    GradeBookFormFactory
from learning.gradebook.imports import AssignmentGradesImport
from learning.models import StudentAssignment, Enrollment
from learning.services import get_student_profile
from learning.settings import GradingSystems, \
    StudentStatuses, GradeTypes, Branches
from learning.tests.factories import EnrollmentFactory
from users.tests.factories import TeacherFactory, UserFactory, StudentFactory, \
    CuratorFactory


# TODO: test redirect to gradebook for teachers if only 1 course in current term


@pytest.mark.django_db
def test_view_gradebook_permission():
    teacher = TeacherFactory()
    teacher_other = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    assert teacher.has_perm("teaching.view_own_gradebook", course)
    assert not teacher_other.has_perm("teaching.view_own_gradebook", course)
    e = EnrollmentFactory(course=course)
    assert not e.student.has_perm("teaching.view_own_gradebook", course)
    assert not UserFactory().has_perm("teaching.view_own_gradebook", course)
    curator = CuratorFactory()
    assert not curator.has_perm("teaching.view_own_gradebook", course)
    assert curator.has_perm("teaching.view_gradebook")


@pytest.mark.django_db
def test_gradebook_view_security(client, lms_resolver):
    course = CourseFactory()
    resolver = lms_resolver(course.get_gradebook_url())
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == "teaching.view_own_gradebook"
    assert resolver.func.view_class.permission_required in perm_registry


@pytest.mark.django_db
def test_gradebook_csv_view_security(client, lms_resolver):
    course = CourseFactory()
    resolver = lms_resolver(course.get_gradebook_url(format='csv'))
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == "teaching.view_own_gradebook"
    assert resolver.func.view_class.permission_required in perm_registry


@pytest.mark.django_db
def test_gradebook_in_csv_format(client):
    teacher = TeacherFactory()
    student1, student2 = StudentFactory.create_batch(2)
    co = CourseFactory.create(teachers=[teacher])
    a1, a2 = AssignmentFactory.create_batch(2, course=co)
    for s in [student1, student2]:
        EnrollmentFactory.create(student=s, course=co)
    gradebook_url = co.get_gradebook_url(format="csv")
    combos = [(a, s, grade + 1)
              for ((a, s), grade)
              in zip([(a, s)
                      for a in [a1, a2]
                      for s in [student1, student2]],
                     range(4))]
    for a, s, score in combos:
        a_s = StudentAssignment.objects.get(student=s, assignment=a)
        a_s.score = score
        a_s.save()
    client.login(teacher)
    gradebook_csv = client.get(gradebook_url).content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(gradebook_csv)) if s]
    assert len(data) == 3
    assert a1.title in data[0]
    row_last_names = [row[0] for row in data]
    for a, s, grade in combos:
        row = row_last_names.index(s.last_name)
        col = data[0].index(a.title)
        assert grade == int(data[row][col])


@pytest.mark.django_db
def test_nonempty_gradebook_view(client):
    teacher = TeacherFactory()
    students = StudentFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher])
    for student in students:
        EnrollmentFactory.create(student=student, course=course)
    as_online = AssignmentFactory.create_batch(2, course=course)
    as_offline = AssignmentFactory.create_batch(
        3, course=course,
        submission_type=AssignmentSubmissionFormats.OTHER)
    url = course.get_gradebook_url()
    client.login(teacher)
    response = client.get(url)
    for student in students:
        name = "{} {}.".format(student.last_name,
                                    student.first_name[0])
        assert smart_bytes(name) in response.content
    for as_ in as_online:
        assert smart_bytes(as_.title) in response.content
        for s in students:
            a_s = StudentAssignment.objects.get(student=s, assignment=as_)
            assert smart_bytes(a_s.get_teacher_url()) in response.content
    for as_ in as_offline:
        assert smart_bytes(as_.title) in response.content
        for s in students:
            a_s = StudentAssignment.objects.get(student=s, assignment=as_)
            assert response.context['form'].GRADE_PREFIX + str(a_s.pk) in response.context['form'].fields


@pytest.mark.django_db
def test_save_gradebook(client, assert_redirect):
    teacher = TeacherFactory()
    client.login(teacher)
    students = StudentFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher])
    for student in students:
        EnrollmentFactory.create(student=student, course=course)
    a1, a2 = AssignmentFactory.create_batch(
        2,
        course=course,
        submission_type=AssignmentSubmissionFormats.OTHER)
    teacher_gradebook_url = course.get_gradebook_url()
    form = {}
    pairs = zip([StudentAssignment.objects.get(student=student, assignment=a)
                 for student in students
                 for a in [a1, a2]],
        [2, 3, 4, 5])
    for submission, grade in pairs:
        enrollment = Enrollment.active.get(student=submission.student,
                                           course=course)
        field_name = BaseGradebookForm.GRADE_PREFIX + str(submission.pk)
        form[field_name] = grade
        field_name = BaseGradebookForm.FINAL_GRADE_PREFIX + str(enrollment.pk)
        form["initial-" + field_name] = GradeTypes.NOT_GRADED
        form[field_name] = GradeTypes.GOOD
    assert_redirect(client.post(teacher_gradebook_url, form),
                    teacher_gradebook_url)
    for a_s, grade in pairs:
        assert grade == StudentAssignment.objects.get(pk=a_s.pk).score
    for student in students:
        assert 'good' == Enrollment.active.get(student=student,
                                               course=course).grade


@pytest.mark.django_db
def test_gradebook_data(settings):
    co = CourseFactory()
    e1, e2, e3, e4, e5 = EnrollmentFactory.create_batch(5, course=co)
    a1, a2, a3 = AssignmentFactory.create_batch(3, course=co,
                                                passing_score=1, maximum_score=10)
    data = gradebook_data(co)
    assert len(data.assignments) == 3
    assert len(data.students) == 5
    e1.is_deleted = True
    e1.save()
    data = gradebook_data(co)
    assert len(data.assignments) == 3
    assert len(data.students) == 4
    e1.is_deleted = False
    e1.save()
    # Check assignments order (should be sorted by deadline)
    a1.deadline_at = datetime.datetime(2017, 11, 1, 0, 0, 0, 0, tzinfo=pytz.UTC)
    a2.deadline_at = datetime.datetime(2017, 11, 9, 0, 0, 0, 0, tzinfo=pytz.UTC)
    a3.deadline_at = datetime.datetime(2017, 11, 5, 0, 0, 0, 0, tzinfo=pytz.UTC)
    a1.save()
    a2.save()
    a3.save()
    data = gradebook_data(co)
    assert list(data.assignments.values()) == [a1, a3, a2]
    # Check students order (should be sorted by surname)
    s1 = e1.student
    s3 = e3.student
    s1.last_name, s3.last_name = s3.last_name, s1.last_name
    s1.save()
    s3.save()
    data = gradebook_data(co)
    assert list(data.students) == [e3.student_id, e2.student_id, e1.student_id,
                                   e4.student_id, e5.student_id]
    # Check grid values
    sa = StudentAssignment.objects.get(assignment=a2, student_id=e3.student_id)
    sa.score = 3
    sa.save()
    data = gradebook_data(co)
    s3_index = 0
    a2_index = 2
    s3_a2_progress = data.submissions[s3_index][a2_index]
    assert s3_a2_progress is not None
    assert s3_a2_progress.score == 3
    for row in data.submissions:
        for cell in row:
            assert cell is not None
    # Check total score
    data = gradebook_data(co)
    assert data.students[s1.pk].total_score == 0
    assert data.students[e2.student_id].total_score == 0
    assert data.students[s3.pk].total_score == 3
    assert data.students[e4.student_id].total_score == 0
    assert data.students[e5.student_id].total_score == 0
    # Check grid for student with inactive status
    student_profile = get_student_profile(e5.student, settings.SITE_ID)
    student_profile.status = StudentStatuses.EXPELLED
    student_profile.save()
    a_new = AssignmentFactory(course=co, passing_score=3, maximum_score=7)
    data = gradebook_data(co)
    s5_index = 4
    new_a_index = 3
    for x, row in enumerate(data.submissions):
        for y, cell in enumerate(row):
            if x == s5_index and y == new_a_index:
                assert data.submissions[x][y] is None
            else:
                assert data.submissions[x][y] is not None


@pytest.mark.django_db
def test_empty_gradebook_data():
    """Smoke test for gradebook without assignments"""
    co = CourseFactory()
    data = gradebook_data(co)
    assert len(data.assignments) == 0
    assert len(data.students) == 0
    assert len(data.submissions) == 0
    e1, e2, e3, e4, e5 = EnrollmentFactory.create_batch(5, course=co)
    data = gradebook_data(co)
    assert len(data.assignments) == 0
    assert len(data.students) == 5
    assert len(data.submissions) == 5
    s1_submissions = data.submissions[0]
    assert len(s1_submissions) == 0


@pytest.mark.django_db
def test_empty_gradebook_view(client):
    """Smoke test for gradebook view with empty assignments list"""
    teacher = TeacherFactory()
    students = StudentFactory.create_batch(3)
    co1 = CourseFactory.create(teachers=[teacher])
    co2 = CourseFactory.create(teachers=[teacher])
    for student in students:
        EnrollmentFactory.create(student=student, course=co1)
        EnrollmentFactory.create(student=student, course=co2)
    client.login(teacher)
    response = client.get(co1.get_gradebook_url())
    for student in students:
        name = "{} {}.".format(student.last_name, student.first_name[0])
        assert smart_bytes(name) in response.content
        enrollment = Enrollment.active.get(student=student, course=co1)
        field = 'final_grade_{}'.format(enrollment.pk)
        assert field in response.context['form'].fields
    assert len(students) == len(response.context['form'].fields)
    for co in [co1, co2]:
        url = co.get_gradebook_url()
        assert smart_bytes(url) in response.content


@pytest.mark.django_db
def test_total_score(client):
    """Calculate total score by assignments for course offering"""
    teacher = TeacherFactory()
    client.login(teacher)
    co = CourseFactory.create(teachers=[teacher])
    student = StudentFactory()
    EnrollmentFactory.create(student=student, course=co)
    assignments_count = 2
    assignments = AssignmentFactory.create_batch(assignments_count,
                                                 course=co)
    # AssignmentFactory implicitly creates StudentAssignment instances
    # with empty grade value.
    default_score = 10
    for assignment in assignments:
        a_s = StudentAssignment.objects.get(student=student,
                                            assignment=assignment)
        a_s.score = default_score
        a_s.save()
    expected_total_score = assignments_count * default_score
    response = client.get(co.get_gradebook_url())
    head_student = next(iter(response.context['gradebook'].students.values()))
    assert head_student.total_score == expected_total_score


@pytest.mark.django_db
def test_total_score_weight(client):
    teacher = TeacherFactory()
    co = CourseFactory(teachers=[teacher])
    client.login(teacher)
    student = StudentFactory()
    EnrollmentFactory(student=student, course=co)
    a1 = AssignmentFactory(course=co, weight=Decimal('1.00'), maximum_score=10)
    a2 = AssignmentFactory(course=co, weight=Decimal('0.3'), maximum_score=20)
    a3 = AssignmentFactory(course=co, weight=Decimal('0.3'), maximum_score=3)
    sa1 = StudentAssignment.objects.get(student=student, assignment=a1)
    sa2 = StudentAssignment.objects.get(student=student, assignment=a2)
    sa1.score = 3
    sa1.save()
    sa2.score = 12
    sa2.save()
    expected_total_score = 3 * a1.weight + 12 * a2.weight
    response = client.get(co.get_gradebook_url())
    head_student = next(iter(response.context['gradebook'].students.values()))
    assert head_student.total_score == expected_total_score
    a4 = AssignmentFactory(course=co, weight=Decimal('0'), maximum_score=3)
    sa4 = StudentAssignment.objects.get(student=student, assignment=a4)
    sa4.score = 2
    sa4.save()
    response = client.get(co.get_gradebook_url())
    head_student = next(iter(response.context['gradebook'].students.values()))
    assert head_student.total_score == expected_total_score


@pytest.mark.django_db
def test_save_gradebook_form(client):
    """Make sure that all fields are optional. Save only sent data"""
    teacher = TeacherFactory.create()
    client.login(teacher)
    co = CourseFactory.create(teachers=[teacher])
    a1, a2 = AssignmentFactory.create_batch(
        2, course=co,
        submission_type=AssignmentSubmissionFormats.OTHER,
        passing_score=10, maximum_score=20)
    e1, e2 = EnrollmentFactory.create_batch(2, course=co,
                                            grade=GradeTypes.EXCELLENT)
    # We have 2 enrollments with `excellent` final grades. Change one of them.
    field_name = BaseGradebookForm.FINAL_GRADE_PREFIX + str(e1.pk)
    form_data = {
        "initial-" + field_name: GradeTypes.EXCELLENT,
        field_name: GradeTypes.GOOD,
        # Empty value should be discarded
        BaseGradebookForm.FINAL_GRADE_PREFIX + str(e2.pk): '',
    }
    data = gradebook_data(co)
    form_cls = GradeBookFormFactory.build_form_class(data)
    form = form_cls(data=form_data)
    # Initial should be empty since we want to save only sent data
    assert not form.initial
    assert form.is_valid()
    assert len(form.changed_data) == 1
    assert field_name in form.changed_data
    conflicts = form.save()
    assert not conflicts
    e1.refresh_from_db()
    e2.refresh_from_db()
    assert e1.grade == GradeTypes.GOOD
    assert e2.grade == GradeTypes.EXCELLENT
    # Now change one of submission grade
    sa11 = StudentAssignment.objects.get(student_id=e1.student_id, assignment=a1)
    sa12 = StudentAssignment.objects.get(student_id=e1.student_id, assignment=a2)
    field_name = BaseGradebookForm.GRADE_PREFIX + str(sa11.pk)
    form_data = {
        field_name: -5,  # invalid value
        # Empty value should be discarded
        BaseGradebookForm.FINAL_GRADE_PREFIX + str(e2.pk): '',
    }
    data = gradebook_data(co)
    form_cls = GradeBookFormFactory.build_form_class(data)
    form = form_cls(data=form_data)
    assert not form.is_valid()
    form_data[field_name] = 2
    form_cls = GradeBookFormFactory.build_form_class(gradebook_data(co))
    form = form_cls(data=form_data)
    assert form.is_valid()
    form.save()
    sa11.refresh_from_db(), sa12.refresh_from_db()
    assert sa11.score == 2
    assert sa12.score is None
    e1.refresh_from_db(), e2.refresh_from_db()
    assert e1.grade == GradeTypes.GOOD
    assert e2.grade == GradeTypes.EXCELLENT


@pytest.mark.django_db
def test_save_gradebook_l10n(client):
    """Input value for grade value can be int or decimal"""
    teacher = TeacherFactory()
    client.login(teacher)
    student = StudentFactory()
    co = CourseFactory.create(teachers=[teacher])
    EnrollmentFactory.create(student=student, course=co)
    a = AssignmentFactory(course=co,
                          submission_type=AssignmentSubmissionFormats.OTHER,
                          passing_score=10, maximum_score=40)
    sa = StudentAssignment.objects.get(student=student, assignment=a)
    field_name = BaseGradebookForm.GRADE_PREFIX + str(sa.pk)
    data = gradebook_data(co)
    form_cls = GradeBookFormFactory.build_form_class(data)
    form = form_cls(data={field_name: 11})
    assert form.is_valid()
    form = form_cls(data={field_name: '11.1'})
    assert form.is_valid()
    form = form_cls(data={field_name: '11,3'})
    assert form.is_valid()


@pytest.mark.django_db
def test_save_gradebook_less_than_passing_score(client):
    """
    Make sure the form is valid when score is less than passing score, but not
    the lowest possible value.
    """
    teacher = TeacherFactory()
    client.login(teacher)
    student = StudentFactory()
    co = CourseFactory.create(teachers=[teacher])
    e = EnrollmentFactory.create(student=student, course=co)
    a = AssignmentFactory(course=co,
                          submission_type=AssignmentSubmissionFormats.OTHER,
                          passing_score=10, maximum_score=40)
    sa = StudentAssignment.objects.get(student=student, assignment=a)
    field_name = BaseGradebookForm.GRADE_PREFIX + str(sa.pk)
    form_data = {
        field_name: 1,  # value less than passing score
    }
    data = gradebook_data(co)
    form_cls = GradeBookFormFactory.build_form_class(data)
    form = form_cls(data=form_data)
    assert form.is_valid()


@pytest.mark.django_db
def test_gradebook_view_form_invalid(client):
    teacher = TeacherFactory()
    client.login(teacher)
    student = StudentFactory()
    co = CourseFactory.create(teachers=[teacher])
    e = EnrollmentFactory.create(student=student, course=co,
                                 grade=GradeTypes.EXCELLENT)
    a = AssignmentFactory(course=co,
                          submission_type=AssignmentSubmissionFormats.OTHER,
                          passing_score=10, maximum_score=40)
    sa = StudentAssignment.objects.get(student=student, assignment=a)
    sa.score = 7
    sa.save()
    final_grade_field_name = BaseGradebookForm.FINAL_GRADE_PREFIX + str(e.pk)
    field_name = BaseGradebookForm.GRADE_PREFIX + str(sa.pk)
    response = client.get(co.get_gradebook_url())
    assert response.status_code == 200
    form = response.context['form']
    assert form[field_name].value() == 7
    assert form[final_grade_field_name].value() == GradeTypes.EXCELLENT
    form_data = {
        field_name: -5  # invalid value
    }
    response = client.post(co.get_gradebook_url(), form_data)
    assert response.status_code == 200
    form = response.context['form']
    assert form[field_name].value() == '-5'
    assert form[final_grade_field_name].value() == GradeTypes.EXCELLENT


@pytest.mark.django_db
def test_gradebook_view_form_conflict(client):
    teacher1, teacher2 = TeacherFactory.create_batch(2)
    client.login(teacher1)
    co = CourseFactory.create(teachers=[teacher1, teacher2])
    student = StudentFactory()
    e = EnrollmentFactory.create(student=student, course=co,
                                 grade=GradeTypes.NOT_GRADED)
    a = AssignmentFactory(course=co,
                          submission_type=AssignmentSubmissionFormats.OTHER,
                          passing_score=10, maximum_score=40)
    sa = StudentAssignment.objects.get(student=student, assignment=a, score=None)
    final_grade_field_name = BaseGradebookForm.FINAL_GRADE_PREFIX + str(e.pk)
    field_name = BaseGradebookForm.GRADE_PREFIX + str(sa.pk)
    response = client.get(co.get_gradebook_url())
    assert response.status_code == 200
    form = response.context['form']
    assert form[field_name].value() is None
    assert form[final_grade_field_name].value() == GradeTypes.NOT_GRADED
    form_data = {
        # "initial-" + field_name: None,
        field_name: 4
    }
    response = client.post(co.get_gradebook_url(), form_data, follow=True)
    assert response.status_code == 200
    form = response.context['form']
    assert form[field_name].value() == 4
    assert form[final_grade_field_name].value() == GradeTypes.NOT_GRADED
    sa.refresh_from_db()
    assert sa.score == 4
    # Try to update assignment score with another profile
    client.login(teacher2)
    form_data[field_name] = 5
    response = client.post(co.get_gradebook_url(), form_data)
    assert response.status_code == 200
    assert response.context['form'].conflicts_on_last_save()
    message = list(response.context['messages'])[0]
    assert 'warning' in message.tags
    # The same have to be for final grade
    form_data = {
        "initial-" + final_grade_field_name: GradeTypes.NOT_GRADED,
        final_grade_field_name: GradeTypes.GOOD
    }
    client.login(teacher1)
    response = client.post(co.get_gradebook_url(), form_data, follow=True)
    assert response.status_code == 200
    form = response.context['form']
    assert form[field_name].value() == 4
    assert form[final_grade_field_name].value() == GradeTypes.GOOD
    sa.refresh_from_db()
    assert sa.score == 4
    e.refresh_from_db()
    assert e.grade == GradeTypes.GOOD
    client.login(teacher2)
    form_data[final_grade_field_name] = GradeTypes.EXCELLENT
    response = client.post(co.get_gradebook_url(), form_data)
    assert response.status_code == 200
    assert response.context['form'].conflicts_on_last_save()
    message = list(response.context['messages'])[0]
    assert 'warning' in message.tags
    final_grade_field = response.context['form'][final_grade_field_name]
    assert final_grade_field.value() == GradeTypes.EXCELLENT
    # Hidden field should store current value from db
    hidden_input = BeautifulSoup(final_grade_field.as_hidden(), "html.parser")
    assert hidden_input.find('input').get('value') == str(e.grade)
    # Check special case when value was changed during form editing but it's the
    # same as current user input. Do not treat this case as a conflict.
    e.refresh_from_db()
    assert e.grade == GradeTypes.GOOD
    sa.refresh_from_db()
    assert sa.score == 4
    form_data[final_grade_field_name] = GradeTypes.GOOD
    response = client.post(co.get_gradebook_url(), form_data)
    assert response.status_code == 302
    e.refresh_from_db()
    assert e.grade == GradeTypes.GOOD
    sa.refresh_from_db()
    assert sa.score == 4


@pytest.mark.django_db
def test_gradebook_import_assignments_from_csv_security(client):
    teacher = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    student_spb = StudentFactory(branch__code=Branches.SPB)
    EnrollmentFactory.create(student=student_spb, course=co)
    assignments = AssignmentFactory.create_batch(
        3,
        course=co,
        submission_type=AssignmentSubmissionFormats.OTHER)
    teacher2 = TeacherFactory()
    client.login(teacher2)
    url = reverse('teaching:gradebook_csv_import_stepic', args=[co.pk])
    response = client.post(url, {'assignment': assignments[0].pk,
                                 'csv_file': StringIO("stub\n")})
    assert response.status_code == 403  # not actual teacher
    # Wrong course offering id
    url = reverse('teaching:gradebook_csv_import_stepic',
                  args=[assignments[0].course_id + 1])
    response = client.post(url, {'assignment': assignments[0].pk,
                                 'csv_file': StringIO("stub\n")})
    assert response.status_code == 403
    # csv_file not provided
    redirect_url = co.get_gradebook_url()
    url = reverse('teaching:gradebook_csv_import_stepic', args=[co.pk])
    response = client.post(url, {'assignment': assignments[0].pk})
    assert response.status_code == 400


@pytest.mark.django_db
def test_gradebook_import_assignments_from_csv_smoke(client, mocker):
    mocker.patch('django.contrib.messages.api.add_message')
    teacher = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    student = StudentFactory()
    student.stepic_id = 20
    student.save()
    EnrollmentFactory.create(student=student, course=co)
    assignments = AssignmentFactory.create_batch(3, course=co)
    assignment = assignments[0]
    for expected_score in [13, Decimal('13.42'), '12.34', '"34,56"']:
        csv_input = force_bytes("stepic_id,total\n"
                                "{},{}\n".format(student.stepic_id,
                                                 expected_score))
        csv_file = BytesIO(csv_input)
        AssignmentGradesImport(assignment, csv_file, "stepic_id").process()
        a_s = StudentAssignment.objects.get(student=student,
                                            assignment=assignment)
        if hasattr(expected_score, "replace"):
            # remove quotes and replace comma
            expected_score = expected_score.replace('"', '').replace(",", ".")
        assert a_s.score == Decimal(expected_score)


@pytest.mark.django_db
def test_gradebook_import_assignments_from_csv(client, tmpdir):
    teacher = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    student1 = StudentFactory(branch__code=Branches.SPB, yandex_login='yandex1',
                              stepic_id='1')
    student2 = StudentFactory(branch__code=Branches.SPB, yandex_login='yandex2',
                              stepic_id='2')
    student3 = StudentFactory(branch__code=Branches.SPB, yandex_login='custom_one',
                              stepic_id='3')
    for s in [student1, student2, student3]:
        EnrollmentFactory.create(student=s, course=co)
    assignment = AssignmentFactory.create(
        course=co,
        submission_type=AssignmentSubmissionFormats.OTHER,
        maximum_score=50)
    # Generate csv file with missing header `login`
    tmp_file = tmpdir.mkdir("csv").join("grades_missing_header.csv")
    tmp_file.write("""
header1,header2,total
1,2,10
2,3,20
    """.strip())
    form = {
        'assignment': assignment.pk,
        'csv_file': tmp_file.open()
    }
    url_import = reverse('teaching:gradebook_csv_import_yandex',
                         args=[co.pk])
    client.login(teacher)
    response = client.post(url_import, form, follow=True)
    assert response.status_code == 200
    assert 'messages' in response.context
    assert list(response.context['messages'])[0].level == messages.ERROR
    #
    tmp_file = tmpdir.join("csv").join("grades_yandex_logins.csv")
    tmp_file.write("""
yandex_login,header2,total
yandex1,1,10
yandex2,2,20
yandex3,3,30
    """.strip())
    form = {
        'assignment': assignment.pk,
        'csv_file': tmp_file.open()
    }
    response = client.post(url_import, form, follow=True)
    assert response.status_code == 200
    assert StudentAssignment.objects.get(student=student1).score == 10
    assert StudentAssignment.objects.get(student=student2).score == 20
    assert StudentAssignment.objects.get(student=student3).score is None
    # Try to override grades from csv with stepik ids
    tmp_file = tmpdir.join("csv").join("grades_stepik_ids.csv")
    tmp_file.write("""
stepic_id,header2,total
2,2,42
3,3,1
4,3,1
5,3,100
    """.strip())
    form = {
        'assignment': assignment.pk,
        'csv_file': tmp_file.open()
    }
    url_import = reverse('teaching:gradebook_csv_import_stepic', args=[co.pk])
    response = client.post(url_import, form, follow=True)
    assert StudentAssignment.objects.get(student=student1).score == 10
    assert StudentAssignment.objects.get(student=student2).score == 42
    assert StudentAssignment.objects.get(student=student3).score == 1
