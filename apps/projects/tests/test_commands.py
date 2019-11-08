import datetime
from io import StringIO

import pytest
import pytz
from django.core import management
from django.core.management import CommandError

from courses.tests.factories import SemesterFactory
from notifications import NotificationTypes
from projects.constants import ProjectTypes, \
    REPORTING_NOTIFY_BEFORE_START, REPORTING_NOTIFY_BEFORE_DEADLINE
from projects.models import ProjectStudent, ReportingPeriod
from projects.tests.factories import ReportingPeriodFactory, \
    ProjectStudentFactory, ProjectFactory
from notifications.models import Notification


@pytest.mark.django_db
def test_autograde_projects(settings):
    settings.LANGUAGE_CODE = 'ru'
    current_term = SemesterFactory.create_current()
    start_on = current_term.starts_at.date()
    end_on = start_on + datetime.timedelta(days=2)
    project_student = ProjectStudentFactory(project__semester=current_term,
                                            project__is_external=False,
                                            supervisor_grade=1,
                                            presentation_grade=2)
    assert project_student.final_grade == ProjectStudent.GRADES.NOT_GRADED
    # No reporting periods were found
    with pytest.raises(CommandError) as e:
        management.call_command("autograde_projects")
    rp = ReportingPeriodFactory(term=current_term, branch=None,
                                start_on=start_on, end_on=end_on)
    # No score settings
    with pytest.raises(CommandError) as e:
        management.call_command("autograde_projects")
    rp.score_excellent = 10
    rp.score_good = 6
    rp.score_pass = 2
    rp.save()
    out = StringIO()
    management.call_command("autograde_projects", stdout=out)
    assert out.getvalue().strip() == "1"
    project_student.refresh_from_db()
    assert project_student.final_grade == ProjectStudent.GRADES.CREDIT


@pytest.mark.django_db
def test_projects_notifications(settings, mocker):
    settings.LANGUAGE_CODE = 'ru'
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    msk_tz = pytz.timezone("Europe/Moscow")
    mocked_now = msk_tz.localize(datetime.datetime(2019, 4, 1, 12, 0))
    mocked_timezone.return_value = mocked_now
    current_term = SemesterFactory.create_current()
    rp_all_research = ReportingPeriodFactory(
        term=current_term,
        project_type=ProjectTypes.research,
        branch=None,
        start_on=mocked_now + datetime.timedelta(days=REPORTING_NOTIFY_BEFORE_START),
        end_on=mocked_now + datetime.timedelta(days=5),
        score_excellent=10, score_good=6,
        score_pass=3)
    project = ProjectFactory(semester=current_term,
                             is_external=False,
                             project_type=ProjectTypes.research)
    project_practice = ProjectFactory(semester=current_term,
                                      is_external=False,
                                      project_type=ProjectTypes.practice)
    project_student = ProjectStudentFactory(project=project,
                                            supervisor_grade=1,
                                            presentation_grade=2)
    ProjectStudentFactory(project=project_practice,
                          supervisor_grade=1,
                          presentation_grade=2)
    assert Notification.objects.count() == 0
    management.call_command("projects_notifications")
    assert Notification.objects.count() == 1
    management.call_command("projects_notifications")
    assert Notification.objects.count() == 1
    n = Notification.objects.first()
    assert n.type.code == NotificationTypes.PROJECT_REPORTING_STARTED.name
    rp_all_practice = ReportingPeriodFactory(
        term=current_term,
        project_type=ProjectTypes.practice,
        branch=None,
        start_on=mocked_now,
        end_on=mocked_now + datetime.timedelta(days=REPORTING_NOTIFY_BEFORE_DEADLINE),
        score_excellent=10, score_good=6,
        score_pass=3)
    management.call_command("projects_notifications")
    assert Notification.objects.count() == 2
    rp_all_practice.start_on += datetime.timedelta(days=REPORTING_NOTIFY_BEFORE_START)
    rp_all_practice.save()
    management.call_command("projects_notifications")
    assert Notification.objects.count() == 3
    # Started earlier that today
    ReportingPeriod.objects.all().delete()
    rp_all_practice = ReportingPeriodFactory(
        term=current_term,
        project_type=ProjectTypes.practice,
        branch=None,
        start_on=mocked_now - datetime.timedelta(days=3),
        end_on=mocked_now + datetime.timedelta(days=REPORTING_NOTIFY_BEFORE_DEADLINE),
        score_excellent=10, score_good=6,
        score_pass=3)
    management.call_command("projects_notifications")
    assert Notification.objects.count() == 4
