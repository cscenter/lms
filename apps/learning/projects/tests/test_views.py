# -*- coding: utf-8 -*-
import factory
import pytest
from django.utils.encoding import smart_bytes
from django.utils.timezone import now

from core.timezone import now_local
from core.urls import reverse_lazy, reverse
from courses.tests.factories import SemesterFactory
from courses.utils import get_current_term_pair
from learning.projects.forms import ReportForm, PracticeCriteriaForm, \
    ReportReviewForm
from learning.projects.models import Report, ProjectStudent, Review, \
    PracticeCriteria
from learning.projects.tests.factories import ProjectFactory, ReportFactory, \
    ReportingPeriodFactory, ReviewFactory, \
    ReviewPracticeCriteriaFactory, review_form_factory
from learning.settings import StudentStatuses, GradeTypes, Branches
from notifications.models import Notification
from users.constants import Roles
from users.tests.factories import StudentFactory, ProjectReviewerFactory, \
    UserFactory, CuratorFactory

URL_REPORTS = reverse_lazy("projects:report_list_reviewers")
URL_PROJECTS = reverse_lazy("projects:current_term_projects")
URL_ALL_PROJECTS = reverse_lazy("projects:all_projects")


@pytest.mark.django_db
def test_user_detail(client):
    """
    Students should have `projects` in their info on profile page.

    Just a simple test to check something appears.
    """
    student = StudentFactory(enrollment_year='2013')
    semester1 = SemesterFactory.create(year=2014, type='spring')
    semester2 = SemesterFactory.create(year=2014, type='autumn')
    p1 = ProjectFactory.create(students=[student], semester=semester1)
    p2 = ProjectFactory.create(students=[student],
                               semester=semester2,
                               description="")
    sp2 = p2.projectstudent_set.all()[0]
    sp2.final_grade = GradeTypes.GOOD
    sp2.save()
    resp = client.get(reverse('user_detail', args=[student.pk]))
    assert smart_bytes(p1.name) in resp.content
    assert smart_bytes(p2.name) in resp.content
    assert smart_bytes(sp2.get_final_grade_display().lower()) in resp.content


@pytest.mark.django_db
def test_staff_diplomas_view(curator, client):
    student = StudentFactory(enrollment_year='2013',
                                   status=StudentStatuses.WILL_GRADUATE)
    semester1 = SemesterFactory.create(year=2014, type='spring')
    p = ProjectFactory.create(students=[student], semester=semester1)
    sp = p.projectstudent_set.all()[0]
    sp.final_grade = GradeTypes.GOOD
    sp.save()
    client.login(curator)
    response = client.get(reverse('staff:exports_students_diplomas_tex',
                                  kwargs={"city_code": "spb"}))
    assert smart_bytes(p.name) in response.content


@pytest.mark.django_db
def test_project_reviewer_only_mixin_security(client, curator):
    response = client.get(URL_REPORTS)
    assert response.status_code == 302
    student = StudentFactory()
    client.login(student)
    response = client.get(URL_REPORTS)
    assert response.status_code == 302
    reviewer = UserFactory.create(groups=[Roles.PROJECT_REVIEWER])
    client.login(reviewer)
    response = client.get(URL_REPORTS)
    assert response.status_code == 200
    assert not response.context["reports"]
    client.login(curator)
    response = client.get(URL_REPORTS, follow=True)
    # Redirects to reports-all page
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.skip
def test_reviewer_list(client, curator):
    """Test GET-filter `show` works"""
    reviewer = ProjectReviewerFactory.create()
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    client.login(reviewer)
    student = StudentFactory()
    response = client.get(URL_REPORTS)
    assert response.status_code == 200
    assert len(response.context["reports"]) == 0
    # Enroll on project from prev term
    project = ProjectFactory(students=[student], reviewers=[reviewer],
                             semester=semester_prev)
    response = client.get(URL_REPORTS)
    assert response.status_code == 200
    assert len(response.context["reports"]) == 0
    # Enroll on project from current term
    ProjectFactory.create(students=[student], reviewers=[reviewer],
                          semester=semester)
    response = client.get(URL_REPORTS)
    assert len(response.context["reports"]) == 1
    # With ?show=available filter show projects from current term to reviewers
    response = client.get(URL_PROJECTS)
    assert len(response.context["reports"]) == 1
    curator.add_group(Roles.PROJECT_REVIEWER)
    client.login(curator)
    # Redirects to list with all reports
    response = client.get(URL_REPORTS, follow=True)
    assert len(response.context["reports"]) == 1
    response = client.get(URL_PROJECTS)
    assert len(response.context["reports"]) == 1
    response = client.get(URL_ALL_PROJECTS)
    assert len(response.context["reports"]) == 2


@pytest.mark.django_db
def test_create_project_presentations(client):
    """
    Test path to presentation file is with valid project id.

    Let's check it due to Django upload files before model creation.
    """
    from django.core.files.base import ContentFile
    semester = SemesterFactory()
    project = ProjectFactory(semester=semester)
    project.presentation = ContentFile("stub", name="test.txt")
    project.supervisor_presentation = ContentFile("stub", name="test.txt")
    project.save()
    assert "None" not in project.presentation.name
    assert "None" not in project.supervisor_presentation.name


@pytest.mark.django_db
def test_project_detail_unauth(client):
    """Make sure unauth user never see report form with any status"""
    student = StudentFactory()
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    reviewer = ProjectReviewerFactory()
    project = ProjectFactory.create(students=[student], reviewers=[reviewer],
                                    semester=semester)
    response = client.get(project.get_absolute_url())
    assert smart_bytes("Следить за проектом") not in response.content
    assert "can_enroll" in response.context
    assert response.context["can_enroll"] is False
    assert "can_view_report" in response.context
    assert response.context["can_view_report"] is False
    assert "you_enrolled" in response.context
    assert response.context["you_enrolled"] is False
    # Try to send form with report
    form = {"text": "report text content"}
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403  # Not student participant


@pytest.mark.django_db
def test_project_detail_student_participant(client):
    from datetime import timedelta
    semester = SemesterFactory.create_current(city_code=Branches.SPB)
    semester_prev = SemesterFactory.create_prev(semester)
    student = StudentFactory()
    reviewer = ProjectReviewerFactory()
    project = ProjectFactory.create(students=[student], reviewers=[reviewer],
                                    semester=semester,
                                    branch__code=Branches.SPB)
    client.login(student)
    response = client.get(project.get_absolute_url())
    assert "can_enroll" in response.context
    assert response.context["can_enroll"] is False
    today = now_local(Branches.SPB).date()
    rp = ReportingPeriodFactory(start_on=today + timedelta(days=1),
                                end_on=today + timedelta(days=2),
                                term=semester, branch=None)
    form = {
        f"{ReportForm.prefix}-text": "report text content",
        f"{ReportForm.prefix}-reporting_period": rp.id,
    }
    # Too early to send reports
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403
    # Project already stale
    project.semester = semester_prev
    project.save()
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403
    # Sending period ended, but they are still can send reports
    project.semester = semester
    project.save()
    rp.start_on = today - timedelta(days=7)
    rp.end_on = today - timedelta(days=2)
    rp.save()
    response = client.post(project.get_absolute_url(), form, follow=True)
    assert response.status_code == 200
    assert Report.objects.count() == 1
    # Test sending form visibility based on sending period activity
    Report.objects.get_queryset().delete()  # delete reports to skip redirect
    response = client.get(project.get_absolute_url())
    assert response.status_code == 200
    project.semester = semester_prev
    project.save()
    response = client.get(project.get_absolute_url())
    assert project.is_active() is False
    project.semester = semester
    project.save()


@pytest.mark.django_db
def test_project_detail_student_participant_notifications(client, curator):
    """Test notifications are added to the queue after report has been sent"""
    from datetime import timedelta
    curator.add_group(Roles.CURATOR_PROJECTS)
    curator.save()
    # This curator not in reviewers group and doesn't receive notifications
    curator2 = UserFactory(is_superuser=True, is_staff=True)
    semester = SemesterFactory.create_current()
    today = now_local(Branches.SPB).date()
    rp = ReportingPeriodFactory(term=semester, start_on=today, branch=None,
                                end_on=today + timedelta(days=1))
    student = StudentFactory(city_id='spb')
    reviewer = ProjectReviewerFactory()
    project = ProjectFactory(students=[student], reviewers=[reviewer],
                             semester=semester, branch__code=Branches.SPB)
    client.login(student)
    form = {
        f"{ReportForm.prefix}-reporting_period": rp.id,
        f"{ReportForm.prefix}-text": "report text content"
    }
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 302
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_project_detail_reviewer(client, curator):
    reviewer = ProjectReviewerFactory()
    client.login(reviewer)
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    student = StudentFactory(city_id='spb')
    project = ProjectFactory(students=[student], semester=semester_prev)
    url = project.get_absolute_url()
    response = client.get(url)
    # hide enrollment button for past projects
    assert "can_enroll" in response.context
    assert response.context["can_enroll"] is False
    current_project = ProjectFactory(students=[student], semester=semester)
    url = reverse("projects:project_detail",
                  args=[current_project.pk])
    response = client.get(url)
    assert response.context["can_enroll"] is True
    assert smart_bytes("Смотреть отчет") not in response.content
    # Also, hide button for already enrolled projects
    current_project.reviewers.add(reviewer)
    current_project.save()
    response = client.get(url)
    assert smart_bytes("Следить за проектом") not in response.content


@pytest.mark.django_db
def test_reviewer_project_enroll(client, curator):
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    student = StudentFactory()
    old_project = ProjectFactory(students=[student], semester=semester_prev)
    url_for_old = reverse("projects:reviewer_project_enroll",
                          args=[old_project.pk])
    reviewer = ProjectReviewerFactory()
    reviewer2 = ProjectReviewerFactory()
    client.login(reviewer)
    response = client.post(url_for_old, {})
    assert response.status_code == 403
    active_project = ProjectFactory(students=[student], semester=semester)
    url_enroll_in_active = reverse("projects:reviewer_project_enroll",
                                   args=[active_project.pk])
    response = client.post(url_enroll_in_active, {}, follow=True)
    assert response.status_code == 200
    assert len(active_project.reviewers.all()) == 1
    assert reviewer in active_project.reviewers.all()
    assert reviewer2 not in active_project.reviewers.all()
    # Curator has no reviewers group, but it's ok
    client.login(curator)
    response = client.post(url_enroll_in_active, {}, follow=True)
    assert response.status_code == 200


@pytest.mark.django_db
def test_reportpage_permissions(client, curator):
    reviewer_participant = ProjectReviewerFactory()
    reviewer = ProjectReviewerFactory()
    report = ReportFactory()
    report.project_student.project.reviewers.add(reviewer_participant)
    report.project_student.project.save()
    # Rewrite unauth to login page
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302
    client.login(reviewer)
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302
    client.login(reviewer_participant)
    # Report is in `sent` status, so participant reviewer has no permissions yet
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302
    report.status = Report.REVIEW
    report.save()
    response = client.get(report.get_absolute_url())
    assert response.status_code == 200
    # Login as author of report
    client.login(report.project_student.student)
    response = client.get(report.get_absolute_url())
    assert response.status_code == 200
    # Login as student, but not participant of review
    student = StudentFactory()
    client.login(student)
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302
    # Add student to project participants, but he's still should be redirected
    ps = ProjectStudent(project=report.project_student.project, student=student)
    ps.save()
    assert ProjectStudent.objects.count() == 2
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302


@pytest.mark.django_db
def test_reportpage_update_permissions():
    """Check report updating restricted to curators only"""
    from learning.projects.views import (ReportUpdateStatusView,
        ReportCuratorAssessmentView)
    from users.mixins import CuratorOnlyMixin
    assert issubclass(ReportCuratorAssessmentView, CuratorOnlyMixin)
    assert issubclass(ReportUpdateStatusView, CuratorOnlyMixin)


@pytest.mark.django_db
def test_report_notifications(client, curator):
    """Test notifications about new comment and on changing report status"""
    curator.add_group(Roles.CURATOR_PROJECTS)
    curator2 = CuratorFactory.create()
    reviewer1, reviewer2 = ProjectReviewerFactory.create_batch(2)
    client.login(reviewer1)
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    student1, student2 = StudentFactory.create_batch(2, city_id='spb')
    project = ProjectFactory(students=[student1, student2],
                             semester=semester,
                             reviewers=[reviewer1, reviewer2])
    ps1, _ = ProjectStudent.objects.get_or_create(project=project,
                                                  student=student1)
    report = ReportFactory(project_student=ps1)
    assert report.status == Report.SENT
    assert Notification.objects.count() == 1
    Notification.objects.get_queryset().delete()
    comment_form = {"new_comment_form-text": "test", "new_comment_form": "Save"}
    # Reviewer can't send comments when status is `SENT`
    client.login(reviewer1)
    client.post(report.get_absolute_url(), comment_form)
    assert Notification.objects.count() == 0
    client.login(student1)
    client.post(report.get_absolute_url(), comment_form)
    assert Notification.objects.count() == 1
    assert Notification.objects.all()[0].recipient == curator
    Notification.objects.get_queryset().delete()
    client.login(curator)
    client.post(report.get_absolute_url(), comment_form)
    assert Notification.objects.count() == 1
    assert Notification.objects.all()[0].recipient == student1
    Notification.objects.get_queryset().delete()
    report.status = Report.REVIEW
    report.save()
    client.post(report.get_absolute_url(), comment_form)
    assert Notification.objects.count() == 3
    Notification.objects.get_queryset().delete()
    client.login(student1)
    client.post(report.get_absolute_url(), comment_form)
    assert Notification.objects.count() == 3
    Notification.objects.get_queryset().delete()
    client.login(reviewer1)
    client.post(report.get_absolute_url(), comment_form)
    assert Notification.objects.count() == 3
    recipients = [n.recipient for n in Notification.objects.all()]
    assert reviewer2 in recipients
    assert curator in recipients
    assert student1 in recipients
    Notification.objects.get_queryset().delete()
    # If report is completed, can't send comments
    report.status = Report.COMPLETED
    report.save()
    response = client.post(report.get_absolute_url(), comment_form)
    assert response.status_code == 403
    assert Notification.objects.count() == 0
    # Create report for second student
    ps2, _ = ProjectStudent.objects.get_or_create(project=project,
                                                  student=student2)
    report2 = ReportFactory(project_student=ps2,
                            reporting_period=report.reporting_period,
                            status=Report.COMPLETED)
    review1 = ReviewFactory(report=report, reviewer=reviewer1)
    # When we rollback status to `review` stage, make sure notifications
    # won't send to reviewers, who already sent review.
    report.status = Report.REVIEW
    report.save()
    client.login(curator)
    update_report2_status_url = report2.get_update_url()
    response = client.post(update_report2_status_url, {
        "report_status_change-status": "review",
    })
    assert Notification.objects.count() == 2  # no reviews on report2 yet
    Notification.objects.get_queryset().delete()
    review2 = ReviewFactory(report=report2, reviewer=reviewer2)
    # Rollback status again, now we have review on report2
    report2.status = Report.COMPLETED
    report2.save()
    client.login(curator)
    response = client.post(update_report2_status_url, {
        "report_status_change-status": "review",
    }, follow=True)
    assert response.status_code == 200
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_review_form_permissions(client, curator, assert_login_redirect):
    reviewer1 = ProjectReviewerFactory()
    report = ReportFactory(status=Report.REVIEW,
                           project_student__project__reviewers=[reviewer1])
    review_form = review_form_factory()
    assert_login_redirect(report.get_review_url(), form=review_form,
                          method='post')
    client.login(reviewer1)
    report.status = Report.SUMMARY
    report.save()
    response = client.post(report.get_review_url(), review_form)
    assert response.status_code == 403  # Report is not in review state
    client.login(curator)
    report.status = Report.REVIEW
    report.save()
    response = client.post(report.get_review_url(), review_form)
    assert response.status_code == 403  # Curator is not a reviewer


@pytest.mark.django_db
def test_review(client, curator, assert_login_redirect):
    reviewer1 = ProjectReviewerFactory()
    report = ReportFactory(status=Report.REVIEW,
                           project_student__project__reviewers=[reviewer1])
    review_form = review_form_factory(is_completed=False)
    review_form[f"{PracticeCriteriaForm.prefix}-score_problems"] = 2
    client.login(reviewer1)
    response = client.post(report.get_review_url(), review_form)
    assert response.status_code == 302
    assert Review.objects.count() == 1
    assert PracticeCriteria.objects.count() == 1
    review = Review.objects.get(report=report)
    assert review.reviewer == reviewer1
    assert review.criteria
    assert review.criteria.score_problems == 2
    assert review.criteria.review == review
    review_form[f"{PracticeCriteriaForm.prefix}-score_problems"] = 1
    response = client.post(report.get_review_url(), review_form)
    assert response.status_code == 302
    assert Review.objects.count() == 1
    assert PracticeCriteria.objects.count() == 1
    review_form[f"{ReportReviewForm.prefix}-is_completed"] = True
    response = client.post(report.get_review_url(), review_form)
    assert response.status_code == 302
    assert Review.objects.count() == 1
    assert PracticeCriteria.objects.count() == 1


@pytest.mark.django_db
def test_review_notifications(client, curator, assert_login_redirect):
    """Test notification about new review for project curators"""
    curator.add_group(Roles.CURATOR_PROJECTS)
    curator2 = CuratorFactory()
    reviewer1 = ProjectReviewerFactory()
    report = ReportFactory(status=Report.REVIEW,
                           project_student__project__reviewers=[reviewer1])
    client.login(reviewer1)
    review_form = review_form_factory()
    response = client.post(report.get_review_url(), review_form)
    assert response.status_code == 302
    assert Review.objects.count() == 1
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_reportpage_summarize_notifications(client, curator):
    from users.mixins import CuratorOnlyMixin
    from learning.projects.views import ReportCuratorSummarizeView
    assert issubclass(ReportCuratorSummarizeView, CuratorOnlyMixin)
    curator.add_group(Roles.PROJECT_REVIEWER)
    curator2 = CuratorFactory.create()
    reviewer1, reviewer2 = ProjectReviewerFactory.create_batch(2)
    client.login(reviewer1)
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    student1, student2 = StudentFactory.create_batch(2)
    project = ProjectFactory(students=[student1, student2],
                             semester=semester,
                             reviewers=[reviewer1, reviewer2])
    ps1, _ = ProjectStudent.objects.get_or_create(project=project,
                                                  student=student1)
    report = ReportFactory(project_student=ps1)
    report.status = Report.SUMMARY
    report.save()
    client.login(curator)
    form = {
        "report_summary_form": "Save",
        "report_summary_form-final_score_note": "test",
    }
    Notification.objects.get_queryset().delete()
    client.post(report.get_absolute_url(), form)
    assert Notification.objects.count() == 0
    form["report_summary_form-complete"] = "1"
    url = reverse("projects:project_report_summarize", kwargs={
        "report_id": report.pk,
        "project_pk": report.project_student.project.pk,
    })
    response = client.post(url, form)
    assert Notification.objects.count() == 1
    assert Notification.objects.all()[0].recipient == student1



# TODO: проверить видимость форм, на уровне контекста, post-запросы
# TODO: test notifications was read on target pages: new comment, new report