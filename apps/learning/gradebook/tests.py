import csv
import datetime
import io
from decimal import Decimal
from io import BytesIO, StringIO

import pytest
import pytz
from bs4 import BeautifulSoup

from django.contrib.messages import constants as messages_constants
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.encoding import force_bytes, smart_bytes
from django.utils.timezone import now
from django.utils.translation import gettext_lazy

from auth.mixins import PermissionRequiredMixin, RolePermissionRequiredMixin
from auth.permissions import perm_registry
from auth.tests.factories import ConnectedAuthServiceFactory
from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.constants import AssignmentFormat, AssignmentStatus
from courses.models import CourseGroupModes, CourseTeacher
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory
)
from grading.tests.factories import CheckerFactory
from learning.gradebook import (
    BaseGradebookForm, GradeBookFilterForm, GradeBookFormFactory,
    get_student_assignment_state, gradebook_data
)
from learning.gradebook.services import assignment_import_scores_from_csv
from learning.gradebook.views import ImportCourseGradesBaseView
from learning.models import AssignmentSubmissionTypes, Enrollment, StudentAssignment, EnrollmentGradeLog
from learning.permissions import EditGradebook, ViewGradebook
from learning.services.personal_assignment_service import (
    get_personal_assignments_by_stepik_id
)
from learning.settings import (
    AssignmentScoreUpdateSource, Branches, GradeTypes, StudentStatuses, EnrollmentGradeUpdateSource, EnrollmentTypes
)
from learning.tests.factories import (
    AssignmentCommentFactory, EnrollmentFactory, StudentAssignmentFactory,
    StudentGroupFactory
)
from users.models import StudentTypes
from users.services import get_student_profile
from users.tests.factories import (
    CuratorFactory, StudentFactory, TeacherFactory, UserFactory
)


# TODO: test redirect to gradebook for teachers if only 1 course in current term


@pytest.mark.django_db
def test_gradebook_view_security(client, lms_resolver):
    course = CourseFactory()
    resolver = lms_resolver(course.get_gradebook_url())
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewGradebook.name
    assert resolver.func.view_class.permission_required in perm_registry


@pytest.mark.django_db
def test_gradebook_csv_view_security(client, lms_resolver):
    course = CourseFactory()
    resolver = lms_resolver(course.get_gradebook_url(format='csv'))
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewGradebook.name
    assert resolver.func.view_class.permission_required in perm_registry


@pytest.mark.django_db
def test_gradebook_download_csv(client):
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
    last_name_column_index = data[0].index(str(gettext_lazy("Last name")))
    row_last_names = [row[last_name_column_index] for row in data]
    for a, s, grade in combos:
        row = row_last_names.index(s.last_name)
        col = data[0].index(a.title)
        assert grade == int(data[row][col])


@pytest.mark.django_db
def test_view_gradebook_csv_gitlab_manytask_columns(client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    gradebook_url = course.get_gradebook_url(format="csv")
    enrollment = EnrollmentFactory(course=course)
    client.login(teacher)
    response = client.get(gradebook_url)
    assert response.status_code == 200
    gradebook_csv = response.content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(gradebook_csv)) if s]
    assert len(data) == 2

    def get_column_value(table, column_name, row_index):
        assert column_name in table[0]
        assert row_index < len(table)
        column_index = table[0].index(column_name)
        return table[row_index][column_index]

    assert get_column_value(data, "gitlab.manytask.org ID", 1) == "-"
    assert get_column_value(data, "gitlab.manytask.org Login", 1) == "-"
    # Connect service providers
    ConnectedAuthServiceFactory(user=enrollment.student_profile.user,
                                provider="gitlab",
                                uid="Test UID2")
    connected_service = ConnectedAuthServiceFactory(user=enrollment.student_profile.user,
                                                    provider="gitlab-manytask",
                                                    uid="Test UID",
                                                    extra_data="")
    response = client.get(gradebook_url)
    assert response.status_code == 200
    gradebook_csv = response.content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(gradebook_csv)) if s]
    assert get_column_value(data, "gitlab.manytask.org ID", 1) == "Test UID"
    assert get_column_value(data, "gitlab.manytask.org Login", 1) == "-"
    # Saved login in extra data
    connected_service.extra_data = {"login": "test-login"}
    connected_service.save()
    response = client.get(gradebook_url)
    assert response.status_code == 200
    gradebook_csv = response.content.decode('utf-8')
    data = [s for s in csv.reader(io.StringIO(gradebook_csv)) if s]
    assert get_column_value(data, "gitlab.manytask.org ID", 1) == "Test UID"
    assert get_column_value(data, "gitlab.manytask.org Login", 1) == "test-login"


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
        submission_type=AssignmentFormat.NO_SUBMIT)
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
            assert response.context_data['form'].ASSIGNMENT_SCORE_PREFIX + str(a_s.pk) in response.context_data[
                'form'].fields


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
        submission_type=AssignmentFormat.NO_SUBMIT)
    teacher_gradebook_url = course.get_gradebook_url()
    form = {}
    pairs = zip([StudentAssignment.objects.get(student=student, assignment=a)
                 for student in students
                 for a in [a1, a2]],
                [2, 3, 4, 5])
    for submission, grade in pairs:
        enrollment = Enrollment.active.get(student=submission.student,
                                           course=course)
        field_name = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(submission.pk)
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
    e1, e2, e3, e4, e5, e6 = EnrollmentFactory.create_batch(6, course=co)
    a1, a2, a3 = AssignmentFactory.create_batch(3, course=co,
                                                passing_score=1, maximum_score=10)
    data = gradebook_data(co)
    assert len(data.assignments) == 3
    assert len(data.students) == 6
    e6.type = EnrollmentTypes.LECTIONS_ONLY
    e6.save()
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
    assert list(ga.assignment for ga in data.assignments.values()) == [a1, a3, a2]
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
    s3_a2_progress = data.student_assignments[s3_index][a2_index]
    assert s3_a2_progress is not None
    assert s3_a2_progress.score == 3
    for row in data.student_assignments:
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
    for x, row in enumerate(data.student_assignments):
        for y, cell in enumerate(row):
            if x == s5_index and y == new_a_index:
                assert data.student_assignments[x][y] is None
            else:
                assert data.student_assignments[x][y] is not None


@pytest.mark.django_db
def test_empty_gradebook_data():
    """Smoke test for gradebook without assignments"""
    co = CourseFactory()
    data = gradebook_data(co)
    assert len(data.assignments) == 0
    assert len(data.students) == 0
    assert len(data.student_assignments) == 0
    e1, e2, e3, e4, e5 = EnrollmentFactory.create_batch(5, course=co)
    data = gradebook_data(co)
    assert len(data.assignments) == 0
    assert len(data.students) == 5
    assert len(data.student_assignments) == 5
    assert len(data.student_assignments[0]) == 0


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
        assert field in response.context_data['form'].fields
    assert len(students) == len(response.context_data['form'].fields)
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
    head_student = next(iter(response.context_data['gradebook'].students.values()))
    assert head_student.total_score == expected_total_score


@pytest.mark.django_db
def test_total_score_weighted(client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    client.login(teacher)
    student = StudentFactory()
    EnrollmentFactory(student=student, course=course)
    a1 = AssignmentFactory(course=course, weight=Decimal('1.00'), maximum_score=10)
    a2 = AssignmentFactory(course=course, weight=Decimal('0.3'), maximum_score=20)
    a3 = AssignmentFactory(course=course, weight=Decimal('0.3'), maximum_score=3)
    sa1 = StudentAssignment.objects.get(student=student, assignment=a1)
    sa2 = StudentAssignment.objects.get(student=student, assignment=a2)
    sa1.score = 3
    sa1.save()
    sa2.score = 12
    sa2.save()
    expected_total_score = 3 * a1.weight + 12 * a2.weight
    response = client.get(course.get_gradebook_url())
    head_student = next(iter(response.context_data['gradebook'].students.values()))
    assert head_student.total_score == expected_total_score
    a4 = AssignmentFactory(course=course, weight=Decimal('0'), maximum_score=3)
    sa4 = StudentAssignment.objects.get(student=student, assignment=a4)
    sa4.score = 2
    sa4.save()
    response = client.get(course.get_gradebook_url())
    head_student = next(iter(response.context_data['gradebook'].students.values()))
    assert head_student.total_score == expected_total_score
    a5 = AssignmentFactory(course=course, maximum_score=3,
                           submission_type=AssignmentFormat.PENALTY)
    sa5 = StudentAssignment.objects.get(student=student, assignment=a5)
    sa5.score = 2
    sa5.save()
    response = client.get(course.get_gradebook_url())
    head_student = next(iter(response.context_data['gradebook'].students.values()))
    assert head_student.total_score == expected_total_score - 2


@pytest.mark.django_db
def test_save_gradebook_form(client):
    """Make sure that all fields are optional. Save only sent data"""
    teacher = TeacherFactory.create()
    client.login(teacher)
    co = CourseFactory.create(teachers=[teacher])
    a1, a2 = AssignmentFactory.create_batch(
        2, course=co,
        submission_type=AssignmentFormat.NO_SUBMIT,
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
    form_cls = GradeBookFormFactory.build_form_class(data, is_readonly=False)
    form = form_cls(data=form_data)
    # Initial should be empty since we want to save only sent data
    assert not form.initial
    assert form.is_valid()
    assert len(form.changed_data) == 1
    assert field_name in form.changed_data
    conflicts = form.save(data, changed_by=teacher)
    assert not conflicts
    e1.refresh_from_db()
    e2.refresh_from_db()
    assert e1.grade == GradeTypes.GOOD
    assert e2.grade == GradeTypes.EXCELLENT
    e1_log = EnrollmentGradeLog.objects.get(enrollment=e1)
    assert not EnrollmentGradeLog.objects.filter(enrollment=e2).exists()
    assert e1_log.grade == GradeTypes.GOOD
    assert e1_log.entry_author == teacher
    assert e1_log.source == EnrollmentGradeUpdateSource.GRADEBOOK
    assert e1_log.grade_changed_at - now() < datetime.timedelta(seconds=5)

    # Now change one of submission grade
    sa11 = StudentAssignment.objects.get(student_id=e1.student_id, assignment=a1)
    sa12 = StudentAssignment.objects.get(student_id=e1.student_id, assignment=a2)
    field_name = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(sa11.pk)
    form_data = {
        field_name: -5,  # invalid value
        # Empty value should be discarded
        BaseGradebookForm.FINAL_GRADE_PREFIX + str(e2.pk): '',
    }
    data = gradebook_data(co)
    form_cls = GradeBookFormFactory.build_form_class(data, is_readonly=False)
    form = form_cls(data=form_data)
    assert not form.is_valid()
    form_data[field_name] = 2
    form_cls = GradeBookFormFactory.build_form_class(gradebook_data(co), is_readonly=False)
    form = form_cls(data=form_data)
    assert form.is_valid()
    form.save(data, changed_by=teacher)
    sa11.refresh_from_db(), sa12.refresh_from_db()
    assert sa11.score == 2
    assert sa12.score is None
    e1.refresh_from_db(), e2.refresh_from_db()
    assert e1.grade == GradeTypes.GOOD
    assert e2.grade == GradeTypes.EXCELLENT
    assert EnrollmentGradeLog.objects.filter(enrollment=e1).count() == 1
    assert not EnrollmentGradeLog.objects.filter(enrollment=e2).exists()


@pytest.mark.django_db
def test_save_gradebook_l10n(client):
    """Input value for grade value can be int or decimal"""
    teacher = TeacherFactory()
    client.login(teacher)
    student = StudentFactory()
    co = CourseFactory.create(teachers=[teacher])
    EnrollmentFactory.create(student=student, course=co)
    a = AssignmentFactory(course=co,
                          submission_type=AssignmentFormat.NO_SUBMIT,
                          passing_score=10, maximum_score=40)
    sa = StudentAssignment.objects.get(student=student, assignment=a)
    field_name = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(sa.pk)
    data = gradebook_data(co)
    form_cls = GradeBookFormFactory.build_form_class(data, is_readonly=False)
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
                          submission_type=AssignmentFormat.NO_SUBMIT,
                          passing_score=10, maximum_score=40)
    sa = StudentAssignment.objects.get(student=student, assignment=a)
    field_name = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(sa.pk)
    form_data = {
        field_name: 1,  # value less than passing score
    }
    data = gradebook_data(co)
    form_cls = GradeBookFormFactory.build_form_class(data, is_readonly=False)
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
                          submission_type=AssignmentFormat.NO_SUBMIT,
                          passing_score=10, maximum_score=40)
    sa = StudentAssignment.objects.get(student=student, assignment=a)
    sa.score = 7
    sa.save()
    final_grade_field_name = BaseGradebookForm.FINAL_GRADE_PREFIX + str(e.pk)
    field_name = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(sa.pk)
    response = client.get(co.get_gradebook_url())
    assert response.status_code == 200
    form = response.context_data['form']
    assert form[field_name].value() == 7
    assert form[final_grade_field_name].value() == GradeTypes.EXCELLENT
    form_data = {
        field_name: -5  # invalid value
    }
    response = client.post(co.get_gradebook_url(), form_data)
    assert response.status_code == 200
    form = response.context_data['form']
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
                          submission_type=AssignmentFormat.NO_SUBMIT,
                          passing_score=10, maximum_score=40)
    sa = StudentAssignment.objects.get(student=student, assignment=a, score=None)
    final_grade_field_name = BaseGradebookForm.FINAL_GRADE_PREFIX + str(e.pk)
    field_name = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(sa.pk)
    response = client.get(co.get_gradebook_url())
    assert response.status_code == 200
    form = response.context_data['form']
    assert form[field_name].value() is None
    assert form[final_grade_field_name].value() == GradeTypes.NOT_GRADED
    form_data = {
        # "initial-" + field_name: None,
        field_name: 4
    }
    response = client.post(co.get_gradebook_url(), form_data, follow=True)
    assert response.status_code == 200
    form = response.context_data['form']
    assert form[field_name].value() == 4
    assert form[final_grade_field_name].value() == GradeTypes.NOT_GRADED
    sa.refresh_from_db()
    assert sa.score == 4
    # Try to update assignment score with another profile
    client.login(teacher2)
    form_data[field_name] = 5
    response = client.post(co.get_gradebook_url(), form_data)
    assert response.status_code == 200
    assert response.context_data['form'].conflicts_on_last_save()
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) > 0
    message = messages[0]
    assert 'warning' in message.tags
    # The same have to be for final grade
    form_data = {
        "initial-" + final_grade_field_name: GradeTypes.NOT_GRADED,
        final_grade_field_name: GradeTypes.GOOD
    }
    client.login(teacher1)
    response = client.post(co.get_gradebook_url(), form_data, follow=True)
    assert response.status_code == 200
    form = response.context_data['form']
    assert form[field_name].value() == 4
    assert form[final_grade_field_name].value() == GradeTypes.GOOD
    sa.refresh_from_db()
    assert sa.score == 4
    e.refresh_from_db()
    assert e.grade == GradeTypes.GOOD
    assert EnrollmentGradeLog.objects.filter(enrollment=e).count() == 1
    client.login(teacher2)
    form_data[final_grade_field_name] = GradeTypes.EXCELLENT
    response = client.post(co.get_gradebook_url(), form_data)
    assert response.status_code == 200
    assert response.context_data['form'].conflicts_on_last_save()
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) > 0
    message = messages[0]
    assert 'warning' in message.tags
    final_grade_field = response.context_data['form'][final_grade_field_name]
    assert final_grade_field.value() == GradeTypes.EXCELLENT
    # Hidden field should store current value from db
    hidden_input = BeautifulSoup(final_grade_field.as_hidden(), "html.parser")
    assert hidden_input.find('input').get('value') == str(e.grade)
    # Check special case when value was changed during form editing but it's the
    # same as current user input. Do not treat this case as a conflict.
    e.refresh_from_db()
    assert e.grade == GradeTypes.GOOD
    assert EnrollmentGradeLog.objects.filter(enrollment=e).count() == 1

    sa.refresh_from_db()
    assert sa.score == 4
    form_data[final_grade_field_name] = GradeTypes.GOOD
    response = client.post(co.get_gradebook_url(), form_data)
    assert response.status_code == 302
    e.refresh_from_db()
    assert e.grade == GradeTypes.GOOD
    sa.refresh_from_db()
    assert sa.score == 4
    assert EnrollmentGradeLog.objects.filter(enrollment=e).count() == 2


@pytest.mark.django_db
def test_gradebook_import_assignment_scores_from_csv_permissions(client):
    teacher = TeacherFactory()
    co = CourseFactory.create(teachers=[teacher])
    student_spb = StudentFactory(branch__code=Branches.SPB)
    EnrollmentFactory.create(student=student_spb, course=co)
    assignments = AssignmentFactory.create_batch(
        3,
        course=co,
        submission_type=AssignmentFormat.NO_SUBMIT)
    teacher2 = TeacherFactory()
    client.login(teacher2)
    url = reverse('teaching:gradebook_import_scores_by_stepik_id', args=[co.pk])
    response = client.post(url, {'assignment': assignments[0].pk,
                                 'csv_file': StringIO("stub\n")})
    assert response.status_code == 403  # not a teacher of the course
    # Course does not exist
    url = reverse('teaching:gradebook_import_scores_by_stepik_id',
                  args=[assignments[0].course_id + 1])
    response = client.post(url, {'assignment': assignments[0].pk,
                                 'csv_file': StringIO("stub\n")})
    assert response.status_code == 404
    # csv_file not provided
    client.login(teacher)
    url = reverse('teaching:gradebook_import_scores_by_stepik_id', args=[co.pk])
    response = client.post(url, {'assignment': assignments[0].pk})
    assert response.status_code == 400


@pytest.mark.django_db
def test_gradebook_import_assignment_scores_from_csv_by_stepik_id_smoke(client, mocker):
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
        csv_input = force_bytes("stepik_id,score\n"
                                "{},{}\n".format(student.stepic_id,
                                                 expected_score))
        csv_file = BytesIO(csv_input)
        with_stepik_id = get_personal_assignments_by_stepik_id(assignment=assignment)
        assignment_import_scores_from_csv(csv_file,
                                          required_headers=['stepik_id', 'score'],
                                          lookup_column_name='stepik_id',
                                          student_assignments=with_stepik_id,
                                          changed_by=teacher,
                                          audit_log_source=AssignmentScoreUpdateSource.CSV_STEPIK)
        a_s = StudentAssignment.objects.get(student=student,
                                            assignment=assignment)
        if hasattr(expected_score, "replace"):
            # remove quotes and replace comma
            expected_score = expected_score.replace('"', '').replace(",", ".")
        assert a_s.score == Decimal(expected_score)


@pytest.mark.django_db
def test_gradebook_import_assignment_score_by_stepik_id(client):
    teacher = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher])
    student1 = StudentFactory(branch__code=Branches.SPB, stepic_id='2')
    student2 = StudentFactory(branch__code=Branches.SPB, stepic_id=None)
    student3 = StudentFactory(branch__code=Branches.SPB, stepic_id='4')
    for s in [student1, student2, student3]:
        EnrollmentFactory.create(student=s, course=course)
    assignment = AssignmentFactory.create(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=50)
    # Missing header
    csv_data = b"""
header1,header2,score
1,2,10
2,3,20
    """.strip()
    form = {
        'assignment': assignment.pk,
        'csv_file': SimpleUploadedFile("data.csv", csv_data)
    }
    import_csv_url = reverse('teaching:gradebook_import_scores_by_stepik_id',
                             args=[course.pk])
    client.login(teacher)
    response = client.post(import_csv_url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].level == messages_constants.ERROR
    csv_data = b"""
stepik_id,header2,score
2,2,42
3,3,1
4,3,1
5,3,100
    """.strip()
    form = {
        'assignment': assignment.pk,
        'csv_file': SimpleUploadedFile("data.csv", csv_data)
    }
    response = client.post(import_csv_url, form, follow=True)
    assert StudentAssignment.objects.get(student=student1).score == 42
    assert StudentAssignment.objects.get(student=student2).score is None
    assert StudentAssignment.objects.get(student=student3).score == 1


@pytest.mark.django_db
def test_gradebook_import_assignment_score_by_yandex_login(client):
    teacher = TeacherFactory()
    branch = BranchFactory(code=Branches.SPB)
    course = CourseFactory(teachers=[teacher])
    student1 = StudentFactory(branch=branch, yandex_login='Yandex-login1')
    student2 = StudentFactory(branch=branch, yandex_login='yandex.login2')
    student3 = StudentFactory(branch=branch, yandex_login='')
    for s in [student1, student2, student3]:
        EnrollmentFactory.create(student=s, course=course)
    assignment = AssignmentFactory(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=50)
    student_assignment3 = StudentAssignment.objects.get(assignment=assignment,
                                                        student=student3)
    assert student_assignment3.score is None
    csv_data = b"""
header1,header2,score
1,2,10
2,3,20
    """.strip()
    csv_file = SimpleUploadedFile("grades_missing_header.csv", csv_data)
    form = {
        'assignment': assignment.pk,
        'csv_file': csv_file
    }
    import_csv_url = reverse('teaching:gradebook_import_scores_by_yandex_login',
                             args=[course.pk])
    client.login(teacher)
    response = client.post(import_csv_url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].level == messages_constants.ERROR
    #
    csv_data = b"""
login,header2,score
yandex-login1,1,10
YANDEX-login2,2,20
,3,30
    """.strip()
    form = {
        'assignment': assignment.pk,
        'csv_file': SimpleUploadedFile("scores.csv", csv_data)
    }
    response = client.post(import_csv_url, form, follow=True)
    assert response.status_code == 200
    assert StudentAssignment.objects.get(student=student1).score == 10
    assert StudentAssignment.objects.get(student=student2).score == 20
    assert StudentAssignment.objects.get(student=student3).score is None


@pytest.mark.django_db
def test_gradebook_import_assignment_score_by_enrollment_id_invalid_data(client):
    teacher = TeacherFactory()
    client.login(teacher)
    course = CourseFactory(teachers=[teacher])
    import_csv_url = reverse('teaching:gradebook_import_scores_by_enrollment_id',
                             args=[course.pk])
    e1, e2, e3 = EnrollmentFactory.create_batch(3, course=course)
    assignment = AssignmentFactory.create(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=50)
    # Invalid headers
    csv_data = b"""
header1,header2,score
1,2,10
2,3,20
    """.strip()
    form = {
        'assignment': assignment.pk,
        'csv_file': SimpleUploadedFile("data.csv", csv_data)
    }
    response = client.post(import_csv_url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) > 0
    assert messages[-1].level == messages_constants.ERROR
    # Score > maximum score
    csv_data = force_bytes(f"""
id,header2,score
{e1.id},2,10
{e2.id},3,200
    """.strip())
    form = {
        'assignment': assignment.pk,
        'csv_file': SimpleUploadedFile("data.csv", csv_data)
    }
    response = client.post(import_csv_url, form, follow=True)
    assert response.status_code == 200
    # Score for enrollment1 has been imported
    assert StudentAssignment.objects.get(student=e1.student).score == 10
    assert StudentAssignment.objects.get(student=e2.student).score is None


@pytest.mark.django_db
def test_gradebook_import_assignment_score_by_enrollment_id(client):
    teacher = TeacherFactory()
    client.login(teacher)
    course = CourseFactory(teachers=[teacher])
    import_csv_url = reverse('teaching:gradebook_import_scores_by_enrollment_id',
                             args=[course.pk])
    e1, e2, e3 = EnrollmentFactory.create_batch(3, course=course)
    assignment = AssignmentFactory.create(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=500)
    csv_data = force_bytes(f"""
id,header2,score
{e1.id},2,42
3,3,1
{e2.id},3,100
{e2.id},3,101
    """.strip())
    form = {
        'assignment': assignment.pk,
        'csv_file': SimpleUploadedFile("data.csv", csv_data)
    }
    response = client.post(import_csv_url, form, follow=True)
    assert StudentAssignment.objects.get(student=e1.student).score == 42
    assert StudentAssignment.objects.get(student=e2.student).score == 101
    assert StudentAssignment.objects.get(student=e3.student).score is None
    # Enrollment id from other course
    other_course = CourseFactory(teachers=[teacher])
    e4 = EnrollmentFactory(course=other_course)
    assignment_other = AssignmentFactory.create(
        course=other_course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=200)
    csv_data = force_bytes(f"""
id,header2,score
{e1.id},2,42
3,3,1
{e2.id},3,100
{e4.id},3,101
    """.strip())
    form = {
        'assignment': assignment.pk,
        'csv_file': SimpleUploadedFile("data.csv", csv_data)
    }
    response = client.post(import_csv_url, form, follow=True)
    assert StudentAssignment.objects.get(student=e2.student).score == 100
    assert StudentAssignment.objects.get(student=e4.student).score is None


@pytest.mark.django_db
def test_gradebook_import_scores_from_yandex_contest_permissions(settings, client, mocker, lms_resolver):
    mocked_api = mocker.patch('grading.api.yandex_contest.YandexContestAPI.standings',
                              return_value=(200, {'titles': [], 'rows': []}))
    curator = CuratorFactory()
    teacher1, teacher2 = TeacherFactory.create_batch(2)
    course = CourseFactory(teachers=[teacher2])
    url = reverse('teaching:api:import-scores:yandex_contest', kwargs={"course_id": course.pk},
                  subdomain=settings.LMS_SUBDOMAIN)
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, RolePermissionRequiredMixin)
    assert resolver.func.view_class.permission_classes == [EditGradebook]
    assert EditGradebook.name in perm_registry
    # Check unauthorized and forbidden requests
    response = client.post(url, data={}, content_type='application/json')
    assert response.status_code == 401
    client.login(UserFactory())
    response = client.post(url, data={}, content_type='application/json')
    assert response.status_code == 403
    client.login(teacher1)
    response = client.post(url, data={}, content_type='application/json')
    assert response.status_code == 403
    # Authorized
    client.login(teacher2)
    response = client.post(url, data={}, content_type='application/json')
    assert response.status_code == 400
    client.login(curator)
    response = client.post(url, data={}, content_type='application/json')
    assert response.status_code == 400
    # Wrong assignment id, but valid permissions
    assignment1 = AssignmentFactory(course=course,
                                    checker=CheckerFactory(),
                                    submission_type=AssignmentFormat.YANDEX_CONTEST)
    assignment2 = AssignmentFactory(checker=CheckerFactory(),
                                    submission_type=AssignmentFormat.YANDEX_CONTEST)
    response = client.post(url, data={'assignment': assignment1.pk}, content_type='application/json')
    assert response.status_code == 201
    response = client.post(url, data={'assignment': assignment2.pk}, content_type='application/json')
    assert response.status_code == 404


def generate_course(group_one_size: int = 5,
                    group_two_size: int = 5,
                    group_one_type: str = StudentTypes.REGULAR,
                    group_two_type: str = StudentTypes.INVITED):
    teacher = TeacherFactory()
    branch = BranchFactory(code=Branches.SPB)
    course = CourseFactory(main_branch=branch, teachers=[teacher],
                           group_mode=CourseGroupModes.MANUAL)
    group_one, group_two = StudentGroupFactory.create_batch(2, course=course)
    group_one_students = StudentFactory.create_batch(group_one_size, branch=branch,
                                                     student_profile__type=group_one_type)
    group_two_students = StudentFactory.create_batch(group_two_size, branch=branch,
                                                     student_profile__type=group_two_type)
    for student in group_one_students:
        EnrollmentFactory(student=student, course=course, student_group=group_one)
    for student in group_two_students:
        EnrollmentFactory(student=student, course=course, student_group=group_two)
    return teacher, course, group_one_students, group_two_students, group_one, group_two


@pytest.mark.django_db
def test_view_gradebook_student_profile_shows_student_type(client):
    teacher, course, regular_students, invited_students, \
    group_one, group_two = generate_course()
    gradebook = gradebook_data(course)
    for pk, students_gradebook, in gradebook.students.items():
        if students_gradebook.student in invited_students:
            assert students_gradebook.student_profile.type == StudentTypes.INVITED
        else:
            assert students_gradebook.student_profile.type == StudentTypes.REGULAR


@pytest.mark.django_db
def test_filter_form_is_hidden(client):
    teacher = TeacherFactory()
    branch = BranchFactory(code=Branches.SPB)
    course = CourseFactory(main_branch=branch, teachers=[teacher])
    form = GradeBookFilterForm(course=course)
    assert not form.is_visible()


@pytest.mark.django_db
def test_view_gradebook_filter_form_contains_all_student_groups(client):
    teacher = TeacherFactory()
    branch = BranchFactory(code=Branches.SPB)
    course = CourseFactory(main_branch=branch, teachers=[teacher],
                           group_mode=CourseGroupModes.MANUAL)
    groups = StudentGroupFactory.create_batch(3, course=course)
    form = GradeBookFilterForm(course=course)
    choices = form.fields['student_group'].choices
    assert len(choices) == 4  # 3 groups + All
    assert choices[0][0] is None
    for group, choice in zip(groups, choices[1:]):
        assert group.name == choice[1]


@pytest.mark.django_db
def test_gradebook_data_returns_only_selected_group():
    teacher, course, students_group_one, students_group_two, \
    group_one, group_two = generate_course()
    data = gradebook_data(course, student_group=group_one.pk)
    assert len(data.students) == len(students_group_one)
    for student in students_group_one:
        assert student.pk in data.students


@pytest.mark.django_db
def test_view_gradebook_filter_form_integration_test(client):
    teacher, course, regular_students, invited_students, \
    group_one, group_two = generate_course(group_one_size=6, group_two_size=4)
    client.login(teacher)
    no_filter_url = course.get_gradebook_url()
    response = client.get(no_filter_url)
    assert len(response.context_data['gradebook'].students) == 10
    wrong_filter_url = course.get_gradebook_url(student_group='wrong')
    response.client.get(wrong_filter_url)
    assert len(response.context_data['gradebook'].students) == 10
    filter_first_url = course.get_gradebook_url(student_group=group_one.pk)
    response = client.get(filter_first_url)
    students = response.context_data['gradebook'].students
    assert len(students) == 6
    for student in regular_students:
        assert student.pk in students
    filter_second_url = course.get_gradebook_url(student_group=group_two.pk)
    response = client.get(filter_second_url)
    students = response.context_data['gradebook'].students
    assert len(students) == 4
    for student in invited_students:
        assert student.pk in students


@pytest.mark.django_db
def test_view_gradebook_query_param_marks_selected_group(client):
    teacher, course, regular_student, invited_students, \
    group_one, group_two = generate_course()
    client.login(teacher)
    course.get_gradebook_url(student_group=group_one.pk)
    filter_first_url = course.get_gradebook_url(student_group=group_one.pk)
    response = client.get(filter_first_url)
    form = response.context_data["filter_form"]
    assert form.cleaned_data['student_group'] == group_one.pk


@pytest.mark.django_db
def test_view_gradebook_submitting_remember_selected_group(client):
    teacher, course, regular_student, \
    invited_students, group_one, group_two = generate_course()
    client.login(teacher)
    filter_first_url = course.get_gradebook_url(student_group=group_one.pk)
    response = client.post(filter_first_url)
    assert response.status_code == 302
    assert f"student_group={group_one.pk}" in response.url


@pytest.mark.django_db
def test_view_gradebook_filtered_data_editable(client, assert_redirect):
    teacher, course, group_one_students, group_two_students, \
    group_one, group_two = generate_course(group_one_size=50, group_two_size=51)
    assignment = AssignmentFactory(course=course, submission_type=AssignmentFormat.NO_SUBMIT)
    sa = StudentAssignment.objects.get(student=group_one_students[0], assignment=assignment)

    # GradeBook should be readonly before filtering because students count > 100
    data = gradebook_data(course)
    assert data.is_readonly

    # but after filtering should be editable: students count < 100
    client.login(teacher)
    field_name = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(sa.pk)
    grade = 3
    form = {
        field_name: grade
    }
    filter_first_url = course.get_gradebook_url(student_group=group_one.pk)
    assert_redirect(client.post(filter_first_url, form), filter_first_url)
    assert StudentAssignment.objects.get(pk=sa.pk).score == grade


@pytest.mark.django_db
def test_gradebook_data_filtering_restricted_assignments(client, assert_redirect):
    teacher, course, group_one_students, group_two_students, \
    group_one, group_two = generate_course(group_one_size=1, group_two_size=1)
    assignment = AssignmentFactory(course=course)
    assignment_restricted_1 = AssignmentFactory(course=course, restricted_to=[group_one])
    assignment_restricted_2 = AssignmentFactory(course=course, restricted_to=[group_two])

    data = gradebook_data(course=course, student_group=group_one.pk)
    assert len(data.assignments) == 2
    assert data.assignments.get(assignment.pk) is not None
    assert data.assignments.get(assignment_restricted_1.pk) is not None
    assert data.assignments.get(assignment_restricted_2.pk) is None
    tasks = map(lambda sp: sp.assignment.id, data.student_assignments[0])
    assert set(tasks) == {assignment.pk, assignment_restricted_1.pk}

    data = gradebook_data(course=course, student_group=group_two.pk)
    assert len(data.assignments) == 2
    assert data.assignments.get(assignment.pk) is not None
    assert data.assignments.get(assignment_restricted_1.pk) is None
    assert data.assignments.get(assignment_restricted_2.pk) is not None
    tasks = map(lambda sp: sp.assignment.pk, data.student_assignments[0])
    assert set(tasks) == {assignment.pk, assignment_restricted_2.pk}

    data = gradebook_data(course=course)
    assert len(data.assignments) == 3
    assert data.assignments.get(assignment.pk) is not None
    assert data.assignments.get(assignment_restricted_1.pk) is not None
    assert data.assignments.get(assignment_restricted_2.pk) is not None
    stud_0_subs, stud_1_subs = data.student_assignments
    for submission in stud_0_subs:
        if submission is not None:
            assert submission.assignment.id in {
                assignment.pk,
                assignment_restricted_1.pk
            }
    for submission in stud_1_subs:
        if submission is not None:
            assert submission.assignment.id in {
                assignment.pk,
                assignment_restricted_2.pk
            }


@pytest.mark.django_db
def test_view_gradebook_save_import_btn_require_editgradebook_perm(client):
    course = CourseFactory()
    teacher, spectator = TeacherFactory.create_batch(2)
    CourseTeacherFactory(course=course, teacher=teacher)
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)

    def has_elements(user):
        client.login(user)
        gradebook_url = course.get_gradebook_url()
        html = client.get(gradebook_url).content.decode('utf-8')
        soup = BeautifulSoup(html, "html.parser")
        has_submit = soup.find("button", {"id": "marks-sheet-save"}) is not None
        has_import = soup.find("i", {"class": "fa fa-upload"}) is not None
        client.logout()
        return has_submit + has_import

    assert has_elements(teacher) == 2
    assert not has_elements(spectator)


@pytest.mark.django_db
def test_view_gradebook_post_require_editgradebook_perm(client):
    course = CourseFactory()
    teacher, spectator = TeacherFactory.create_batch(2)
    CourseTeacherFactory(course=course, teacher=teacher)
    CourseTeacherFactory(course=course, teacher=spectator,
                         roles=CourseTeacher.roles.spectator)

    client.login(teacher)
    gradebook_url = course.get_gradebook_url()
    response = client.post(gradebook_url, follow=True)
    assert response.status_code == 200
    client.logout()

    client.login(spectator)
    response = client.post(gradebook_url, follow=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_view_gradebook_readonly_without_editgradebook_perm(client):
    course = CourseFactory()
    teacher = TeacherFactory()
    CourseTeacherFactory(course=course, teacher=teacher,
                         roles=CourseTeacher.roles.spectator)
    AssignmentFactory(course=course,
                      submission_type=AssignmentFormat.NO_SUBMIT)
    enrollment = EnrollmentFactory(course=course)
    client.login(teacher)
    gradebook_url = course.get_gradebook_url()
    response = client.get(gradebook_url)
    gradebook = response.context_data['gradebook']
    assert gradebook.student_assignments

    html = response.content.decode('utf-8')
    soup = BeautifulSoup(html, "html.parser")
    assert not soup.find_all("input", {
        "class": "cell __assignment __input"
    })
    final_grade_widget = soup.find("select", {
        "name": f"final_grade_{enrollment.pk}"
    })
    assert final_grade_widget.get('disabled') == ''


@pytest.mark.django_db
def test_get_student_assignment_state():
    sa = StudentAssignmentFactory()
    assert get_student_assignment_state(sa) == "—"
    AssignmentCommentFactory(student_assignment=sa,
                             type=AssignmentSubmissionTypes.SOLUTION)
    assert get_student_assignment_state(sa) == "…"
    sa.score = 0
    assert get_student_assignment_state(sa) == sa.get_score_verbose_display()
    sa.score = None
    sa.status = AssignmentStatus.ON_CHECKING
    assert get_student_assignment_state(sa) == "…"
    sa.status = AssignmentStatus.NEED_FIXES
    assert get_student_assignment_state(sa) == "…"
    sa.status = AssignmentStatus.COMPLETED
    assert get_student_assignment_state(sa) == "…"
    sa.score = 1
    sa.status = AssignmentStatus.NOT_SUBMITTED
    assert get_student_assignment_state(sa) == sa.get_score_verbose_display()


@pytest.mark.parametrize('teaching_dispatch_name,staff_dispatch_name',
                         [('teaching:gradebook_import_course_grades_by_enrollment_id',
                           'staff:gradebook_import_course_grades_by_enrollment_id'),
                          ('teaching:gradebook_import_course_grades_by_yandex_login',
                           'staff:gradebook_import_course_grades_by_yandex_login'),
                          ('teaching:gradebook_import_course_grades_by_stepik_id',
                           'staff:gradebook_import_course_grades_by_stepik_id')])
@pytest.mark.django_db
def test_gradebook_import_course_grades_permissions(teaching_dispatch_name,
                                                    staff_dispatch_name,
                                                    client, lms_resolver,
                                                    assert_login_redirect):
    curator = CuratorFactory()
    teacher1, teacher2, spectator = TeacherFactory.create_batch(3)
    course = CourseFactory(teachers=[teacher1])
    CourseTeacherFactory(teacher=spectator, course=course, roles=CourseTeacher.roles.spectator)
    teaching_url = reverse(teaching_dispatch_name, args=[course.pk])
    staff_url = reverse(teaching_dispatch_name, args=[course.pk])
    resolver_teaching = lms_resolver(teaching_url)
    resolver_staff = lms_resolver(staff_url)
    assert resolver_teaching.func.view_class == resolver_staff.func.view_class
    assert issubclass(resolver_teaching.func.view_class, PermissionRequiredMixin)
    assert issubclass(resolver_teaching.func.view_class, ImportCourseGradesBaseView)
    assert resolver_teaching.func.view_class.permission_required == EditGradebook.name
    assert EditGradebook.name in perm_registry

    assert_login_redirect(teaching_url, method='post')

    client.login(UserFactory())
    response = client.post(teaching_url, data={}, content_type='application/json')
    assert response.status_code == 403

    client.login(teacher2)
    response = client.post(teaching_url, data={}, content_type='application/json')
    assert response.status_code == 403

    e = EnrollmentFactory(course=course)
    client.login(e.student)
    response = client.post(teaching_url, data={}, content_type='application/json')
    assert response.status_code == 403

    client.login(spectator)
    response = client.post(teaching_url, data={}, content_type='application/json')
    assert response.status_code == 403

    client.login(teacher1)
    response = client.post(teaching_url, data={}, content_type='application/json')
    assert response.status_code == 400

    client.login(curator)
    response = client.post(teaching_url, data={}, content_type='application/json')
    assert response.status_code == 400


@pytest.mark.parametrize('id_column_name,dispatch_view_name',
                         [('id', 'teaching:gradebook_import_course_grades_by_enrollment_id'),
                          ('логин на яндексе', 'teaching:gradebook_import_course_grades_by_yandex_login'),
                          ('stepik_id', 'teaching:gradebook_import_course_grades_by_stepik_id')])
@pytest.mark.django_db
def test_gradebook_import_course_grades_wrong_headers(id_column_name, dispatch_view_name, client):
    teacher = TeacherFactory()
    course = CourseFactory(teachers=[teacher])
    url = reverse(dispatch_view_name, args=[course.pk])
    e = EnrollmentFactory(course=course)
    assignment = AssignmentFactory.create(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=500)

    client.login(teacher)
    csv_data = force_bytes(f"""
wrong_id_header,header2,Итоговая оценка
{e.id},1,Отлично
""".strip())

    form = {'csv_file': SimpleUploadedFile("data.csv", csv_data)}
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].level == messages_constants.ERROR
    assert f"Header '{id_column_name}' not found" in str(messages[0])

    csv_data = force_bytes(f"""
{id_column_name},header2,WrongGradeColumn
{e.id},1,Отлично
""".strip())

    form = {'csv_file': SimpleUploadedFile("data.csv", csv_data)}
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].level == messages_constants.ERROR
    assert f"Header 'итоговая оценка' not found" in str(messages[0])


    csv_data = force_bytes(f"""
WrongIDColumn,header2,WrongGradeColumn
{e.id},1,Отлично
""".strip())

    form = {'csv_file': SimpleUploadedFile("data.csv", csv_data)}
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].level == messages_constants.ERROR
    assert f"Header 'итоговая оценка' not found" in str(messages[0])
    assert f"Header '{id_column_name}' not found" in str(messages[0])

    csv_data = force_bytes(f"""

totally-invalid-headers
{e.id},1,Отлично
""".strip())
    form = {'csv_file': SimpleUploadedFile("data.csv", csv_data)}
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert messages[0].level == messages_constants.ERROR
    assert f"Header 'итоговая оценка' not found" in str(messages[0])
    assert f"Header '{id_column_name}' not found" in str(messages[0])


    e.refresh_from_db()
    assert e.grade == GradeTypes.NOT_GRADED
    assert not EnrollmentGradeLog.objects.count()


@pytest.mark.django_db
def test_gradebook_import_course_grades_by_enrollment_id(client):
    teacher = TeacherFactory()
    client.login(teacher)
    course = CourseFactory(teachers=[teacher])
    import_csv_url = reverse('teaching:gradebook_import_course_grades_by_enrollment_id',
                             args=[course.pk])
    e1, e2, e3 = EnrollmentFactory.create_batch(3, course=course)
    assignment = AssignmentFactory.create(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=500)
    csv_data = force_bytes(f"""
id,header2,Итоговая оценка
{e1.id},1,Отлично
0,3,1
,1,1
{e2.id},2,Перезачтено
{e2.id},2,cadabra
incorrect-id,2,Отлично
{e3.id},3,Незачтено
{e3.id},3,Незачёт
{e3.id},3,Зачёт
{e3.id},3,1
""".strip())
    form = {'csv_file': SimpleUploadedFile("data.csv", csv_data)}
    response = client.post(import_csv_url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 2
    assert messages[0].level == messages_constants.INFO
    assert messages[1].level == messages_constants.ERROR
    assert 'для 4 из 7 строк с верными идентификаторами студентов' in str(messages[0])
    assert all(error_msg in str(messages[1]) for error_msg in [
        'Строка 2: студент с идентификатором "0" не найден.',
        'Строка 3: студент с идентификатором "" не найден.',
        "Строка 5: Оценки 'cadabra' не существует.",
        'Строка 6: студент с идентификатором "incorrect-id" не найден.',
        "Строка 7: Оценки 'Незачтено' не существует.",
        f"Строка 10: оценка '1' не подходит для системы оценивая этого курса, идентификатор студента '{e3.id}'."
    ])
    e1.refresh_from_db()
    e2.refresh_from_db()
    e3.refresh_from_db()
    assert e1.grade == GradeTypes.EXCELLENT
    assert e2.grade == GradeTypes.RE_CREDIT
    assert e3.grade == GradeTypes.CREDIT
    assert EnrollmentGradeLog.objects.count() == 4
    log1, log2 = EnrollmentGradeLog.objects.filter(enrollment=e3).order_by('grade_changed_at')
    assert log1.grade == GradeTypes.UNSATISFACTORY
    assert log2.grade == GradeTypes.CREDIT
    assert log2.entry_author == teacher


@pytest.mark.django_db
def test_gradebook_import_course_grades_by_stepik_id(client):
    teacher = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher])
    import_csv_url = reverse('teaching:gradebook_import_course_grades_by_stepik_id',
                             args=[course.pk])
    student1 = StudentFactory(branch__code=Branches.SPB, stepic_id='2')
    student2 = StudentFactory(branch__code=Branches.SPB, stepic_id=None)
    student3 = StudentFactory(branch__code=Branches.SPB, stepic_id='4')
    e1 = EnrollmentFactory(student=student1, course=course)
    e2 = EnrollmentFactory(student=student2, course=course)
    e3 = EnrollmentFactory(student=student3, course=course)
    assignment = AssignmentFactory.create(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=50)
    client.login(teacher)
    csv_data = force_bytes(f"""
stepik_id,header2,Итоговая оценка
{student1.stepic_id},1,Отлично
3,3,1
,2,Перезачтено
{student1.stepic_id},2,cadabra
incorrect-id,2,Отлично
{student3.stepic_id},3,Незачет
{student3.stepic_id},3,зачёт
{student3.stepic_id},3,1
""".strip())
    form = {'csv_file': SimpleUploadedFile("data.csv", csv_data)}
    response = client.post(import_csv_url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 2
    assert messages[0].level == messages_constants.INFO
    assert messages[1].level == messages_constants.ERROR
    assert 'для 3 из 5 строк с верными идентификаторами студентов' in str(messages[0])
    assert all(error_msg in str(messages[1]) for error_msg in [
        'Строка 2: студент с идентификатором "3" не найден.',
        'Строка 3: студент с идентификатором "" не найден.',
        "Строка 4: Оценки 'cadabra' не существует.",
        'Строка 5: студент с идентификатором "incorrect-id" не найден.',
        "Строка 8: оценка '1' не подходит для системы оценивая этого курса,"
        f" идентификатор студента '{student3.stepic_id}'."
    ])
    e1.refresh_from_db()
    e2.refresh_from_db()
    e3.refresh_from_db()
    assert e1.grade == GradeTypes.EXCELLENT
    assert e2.grade == GradeTypes.NOT_GRADED
    assert e3.grade == GradeTypes.CREDIT
    assert EnrollmentGradeLog.objects.count() == 3
    log1, log2 = EnrollmentGradeLog.objects.filter(enrollment=e3).order_by('grade_changed_at')
    assert log1.grade == GradeTypes.UNSATISFACTORY
    assert log2.grade == GradeTypes.CREDIT
    assert log1.entry_author == teacher


@pytest.mark.django_db
def test_gradebook_import_course_grades_by_yandex_login(client):
    teacher = TeacherFactory()
    course = CourseFactory.create(teachers=[teacher])
    import_csv_url = reverse('teaching:gradebook_import_course_grades_by_yandex_login',
                             args=[course.pk])
    student1 = StudentFactory(branch__code=Branches.SPB, yandex_login='Yandex-login1')
    student2 = StudentFactory(branch__code=Branches.SPB, yandex_login='')
    student3 = StudentFactory(branch__code=Branches.SPB, yandex_login='Yandex-login3')
    e1 = EnrollmentFactory(student=student1, course=course)
    e2 = EnrollmentFactory(student=student2, course=course)
    e3 = EnrollmentFactory(student=student3, course=course)
    assignment = AssignmentFactory.create(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT,
        maximum_score=50)
    client.login(teacher)
    csv_data = force_bytes(f"""
Логин на Яндексе,header2,Итоговая оценка
{student1.yandex_login},1,Отлично
3,3,1
,2,Перезачтено
{student1.yandex_login},2,cadabra
incorrect-id,2,Отлично
{student3.yandex_login},3,Незачет
{student3.yandex_login},3,зачёт
{student3.yandex_login},3,1
""".strip())
    form = {'csv_file': SimpleUploadedFile("data.csv", csv_data)}
    response = client.post(import_csv_url, form, follow=True)
    assert response.status_code == 200
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 2
    assert messages[0].level == messages_constants.INFO
    assert messages[1].level == messages_constants.ERROR
    assert 'для 3 из 5 строк с верными идентификаторами студентов' in str(messages[0])
    assert all(error_msg in str(messages[1]) for error_msg in [
        'Строка 2: студент с идентификатором "3" не найден.',
        'Строка 3: студент с идентификатором "" не найден.',
        "Строка 4: Оценки 'cadabra' не существует.",
        'Строка 5: студент с идентификатором "incorrect-id" не найден.',
        "Строка 8: оценка '1' не подходит для системы оценивая этого курса, идентификатор студента"
        f" '{student3.yandex_login}'."
    ])
    e1.refresh_from_db()
    e2.refresh_from_db()
    e3.refresh_from_db()
    assert e1.grade == GradeTypes.EXCELLENT
    assert e2.grade == GradeTypes.NOT_GRADED
    assert e3.grade == GradeTypes.CREDIT
    assert EnrollmentGradeLog.objects.count() == 3
    log1, log2 = EnrollmentGradeLog.objects.filter(enrollment=e3).order_by('grade_changed_at')
    assert log1.grade == GradeTypes.UNSATISFACTORY
    assert log2.grade == GradeTypes.CREDIT
    assert log1.entry_author == teacher
