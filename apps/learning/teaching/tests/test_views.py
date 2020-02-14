import pytest
from django.utils.encoding import smart_bytes

from core.tests.utils import CSCTestCase
from core.urls import reverse
from courses.tests.factories import CourseFactory, SemesterFactory, \
    AssignmentFactory
from learning.models import StudentAssignment
from learning.settings import Branches
from learning.tests.factories import EnrollmentFactory, AssignmentCommentFactory
from learning.tests.mixins import MyUtilitiesMixin
from users.constants import Roles
from users.tests.factories import UserFactory, CuratorFactory, TeacherFactory, \
    StudentFactory


@pytest.mark.django_db
def test_teaching_index_page_smoke(client):
    """Just to make sure this view doesn't return 50x error"""
    response = client.get(reverse("teaching:base"))
    assert response.status_code == 302


class AssignmentTeacherListTests(MyUtilitiesMixin, CSCTestCase):
    url_name = 'teaching:assignment_list'
    groups_allowed = [Roles.TEACHER]

    def test_group_security(self):
        """Custom logic instead of GroupSecurityCheckMixin.
        Teacher can get 302 if no CO yet"""
        self.assertLoginRedirect(reverse(self.url_name))
        all_test_groups = [
            [],
            [Roles.TEACHER],
            [Roles.STUDENT],
            [Roles.GRADUATE]
        ]
        for groups in all_test_groups:
            user = UserFactory.create(groups=groups)
            self.doLogin(user)
            if any(group in self.groups_allowed for group in groups):
                co = CourseFactory.create(teachers=[user])
                # Create co for teacher to prevent 404 error
                self.assertStatusCode(200, self.url_name)
            else:
                self.assertLoginRedirect(reverse(self.url_name))
            self.client.logout()
        self.doLogin(CuratorFactory())
        self.assertStatusCode(302, self.url_name)

    def test_list(self):
        # Default filter for grade - `no_grade`
        TEACHER_ASSIGNMENTS_PAGE = reverse(self.url_name)
        teacher = TeacherFactory()
        students = StudentFactory.create_batch(3)
        s = SemesterFactory.create_current(for_branch=Branches.SPB)
        # some other teacher's course offering
        co_other = CourseFactory.create(semester=s)
        AssignmentFactory.create_batch(2, course=co_other)
        self.doLogin(teacher)
        # no course offerings yet, return 302
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE)
        self.assertEqual(302, resp.status_code)
        # Create co, assignments and enroll students
        co = CourseFactory.create(semester=s, teachers=[teacher])
        for student1 in students:
            EnrollmentFactory.create(student=student1, course=co)
        assignment = AssignmentFactory.create(course=co)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE)
        # TODO: add wrong term type and check redirect.
        # By default we show all submissions without grades
        self.assertEqual(3, len(resp.context['student_assignment_list']))
        # Show submissions without comments
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEqual(3, len(resp.context['student_assignment_list']))
        # TODO: add test which assignment selected by default.
        sas = ((StudentAssignment.objects.get(student=student,
                                              assignment=assignment))
               for student in students)
        self.assertSameObjects(sas, resp.context['student_assignment_list'])
        # Let's check assignments with last comment from student only
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEqual(0, len(resp.context['student_assignment_list']))
        # Teacher commented on student1 assignment
        student1, student2, student3 = students
        sa1: StudentAssignment = StudentAssignment.objects.get(
            student=student1, assignment=assignment)
        sa2 = StudentAssignment.objects.get(student=student2,
                                            assignment=assignment)
        AssignmentCommentFactory.create(student_assignment=sa1, author=teacher)
        assert sa1.last_comment_from == sa1.CommentAuthorTypes.TEACHER
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEqual(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEqual(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(reverse(self.url_name) + "?comment=teacher")
        self.assertEqual(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEqual(2, len(resp.context['student_assignment_list']))
        # Student2 commented on assignment
        AssignmentCommentFactory.create_batch(2, student_assignment=sa2,
                                              author=student2)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEqual(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEqual(1, len(resp.context['student_assignment_list']))
        self.assertSameObjects([sa2], resp.context['student_assignment_list'])
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEqual(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEqual(1, len(resp.context['student_assignment_list']))
        # Teacher answered on the student2 assignment
        AssignmentCommentFactory.create(student_assignment=sa2, author=teacher)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEqual(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEqual(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEqual(2, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEqual(1, len(resp.context['student_assignment_list']))
        # Student 3 add comment on assignment
        sa3 = StudentAssignment.objects.get(student=student3,
                                            assignment=assignment)
        AssignmentCommentFactory.create_batch(3, student_assignment=sa3,
                                              author=student3)
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=any")
        self.assertEqual(3, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=student")
        self.assertEqual(1, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=teacher")
        self.assertEqual(2, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE + "?comment=empty")
        self.assertEqual(0, len(resp.context['student_assignment_list']))
        # teacher has set a grade
        sa3.score = 3
        sa3.save()
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&score=no")
        self.assertEqual(0, len(resp.context['student_assignment_list']))
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&score=any")
        self.assertEqual(1, len(resp.context['student_assignment_list']))
        sa3.refresh_from_db()
        sa1.score = 3
        sa1.save()
        resp = self.client.get(TEACHER_ASSIGNMENTS_PAGE +
                               "?comment=student&score=yes")
        self.assertEqual(1, len(resp.context['student_assignment_list']))


class AssignmentTeacherDetailsTest(MyUtilitiesMixin, CSCTestCase):
    def test_security(self):
        teacher = TeacherFactory()
        a = AssignmentFactory.create(course__teachers=[teacher])
        url = a.get_teacher_url()
        self.assertLoginRedirect(url)
        test_groups = [
            [],
            [Roles.TEACHER],
            [Roles.STUDENT],
        ]
        for groups in test_groups:
            self.doLogin(UserFactory.create(groups=groups))
            if groups == [Roles.TEACHER]:
                self.assertEqual(403, self.client.get(url).status_code)
            else:
                self.assertLoginRedirect(url)
            self.doLogout()
        self.doLogin(teacher)
        self.assertEqual(200, self.client.get(url).status_code)

    def test_details(self):
        teacher = TeacherFactory()
        student = StudentFactory()
        s = SemesterFactory.create_current(for_branch=Branches.SPB)
        co = CourseFactory.create(semester=s, teachers=[teacher])
        a = AssignmentFactory.create(course=co)
        self.doLogin(teacher)
        url = a.get_teacher_url()
        resp = self.client.get(url)
        self.assertEqual(a, resp.context['assignment'])
        self.assertEqual(0, len(resp.context['a_s_list']))
        EnrollmentFactory.create(student=student, course=co)
        a_s = StudentAssignment.objects.get(student=student, assignment=a)
        resp = self.client.get(url)
        self.assertEqual(a, resp.context['assignment'])
        self.assertSameObjects([a_s], resp.context['a_s_list'])


@pytest.mark.django_db
def test_assignment_contents(client):
    teacher = TeacherFactory()
    student = StudentFactory()
    co = CourseFactory.create(teachers=[teacher])
    EnrollmentFactory.create(student=student, course=co)
    a = AssignmentFactory.create(course=co)
    a_s = (StudentAssignment.objects
           .get(assignment=a, student=student))
    client.login(teacher)
    assert smart_bytes(a.text) in client.get(a_s.get_teacher_url()).content
