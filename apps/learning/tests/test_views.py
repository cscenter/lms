# -*- coding: utf-8 -*-
import logging

import pytest
import pytz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.encoding import smart_bytes
from testfixtures import LogCapture

from core.timezone import now_local
from core.utils import city_aware_reverse
from courses.models import Course
from courses.utils import get_current_term_pair
from learning.enrollment import course_failed_by_student
from learning.tests.factories import *
from learning.settings import StudentStatuses, GradeTypes
from learning.tests.utils import check_url_security
from users.factories import StudentFactory, StudentClubFactory, \
    GraduateFactory, TeacherCenterFactory
from users.constants import AcademicRoles
from .mixins import *


# TODO: Список отображаемых курсов для центра/клуба
# TODO: Написать тест, который проверяет, что по-умолчанию в форму
# редактирования описания ПРОЧТЕНИЯ подставляется описание из курса. И описание прочтения, если оно уже есть.
# TODO: test redirects on course offering page if tab exists but user has no access
# TODO: test assignment deadline


class GroupSecurityCheckMixin(MyUtilitiesMixin):
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
            [AcademicRoles.TEACHER_CENTER],
            [AcademicRoles.STUDENT_CENTER],
            [AcademicRoles.GRADUATE_CENTER]
        ]
        for groups in all_test_groups:
            self.doLogin(UserFactory.create(groups=groups, city_id='spb'))
            if any(group in self.groups_allowed for group in groups):
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertLoginRedirect(reverse(self.url_name))
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True, city_id='spb'))
        self.assertStatusCode(200, self.url_name)


@pytest.mark.django_db
def test_video_list(client):
    CourseFactory.create_batch(2, is_published_in_video=False)
    with_video = CourseFactory.create_batch(5,
                                            is_published_in_video=True)
    response = client.get(reverse('course_video_list'))
    co_to_show = response.context['object_list']
    assert len(co_to_show) == 5
    assert set(with_video) == set(co_to_show)


class CourseListTeacherTests(GroupSecurityCheckMixin,
                             MyUtilitiesMixin, TestCase):
    url_name = 'course_list_teacher'
    groups_allowed = [AcademicRoles.TEACHER_CENTER]


class CourseDetailTests(MyUtilitiesMixin, TestCase):
    def test_basic_get(self):
        co = CourseFactory.create()
        assert 200 == self.client.get(co.get_absolute_url()).status_code
        url = city_aware_reverse('course_detail', kwargs={
            "course_slug": "space-odyssey",
            "semester_slug": "2010",
            "city_code": ""
        })
        # Can't parse `semester_slug`
        self.assertEqual(400, self.client.get(url).status_code)

    def test_course_user_relations(self):
        """
        Testing is_enrolled and is_actual_teacher here
        """
        student = StudentCenterFactory()
        teacher = TeacherCenterFactory()
        co = CourseFactory.create()
        co_other = CourseFactory.create()
        url = co.get_absolute_url()
        ctx = self.client.get(url).context
        self.assertEqual(None, ctx['request_user_enrollment'])
        self.assertEqual(False, ctx['is_actual_teacher'])
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
        student = StudentCenterFactory(city_id='spb')
        teacher = TeacherCenterFactory(city_id='spb')
        today = now_local(student.city_code).date()
        next_day = today + datetime.timedelta(days=1)
        co = CourseFactory.create(teachers=[teacher],
                                  semester=SemesterFactory.create_current(),
                                  completed_at=next_day)
        url = co.get_absolute_url()
        EnrollmentFactory(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        self.assertNotContains(self.client.get(url), a.title)
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.title)
        a_s = StudentAssignment.objects.get(assignment=a, student=student)
        self.assertContains(self.client.get(url), a_s.get_student_url())
        a_s.delete()
        with LogCapture(level=logging.INFO) as l:
            self.assertEqual(200, self.client.get(url).status_code)
            l.check(('learning.tabs',
                     'INFO',
                     f"no StudentAssignment for "
                     f"student ID {student.pk}, assignment ID {a.pk}"))
        self.client.logout()
        self.doLogin(teacher)
        self.assertContains(self.client.get(url), a.title)
        self.assertContains(self.client.get(url),
                            reverse('assignment_detail_teacher', args=[a.pk]))


class CourseEditDescrTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = TeacherCenterFactory()
        teacher_other = TeacherCenterFactory()
        co = CourseFactory.create(teachers=[teacher])
        url = co.get_update_url()
        self.assertLoginRedirect(url)
        self.doLogin(teacher_other)
        self.assertLoginRedirect(url)
        self.doLogout()
        self.doLogin(teacher)
        self.assertStatusCode(200, url, make_reverse=False)


class ASStudentDetailTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory(city_id='spb')
        s = SemesterFactory.create_current(city_code=settings.DEFAULT_CITY_CODE)
        co = CourseFactory(city_id='spb', semester=s,
                           teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        assert self.client.get(url).status_code == 302
        self.assertLoginRedirect(url)
        test_groups = [
            [],
            [AcademicRoles.TEACHER_CENTER],
            [AcademicRoles.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups, city_id='spb'))
            if not groups:
                assert self.client.get(url).status_code == 302
            else:
                self.assertLoginRedirect(url)
            self.doLogout()
        self.doLogin(student)
        assert self.client.get(url).status_code == 200
        # Change student to graduate, make sure they have access to HW
        student.groups.clear()
        student.groups.add(AcademicRoles.GRADUATE_CENTER)
        student.save()
        self.assertEqual(200, self.client.get(url).status_code)

    def test_failed_course(self):
        """
        Make sure student has access only to assignments which he passed if
        he completed course with unsatisfactory grade
        """
        teacher = TeacherCenterFactory()
        student = StudentFactory(city_id='spb')
        past_year = datetime.datetime.now().year - 3
        past_semester = SemesterFactory.create(year=past_year)
        co = CourseFactory(city_id='spb', teachers=[teacher],
                           semester=past_semester)
        enrollment = EnrollmentFactory(student=student, course=co,
                                       grade=GradeTypes.UNSATISFACTORY)
        a = AssignmentFactory(course=co)
        s_a = StudentAssignment.objects.get(student=student, assignment=a)
        assert s_a.score is None
        self.doLogin(student)
        url = s_a.get_student_url()
        response = self.client.get(url)
        self.assertLoginRedirect(url)
        # assert response.status_code == 403
        # Student discussed the assignment, so has access
        ac = AssignmentCommentFactory.create(student_assignment=s_a,
                                             author=student)
        response = self.client.get(url)
        co.refresh_from_db()
        assert course_failed_by_student(co, student)
        # Course completed, but not failed, user can see all assignments
        ac.delete()
        enrollment.grade = GradeTypes.GOOD
        enrollment.save()
        response = self.client.get(url)
        assert not course_failed_by_student(co, student)
        assert response.status_code == 200
        # The same behavior should be for expelled student
        student.status = StudentStatuses.EXPELLED
        student.save()
        self.doLogin(student)
        response = self.client.get(url)
        assert response.status_code == 200
        enrollment.grade = GradeTypes.UNSATISFACTORY
        enrollment.save()
        response = self.client.get(url)
        self.assertLoginRedirect(url)
        ac = AssignmentCommentFactory.create(student_assignment=s_a,
                                             author=student)
        response = self.client.get(url)
        assert response.status_code == 200
        # Ok, next case - completed course failed, no comments but has grade
        ac.delete()
        s_a.score = 1
        s_a.save()
        response = self.client.get(url)
        assert response.status_code == 200
        # The same if student not expelled
        student.status = StudentStatuses.WILL_GRADUATE
        student.save()
        self.doLogin(student)
        response = self.client.get(url)
        assert response.status_code == 200

    def test_assignment_contents(self):
        student = StudentCenterFactory(city_id='spb')
        semester = SemesterFactory.create_current()
        co = CourseFactory.create(city_id='spb', semester=semester)
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        self.doLogin(student)
        self.assertContains(self.client.get(url), a.text)

    def test_teacher_redirect_to_appropriate_link(self):
        student = StudentCenterFactory(city_id='spb')
        teacher = TeacherCenterFactory()
        semester = SemesterFactory.create_current()
        co = CourseFactory(city_id='spb', teachers=[teacher],
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
        student = StudentCenterFactory(city_id='spb')
        # Create open reading to make sure student has access to CO
        co = CourseFactory(city_id='spb', is_open=True)
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_student_url()
        comment_dict = {'text': "Test comment without file"}
        self.doLogin(student)
        self.assertRedirects(self.client.post(url, comment_dict), url)
        self.assertContains(self.client.get(url), comment_dict['text'])
        f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
        comment_dict = {'text': "Test comment with file",
                        'attached_file': f}
        self.assertRedirects(self.client.post(url, comment_dict), url)
        resp = self.client.get(url)
        self.assertContains(resp, comment_dict['text'])
        self.assertContains(resp, 'attachment1')


class ASTeacherDetailTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        co = CourseFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_teacher_url()
        assert self.client.get(url).status_code == 302
        self.assertLoginRedirect(url)
        # Test GET
        test_groups = [
            [],
            [AcademicRoles.TEACHER_CENTER],
            [AcademicRoles.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == [AcademicRoles.TEACHER_CENTER]:
                self.assertLoginRedirect(url)
            else:
                assert self.client.get(url).status_code == 302
            self.doLogout()
        self.doLogin(teacher)
        self.assertEqual(200, self.client.get(url).status_code)
        self.doLogout()
        self.doLogin(student)
        assert self.client.get(url).status_code == 302
        self.assertLoginRedirect(url)
        self.doLogout()
        # Test POST
        grade_dict = {'grading_form': True, 'score': 3}
        test_groups = [
            [],
            [AcademicRoles.TEACHER_CENTER],
            [AcademicRoles.STUDENT_CENTER]
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == [AcademicRoles.TEACHER_CENTER]:
                self.assertPOSTLoginRedirect(url, grade_dict)
            else:
                assert self.client.get(url).status_code == 302
            self.doLogout()

    def test_comment(self):
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        co = CourseFactory.create(teachers=[teacher])
        EnrollmentFactory.create(student=student, course=co)
        a = AssignmentFactory.create(course=co)
        a_s = (StudentAssignment.objects
               .filter(assignment=a, student=student)
               .get())
        url = a_s.get_teacher_url()
        comment_dict = {'text': "Test comment without file"}
        self.doLogin(teacher)
        self.assertRedirects(self.client.post(url, comment_dict), url)
        self.assertContains(self.client.get(url), comment_dict['text'])
        f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
        comment_dict = {'text': "Test comment with file",
                        'attached_file': f}
        self.assertRedirects(self.client.post(url, comment_dict), url)
        resp = self.client.get(url)
        self.assertContains(resp, comment_dict['text'])
        self.assertContains(resp, 'attachment1')

    def test_grading(self):
        teacher = TeacherCenterFactory()
        co = CourseFactory.create(teachers=[teacher])
        student = StudentCenterFactory()
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
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
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
        self.assertEqual(None, self.client.get(url1).context['next_a_s_pk'])
        self.assertEqual(None, self.client.get(url2).context['next_a_s_pk'])
        [AssignmentCommentFactory.create(author=a_s.student,
                                         student_assignment=a_s)
         for a_s in [a_s1, a_s2]]
        self.assertEqual(a_s2.pk, self.client.get(url1).context['next_a_s_pk'])
        self.assertEqual(a_s1.pk, self.client.get(url2).context['next_a_s_pk'])


# Ok, py.test starts here

@pytest.mark.django_db
def test_events_smoke(client):
    evt = EventFactory.create()
    url = evt.get_absolute_url()
    response = client.get(url)
    assert response.status_code == 200
    assert evt.name.encode() in response.content
    assert smart_bytes(evt.venue.get_absolute_url()) in response.content


# TODO: test CourseOffering edit-description page. returned more than one CourseOffering error if we have CO for kzn and spb





@pytest.mark.django_db
def test_student_courses_list(client, settings):
    url = reverse('course_list_student')
    check_url_security(client, settings,
                       groups_allowed=[AcademicRoles.STUDENT_CENTER],
                       url=url)
    student_spb = StudentCenterFactory(city_id='spb')
    client.login(student_spb)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['archive_enrolled']) == 0
    now_year, now_season = get_current_term_pair(student_spb.city_id)
    current_term_spb = SemesterFactory.create(year=now_year, type=now_season)
    cos = CourseFactory.create_batch(4, semester=current_term_spb,
                                     city_id='spb', is_open=False)
    cos_available = cos[:2]
    cos_enrolled = cos[2:]
    prev_year = now_year - 1
    cos_archived = CourseFactory.create_batch(
        3, semester__year=prev_year, is_open=False)
    for co in cos_enrolled:
        EnrollmentFactory.create(student=student_spb, course=co)
    for co in cos_archived:
        EnrollmentFactory.create(student=student_spb, course=co)
    response = client.get(url)
    assert len(cos_enrolled) == len(response.context['ongoing_enrolled'])
    assert set(cos_enrolled) == set(response.context['ongoing_enrolled'])
    assert len(cos_archived) == len(response.context['archive_enrolled'])
    assert set(cos_archived) == set(response.context['archive_enrolled'])
    assert len(cos_available) == len(response.context['ongoing_rest'])
    assert set(cos_available) == set(response.context['ongoing_rest'])
    # Add co from other city
    now_year, now_season = get_current_term_pair('nsk')
    current_term_nsk = SemesterFactory.create(year=now_year, type=now_season)
    co_nsk = CourseFactory.create(semester=current_term_nsk,
                                  city_id='nsk', is_open=False)
    response = client.get(url)
    assert len(cos_enrolled) == len(response.context['ongoing_enrolled'])
    assert len(cos_available) == len(response.context['ongoing_rest'])
    assert len(cos_archived) == len(response.context['archive_enrolled'])
    # Test for student from nsk
    student_nsk = StudentCenterFactory(city_id='nsk')
    client.login(student_nsk)
    CourseFactory.create(semester__year=prev_year, city_id='nsk',
                         is_open=False)
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 1
    assert set(response.context['ongoing_rest']) == {co_nsk}
    assert len(response.context['archive_enrolled']) == 0
    # Add open reading, it should be available on compscicenter.ru
    co_open = CourseFactory.create(semester=current_term_nsk,
                                   city_id='nsk', is_open=True)
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 2
    assert set(response.context['ongoing_rest']) == {co_nsk, co_open}
    assert len(response.context['archive_enrolled']) == 0


@pytest.mark.django_db
def test_student_courses_list_csclub(client, settings, mocker):
    settings.SITE_ID = settings.CLUB_SITE_ID
    # Fix year and term
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    now_fixed = datetime.datetime(2016, month=3, day=8, tzinfo=pytz.utc)
    mocked_timezone.return_value = now_fixed
    now_year, now_season = get_current_term_pair(settings.DEFAULT_CITY_CODE)
    assert now_season == "spring"
    url = reverse('course_list_student')
    student = StudentClubFactory(city_id='spb')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
    # Make sure in tests we fallback to default city which is 'spb'
    assert response.context['request'].city_code == 'spb'
    # Show only open courses
    current_term = SemesterFactory.create_current(
        city_code=settings.DEFAULT_CITY_CODE)
    assert current_term.type == "spring"
    settings.SITE_ID = settings.CENTER_SITE_ID
    co = CourseFactory.create(semester__type=now_season,
                              semester__year=now_year, city_id='nsk',
                              is_open=False)
    settings.SITE_ID = settings.CLUB_SITE_ID
    # compsciclub.ru can't see center courses with default manager
    assert Course.objects.count() == 0
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['archive_enrolled']) == 0
    settings.SITE_ID = settings.CENTER_SITE_ID
    co.is_open = True
    co.save()
    settings.SITE_ID = settings.CLUB_SITE_ID
    assert Course.objects.count() == 1
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 0
    assert len(response.context['archive_enrolled']) == 0
    co.city_id = 'spb'
    co.save()
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 1
    assert set(response.context['ongoing_rest']) == {co}
    assert len(response.context['archive_enrolled']) == 0
    # Summer courses are hidden for compsciclub.ru
    summer_semester = SemesterFactory.create(year=now_year - 1, type='summer')
    co.semester = summer_semester
    co.save()
    settings.SITE_ID = settings.CENTER_SITE_ID
    co_active = CourseFactory.create(semester__type=now_season,
                                     semester__year=now_year,
                                     city_id='spb',
                                     is_open=True)
    settings.SITE_ID = settings.CLUB_SITE_ID
    response = client.get(url)
    assert len(response.context['ongoing_enrolled']) == 0
    assert len(response.context['ongoing_rest']) == 1
    assert set(response.context['ongoing_rest']) == {co_active}
    assert len(response.context['archive_enrolled']) == 0
    # But student can see them in list if they already enrolled
    EnrollmentFactory.create(student=student, course=co)
    response = client.get(url)
    assert len(response.context['ongoing_rest']) == 1
    assert len(response.context['archive_enrolled']) == 1
    assert set(response.context['archive_enrolled']) == {co}


@pytest.mark.django_db
def test_api_testimonials_smoke(client):
    GraduateFactory(csc_review='test', photo='stub.JPG')
    response = client.get(reverse("api:testimonials"))
    assert response.status_code == 200
