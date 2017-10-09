import datetime

import pytest
import pytz
from bs4 import BeautifulSoup
from django.forms import model_to_dict

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, formats
from django.utils.encoding import smart_bytes
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from core.admin import get_admin_url
from learning.factories import SemesterFactory, CourseOfferingFactory, \
    AssignmentFactory, EnrollmentFactory, AssignmentCommentFactory, \
    StudentAssignmentFactory
from learning.models import StudentAssignment, Assignment, CourseOffering
from learning.settings import GRADES, PARTICIPANT_GROUPS
from learning.tests.mixins import MyUtilitiesMixin
from learning.tests.test_views import GroupSecurityCheckMixin
from learning.tests.utils import assert_login_redirect
from learning.utils import get_current_term_pair
from users.factories import UserFactory, TeacherCenterFactory, StudentFactory, \
    StudentCenterFactory


class StudentAssignmentListTests(GroupSecurityCheckMixin,
                                 MyUtilitiesMixin, TestCase):
    url_name = 'assignment_list_student'
    groups_allowed = [PARTICIPANT_GROUPS.STUDENT_CENTER]

    def test_list(self):
        u = StudentCenterFactory()
        now_year, now_season = get_current_term_pair('spb')
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(semester=s)
        as1 = AssignmentFactory.create_batch(2, course_offering=co)
        self.doLogin(u)
        # no assignments yet
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        self.assertEquals(0, len(resp.context['assignment_list_archive']))
        # enroll at course offering, assignments are shown
        EnrollmentFactory.create(student=u, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(2, len(resp.context['assignment_list_open']))
        self.assertEquals(0, len(resp.context['assignment_list_archive']))
        # add a few assignments, they should show up
        as2 = AssignmentFactory.create_batch(3, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        self.assertSameObjects([(StudentAssignment.objects
                                 .get(assignment=a, student=u))
                                for a in (as1 + as2)],
                               resp.context['assignment_list_open'])
        # Add few old assignments from current semester with expired deadline
        deadline_at = (datetime.datetime.now().replace(tzinfo=timezone.utc)
                       - datetime.timedelta(days=1))
        as_olds = AssignmentFactory.create_batch(2, course_offering=co,
                                             deadline_at=deadline_at)
        resp = self.client.get(reverse(self.url_name))
        for a in as1 + as2 + as_olds:
            self.assertContains(resp, a.title)
        for a in as_olds:
            self.assertContains(resp, a.title)
        self.assertSameObjects([(StudentAssignment.objects
                                 .get(assignment=a, student=u))
                                for a in (as1 + as2)],
                               resp.context['assignment_list_open'])
        self.assertSameObjects([(StudentAssignment.objects
                                 .get(assignment=a, student=u)) for a in as_olds],
                                resp.context['assignment_list_archive'])
        # Now add assignment from old semester
        old_s = SemesterFactory.create(year=now_year - 1, type=now_season)
        old_co = CourseOfferingFactory.create(semester=old_s)
        as_past = AssignmentFactory(course_offering=old_co)
        resp = self.client.get(reverse(self.url_name))
        self.assertNotIn(as_past, resp.context['assignment_list_archive'])

    def test_assignments_from_unenrolled_course_offering(self):
        """Move to archive active assignments from course offerings
        which student already leave
        """
        u = StudentCenterFactory()
        now_year, now_season = get_current_term_pair('spb')
        s = SemesterFactory.create(year=now_year, type=now_season)
        # Create open co to pass enrollment limit
        co = CourseOfferingFactory.create(semester=s, is_open=True)
        as1 = AssignmentFactory.create_batch(2, course_offering=co)
        self.doLogin(u)
        # enroll at course offering, assignments are shown
        EnrollmentFactory.create(student=u, course_offering=co)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(2, len(resp.context['assignment_list_open']))
        self.assertEquals(0, len(resp.context['assignment_list_archive']))
        # Now unenroll from the course
        form = {'course_offering_pk': co.pk}
        response = self.client.post(co.get_unenroll_url(), form)
        resp = self.client.get(reverse(self.url_name))
        self.assertEquals(0, len(resp.context['assignment_list_open']))
        self.assertEquals(2, len(resp.context['assignment_list_archive']))


@pytest.mark.django_db
def test_security_assignmentstudent_detail(client, settings):
    """
    Students can't see assignments from completed course, which they failed
    """
    teacher = TeacherCenterFactory()
    student = StudentCenterFactory()
    past_year = datetime.datetime.now().year - 3
    past_semester = SemesterFactory.create(year=past_year)
    co = CourseOfferingFactory(teachers=[teacher], semester=past_semester)
    enrollment = EnrollmentFactory(student=student, course_offering=co,
                                   grade=GRADES.unsatisfactory)
    a = AssignmentFactory(course_offering=co)
    a_s = StudentAssignment.objects.get(student=student, assignment=a)
    url = a_s.get_student_url()
    client.login(student)
    assert_login_redirect(client, settings, url)
    # Teacher still can view student assignment
    client.login(teacher)
    response = client.get(a_s.get_teacher_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_security_courseoffering_detail(client):
    """Student can't watch news from completed course which they failed"""
    teacher = TeacherCenterFactory()
    student = StudentFactory()
    past_year = datetime.datetime.now().year - 3
    co = CourseOfferingFactory(teachers=[teacher], semester__year=past_year)
    enrollment = EnrollmentFactory(student=student, course_offering=co,
                                   grade=GRADES.unsatisfactory)
    a = AssignmentFactory(course_offering=co)
    co.refresh_from_db()
    assert co.failed_by_student(student)
    client.login(student)
    url = co.get_absolute_url()
    response = client.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find(text=_("News")) is None
    # Change student co mark
    enrollment.grade = GRADES.excellent
    enrollment.save()
    response = client.get(url)
    assert not co.failed_by_student(student)
    # Change course offering state to not completed
    co.completed_at = now().date() + datetime.timedelta(days=1)
    co.save()
    response = client.get(url)
    assert not co.failed_by_student(student)


@pytest.mark.django_db
def test_assignment_contents(client):
    teacher = TeacherCenterFactory()
    student = StudentCenterFactory()
    # XXX: Unexpected Segfault when running pytest.
    # Move this test from ASTeacherDetailTests cls.
    # No idea why it's happening on login action
    # if assignment `notify_teachers` field not specified.
    # Problem can be related to pytest, django tests or factory-boy
    co = CourseOfferingFactory.create(teachers=[teacher])
    EnrollmentFactory.create(student=student, course_offering=co)
    a = AssignmentFactory.create(course_offering=co)
    a_s = (StudentAssignment.objects
           .filter(assignment=a, student=student)
           .get())
    client.login(teacher)
    assert smart_bytes(a.text) in client.get(a_s.get_teacher_url()).content


@pytest.mark.django_db
def test_studentassignment_last_comment_from():
    """`last_comment_from` attribute is updated by signal"""
    teacher = TeacherCenterFactory.create()
    student = StudentCenterFactory.create()
    now_year, now_season = get_current_term_pair('spb')
    s = SemesterFactory.create(year=now_year, type=now_season)
    co = CourseOfferingFactory.create(city_id='spb', semester=s,
                                      teachers=[teacher])
    EnrollmentFactory.create(student=student, course_offering=co)
    assignment = AssignmentFactory.create(course_offering=co)
    sa = StudentAssignment.objects.get(assignment=assignment)
    # Nobody comments yet
    assert sa.last_comment_from == StudentAssignment.LAST_COMMENT_NOBODY
    AssignmentCommentFactory.create(student_assignment=sa, author=student)
    sa.refresh_from_db()
    assert sa.last_comment_from == StudentAssignment.LAST_COMMENT_STUDENT
    AssignmentCommentFactory.create(student_assignment=sa, author=teacher)
    sa.refresh_from_db()
    assert sa.last_comment_from == StudentAssignment.LAST_COMMENT_TEACHER


@pytest.mark.django_db
def test_studentassignment_first_submission_at(curator):
    """`first_submission_at` attribute is updated by signal"""
    teacher = TeacherCenterFactory.create()
    student = StudentCenterFactory.create()
    co = CourseOfferingFactory.create(teachers=[teacher])
    EnrollmentFactory.create(student=student, course_offering=co)
    assignment = AssignmentFactory.create(course_offering=co)
    sa = StudentAssignment.objects.get(assignment=assignment)
    assert sa.first_submission_at is None
    AssignmentCommentFactory.create(student_assignment=sa, author=teacher)
    sa.refresh_from_db()
    assert sa.first_submission_at is None
    AssignmentCommentFactory.create(student_assignment=sa, author=curator)
    sa.refresh_from_db()
    assert sa.first_submission_at is None
    AssignmentCommentFactory.create(student_assignment=sa, author=student)
    sa.refresh_from_db()
    assert sa.first_submission_at is not None
    first_submission_at = sa.first_submission_at
    # Make sure it doesn't changed
    AssignmentCommentFactory.create(student_assignment=sa, author=teacher)
    sa.refresh_from_db()
    assert sa.first_submission_at == first_submission_at
    # Second comment from student shouldn't change time
    AssignmentCommentFactory.create(student_assignment=sa, author=student)
    sa.refresh_from_db()
    assert sa.first_submission_at == first_submission_at


class AssignmentCRUDTests(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = TeacherCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = AssignmentFactory.attributes(create=True)
        form.update({'course_offering': co.pk,
                     'attached_file': None})
        url = co.get_create_assignment_url()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()
        a = AssignmentFactory.create()
        url = a.get_update_url()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()
        url = a.get_delete_url()
        self.assertLoginRedirect(url)
        self.assertPOSTLoginRedirect(url, form)
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            self.assertLoginRedirect(url)
            self.assertPOSTLoginRedirect(url, form)
            self.doLogout()

    def test_create(self):
        teacher = TeacherCenterFactory()
        CourseOfferingFactory.create_batch(3, teachers=[teacher])
        co = CourseOfferingFactory.create(teachers=[teacher])
        form = AssignmentFactory.attributes(create=True)
        deadline_date = form['deadline_at'].strftime("%d.%m.%Y")
        deadline_time = form['deadline_at'].strftime("%H:%M")
        form.update({'course_offering': co.pk,
                     'attached_file': None,
                     'deadline_at_0': deadline_date,
                     'deadline_at_1': deadline_time})
        url = co.get_create_assignment_url()
        self.doLogin(teacher)
        self.client.post(url, form)
        assert Assignment.objects.count() == 1

    def test_update(self):
        teacher = TeacherCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        for student in students:
            EnrollmentFactory.create(student=student,
                                     course_offering=co)
        a = AssignmentFactory.create(course_offering=co)
        form = model_to_dict(a)
        deadline_date = form['deadline_at'].strftime("%d.%m.%Y")
        deadline_time = form['deadline_at'].strftime("%H:%M")
        form.update({'title': a.title + " foo42bar",
                     'course_offering': co.pk,
                     'attached_file': None,
                     'deadline_at_0': deadline_date,
                     'deadline_at_1': deadline_time})
        url = a.get_update_url()
        list_url = reverse('assignment_list_teacher')
        self.doLogin(teacher)
        self.assertNotContains(self.client.get(list_url), form['title'])
        self.assertRedirects(self.client.post(url, form),
                             reverse("assignment_detail_teacher", args=[a.pk]))
        # Show student assignments without comments
        self.assertContains(self.client.get( list_url + "?status=all"), form['title'])

    def test_delete(self):
        teacher = TeacherCenterFactory()
        co = CourseOfferingFactory.create(teachers=[teacher])
        a = AssignmentFactory.create(course_offering=co)
        url = a.get_delete_url()
        list_url = reverse('assignment_list_teacher')
        self.doLogin(teacher)
        self.assertContains(self.client.get(list_url), a.title)
        self.assertContains(self.client.get(url), a.title)
        self.assertRedirects(self.client.post(url), list_url)
        self.assertNotContains(self.client.get(list_url), a.title)


class AssignmentTeacherDetailsTest(MyUtilitiesMixin, TestCase):
    def test_security(self):
        teacher = TeacherCenterFactory()
        a = AssignmentFactory.create(course_offering__teachers=[teacher])
        url = reverse('assignment_detail_teacher', args=[a.pk])
        self.assertLoginRedirect(url)
        test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == [PARTICIPANT_GROUPS.TEACHER_CENTER]:
                self.assertEquals(403, self.client.get(url).status_code)
            else:
                self.assertLoginRedirect(url)
            self.doLogout()
        self.doLogin(teacher)
        self.assertEquals(200, self.client.get(url).status_code)

    def test_details(self):
        teacher = TeacherCenterFactory()
        student = StudentCenterFactory()
        now_year, now_season = get_current_term_pair('spb')
        s = SemesterFactory.create(year=now_year, type=now_season)
        co = CourseOfferingFactory.create(city='spb', semester=s,
                                          teachers=[teacher])
        a = AssignmentFactory.create(course_offering=co)
        self.doLogin(teacher)
        url = reverse('assignment_detail_teacher', args=[a.pk])
        resp = self.client.get(url)
        self.assertEquals(a, resp.context['assignment'])
        self.assertEquals(0, len(resp.context['a_s_list']))
        EnrollmentFactory.create(student=student, course_offering=co)
        a_s = StudentAssignment.objects.get(student=student, assignment=a)
        resp = self.client.get(url)
        self.assertEquals(a, resp.context['assignment'])
        self.assertSameObjects([a_s], resp.context['a_s_list'])


class AssignmentTeacherListTests(MyUtilitiesMixin, TestCase):
    url_name = 'assignment_list_teacher'
    groups_allowed = [PARTICIPANT_GROUPS.TEACHER_CENTER]

    def test_group_security(self):
        """Custom logic instead of GroupSecurityCheckMixin.
        Teacher can get 302 if no CO yet"""
        self.assertLoginRedirect(reverse(self.url_name))
        all_test_groups = [
            [],
            [PARTICIPANT_GROUPS.TEACHER_CENTER],
            [PARTICIPANT_GROUPS.STUDENT_CENTER],
            [PARTICIPANT_GROUPS.GRADUATE_CENTER]
        ]
        for groups in all_test_groups:
            user = UserFactory.create(groups=groups)
            self.doLogin(user)
            if any(group in self.groups_allowed for group in groups):
                co = CourseOfferingFactory.create(teachers=[user])
                # Create co for teacher to prevent 404 error
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertLoginRedirect(reverse(self.url_name))
            self.client.logout()
        self.doLogin(UserFactory.create(is_superuser=True, is_staff=True))
        self.assertStatusCode(302, self.url_name)

    def test_list(self):
        # Default filter for grade - `no_grade`
        TEACHER_ASSIGNMENTS_PAGE = reverse(self.url_name)
        teacher = TeacherCenterFactory()
        students = UserFactory.create_batch(3, groups=['Student [CENTER]'])
        now_year, now_season = get_current_term_pair('spb')
        s = SemesterFactory.create(year=now_year, type=now_season)
        # some other teacher's course offering
        co_other = CourseOfferingFactory.create(city='spb', semester=s)
        AssignmentFactory.create_batch(2, course_offering=co_other)
        self.doLogin(teacher)
        # no course offerings yet, return 302
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE)
        self.assertEquals(302, resp.status_code)
        # Create co, assignments and enroll students
        co = CourseOfferingFactory.create(city='spb', semester=s,
                                          teachers=[teacher])
        for student1 in students:
            EnrollmentFactory.create(student=student1, course_offering=co)
        assignment = AssignmentFactory.create(course_offering=co)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE)
        # TODO: add wrong term type and check redirect.
        # By default we show all submissions without grades
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        # Show submissions without comments
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        # TODO: add test which assignment selected by default.
        sas = ((StudentAssignment.objects.get(student=student,
                                              assignment=assignment))
               for student in students)
        self.assertSameObjects(sas, resp.context['student_assignment_list'])
        # Let's check assignments with last comment from student only
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        # Teacher commented on student1 assignment
        student1, student2, student3 = students
        sa1 = StudentAssignment.objects.get(student=student1,
                                            assignment=assignment)
        sa2 = StudentAssignment.objects.get(student=student2,
                                            assignment=assignment)
        AssignmentCommentFactory.create(student_assignment=sa1, author=teacher)
        assert sa1.last_comment_from == sa1.LAST_COMMENT_TEACHER
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(reverse(self.url_name) + "?comment=teacher")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(2, len(resp.context['student_assignment_list']))
        # Student2 commented on assignment
        AssignmentCommentFactory.create_batch(2, student_assignment=sa2,
                                              author=student2)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        self.assertSameObjects([sa2], resp.context['student_assignment_list'])
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        # Teacher answered on the student2 assignment
        AssignmentCommentFactory.create(student_assignment=sa2, author=teacher)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEquals(2, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        # Student 3 add comment on assignment
        sa3 = StudentAssignment.objects.get(student=student3,
                                            assignment=assignment)
        AssignmentCommentFactory.create_batch(3, student_assignment=sa3,
                                              author=student3)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEquals(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEquals(2, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        # teacher has set a grade
        sa3.grade = 3
        sa3.save()
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&grades=no")
        self.assertEquals(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&grades=all")
        self.assertEquals(1, len(resp.context['student_assignment_list']))
        sa3.refresh_from_db()
        sa1.grade = 3
        sa1.save()
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&grades=yes")
        self.assertEquals(1, len(resp.context['student_assignment_list']))


@pytest.mark.django_db
def test_assignment_admin_view(settings, admin_client):
    # Datetime widget formatting depends on locale, change it
    settings.LANGUAGE_CODE = 'ru'
    co_in_spb = CourseOfferingFactory(city_id='spb')
    co_in_nsk = CourseOfferingFactory(city_id='nsk')
    form_data = {
        "course_offering": "",
        "deadline_at_0": "29.06.2017",
        "deadline_at_1": "00:00:00",
        "title": "title",
        "text": "text",
        "grade_min": "3",
        "grade_max": "5",
        "_continue": "save_and_continue"
    }
    # Test with empty city aware field
    add_url = reverse('admin:learning_assignment_add')
    response = admin_client.post(add_url, form_data)
    assert response.status_code == 200
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    # Send valid data
    form_data["course_offering"] = co_in_spb.pk
    response = admin_client.post(add_url, form_data, follow=True)
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
    response = admin_client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    date_input = widget.find('input', {"name": 'deadline_at_0'})
    assert date_input.get('value') == '29.06.2017'
    # We can't update course offering through admin interface
    response = admin_client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    assert assignment.course_offering_id == co_in_spb.pk
    # But do it manually to test widget
    assignment.course_offering = co_in_nsk
    assignment.save()
    form_data["deadline_at_1"] = "00:00:00"
    response = admin_client.post(change_url, form_data)
    assignment.refresh_from_db()
    response = admin_client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    assert assignment.deadline_at.hour == 17  # UTC +7 in nsk
    assert assignment.deadline_at.minute == 0
    # Update course_offering and deadline time
    assignment.course_offering = co_in_spb
    assignment.save()
    form_data["deadline_at_1"] = "06:00:00"
    response = admin_client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    response = admin_client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '06:00:00'
    assert assignment.deadline_at.hour == 3
    assert assignment.deadline_at.minute == 0
    # Update course offering and deadline, but choose values when
    # UTC time shouldn't change
    assignment.course_offering = co_in_nsk
    assignment.save()
    form_data["deadline_at_1"] = "10:00:00"
    response = admin_client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    response = admin_client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '10:00:00'
    assert assignment.deadline_at.hour == 3
    assert assignment.deadline_at.minute == 0
    assert assignment.course_offering_id == co_in_nsk.pk


@pytest.mark.django_db
def test_assignment_public_form_for_teachers(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    teacher = TeacherCenterFactory()
    co_in_spb = CourseOfferingFactory(city='spb', teachers=[teacher])
    client.login(teacher)
    form_data = {
        "title": "title",
        "text": "text",
        "deadline_at_0": "29.06.2017",
        "deadline_at_1": "00:00",
        "grade_min": "3",
        "grade_max": "5",
    }
    add_url = co_in_spb.get_create_assignment_url()
    response = client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    assert Assignment.objects.count() == 1
    assignment = Assignment.objects.first()
    # In DB we store datetime values in UTC
    assert assignment.deadline_at.day == 28
    assert assignment.deadline_at.hour == 21
    assert assignment.deadline_at.minute == 0
    assert assignment.course_offering_id == co_in_spb.pk
    tz_diff = datetime.timedelta(hours=3)  # UTC+3 for msk timezone
    assert assignment.deadline_at_local().utcoffset() == tz_diff
    # Check widget shows local time
    response = client.get(assignment.get_update_url())
    widget_html = response.context['form']['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00'
    # Clone CO from msk
    co_in_nsk = CourseOfferingFactory(city='nsk', course=co_in_spb.course,
                                      teachers=[teacher])
    add_url = co_in_nsk.get_create_assignment_url()
    response = client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    assert Assignment.objects.count() == 2
    assignment_last = Assignment.objects.order_by("pk").last()
    assert assignment_last.course_offering_id == co_in_nsk.pk
    tz_diff = datetime.timedelta(hours=7)  # UTC+7 for nsk timezone
    assert assignment_last.deadline_at_local().utcoffset() == tz_diff
    assert assignment_last.deadline_at.hour == 17


@pytest.mark.django_db
def test_assignment_deadline_display_for_teacher(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    teacher = TeacherCenterFactory()
    assignment = AssignmentFactory(deadline_at=dt,
                                   course_offering__city_id='spb',
                                   course_offering__teachers=[teacher])
    url_for_teacher = reverse("assignment_detail_teacher",
                              kwargs={"pk": assignment.pk})
    client.login(teacher)
    response = client.get(url_for_teacher)
    html = BeautifulSoup(response.content, "html.parser")
    # Note: On this page used `naturalday` filter, so use passed datetime
    deadline_str = formats.date_format(assignment.deadline_at_local(),
                                       'd E Y H:i')
    assert deadline_str == "01 января 2017 18:00"
    assert any(deadline_str in s.string for s in html.find_all('p'))
    # Test student submission page
    sa = StudentAssignmentFactory(assignment=assignment)
    response = client.get(sa.get_teacher_url())
    html = BeautifulSoup(response.content, "html.parser")
    # Note: On this page used `naturalday` filter, so use passed datetime
    deadline_str = formats.date_format(assignment.deadline_at_local(),
                                       'd E Y H:i')
    assert deadline_str == "01 января 2017 18:00"
    assert any(deadline_str in s.string for s in
               html.find_all('span', {"class": "nowrap"}))


@pytest.mark.django_db
def test_assignment_deadline_l10n_on_course_offering_detail(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    teacher = TeacherCenterFactory()
    assignment = AssignmentFactory(deadline_at=dt,
                                   course_offering__city_id='spb',
                                   course_offering__teachers=[teacher])
    co = assignment.course_offering
    client.login(teacher)
    response = client.get(co.get_url_for_tab('assignments'))
    html = BeautifulSoup(response.content, "html.parser")
    deadline_date_str = formats.date_format(assignment.deadline_at_local(), 'd E')
    assert deadline_date_str == "01 января"
    assert any(deadline_date_str in s.text for s in
               html.find_all('div', {"class": "assignment-deadline"}))
    deadline_time_str = formats.date_format(assignment.deadline_at_local(), 'H:i')
    assert deadline_time_str == "18:00"
    assert any(deadline_time_str in s.string for s in
               html.find_all('span', {"class": "text-muted"}))


@pytest.mark.django_db
def test_deadline_l10n_on_student_assignments_page(settings, client):
    settings.LANGUAGE_CODE = 'ru'  # formatting depends on locale
    format_date_part = 'd E Y'
    format_time_part = 'H:i'
    # This day will be in archive block
    dt = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    current_term = SemesterFactory.create_current()
    assignment = AssignmentFactory(deadline_at=dt,
                                   course_offering__city_id='spb',
                                   course_offering__semester_id=current_term.pk)
    sa = StudentAssignmentFactory(assignment=assignment)
    url = reverse('assignment_list_student')
    student = sa.student
    client.login(student)
    response = client.get(url)
    html = BeautifulSoup(response.content, "html.parser")
    # Note: On this page used `naturalday` filter, so use passed datetime
    year_part = formats.date_format(assignment.deadline_at_local(),
                                    format_date_part)
    assert year_part == "01 января 2017"
    time_part = formats.date_format(assignment.deadline_at_local(),
                                    format_time_part)
    assert time_part == "18:00"
    assert any(year_part in s.text and time_part in s.text for s in
               html.find_all('div', {'class': 'assignment-date'}))
    # Test `upcoming` block
    now_year, _ = get_current_term_pair('spb')
    dt = dt.replace(year=now_year + 1, month=2, hour=14)
    assignment.deadline_at = dt
    assignment.save()
    year_part = formats.date_format(assignment.deadline_at_local(),
                                    format_date_part)
    assert year_part == "01 февраля {}".format(now_year + 1)
    time_part = formats.date_format(assignment.deadline_at_local(),
                                    format_time_part)
    assert time_part == "17:00"
    response = client.get(url)
    html = BeautifulSoup(response.content, "html.parser")
    assert any(year_part in s.text and time_part in s.text for s in
               html.find_all('div', {'class': 'assignment-date'}))

# TODO: assignment submission page - comments localisation, assignment created localization
# TODO: Преподавание -> Задания, добавить тест для deadline_local


@pytest.mark.django_db
def test_first_comment_after_deadline(client):
    dt = datetime.datetime(2017, 1, 1, 23, 58, 0, 0, tzinfo=pytz.UTC)
    assignment = AssignmentFactory(deadline_at=dt,
                                   course_offering__city_id='spb')
    sa = StudentAssignmentFactory(assignment=assignment)
    student = sa.student
    comment = AssignmentCommentFactory.create(student_assignment=sa,
                                              author=student,
                                              created=dt)
    client.login(student)
    response = client.get(sa.get_student_url())
    assert response.status_code == 200
    # Consider last min in favor of student
    assert response.context['first_comment_after_deadline'] is None
    assert smart_bytes('<hr class="deadline">') not in response.content
    comment.created = dt + datetime.timedelta(minutes=1)
    comment.save()
    response = client.get(sa.get_student_url())
    assert response.context['first_comment_after_deadline'] == comment
    assert smart_bytes('<hr class="deadline">') in response.content
