

# Copied from learning/tests/test_reports.
import pytest

from learning.admission.factories import CampaignFactory, ApplicantFactory, \
    CommentFactory, InterviewFactory
from learning.admission.reports import AdmissionReport


def check_value_for_header(report, header, row_index, expected_value):
    """
    Make sure that `header` in report headers.
    Value related to `header` for data[row_index] should be
    equal to `expected_value`
    """
    assert header in report.headers
    header_index = report.headers.index(header)
    export_data = report.export_row(report.data[row_index])
    assert export_data[header_index] == expected_value


@pytest.mark.django_db
def test_report_smoke():
    campaign = CampaignFactory(city_id="spb")
    applicant = ApplicantFactory(campaign=campaign)
    interview = InterviewFactory(applicant=applicant)
    CommentFactory(score=1, interview=interview)
    report = AdmissionReport(campaign=campaign)
    assert len(report.data) == 1
    check_value_for_header(report, 'Результаты интервью', 0, '1.00')
