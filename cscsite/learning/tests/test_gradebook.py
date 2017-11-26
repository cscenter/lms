import datetime
import pytest
import pytz
import unicodecsv
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import smart_bytes

from learning.factories import SemesterFactory, CourseOfferingFactory, \
    AssignmentFactory, EnrollmentFactory
from learning.forms import MarksSheetTeacherImportGradesForm
from learning.gradebook import gradebook_data
from learning.models import StudentAssignment, Enrollment
from learning.settings import GRADING_TYPES, GRADES, PARTICIPANT_GROUPS, \
    STUDENT_STATUS
from learning.tests.mixins import MyUtilitiesMixin
from learning.tests.test_views import GroupSecurityCheckMixin
from users.factories import TeacherCenterFactory, StudentCenterFactory, \
    UserFactory


# TODO: test redirect to gradebook for teachers if only 1 course in current term


@pytest.mark.django_db
def test_gradebook_recalculate_grading_type(client):
    teacher = TeacherCenterFactory.create()
    students = StudentCenterFactory.create_batch(2)
    s = SemesterFactory.create_current()
    co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
    assert co.grading_type == GRADING_TYPES.default
    assignments = AssignmentFactory.create_batch(2,
                                                 course_offering=co,
                                                 is_online=True)
    client.login(teacher)
    url = co.get_gradebook_url()
    form = {}
    for s in students:
        enrollment = EnrollmentFactory.create(student=s, course_offering=co)
        field = 'final_grade_{}'.format(enrollment.pk)
        form[field] = GRADES.good
    # Save empty form first
    response = client.post(url, {}, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.default
    # Update final grades, still should be `default`
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.default
    student = students[0]
    user_detail_url = reverse('user_detail', args=[student.pk])
    # Now we should get `binary` type after all final grades
    # will be equal `pass`
    for key in form:
        form[key] = getattr(GRADES, 'pass')
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.binary
    response = client.get(user_detail_url)
    assert smart_bytes("/enrollment|pass/") in response.content
    assert smart_bytes("/satisfactory/") not in response.content
    # Update random submission grade, grading_type shouldn't change
    submission = StudentAssignment.objects.get(student=student,
                                               assignment=assignments[0])
    form = {
        'a_s_{}'.format(submission.pk): 2  # random valid grade
    }
    response = client.post(url, form, follow=True)
    assert response.status_code == 200
    co.refresh_from_db()
    assert co.grading_type == GRADING_TYPES.binary
    # Manually set default grading type and check that grade repr changed
    co.grading_type = GRADING_TYPES.default
    co.save()
    response = client.get(user_detail_url)
    assert smart_bytes("/enrollment|pass/") not in response.content
    assert smart_bytes("/satisfactory/") in response.content


class MarksSheetCSVTest(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co)
        EnrollmentFactory.create(student=student, course_offering=co)
        url = co.get_gradebook_url(format="csv")
        self.assertLoginRedirect(url)
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
        self.doLogin(TeacherCenterFactory())
        self.assertEquals(404, self.client.get(url).status_code)
        self.doLogin(student)
        self.assertLoginRedirect(url)
        self.doLogin(teacher)
        self.assertEquals(200, self.client.get(url).status_code)

    def test_csv(self):
        teacher = TeacherCenterFactory()
        student1, student2 = StudentCenterFactory.create_batch(2)
        co = CourseOfferingFactory.create(teachers=[teacher])
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co)
        for s in [student1, student2]:
            EnrollmentFactory.create(student=s, course_offering=co)
        url = co.get_gradebook_url(format="csv")
        combos = [(a, s, grade + 1)
                  for ((a, s), grade)
                  in zip([(a, s)
                          for a in [a1, a2]
                          for s in [student1, student2]],
                         range(4))]
        for a, s, grade in combos:
            a_s = StudentAssignment.objects.get(student=s, assignment=a)
            a_s.grade = grade
            a_s.save()
        self.doLogin(teacher)
        data = [row for row in unicodecsv.reader(self.client.get(url)) if row]
        self.assertEquals(3, len(data))
        self.assertIn(a1.title, data[0])
        row_last_names = [row[0] for row in data]
        for a, s, grade in combos:
            row = row_last_names.index(s.last_name)
            col = data[0].index(a.title)
            self.assertEquals(grade, int(data[row][col]))


class MarksSheetTeacherTests(MyUtilitiesMixin, TestCase):
    # TODO(Dmitry): test security

    def test_empty_markssheet(self):
        """Test marksheet with empty assignments list"""
        teacher = TeacherCenterFactory()
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        co1 = CourseOfferingFactory.create(teachers=[teacher])
        co2 = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student, course_offering=co1)
            EnrollmentFactory.create(student=student,
                                     course_offering=co2)
        url = co1.get_gradebook_url()
        self.doLogin(teacher)
        resp = self.client.get(url)
        for student in students:
            name = "{}&nbsp;{}.".format(student.last_name,
                                        student.first_name[0])
            self.assertContains(resp, name, 1)
            enrollment = Enrollment.active.get(student=student,
                                        course_offering=co1)
            field = 'final_grade_{}'.format(enrollment.pk)
            self.assertIn(field, resp.context['form'].fields)
        for co in [co1, co2]:
            url = co.get_gradebook_url()
            self.assertContains(resp, url)

    def test_nonempty_markssheet(self):
        teacher = TeacherCenterFactory()
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        as_online = AssignmentFactory.create_batch(2, course_offering=co)
        as_offline = AssignmentFactory.create_batch(3, course_offering=co,
                                                    is_online=False)
        url = co.get_gradebook_url()
        self.doLogin(teacher)
        resp = self.client.get(url)
        for student in students:
            name = "{}&nbsp;{}.".format(student.last_name,
                                        student.first_name[0])
            self.assertContains(resp, name)
        for as_ in as_online:
            self.assertContains(resp, as_.title)
            for s in students:
                a_s = StudentAssignment.objects.get(student=s, assignment=as_)
                self.assertContains(resp, a_s.get_teacher_url())
        for as_ in as_offline:
            self.assertContains(resp, as_.title)
            for s in students:
                a_s = StudentAssignment.objects.get(student=s, assignment=as_)
                self.assertIn('a_s_{}'.format(a_s.pk),
                              resp.context['form'].fields)

    def test_total_score(self):
        """Calculate total score by assignments for course offering"""
        teacher = TeacherCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        student = StudentCenterFactory()
        EnrollmentFactory.create(student=student, course_offering=co)
        as_cnt = 2
        assignments = AssignmentFactory.create_batch(as_cnt, course_offering=co)
        # AssignmentFactory implicitly create StudentAssignment instances
        # with empty grade value.
        default_grade = 10
        for assignment in assignments:
            a_s = StudentAssignment.objects.get(student=student,
                                                assignment=assignment)
            a_s.grade = default_grade
            a_s.save()
        expected_total_score = as_cnt * default_grade
        url = co.get_gradebook_url()
        self.doLogin(teacher)
        resp = self.client.get(url)
        head_student = next(iter(resp.context['students'].items()))
        self.assertEquals(head_student[1]["total"], expected_total_score)

    def test_save_markssheet(self):
        teacher = TeacherCenterFactory()
        students = UserFactory.create_batch(2, groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co,
                                                is_online=False)
        url = co.get_gradebook_url()
        self.doLogin(teacher)
        form = {}
        pairs = zip([StudentAssignment.objects.get(student=student, assignment=a)
                     for student in students
                     for a in [a1, a2]],
            [2, 3, 4, 5])
        for submission, grade in pairs:
            enrollment = Enrollment.active.get(student=submission.student,
                                                course_offering=co)
            form['a_s_{}'.format(submission.pk)] = grade
            field = 'final_grade_{}'.format(enrollment.pk)
            form[field] = 'good'
        self.assertRedirects(self.client.post(url, form), url)
        for a_s, grade in pairs:
            self.assertEqual(grade, (StudentAssignment.objects
                                     .get(pk=a_s.pk)
                                     .grade))
        for student in students:
            self.assertEqual('good', (Enrollment.active
                                      .get(student=student,
                                           course_offering=co)
                                      .grade))

    def test_import_stepic(self):
        teacher = TeacherCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        student = StudentCenterFactory()
        EnrollmentFactory.create(student=student, course_offering=co)
        assignments = AssignmentFactory.create_batch(3, course_offering=co)
        # for assignment in assignments:
        #     a_s = StudentAssignment.objects.get(student=student,
        #                                         assignment=assignment)
        # Import grades allowed only for particular course offering
        form_fields = {'assignment': assignments[0].pk}
        form = MarksSheetTeacherImportGradesForm(form_fields,
                                                 course_id=co.course.pk)
        self.assertFalse(form.is_valid())
        self.assertListEqual(list(form.errors.keys()), ['csv_file'])
        # Teachers can import grades only for own CO
        teacher2 = TeacherCenterFactory()
        self.doLogin(teacher2)
        url = reverse('markssheet_teacher_csv_import_stepic', args=[co.pk])
        resp = self.client.post(url, {'assignment': assignments[0].pk})
        self.assertEqual(resp.status_code, 404)
        # Wrong assignment id
        self.doLogin(teacher)
        form = MarksSheetTeacherImportGradesForm(
            {'assignment': max((a.pk for a in assignments)) + 1},
            course_id=co.course.id)
        self.assertFalse(form.is_valid())
        self.assertIn('assignment', form.errors)
        # Wrong course offering id
        form = MarksSheetTeacherImportGradesForm(form_fields, course_id=-1)
        self.assertFalse(form.is_valid())
        self.assertIn('assignment', form.errors)
        # CO not found
        url = reverse('markssheet_teacher_csv_import_stepic', args=[co.pk + 1])
        resp = self.client.post(url, {'assignment': assignments[0].pk})
        self.assertEqual(resp.status_code, 404)
        # Check redirects
        redirect_url = co.get_gradebook_url()
        url = reverse('markssheet_teacher_csv_import_stepic', args=[co.pk])
        resp = self.client.post(url, {'assignment': assignments[0].pk})
        self.assertRedirects(resp, redirect_url)
        self.assertIn('messages', resp.cookies)
        # TODO: provide testing with request.FILES. Move it to test_utils...
    # TODO: write test for user search by stepic id


@pytest.mark.django_db
def test_gradebook_data():
    co = CourseOfferingFactory()
    e1, e2, e3, e4, e5 = EnrollmentFactory.create_batch(5, course_offering=co)
    a1, a2, a3 = AssignmentFactory.create_batch(3, course_offering=co,
                                                grade_min=1, grade_max=10)
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
    sa.grade = 3
    sa.save()
    data = gradebook_data(co)
    s3_index = 0
    a2_index = 2
    s3_a2_progress = data.submissions[s3_index][a2_index]
    assert s3_a2_progress is not None
    assert s3_a2_progress["score"] == 3
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
    # Check grid with expelled students
    e5.student.status = STUDENT_STATUS.expelled
    e5.student.save()
    a_new = AssignmentFactory(course_offering=co, grade_min=3, grade_max=7)
    data = gradebook_data(co)
    s5_index = 4
    new_a_index = 3
    for x, row in enumerate(data.submissions):
        for y, cell in enumerate(row):
            if x == s5_index and y == new_a_index:
                assert data.submissions[x][y] is None
            else:
                assert data.submissions[x][y] is not None

