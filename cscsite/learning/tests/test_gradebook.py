import pytest
import unicodecsv
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import smart_bytes

from learning.factories import SemesterFactory, CourseOfferingFactory, \
    AssignmentFactory, EnrollmentFactory
from learning.forms import MarksSheetTeacherImportGradesForm
from learning.models import StudentAssignment, Enrollment
from learning.settings import GRADING_TYPES, GRADES, PARTICIPANT_GROUPS
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
    url = reverse('markssheet_teacher', args=[co.get_city(),
                                              co.course.slug,
                                              co.semester.year,
                                              co.semester.type])
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
        url = reverse('markssheet_teacher_csv',
                      args=[co.get_city(), co.course.slug, co.semester.slug])
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
        student1, student2 = UserFactory.create_batch(2, groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        a1, a2 = AssignmentFactory.create_batch(2, course_offering=co)
        [EnrollmentFactory.create(student=s, course_offering=co)
            for s in [student1, student2]]
        url = reverse('markssheet_teacher_csv',
                      args=[co.get_city(), co.course.slug, co.semester.slug])
        combos = [(a, s, grade+1)
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
        url = reverse('markssheet_teacher', args=[co1.get_city(),
                                                  co1.course.slug,
                                                  co1.semester.year,
                                                  co1.semester.type])
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
            url = reverse('markssheet_teacher',
                          args=[co.get_city(),
                                co.course.slug,
                                co.semester.year,
                                co.semester.type])
            self.assertContains(resp, url)

    def test_nonempty_markssheet(self):
        teacher = TeacherCenterFactory()
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        co = CourseOfferingFactory.create(teachers=[teacher])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        as_online = AssignmentFactory.create_batch(
            2, course_offering=co)
        as_offline = AssignmentFactory.create_batch(
            3, course_offering=co, is_online=False)
        url = reverse('markssheet_teacher', args=[co.get_city(),
                                                  co.course.slug,
                                                  co.semester.year,
                                                  co.semester.type])
        self.doLogin(teacher)
        resp = self.client.get(url)
        for student in students:
            name = "{}&nbsp;{}.".format(student.last_name,
                                        student.first_name[0])
            self.assertContains(resp, name)
        for as_ in as_online:
            self.assertContains(resp, as_.title)
            for student in students:
                a_s = StudentAssignment.objects.get(student=student,
                                                    assignment=as_)
                a_s_url = reverse('a_s_detail_teacher', args=[a_s.pk])
                self.assertContains(resp, a_s_url)
        for as_ in as_offline:
            self.assertContains(resp, as_.title)
            for student in students:
                a_s = StudentAssignment.objects.get(student=student,
                                                    assignment=as_)
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
        url = reverse('markssheet_teacher', args=[co.get_city(),
                                                  co.course.slug,
                                                  co.semester.year,
                                                  co.semester.type])
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
        url = reverse('markssheet_teacher', args=[co.get_city(),
                                                  co.course.slug,
                                                  co.semester.year,
                                                  co.semester.type])
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
        redirect_url = reverse('markssheet_teacher',
                               args=[co.get_city(),
                                     co.course.slug,
                                     co.semester.year,
                                     co.semester.type])
        url = reverse('markssheet_teacher_csv_import_stepic', args=[co.pk])
        resp = self.client.post(url, {'assignment': assignments[0].pk})
        self.assertRedirects(resp, redirect_url)
        self.assertIn('messages', resp.cookies)
        # TODO: provide testing with request.FILES. Move it to test_utils...
    # TODO: write test for user search by stepic id
