import pytest
from django_ses.signals import bounce_received

from core.urls import reverse
from users.tests.factories import UserFactory

sns_message = {
    'Type': 'Notification',
    'MessageId': 'db79444b-5f2d-5a3b-a17e-1df202c7456d',
    'TopicArn': 'arn:aws:sns:eu-west-1:297302290031:lms-emails-delivery',
    'Subject': 'Amazon SES Email Event Notification',
    'Message': '{"eventType":"Bounce","bounce":{"feedbackId":"0102017bdf7e1232-fe460e8d-f8bf-4f2c-aebe-f8ab18d07417-000000","bounceType":"Permanent","bounceSubType":"General","bouncedRecipients":[{"emailAddress":"bounce@simulator.amazonses.com","action":"failed","status":"5.1.1","diagnosticCode":"smtp; 550 5.1.1 user unknown"}],"timestamp":"2021-09-13T14:09:46.625Z","reportingMTA":"dns; a7-17.smtp-out.eu-west-1.amazonses.com"},"mail":{"timestamp":"2021-09-13T14:09:45.797Z","source":"noreply@compscicenter.ru","sourceArn":"arn:aws:ses:eu-west-1:297302290031:identity/noreply@compscicenter.ru","sendingAccountId":"297302290031","messageId":"0102017bdf7e0f45-b18f8a29-0cb6-44d0-8475-bde02530be89-000000","destination":["bounce@simulator.amazonses.com"],"headersTruncated":false,"headers":[{"name":"Content-Type","value":"multipart/mixed; boundary=\\"===============3908962620379402182==\\""},{"name":"MIME-Version","value":"1.0"},{"name":"Subject","value":"Amazon SES Test (SDK for Python)"},{"name":"From","value":"noreply@compscicenter.ru"},{"name":"To","value":"bounce@simulator.amazonses.com"}],"commonHeaders":{"from":["noreply@compscicenter.ru"],"to":["bounce@simulator.amazonses.com"],"messageId":"0102017bdf7e0f45-b18f8a29-0cb6-44d0-8475-bde02530be89-000000","subject":"Amazon SES Test (SDK for Python)"},"tags":{"ses:operation":["SendRawEmail"],"ses:configuration-set":["lms"],"ses:source-ip":["52.28.201.159"],"ses:from-domain":["compscicenter.ru"],"ses:caller-identity":["ses-smtp-user.20160412-151609"]}}}\n',
    'Timestamp': '2021-09-13T14:09:46.747Z',
    'SignatureVersion': '1',
    'Signature': 'XXX',
    'SigningCertURL': 'XXX',
    'UnsubscribeURL': 'XXX'
}


@pytest.mark.django_db
def test_bounce_handler(settings, client, mocker):
    mocker.patch('django_ses.settings.VERIFY_EVENT_SIGNATURES', False)
    user = UserFactory(email='bounce@simulator.amazonses.com')
    user2 = UserFactory(email='another@email.com')
    assert user.email_suspension_details is None
    # Actually it doesn't guarantee that a real signal handler was connected
    mocked = mocker.patch('core.signals.bounce_handler')
    bounce_received.connect(mocked)
    webhook_url = reverse('aws_ses_events_webhook', subdomain=settings.LMS_SUBDOMAIN)
    response = client.post(webhook_url, data=sns_message, content_type='application/json')
    assert response.status_code == 200
    mocked.assert_called_once()
    user.refresh_from_db()
    user2.refresh_from_db()
    assert user.email_suspension_details is not None
    # No idea why mypy throws an error here
    assert user.email_suspension_details['bounceSubType'] == 'General'  # type: ignore[unreachable]
    assert 'action' in user.email_suspension_details
    assert user.email_suspension_details['action'] == 'failed'
    assert 'status' in user.email_suspension_details
    assert 'diagnosticCode' in user.email_suspension_details
    assert user2.email_suspension_details is None

