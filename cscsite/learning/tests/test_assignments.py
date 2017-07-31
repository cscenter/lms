import datetime

import pytest
from bs4 import BeautifulSoup

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_bytes
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from learning.factories import SemesterFactory, CourseOfferingFactory, \
    AssignmentFactory, EnrollmentFactory, AssignmentCommentFactory
from learning.models import StudentAssignment
from learning.settings import GRADES
from learning.tests.mixins import MyUtilitiesMixin
from learning.tests.test_views import GroupSecurityCheckMixin
from learning.utils import get_current_semester_pair
from users.factories import UserFactory, TeacherCenterFactory, StudentFactory, \
    StudentCenterFactory


class StudentAssignmentListTests(GroupSecurityCheckMixin,
                                 MyUtilitiesMixin, TestCase):
    url_name = 'assignment_list_student'
    groups_allowed = ['Student [CENTER]']

    def test_list(self):
        u = UserFactory.create(groups=['Student [CENTER]'])
        now_year, now_season = get_current_semester_pair()
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
        u = UserFactory.create(groups=['Student [CENTER]'])
        now_year, now_season = get_current_semester_pair()
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
class TestCompletedCourseOfferingBehaviour(object):
    def test_security_assignmentstudent_detail(self, client):
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
        url = reverse('a_s_detail_student', args=[a_s.pk])
        client.login(student)
        response = client.get(url)
        assert response.status_code == 403
        # Teacher still can view student assignment
        url = reverse('a_s_detail_teacher', args=[a_s.pk])
        client.login(teacher)
        response = client.get(url)
        assert response.status_code == 200

    def test_security_courseoffering_detail(self, client):
        """Student can't watch news from completed course which they failed"""
        teacher = TeacherCenterFactory()
        student = StudentFactory()
        past_year = datetime.datetime.now().year - 3
        past_semester = SemesterFactory.create(year=past_year)
        co = CourseOfferingFactory(teachers=[teacher], semester=past_semester)
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
    teacher = UserFactory.create(groups=['Teacher [CENTER]'])
    student = UserFactory.create(groups=['Student [CENTER]'])
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
    url = reverse('a_s_detail_teacher', args=[a_s.pk])
    client.login(teacher)
    assert smart_bytes(a.text) in client.get(url).content


@pytest.mark.django_db
def test_studentassignment_last_comment_from(client):
    """`last_comment_from` attribute is updated by signal"""
    teacher = TeacherCenterFactory.create()
    student = StudentCenterFactory.create()
    now_year, now_season = get_current_semester_pair()
    s = SemesterFactory.create(year=now_year, type=now_season)
    co = CourseOfferingFactory.create(semester=s, teachers=[teacher])
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
