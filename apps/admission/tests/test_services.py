import pytest

from admission.constants import ChallengeStatuses
from admission.models import Exam
from admission.services import EmailQueueService, create_student_from_applicant
from admission.tests.factories import CampaignFactory, ApplicantFactory, \
    ExamFactory
from core.tests.factories import EmailTemplateFactory, BranchFactory
from users.models import StudentTypes


@pytest.mark.django_db
def test_new_exam_invitation_email():
    email_template = EmailTemplateFactory()
    campaign = CampaignFactory(template_exam_invitation=email_template.name)
    applicant = ApplicantFactory(campaign=campaign)
    with pytest.raises(Exam.DoesNotExist):
        EmailQueueService.new_exam_invitation(applicant)
    exam = ExamFactory(applicant=applicant, status=ChallengeStatuses.REGISTERED,
                       yandex_contest_id='42')
    email, created = EmailQueueService.new_exam_invitation(applicant)
    assert created
    assert email.template == email_template
    assert email.to == [applicant.email]
    # Render on delivery
    assert not email.subject
    assert not email.message
    assert not email.html_message
    assert 'YANDEX_LOGIN' in email.context
    assert email.context['YANDEX_LOGIN'] == applicant.yandex_login
    assert 'CONTEST_ID' in email.context
    assert email.context['CONTEST_ID'] == '42'
    email2, created = EmailQueueService.new_exam_invitation(applicant)
    assert not created
    assert email2 == email
    email3, created = EmailQueueService.new_exam_invitation(applicant,
                                                            allow_duplicates=True)
    assert created
    assert email3.pk > email2.pk


@pytest.mark.django_db
def test_create_student_from_applicant(settings):
    branch = BranchFactory(time_zone='Asia/Yekaterinburg')
    campaign = CampaignFactory(branch=branch)
    applicant = ApplicantFactory(campaign=campaign)
    user = create_student_from_applicant(applicant)
    student_profile = user.get_student_profile(settings.SITE_ID)
    assert student_profile.branch == branch
    assert student_profile.year_of_admission == applicant.campaign.year
    assert student_profile.type == StudentTypes.REGULAR
    assert user.time_zone == branch.time_zone
