from datetime import timedelta

import pytest
from bs4 import BeautifulSoup

from django.contrib.messages import get_messages
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from core.tests.factories import BranchFactory
from core.urls import reverse
from courses.constants import AssigneeMode, AssignmentFormat, AssignmentStatus
from courses.models import CourseTeacher
from courses.tests.factories import (
    AssignmentFactory, CourseFactory, CourseTeacherFactory, SemesterFactory
)
from courses.utils import get_current_term_pair
from grading.constants import CheckingSystemTypes, YandexCompilers
from grading.tests.factories import CheckerFactory
from learning.forms import AssignmentSolutionYandexContestForm
from learning.models import (
    AssignmentComment, AssignmentNotification, AssignmentSubmissionTypes,
    StudentAssignment
)
from learning.permissions import ViewCourses, ViewOwnStudentAssignment
from learning.settings import Branches
from learning.tests.factories import (
    AssignmentCommentFactory, EnrollmentFactory, StudentAssignmentFactory
)
from users.tests.factories import (
    StudentFactory, StudentProfileFactory, TeacherFactory, UserFactory
)

# TODO: test ViewOwnAssignment in test_permissions.py


@pytest.mark.django_db
def test_view_student_assignment_detail_permissions(client, lms_resolver,
                                                    assert_login_redirect):
    from auth.permissions import perm_registry
    teacher = TeacherFactory()
    student = StudentFactory()
    course = CourseFactory(teachers=[teacher],
                           semester=SemesterFactory.create_current())
    AssignmentFactory(course=course)
    EnrollmentFactory(student=student, course=course)
    student_assignment = StudentAssignment.objects.get(student=student)
    url = student_assignment.get_student_url()
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewOwnStudentAssignment.name
    assert resolver.func.view_class.permission_required in perm_registry
    assert_login_redirect(url, method='get')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_view_student_assignment_detail_handle_no_permission(client):
    teacher = TeacherFactory()
    client.login(teacher)
    course = CourseFactory(teachers=[teacher])
    student_assignment = StudentAssignmentFactory(assignment__course=course)
    url = student_assignment.get_student_url()
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == student_assignment.get_teacher_url()


@pytest.mark.django_db
def test_view_personal_assignment_contents(client):
    student_profile = StudentProfileFactory()
    student = student_profile.user
    semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student_profile.branch, semester=semester)
    EnrollmentFactory(student_profile=student_profile,
                      student=student,
                      course=course)
    assignment = AssignmentFactory(course=course)
    student_assignment = (StudentAssignment.objects
                          .filter(assignment=assignment, student=student)
                          .get())
    url = student_assignment.get_student_url()
    client.login(student)
    response = client.get(url)
    assert smart_bytes(assignment.text) in response.content


@pytest.mark.django_db
def test_view_student_assignment_detail_comment(client):
    student_profile = StudentProfileFactory()
    student = student_profile.user
    semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student_profile.branch, semester=semester)
    EnrollmentFactory(student_profile=student_profile,
                      student=student,
                      course=course)
    assignment = AssignmentFactory(course=course)
    student_assignment = (StudentAssignment.objects
                          .get(assignment=assignment, student=student))
    student_url = student_assignment.get_student_url()
    create_comment_url = reverse("study:assignment_comment_create",
                                 kwargs={"pk": student_assignment.pk})
    form_data = {
        'comment-text': "Test comment without file"
    }
    client.login(student)
    response = client.post(create_comment_url, form_data)
    assert response.status_code == 302
    assert response.url == student_url
    response = client.get(student_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
    form_data = {
        'comment-text': "Test comment with file",
        'comment-attached_file': f
    }
    response = client.post(create_comment_url, form_data)
    assert response.status_code == 302
    assert response.url == student_url
    response = client.get(student_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    assert smart_bytes('attachment1') in response.content


@pytest.mark.django_db
def test_view_new_comment_on_assignment_page(client, assert_redirect):
    semester = SemesterFactory.create_current()
    student_profile = StudentProfileFactory()
    course = CourseFactory(main_branch=student_profile.branch, semester=semester)
    course_teacher1, course_teacher2 = CourseTeacherFactory.create_batch(2, course=course,
                                                        roles=CourseTeacher.roles.reviewer)
    EnrollmentFactory(student_profile=student_profile,
                      student=student_profile.user,
                      course=course)
    assignment = AssignmentFactory(course=course, assignee_mode=AssigneeMode.MANUAL,
                                   assignees=[course_teacher1, course_teacher2])
    personal_assignment = (StudentAssignment.objects
                           .filter(assignment=assignment, student=student_profile.user)
                           .get())
    client.login(student_profile.user)
    detail_url = personal_assignment.get_student_url()
    create_comment_url = reverse("study:assignment_comment_create",
                                 kwargs={"pk": personal_assignment.pk})
    recipients_count = 2
    assert AssignmentNotification.objects.count() == 1
    n = AssignmentNotification.objects.first()
    assert n.is_about_creation
    # Publish new comment
    AssignmentNotification.objects.all().delete()
    form_data = {
        'comment-text': "Test comment with file",
        'comment-attached_file': SimpleUploadedFile("attachment1.txt", b"attachment1_content")
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, detail_url)
    response = client.get(detail_url)
    assert smart_bytes(form_data['comment-text']) in response.content
    assert smart_bytes('attachment1') in response.content
    assert AssignmentNotification.objects.count() == recipients_count
    # Create new draft comment
    assert AssignmentComment.objects.count() == 1
    AssignmentNotification.objects.all().delete()
    form_data = {
        'comment-text': "Test comment 2 with file",
        'comment-attached_file': SimpleUploadedFile("a.txt", b"a_content"),
        'save-draft': 'Submit button text'
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, detail_url)
    assert AssignmentComment.objects.count() == 2
    assert AssignmentNotification.objects.count() == 0
    response = client.get(detail_url)
    assert 'comment_form' in response.context_data
    form = response.context_data['comment_form']
    assert form_data['comment-text'] == form.instance.text
    rendered_form = BeautifulSoup(str(form), "html.parser")
    file_name = rendered_form.find('span', class_='fileinput-filename')
    assert file_name and file_name.string == form.instance.attached_file_name
    # Publish another comment. This one should override draft comment.
    # But first create draft comment from another teacher and make sure
    # it won't be published on publishing new comment from the first teacher
    teacher2_draft = AssignmentCommentFactory(author=course_teacher2.teacher,
                                              student_assignment=personal_assignment,
                                              is_published=False)
    assert AssignmentComment.published.count() == 1
    draft = AssignmentComment.objects.get(text=form_data['comment-text'])
    form_data = {
        'comment-text': "Updated test comment 2 with file",
        'comment-attached_file': SimpleUploadedFile("test_file_b.txt", b"b_content"),
    }
    response = client.post(create_comment_url, form_data)
    assert_redirect(response, detail_url)
    assert AssignmentComment.published.count() == 2
    assert AssignmentNotification.objects.count() == recipients_count
    draft.refresh_from_db()
    assert draft.is_published
    assert draft.attached_file_name.startswith('test_file_b')
    teacher2_draft.refresh_from_db()
    assert not teacher2_draft.is_published


@pytest.mark.django_db
def test_view_solution_form_is_visible_by_default(client):
    student_profile = StudentProfileFactory()
    student = student_profile.user
    course = CourseFactory(main_branch=student_profile.branch,
                           semester=SemesterFactory.create_current(),
                           ask_ttc=False)
    EnrollmentFactory(student_profile=student_profile,
                      student=student,
                      course=course)
    assignment = AssignmentFactory(course=course)
    student_assignment = (StudentAssignment.objects
                          .get(assignment=assignment, student=student))
    student_url = student_assignment.get_student_url()
    client.login(student)
    response = client.get(student_url)
    rendered = BeautifulSoup(response.content, "html.parser")
    button_solution_find = rendered.find(id="add-solution")
    button_comment_find = rendered.find(id="add-comment")
    form_solution_find = rendered.find(id="solution-form-wrapper")
    form_comment_find = rendered.find(id="comment-form-wrapper")
    assert 'active' in button_solution_find.attrs['class']
    assert 'active' not in button_comment_find.attrs['class']
    assert 'hidden' not in form_solution_find.attrs['class']
    assert 'hidden' in form_comment_find.attrs['class']


@pytest.mark.django_db
def test_view_student_assignment_add_solution(client):
    student_profile = StudentProfileFactory()
    student = student_profile.user
    semester = SemesterFactory.create_current()
    course = CourseFactory(main_branch=student_profile.branch,
                           semester=semester, ask_ttc=False)
    EnrollmentFactory(student_profile=student_profile,
                      student=student,
                      course=course)
    assignment = AssignmentFactory(course=course)
    student_assignment = (StudentAssignment.objects
                          .get(assignment=assignment, student=student))
    student_url = student_assignment.get_student_url()
    create_solution_url = reverse("study:assignment_solution_create",
                                  kwargs={"pk": student_assignment.pk})
    form_data = {
        'solution-text': "Test comment without file"
    }
    client.login(student)
    response = client.post(create_solution_url, form_data)
    assert response.status_code == 302
    assert response.url == student_url
    response = client.get(student_url)
    assert smart_bytes(form_data['solution-text']) in response.content
    f = SimpleUploadedFile("attachment1.txt", b"attachment1_content")
    form_data = {
        'solution-text': "Test solution with file",
        'solution-attached_file': f
    }
    response = client.post(create_solution_url, form_data)
    assert response.status_code == 302
    assert response.url == student_url
    response = client.get(student_url)
    assert smart_bytes(form_data['solution-text']) in response.content
    assert smart_bytes('attachment1') in response.content
    # Make execution field mandatory
    form_data = {
        'solution-text': 'Test solution',
    }
    course.ask_ttc = True
    course.save()
    response = client.post(create_solution_url, form_data)
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert 'error' in messages[0].tags
    client.get('/', follow=True)  # Flush messages with middleware
    form_data = {
        'solution-text': 'Test solution',
        'solution-execution_time': '1:12',
    }
    response = client.post(create_solution_url, form_data)
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert 'success' in messages[0].tags
    student_assignment.refresh_from_db()
    assert student_assignment.execution_time == timedelta(hours=1, minutes=12)
    # Add another solution
    form_data = {
        'solution-text': 'Fixes on test solution',
        'solution-execution_time': '0:34',
    }
    response = client.post(create_solution_url, form_data)
    student_assignment.refresh_from_db()
    assert student_assignment.execution_time == timedelta(hours=1, minutes=46)


@pytest.mark.django_db
def test_view_student_assignment_add_solution_review_code_type(client, mocker):
    mocker.patch('grading.tasks.update_checker_yandex_contest_problem_compilers')
    mocker.patch('grading.tasks.add_new_submission_to_checking_system')
    student = UserFactory()
    student_profile = StudentProfileFactory(user=student)
    course = CourseFactory(ask_ttc=False)
    enrollment = EnrollmentFactory(course=course, student=student, student_profile=student_profile)
    code_review_checker = CheckerFactory(checking_system__type=CheckingSystemTypes.YANDEX_CONTEST,
                                         settings={'compilers': [YandexCompilers.c11], 'contest_id': 42, 'problem_id': 42})
    assignment = AssignmentFactory(course=course,
                                   submission_type=AssignmentFormat.CODE_REVIEW,
                                   checker=code_review_checker)
    student_assignment = (StudentAssignment.objects
                          .get(assignment=assignment,
                               student=student))
    create_solution_url = reverse("study:assignment_solution_create",
                                  kwargs={"pk": student_assignment.pk})
    form_data = {
        f'{AssignmentSolutionYandexContestForm.prefix}-compiler': YandexCompilers.c11,
        f'{AssignmentSolutionYandexContestForm.prefix}-attached_file': ContentFile("stub", name="test.txt")
    }
    client.login(student)
    response = client.post(create_solution_url, form_data)
    assert response.status_code == 302
    assert AssignmentComment.objects.filter(type=AssignmentSubmissionTypes.SOLUTION).count() == 1


@pytest.mark.django_db
def test_view_student_assignment_post_solution_for_assignment_without_solutions(client):
    student_profile = StudentProfileFactory()
    student = student_profile.user
    course = CourseFactory(main_branch=student_profile.branch,
                           semester=SemesterFactory.create_current(),
                           ask_ttc=False)
    EnrollmentFactory(student_profile=student_profile,
                      student=student,
                      course=course)
    assignment = AssignmentFactory(
        course=course,
        submission_type=AssignmentFormat.NO_SUBMIT)
    student_assignment = (StudentAssignment.objects
                          .get(assignment=assignment, student=student))
    student_url = student_assignment.get_student_url()
    client.login(student)
    response = client.get(student_url)
    assert response.context_data['solution_form'] is None
    create_solution_url = reverse("study:assignment_solution_create",
                                  kwargs={"pk": student_assignment.pk})
    form_data = {
        'solution-text': "Test comment without file"
    }
    response = client.post(create_solution_url, form_data)
    assert response.status_code == 403
    response = client.get(student_url)
    assert smart_bytes(form_data['solution-text']) not in response.content
    html = BeautifulSoup(response.content, "html.parser")
    assert html.find(id="add-solution") is None
    assert html.find(id="solution-form-wrapper") is None


@pytest.mark.django_db
def test_view_student_assignment_comment_author_should_be_resolved(client):
    student = StudentFactory()
    sa = StudentAssignmentFactory(student=student)
    create_comment_url = reverse("study:assignment_comment_create",
                                 kwargs={"pk": sa.pk})
    form_data = {
        'comment-text': "Test comment with file"
    }
    client.login(student)
    client.post(create_comment_url, form_data)
    assert AssignmentComment.objects.count() == 1
    comment = AssignmentComment.objects.first()
    assert comment.author == student
    assert comment.student_assignment == sa


@pytest.mark.django_db
def test_view_assignment_comment_author_cannot_be_modified_by_user(client):
    student1, student2 = StudentFactory.create_batch(2)
    sa1 = StudentAssignmentFactory(student=student1)
    sa2 = StudentAssignmentFactory(student=student2)
    create_comment_url = reverse("study:assignment_comment_create",
                                 kwargs={"pk": sa1.pk})
    form_data = {
        'comment-text': "Test comment with file",
        # Attempt to explicitly override system fields via POST data
        'author': student2.pk,
        'student_assignment': sa2.pk
    }
    client.login(student1)
    client.post(create_comment_url, form_data)
    assert AssignmentComment.objects.count() == 1
    comment = AssignmentComment.objects.first()
    assert comment.author == student1
    assert comment.student_assignment == sa1


@pytest.mark.django_db
def test_view_student_courses_list(client, lms_resolver, assert_login_redirect):
    url = reverse('study:course_list')
    resolver = lms_resolver(url)
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == ViewCourses.name
    student_profile_spb = StudentProfileFactory(branch__code=Branches.SPB)
    student_spb = student_profile_spb.user
    client.login(student_spb)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context_data['ongoing_rest']) == 0
    assert len(response.context_data['ongoing_enrolled']) == 0
    assert len(response.context_data['archive']) == 0
    current_term = get_current_term_pair(student_spb.time_zone)
    current_term_spb = SemesterFactory(year=current_term.year,
                                       type=current_term.type)
    cos = CourseFactory.create_batch(4, semester=current_term_spb,
                                     main_branch=student_profile_spb.branch)
    cos_available = cos[:2]
    cos_enrolled = cos[2:]
    prev_year = current_term.year - 1
    cos_archived = CourseFactory.create_batch(3, semester__year=prev_year)
    for co in cos_enrolled:
        EnrollmentFactory.create(student=student_spb,
                                 student_profile=student_profile_spb,
                                 course=co)
    for co in cos_archived:
        EnrollmentFactory.create(student=student_spb,
                                 student_profile=student_profile_spb,
                                 course=co)
    response = client.get(url)
    assert len(cos_enrolled) == len(response.context_data['ongoing_enrolled'])
    assert set(cos_enrolled) == set(response.context_data['ongoing_enrolled'])
    assert len(cos_archived) == len(response.context_data['archive'])
    assert set(cos_archived) == set(response.context_data['archive'])
    assert len(cos_available) == len(response.context_data['ongoing_rest'])
    assert set(cos_available) == set(response.context_data['ongoing_rest'])
    # Add courses from other branch
    current_term_nsk = SemesterFactory.create_current(for_branch=Branches.NSK)
    co_nsk = CourseFactory.create(semester=current_term_nsk,
                                  main_branch__code=Branches.NSK)
    response = client.get(url)
    assert len(cos_enrolled) == len(response.context_data['ongoing_enrolled'])
    assert len(cos_available) == len(response.context_data['ongoing_rest'])
    assert len(cos_archived) == len(response.context_data['archive'])
    # Test for student from nsk
    student_profile_nsk = StudentProfileFactory(branch__code=Branches.NSK)
    student_nsk = student_profile_nsk.user
    client.login(student_nsk)
    CourseFactory.create(semester__year=prev_year,
                         main_branch=student_profile_nsk.branch)
    response = client.get(url)
    assert len(response.context_data['ongoing_enrolled']) == 0
    assert len(response.context_data['ongoing_rest']) == 1
    assert set(response.context_data['ongoing_rest']) == {co_nsk}
    assert len(response.context_data['archive']) == 0
    # Add open reading, it should be available on compscicenter.ru
    co_open = CourseFactory.create(semester=current_term_nsk,
                                   main_branch=student_profile_nsk.branch)
    response = client.get(url)
    assert len(response.context_data['ongoing_enrolled']) == 0
    assert len(response.context_data['ongoing_rest']) == 2
    assert set(response.context_data['ongoing_rest']) == {co_nsk, co_open}
    assert len(response.context_data['archive']) == 0


@pytest.mark.django_db
def test_view_course_list_course_not_in_student_branch(client, lms_resolver, assert_login_redirect):
    url = reverse('study:course_list')
    student_profile_spb = StudentProfileFactory(branch__code=Branches.SPB)
    student_spb = student_profile_spb.user
    client.login(student_spb)
    response = client.get(url)
    assert len(response.context_data['ongoing_enrolled']) == 0
    current_term = SemesterFactory.create_current(for_branch=student_profile_spb.branch.code)
    course = CourseFactory(semester=current_term, main_branch=BranchFactory())
    # Student could be enrolled in with admin UI to the course
    # they don't has permissions
    EnrollmentFactory(course=course,
                      student_profile=student_profile_spb,
                      student=student_spb)
    # It still should be visible in the ongoing or archive courses
    response = client.get(url)
    assert len(response.context_data['ongoing_enrolled']) == 1
    prev_term = SemesterFactory.create_prev(current_term)
    course = CourseFactory(semester=prev_term, main_branch=BranchFactory())
    EnrollmentFactory(course=course,
                      student_profile=student_profile_spb,
                      student=student_spb)
    response = client.get(url)
    assert len(response.context_data['ongoing_enrolled']) == 1
    assert len(response.context_data['archive']) == 1
    assert response.context_data['archive'] == [course]


@pytest.mark.django_db
def test_view_student_assignment_list_filter_course_choices(client):
    course_one, course_two = CourseFactory.create_batch(2, semester=SemesterFactory.create_current())
    student = StudentFactory()
    EnrollmentFactory(course=course_one, student=student)
    EnrollmentFactory(course=course_two, student=student)
    url = reverse('study:assignment_list')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
    filter_form = response.context['filter_form']
    course_choices_pk = set(cc[0] for cc in filter_form.fields['course'].choices)
    assert len(course_choices_pk) == 3
    assert course_choices_pk == {None, course_one.pk, course_two.pk}


@pytest.mark.django_db
def test_view_student_assignment_list_course_filtering(client):
    course_one, course_two = CourseFactory.create_batch(2, semester=SemesterFactory.create_current())
    student = StudentFactory()
    EnrollmentFactory(course=course_one, student=student)
    EnrollmentFactory(course=course_two, student=student)
    a_one = AssignmentFactory(course=course_one)
    a_two = AssignmentFactory(course=course_two)
    sa_one = StudentAssignment.objects.get(student=student, assignment=a_one)
    sa_two = StudentAssignment.objects.get(student=student, assignment=a_two)
    url = reverse('study:assignment_list')
    client.login(student)

    response = client.get(url)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert len(open_assignments) == 2

    form_data = {
        "course": course_one.pk
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert open_assignments == [sa_one]
    assert f'course={course_one.pk}' in response.redirect_chain[-1][0]

    form_data = {
        "course": course_two.pk
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert open_assignments == [sa_two]
    assert f'course={course_two.pk}' in response.redirect_chain[-1][0]

    form_data = {
        "course": ''
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa_one, sa_two}
    assert 'course=' not in response.redirect_chain[-1][0]


@pytest.mark.django_db
def test_view_student_assignment_list_filter_status_choices(client):
    student = StudentFactory()
    url = reverse('study:assignment_list')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
    filter_form = response.context['filter_form']
    statuses = set(status[0] for status in filter_form.fields['status'].choices)
    assert len(statuses) == len(AssignmentStatus.choices) - 1
    all_statuses = set(map(lambda status: status[0], AssignmentStatus.choices))
    assert all_statuses.difference(statuses) == {AssignmentStatus.NEW}


@pytest.mark.django_db
def test_view_student_assignment_list_filter_assignment_format_choices(client):
    student = StudentFactory()
    url = reverse('study:assignment_list')
    client.login(student)
    response = client.get(url)
    assert response.status_code == 200
    filter_form = response.context['filter_form']
    formats = set(status[0] for status in filter_form.fields['format'].choices)
    assert len(formats) == len(AssignmentFormat.choices)
    all_formats = set(map(lambda status: status[0], AssignmentFormat.choices))
    assert formats == all_formats


@pytest.mark.django_db
def test_view_student_assignment_list_assignment_status_filtering(client):
    course_one, course_two = CourseFactory.create_batch(2, semester=SemesterFactory.create_current())
    student = StudentFactory()
    EnrollmentFactory(course=course_one, student=student)
    EnrollmentFactory(course=course_two, student=student)
    AssignmentFactory.create_batch(size=4, course=course_one)
    a_two = AssignmentFactory(course=course_two)
    sa1_c1, sa2_c1, sa3_c1, sa4_c1 = StudentAssignment.objects.filter(student=student,
                                                                    assignment__course=course_one)
    sa_c2 = StudentAssignment.objects.get(student=student, assignment=a_two)
    sa2_c1.status = AssignmentStatus.ON_CHECKING
    sa3_c1.status = AssignmentStatus.NEED_FIXES
    sa4_c1.status = AssignmentStatus.COMPLETED
    sa2_c1.save()
    sa3_c1.save()
    sa4_c1.save()
    url = reverse('study:assignment_list')
    client.login(student)

    response = client.get(url)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert len(open_assignments) == 5

    form_data = {
        "status": []
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c1, sa2_c1, sa3_c1, sa4_c1, sa_c2}
    assert response.redirect_chain[-1][0][-1] == '?'  # /learning/assignments/?

    form_data = {
        "status": [AssignmentStatus.NOT_SUBMITTED]
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c1, sa_c2}
    assert f"status={AssignmentStatus.NOT_SUBMITTED}" in response.redirect_chain[-1][0]

    # Status NEW not allowed, so filter is not working
    form_data = {
        "status": [AssignmentStatus.NEW]
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c1, sa2_c1, sa3_c1, sa4_c1, sa_c2}

    form_data = {
        "status": [AssignmentStatus.ON_CHECKING,
                   AssignmentStatus.NEED_FIXES,
                   AssignmentStatus.COMPLETED]
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa2_c1, sa3_c1, sa4_c1}
    assert f"status={AssignmentStatus.ON_CHECKING}" in response.redirect_chain[-1][0]
    assert f"status={AssignmentStatus.NEED_FIXES}" in response.redirect_chain[-1][0]
    assert f"status={AssignmentStatus.COMPLETED}" in response.redirect_chain[-1][0]


@pytest.mark.django_db
def test_view_student_assignment_list_assignment_format_filtering(client):
    course_one, course_two = CourseFactory.create_batch(2, semester=SemesterFactory.create_current())
    student = StudentFactory()
    EnrollmentFactory(course=course_one, student=student)
    EnrollmentFactory(course=course_two, student=student)
    a1_c1 = AssignmentFactory(course=course_one, submission_type=AssignmentFormat.NO_SUBMIT)
    a2_c1 = AssignmentFactory(course=course_one, submission_type=AssignmentFormat.ONLINE)
    a3_c1 = AssignmentFactory(course=course_one, submission_type=AssignmentFormat.CODE_REVIEW)
    a1_c2 = AssignmentFactory(course=course_two, submission_type=AssignmentFormat.NO_SUBMIT)
    sa1_c1 = StudentAssignment.objects.get(student=student, assignment=a1_c1)
    sa2_c1 = StudentAssignment.objects.get(student=student, assignment=a2_c1)
    sa3_c1 = StudentAssignment.objects.get(student=student, assignment=a3_c1)
    sa1_c2 = StudentAssignment.objects.get(student=student, assignment=a1_c2)
    url = reverse('study:assignment_list')
    client.login(student)

    response = client.get(url)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert len(open_assignments) == 4

    form_data = {
        "format": []
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c1, sa2_c1, sa3_c1, sa1_c2}
    assert response.redirect_chain[-1][0][-1] == '?'  # /learning/assignments/?

    form_data = {
        "format": [AssignmentFormat.NO_SUBMIT]
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c1, sa1_c2}
    assert f"format={AssignmentFormat.NO_SUBMIT}" in response.redirect_chain[-1][0]

    form_data = {
        "format": [AssignmentFormat.ONLINE,
                   AssignmentFormat.CODE_REVIEW]
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa2_c1, sa3_c1}
    assert f"format={AssignmentFormat.ONLINE}" in response.redirect_chain[-1][0]
    assert f"format={AssignmentFormat.CODE_REVIEW}" in response.redirect_chain[-1][0]


@pytest.mark.django_db
def test_view_student_assignment_list_filtering(client):
    course_one, course_two = CourseFactory.create_batch(2, semester=SemesterFactory.create_current())
    student = StudentFactory()
    EnrollmentFactory(course=course_one, student=student)
    EnrollmentFactory(course=course_two, student=student)
    a1_c1 = AssignmentFactory(course=course_one, submission_type=AssignmentFormat.NO_SUBMIT)
    a2_c1 = AssignmentFactory(course=course_one, submission_type=AssignmentFormat.ONLINE)
    a3_c1 = AssignmentFactory(course=course_one, submission_type=AssignmentFormat.CODE_REVIEW)

    sa1_c1 = StudentAssignment.objects.get(student=student, assignment=a1_c1)
    sa2_c1 = StudentAssignment.objects.get(student=student, assignment=a2_c1)
    sa3_c1 = StudentAssignment.objects.get(student=student, assignment=a3_c1)

    sa1_c1.status = AssignmentStatus.NOT_SUBMITTED
    sa2_c1.status = AssignmentStatus.ON_CHECKING
    sa3_c1.status = AssignmentStatus.NEED_FIXES
    sa1_c1.save()
    sa2_c1.save()
    sa3_c1.save()

    a1_c2 = AssignmentFactory(course=course_two, submission_type=AssignmentFormat.NO_SUBMIT)
    a2_c2 = AssignmentFactory(course=course_two, submission_type=AssignmentFormat.YANDEX_CONTEST)
    a3_c2 = AssignmentFactory(course=course_two, submission_type=AssignmentFormat.EXTERNAL)

    sa1_c2 = StudentAssignment.objects.get(student=student, assignment=a1_c2)
    sa2_c2 = StudentAssignment.objects.get(student=student, assignment=a2_c2)
    sa3_c2 = StudentAssignment.objects.get(student=student, assignment=a3_c2)

    sa1_c2.status = AssignmentStatus.NOT_SUBMITTED
    sa2_c2.status = AssignmentStatus.COMPLETED
    sa1_c2.status = AssignmentStatus.NOT_SUBMITTED
    sa1_c2.save()
    sa2_c2.save()
    sa3_c2.save()

    url = reverse('study:assignment_list')
    client.login(student)

    response = client.get(url)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert len(open_assignments) == 6

    form_data = {
        "course": '',
        "status": [],
        "format": []
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c1, sa2_c1, sa3_c1, sa1_c2, sa2_c2, sa3_c2}
    assert response.redirect_chain[-1][0][-1] == '?'  # /learning/assignments/?

    form_data = {
        "course": course_two.pk,
        "format": [AssignmentFormat.NO_SUBMIT, AssignmentFormat.EXTERNAL],
        "status": [AssignmentStatus.COMPLETED]
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert not set(open_assignments)
    assert f"course={course_two.pk}" in response.redirect_chain[-1][0]
    assert f"format={AssignmentFormat.NO_SUBMIT}" in response.redirect_chain[-1][0]
    assert f"format={AssignmentFormat.EXTERNAL}" in response.redirect_chain[-1][0]
    assert f"status={AssignmentStatus.COMPLETED}" in response.redirect_chain[-1][0]

    form_data["status"] = [AssignmentStatus.NOT_SUBMITTED]
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c2, sa3_c2}
    assert f"status={AssignmentStatus.NOT_SUBMITTED}" in response.redirect_chain[-1][0]

    form_data = {
        "course": '',
        "format": [AssignmentFormat.NO_SUBMIT],
        "status": [AssignmentStatus.NOT_SUBMITTED]
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c1, sa1_c2}
    assert f"format={AssignmentFormat.NO_SUBMIT}" in response.redirect_chain[-1][0]
    assert f"status={AssignmentStatus.NOT_SUBMITTED}" in response.redirect_chain[-1][0]


    form_data = {
        "course": '',
        "format": [AssignmentFormat.ONLINE, AssignmentFormat.CODE_REVIEW,
                   AssignmentFormat.YANDEX_CONTEST, AssignmentFormat.EXTERNAL],
        "status": [AssignmentStatus.NOT_SUBMITTED, AssignmentStatus.ON_CHECKING,
                   AssignmentStatus.NEED_FIXES, AssignmentStatus.COMPLETED]
    }
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa2_c1, sa3_c1, sa2_c2, sa3_c2}

    assert f"format={AssignmentFormat.ONLINE}" in response.redirect_chain[-1][0]
    assert f"format={AssignmentFormat.CODE_REVIEW}" in response.redirect_chain[-1][0]
    assert f"format={AssignmentFormat.YANDEX_CONTEST}" in response.redirect_chain[-1][0]
    assert f"format={AssignmentFormat.EXTERNAL}" in response.redirect_chain[-1][0]

    assert f"status={AssignmentStatus.NOT_SUBMITTED}" in response.redirect_chain[-1][0]
    assert f"status={AssignmentStatus.ON_CHECKING}" in response.redirect_chain[-1][0]
    assert f"status={AssignmentStatus.NEED_FIXES}" in response.redirect_chain[-1][0]
    assert f"status={AssignmentStatus.COMPLETED}" in response.redirect_chain[-1][0]

    # forbidden status AssignmentStatus.NEW for filter
    form_data["status"].append(AssignmentStatus.NEW)
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    open_assignments = response.context['assignment_list_open']
    assert set(open_assignments) == {sa1_c1, sa2_c1, sa3_c1, sa1_c2, sa2_c2, sa3_c2}

