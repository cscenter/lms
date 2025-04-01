import pytest
import re
from django.utils import timezone

from admission.constants import InterviewSections, ApplicantStatuses
from admission.reports import AdmissionApplicantsCampaignReport, AdmissionExamReport, ApplicantStatusLogsReport, AdmissionApplicantsYearReport
from admission.tests.factories import (
    ApplicantFactory,
    ApplicantStatusLogFactory,
    CampaignFactory,
    CommentFactory,
    ExamFactory,
    InterviewFactory,
)
from learning.settings import Branches


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
    campaign = CampaignFactory(branch__code=Branches.SPB)
    applicant = ApplicantFactory(campaign=campaign)
    interview = InterviewFactory(
        applicant=applicant, section=InterviewSections.ALL_IN_ONE
    )
    CommentFactory(score=1, interview=interview)
    report = AdmissionApplicantsCampaignReport(campaign=campaign)
    assert len(report.data) == 1


@pytest.mark.django_db
def test_exam_report():
    campaign = CampaignFactory(branch__code=Branches.SPB)
    report = AdmissionExamReport(campaign)
    df = report.generate()
    rows, columns = df.shape
    assert rows == 0
    static_headers_len = columns
    exam = ExamFactory(score=None, applicant__campaign=campaign)
    df = report.generate()
    rows, columns = df.shape
    assert rows == 1
    exam2 = ExamFactory(
        applicant__campaign=campaign, score=0, details={"scores": ["1"]}
    )
    df = report.generate()
    rows, columns = df.shape
    assert rows == 2
    assert columns == static_headers_len + 1
    assert df.loc[0, "ID"] == exam.applicant_id
    assert df.loc[0, "Итого"] == "-"
    assert df.loc[0, "Задача 1"] == ""
    assert str(df.loc[1, "Итого"]) == "0"
    assert df.loc[1, "Задача 1"] == "1"
    exam3 = ExamFactory(
        applicant__campaign=campaign, score=0, details={"scores": ["42", "43"]}
    )
    # Different `scores` dimensions for exam2 and exam3
    with pytest.raises(AssertionError):
        df = report.generate()


@pytest.mark.django_db
def test_applicant_status_logs_report():
    """Test for ApplicantStatusLogsReport class."""
    # Create a current campaign
    campaign = CampaignFactory(current=True)
    
    # Create applicants with status logs
    applicant1 = ApplicantFactory(campaign=campaign)
    applicant2 = ApplicantFactory(campaign=campaign)
    
    # Create status logs
    log1 = ApplicantStatusLogFactory(
        applicant=applicant1,
        former_status=ApplicantStatuses.PENDING,
        status=ApplicantStatuses.PERMIT_TO_EXAM
    )
    
    log2 = ApplicantStatusLogFactory(
        applicant=applicant2,
        former_status=ApplicantStatuses.PASSED_EXAM,
        status=ApplicantStatuses.ACCEPT
    )
    
    # Create report
    report = ApplicantStatusLogsReport()
    
    # Check headers
    assert 'ID' in report.headers
    assert 'Former status' in report.headers or 'Предыдущий статус' in report.headers
    assert 'Status' in report.headers or 'Статус' in report.headers
    assert 'Entry Added' in report.headers or 'Дата изменения' in report.headers
    
    # Check data
    assert len(report.data) == 2  # Should have two logs
    
    # Check that dates are in ISO format or similar format
    date_pattern = r'\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2})?)?'
    assert re.match(date_pattern, report.data[0][3])
    assert re.match(date_pattern, report.data[1][3])
