import datetime
from bs4 import BeautifulSoup
import pytest
from apps.core.timezone.utils import now_local
from apps.core.urls import reverse
from apps.grading.api.yandex_contest import SubmissionVerdict
from apps.grading.constants import SubmissionStatus
from apps.grading.tests.factories import CheckerFactory, SubmissionFactory


@pytest.mark.django_db
def test_student_assignment_detail_view_get(client):
    
    submission = SubmissionFactory(status=SubmissionStatus.PASSED,
                                   meta={'verdict': SubmissionVerdict.OK.value})
    client.login(submission.assignment_submission.student_assignment.student)
    
    # Update course completed_at to make it active course
    course = submission.assignment_submission.student_assignment.assignment.course
    course.completed_at = now_local(course.get_timezone()).date() + datetime.timedelta(days=2)
    course.save()
    
    # Add checker with for assignment here because of circle import in factory
    assignment = submission.assignment_submission.student_assignment.assignment
    assignment.checker = CheckerFactory()
    assignment.save()

    url = reverse('study:student_assignment_detail', kwargs={"pk": submission.assignment_submission.student_assignment.pk})
    response = client.get(url).content.decode('utf-8')

    soup = BeautifulSoup(response, "html.parser")
    assert soup.find(text=SubmissionVerdict.OK.value) is not None
