# -*- coding: utf-8 -*-
import datetime
import logging

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.encoding import smart_bytes
from testfixtures import LogCapture

from core.tests.utils import CSCTestCase
from core.timezone import now_local
from core.urls import branch_aware_reverse, reverse
from courses.tests.factories import *
from learning.settings import Branches
from learning.tests.factories import *
from users.constants import Roles
from users.tests.factories import UserFactory, StudentFactory, TeacherFactory, \
    CuratorFactory
from .mixins import *


# TODO: Список отображаемых курсов для центра/клуба
# TODO: Написать тест, который проверяет, что по-умолчанию в форму
# редактирования описания ПРОЧТЕНИЯ подставляется описание из курса. И описание прочтения, если оно уже есть.
# TODO: test redirects on course offering page if tab exists but user has no access
# TODO: test assignment deadline


class CourseListTeacherTests(MyUtilitiesMixin, CSCTestCase):
    url_name = 'teaching:course_list'
    groups_allowed = [Roles.TEACHER]

    def test_group_security(self):
        """
        Checks if only users in groups listed in self.groups_allowed can
        access the page which url is stored in self.url_name.
        Also checks that curator can access any page
        """
        self.assertTrue(self.groups_allowed is not None)
        self.assertTrue(self.url_name is not None)
        self.assertLoginRedirect(reverse(self.url_name))
        all_test_groups = [
            [],
            [Roles.TEACHER],
            [Roles.STUDENT],
            [Roles.GRADUATE]
        ]
        for groups in all_test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if any(group in self.groups_allowed for group in groups):
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertLoginRedirect(reverse(self.url_name))
            self.client.logout()
        self.doLogin(CuratorFactory())
        self.assertStatusCode(200, self.url_name)


class CourseDetailTests(MyUtilitiesMixin, CSCTestCase):
    def test_basic_get(self):
        course = CourseFactory.create()
        assert 200 == self.client.get(course.get_absolute_url()).status_code
        url = branch_aware_reverse('courses:course_detail', kwargs={
            "course_slug": "space-odyssey",
            "semester_year": 2010,
            "semester_type": "autumn",
            "branch_code_request": ""
        })
        assert self.client.get(url).status_code == 404

    def test_course_user_relations(self):
        """
        Testing is_enrolled and is_actual_teacher here
        """
        student = StudentFactory()
        teacher = TeacherFactory()
        co = CourseFactory.create()
        co_other = CourseFactory.create()
        url = co.get_absolute_url()
        ctx = self.client.get(url).context
        self.doLogin(student)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        EnrollmentFactory.create(student=student, course=co_other)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        EnrollmentFactory.create(student=student, course=co)
        ctx = self.client.get(url).context
        self.assertEqual(True, ctx['request_user_enrollment'] is not None)
        self.assertEqual(False, ctx['is_actual_teacher'])
        self.client.logout()
        self.doLogin(teacher)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        CourseTeacherFactory(course=co_other, teacher=teacher)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
        CourseTeacherFactory(course=co, teacher=teacher)
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(True, ctx['is_actual_teacher'])

    def test_assignment_list(self):
        student = StudentFactory()
        teacher = TeacherFactory()
        today = now_local(student.get_timezone()).date()
        next_day = today + datetime.timedelta(days=1)
        course = CourseFactory(teachers=[teacher],
                               semester=SemesterFactory.create_current(),
                               completed_at=next_day)
        course_url = course.get_absolute_url()
        EnrollmentFactory(student=student, course=course)
        a = AssignmentFactory.create(course=course)
        response = self.client.get(course_url)
        assert response.status_code == 200
        self.doLogin(student)
        self.assertContains(self.client.get(course_url), a.title)
        a_s = StudentAssignment.objects.get(assignment=a, student=student)
        self.assertContains(self.client.get(course_url), a_s.get_student_url())
        a_s.delete()
        with LogCapture(level=logging.INFO) as l:
            self.assertEqual(200, self.client.get(course_url).status_code)
            l.check(('learning.tabs',
                     'INFO',
                     f"no StudentAssignment for "
                     f"student ID {student.pk}, assignment ID {a.pk}"))
        self.client.logout()
        self.doLogin(teacher)
        self.assertContains(self.client.get(course_url), a.title)
        self.assertContains(self.client.get(course_url), a.get_teacher_url())


class CourseEditDescrTests(MyUtilitiesMixin, CSCTestCase):
    def test_security(self):
        teacher = TeacherFactory()
        teacher_other = TeacherFactory()
        co = CourseFactory.create(teachers=[teacher])
        url = co.get_update_url()
        self.assertLoginRedirect(url)
        self.doLogin(teacher_other)
        self.assertLoginRedirect(url)
        self.doLogout()
        self.doLogin(teacher)
        self.assertStatusCode(200, url, make_reverse=False)


class ASStudentDetailTests(MyUtilitiesMixin, CSCTestCase):
    def test_security(self):
        teacher = TeacherFactory()
        student = StudentFactory()
        s = SemesterFactory.create_current()
        co = CourseFactory(main_branch=student.branch, semester=s,
                           teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        student_url = a_s.get_student_url()
        assert self.client.get(student_url).status_code == 302
        self.assertLoginRedirect(student_url)
        test_groups = [
            [],
            [Roles.TEACHER],
            [Roles.STUDENT],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            assert self.client.get(student_url).status_code == 403
            self.doLogout()
        self.doLogin(student)
        assert self.client.get(student_url).status_code == 200
        # Change student to graduate, make sure they have access to HW
        student.groups.all().delete()
        student.add_group(Roles.GRADUATE)
        student.save()
        self.assertEqual(200, self.client.get(student_url).status_code)

    def test_assignment_contents(self):
        student = StudentFactory()
        semester = SemesterFactory.create_current()
        co = CourseFactory(main_branch=student.branch, semester=semester)
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.text)

    def test_teacher_redirect_to_appropriate_link(self):
        student = StudentFactory()
        teacher = TeacherFactory()
        semester = SemesterFactory.create_current()
        co = CourseFactory(main_branch=student.branch, teachers=[teacher],
                           semester=semester)
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        self.doLogin(student)
        assert self.client.get(url).status_code == 200
        self.doLogin(teacher)
        expected_url = a_s.get_teacher_url()
        self.assertEqual(302, self.client.get(url).status_code)
        self.assertRedirects(self.client.get(url), expected_url)

    def test_comment(self):
        student = StudentFactory()
        # Create open reading to make sure student has access to CO
        co = CourseFactory(main_branch=student.branch, is_open=True)
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        student_url = a_s.get_student_url()
        create_comment_url = reverse("study:assignment_comment_create",
                                     kwargs={"pk": a_s.pk})
        comment_dict = {'text': "Test comment without file"}
        self.doLogin(student)
        self.assertRedirects(self.client.post(create_comment_url, comment_dict),
                             student_url)
        response = self.client.get(student_url)
        assert smart_bytes(comment_dict['text']) in response.content
        f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
        comment_dict = {'text': "Test comment with file",
                        'attached_file': f}
        self.assertRedirects(self.client.post(create_comment_url, comment_dict),
                             student_url)
        response = self.client.get(student_url)
        assert smart_bytes(comment_dict['text']) in response.content
        assert smart_bytes('attachment1') in response.content


class ASTeacherDetailTests(MyUtilitiesMixin, CSCTestCase):
    def test_security(self):
        teacher = TeacherFactory()
        student = StudentFactory()
        co = CourseFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        teacher_url = a_s.get_teacher_url()
        assert self.client.get(teacher_url).status_code == 302
        self.assertLoginRedirect(teacher_url)
        # Test GET
        test_groups = [
            [],
            [Roles.TEACHER],
            [Roles.STUDENT],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups,
                                            branch__code=Branches.SPB))
            response = self.client.get(teacher_url)
            assert response.status_code == 403
            self.doLogout()
        self.doLogin(teacher)
        assert self.client.get(teacher_url).status_code == 200
        self.doLogout()
        self.doLogin(student)
        assert self.client.get(teacher_url).status_code == 403
        self.doLogout()
        # Test POST
        grade_dict = {'grading_form': True, 'score': 3}
        test_groups = [
            [],
            [Roles.TEACHER],
            [Roles.STUDENT]
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups,
                                            branch__code=Branches.SPB))
            assert self.client.get(teacher_url).status_code == 403
            self.doLogout()

    def test_comment(self):
        teacher = TeacherFactory()
        enrollment = EnrollmentFactory(course__teachers=[teacher])
        student = enrollment.student
        a = AssignmentFactory.create(course=enrollment.course)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        teacher_url = a_s.get_teacher_url()
        create_comment_url = reverse("teaching:assignment_comment_create",
                                     kwargs={"pk": a_s.pk})
        form_dict = {'text': "Test comment without file"}
        self.doLogin(teacher)
        self.assertRedirects(self.client.post(create_comment_url, form_dict), teacher_url)
        response = self.client.get(teacher_url)
        assert smart_bytes(form_dict['text']) in response.content
        f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
        form_dict = {'text': "Test comment with file",
                     'attached_file': f}
        self.assertRedirects(self.client.post(create_comment_url, form_dict), teacher_url)
        response = self.client.get(teacher_url)
        assert smart_bytes(form_dict['text']) in response.content
        assert smart_bytes('attachment1') in response.content

    def test_grading(self):
        teacher = TeacherFactory()
        co = CourseFactory.create(teachers=[teacher])
        student = StudentFactory()
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co, maximum_score=13)
        a_s = (StudentAssignment.objects
               .get(assignment=a, student=student))
        url = a_s.get_teacher_url()
        grade_dict = {
            'grading_form': True,
            'score': 11
        }
        self.doLogin(teacher)
        self.assertRedirects(self.client.post(url, grade_dict), url)
        self.assertEqual(11, StudentAssignment.objects.get(pk=a_s.pk).score)
        resp = self.client.get(url)
        self.assertContains(resp, "value=\"11\"")
        self.assertContains(resp, "/{}".format(13))
        # wrong grading value can't be set
        grade_dict['score'] = 42
        self.client.post(url, grade_dict)
        self.assertEqual(400, self.client.post(url, grade_dict).status_code)
        self.assertEqual(11, StudentAssignment.objects.get(pk=a_s.pk).score)

    def test_next_unchecked(self):
        teacher = TeacherFactory()
        student = StudentFactory()
        co = CourseFactory.create(teachers=[teacher])
        co_other = CourseFactory.create()
        EnrollmentFactory.create(student=student, course=co)
        EnrollmentFactory.create(student=student, course=co_other)
        a1, a2 = AssignmentFactory.create_batch(2, course=co)
        a_other = AssignmentFactory.create(course=co_other)
        a_s1 = (StudentAssignment.objects
                .get(assignment=a1, student=student))
        a_s2 = (StudentAssignment.objects
                .get(assignment=a2, student=student))
        a_s_other = (StudentAssignment.objects
                     .get(assignment=a_other, student=student))
        url1 = a_s1.get_teacher_url()
        url2 = a_s2.get_teacher_url()
        self.doLogin(teacher)
        assert self.client.get(url1).context['next_student_assignment'] is None
        assert self.client.get(url2).context['next_student_assignment'] is None
        [AssignmentCommentFactory.create(author=a_s.student,
                                         student_assignment=a_s)
         for a_s in [a_s1, a_s2]]
        assert self.client.get(url1).context['next_student_assignment'] == a_s2
        assert self.client.get(url2).context['next_student_assignment'] == a_s1


@pytest.mark.django_db
def test_events_smoke(client):
    evt = EventFactory.create()
    url = evt.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 200
    assert evt.name.encode() in response.content
    assert smart_bytes(evt.venue.get_absolute_url()) in response.content


# TODO: test CourseOffering edit-description page. returned more than one CourseOffering error if we have CO for kzn and spb


