import pytest

from admission.reports import AdmissionApplicantsReport, AdmissionExamReport
from admission.tests.factories import CampaignFactory, ApplicantFactory, \
    CommentFactory, InterviewFactory, ExamFactory
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
    interview = InterviewFactory(applicant=applicant)
    CommentFactory(score=1, interview=interview)
    report = AdmissionApplicantsReport(campaign=campaign)
    assert len(report.data) == 1
    check_value_for_header(report, 'Результаты интервью', 0, '1.00')


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
    exam2 = ExamFactory(applicant__campaign=campaign, score=0,
                        details={'scores': ['1']})
    df = report.generate()
    rows, columns = df.shape
    assert rows == 2
    assert columns == static_headers_len + 1
    assert df.loc[0, 'ID'] == exam.applicant_id
    assert df.loc[0, 'Итого'] == '-'
    assert df.loc[0, 'Задача 1'] == ''
    assert str(df.loc[1, 'Итого']) == '0'
    assert df.loc[1, 'Задача 1'] == '1'
    exam3 = ExamFactory(applicant__campaign=campaign, score=0,
                        details={'scores': ['42', '43']})
    # Different `scores` dimensions for exam2 and exam3
    with pytest.raises(AssertionError):
        df = report.generate()
