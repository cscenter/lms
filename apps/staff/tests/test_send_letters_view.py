import pytest
from unittest.mock import patch
from django.contrib.messages import get_messages
from django.utils import timezone

from core.tests.factories import EmailTemplateFactory, BranchFactory
from core.urls import reverse
from staff.forms import ConfirmSendLettersForm
from staff.views.send_letters_view import ConfirmView, SendView
from study_programs.tests.factories import AcademicDisciplineFactory
from users.tests.factories import CuratorFactory, StudentProfileFactory, StudentFactory
from learning.settings import StudentStatuses


# Fixtures
@pytest.fixture
def curator():
    """Create a curator user for testing."""
    return CuratorFactory()


@pytest.fixture
def email_template():
    """Create an email template for testing."""
    return EmailTemplateFactory()


@pytest.fixture
def branch():
    """Create a branch for testing."""
    return BranchFactory()


@pytest.fixture
def academic_discipline():
    """Create an academic discipline for testing."""
    return AcademicDisciplineFactory()


@pytest.fixture
def student_profiles(branch, academic_discipline):
    """Create student profiles with different attributes for testing."""
    # Create 5 students with different attributes
    
    # Student 1: Academic leave status
    student1 = StudentFactory()
    profile1 = StudentProfileFactory(
        user=student1,
        branch=branch,
        status=StudentStatuses.ACADEMIC_LEAVE,
        year_of_admission=2019
    )
    profile1.academic_disciplines.add(academic_discipline)
    
    # Student 2: Regular status, admitted in 2021
    student2 = StudentFactory()
    profile2 = StudentProfileFactory(
        user=student2,
        branch=branch,
        status="",  # Empty status means studying in progress
        year_of_admission=2021
    )
    profile2.academic_disciplines.add(academic_discipline)
    
    # Student 3: Regular status, admitted in 2020
    student3 = StudentFactory()
    profile3 = StudentProfileFactory(
        user=student3,
        branch=branch,
        status="",  # Empty status means studying in progress
        year_of_admission=2020
    )
    profile3.academic_disciplines.add(academic_discipline)
    
    # Student 4: Regular status, admitted in 2022
    student4 = StudentFactory()
    profile4 = StudentProfileFactory(
        user=student4,
        branch=branch,
        status="",  # Empty status means studying in progress
        year_of_admission=2022
    )
    profile4.academic_disciplines.add(academic_discipline)
    
    # Student 5: Regular status, admitted in 2021, year_of_curriculum=2022
    student5 = StudentFactory()
    profile5 = StudentProfileFactory(
        user=student5,
        branch=branch,
        status="",  # Empty status means studying in progress
        year_of_admission=2021,
        year_of_curriculum=2022
    )
    profile5.academic_disciplines.add(academic_discipline)
    
    return [profile1, profile2, profile3, profile4, profile5]


# Tests for SendView._send_emails method
@pytest.mark.django_db
@pytest.mark.parametrize("data,is_test,expected_count", [
    (None, False, 2),  # No scheduled time, not a test
    ("2023-01-01T12:00:00+03:00", False, 2),  # ISO format string, not a test
    (timezone.now(), False, 2),  # Timezone aware datetime, not a test
    (None, True, 2),  # No scheduled time, is a test
])
def test_send_view_send_emails(data, is_test, expected_count, email_template):
    """Test the SendView._send_emails method."""
    # Arrange
    emails = ["test1@example.com", "test2@example.com"]
    
    # Act
    with patch('post_office.mail.send') as mock_send:
        result = SendView._send_emails(emails, email_template.name, data, is_test)
    
    # Assert
    assert result == expected_count
    assert mock_send.call_count == expected_count


# Tests for ConfirmView.send_letters method
@pytest.mark.django_db
def test_confirm_view_send_letters_no_filters(student_profiles, email_template):
    """Test the ConfirmView.send_letters method with no filters."""
    # Arrange
    branch = []
    year_of_admission = []
    year_of_curriculum = []
    student_type = []
    status = []
    academic_disciplines = []
    scheduled_time = timezone.now()
    
    # Act
    emails, filter_description = ConfirmView.send_letters(
        email_template.id, branch, year_of_admission, year_of_curriculum,
        student_type, status, academic_disciplines, scheduled_time
    )
    
    # Assert
    assert len(emails) == 5  # All students
    assert len(filter_description) == 1  # Only the count message


@pytest.mark.django_db
def test_confirm_view_send_letters_with_branch_filter(student_profiles, email_template, branch):
    """Test the ConfirmView.send_letters method with branch filter."""
    # Arrange
    branch_filter = [str(branch.id)]
    year_of_admission = []
    year_of_curriculum = []
    student_type = []
    status = []
    academic_disciplines = []
    scheduled_time = timezone.now()
    
    # Act
    emails, filter_description = ConfirmView.send_letters(
        email_template.id, branch_filter, year_of_admission, year_of_curriculum,
        student_type, status, academic_disciplines, scheduled_time
    )
    
    # Assert
    assert len(emails) == 5  # All students belong to the branch
    assert len(filter_description) == 2  # Branch filter + count message


@pytest.mark.django_db
def test_confirm_view_send_letters_with_status_filter(student_profiles, email_template):
    """Test the ConfirmView.send_letters method with status filter."""
    # Arrange
    branch = []
    year_of_admission = []
    year_of_curriculum = []
    student_type = []
    status = [StudentStatuses.ACADEMIC_LEAVE]
    academic_disciplines = []
    scheduled_time = timezone.now()
    
    # Act
    emails, filter_description = ConfirmView.send_letters(
        email_template.id, branch, year_of_admission, year_of_curriculum,
        student_type, status, academic_disciplines, scheduled_time
    )
    
    # Assert
    assert len(emails) == 1  # Only one student has ACADEMIC_LEAVE status
    assert len(filter_description) == 2  # Status filter + count message


@pytest.mark.django_db
def test_confirm_view_send_letters_with_year_of_admission_filter(student_profiles, email_template):
    """Test the ConfirmView.send_letters method with year_of_admission filter."""
    # Arrange
    branch = []
    year_of_admission = ["2020"]
    year_of_curriculum = []
    student_type = []
    status = []
    academic_disciplines = []
    scheduled_time = timezone.now()
    
    # Act
    emails, filter_description = ConfirmView.send_letters(
        email_template.id, branch, year_of_admission, year_of_curriculum,
        student_type, status, academic_disciplines, scheduled_time
    )
    
    # Assert
    assert len(emails) == 1  # Only one student has year_of_admission=2020
    assert len(filter_description) == 2  # Year filter + count message


@pytest.mark.django_db
def test_confirm_view_send_letters_with_year_of_curriculum_filter(student_profiles, email_template):
    """Test the ConfirmView.send_letters method with year_of_curriculum filter."""
    # Arrange
    branch = []
    year_of_admission = []
    year_of_curriculum = ["2022"]
    student_type = []
    status = []
    academic_disciplines = []
    scheduled_time = timezone.now()
    
    # Act
    emails, filter_description = ConfirmView.send_letters(
        email_template.id, branch, year_of_admission, year_of_curriculum,
        student_type, status, academic_disciplines, scheduled_time
    )
    
    # Assert
    assert len(emails) == 1  # Only one student has year_of_curriculum=2022
    assert len(filter_description) == 2  # Year filter + count message


@pytest.mark.django_db
def test_confirm_view_send_letters_with_academic_disciplines_filter(student_profiles, email_template, academic_discipline):
    """Test the ConfirmView.send_letters method with academic_disciplines filter."""
    # Arrange
    branch = []
    year_of_admission = []
    year_of_curriculum = []
    student_type = []
    status = []
    academic_disciplines = [str(academic_discipline.id)]
    scheduled_time = timezone.now()
    
    # Act
    emails, filter_description = ConfirmView.send_letters(
        email_template.id, branch, year_of_admission, year_of_curriculum,
        student_type, status, academic_disciplines, scheduled_time
    )
    
    # Assert
    assert len(emails) == 5  # All students have the academic discipline
    assert len(filter_description) == 2  # Academic discipline filter + count message


@pytest.mark.django_db
def test_confirm_view_send_letters_with_multiple_filters(student_profiles, email_template, branch, academic_discipline):
    """Test the ConfirmView.send_letters method with multiple filters."""
    # Arrange
    branch_filter = [str(branch.id)]
    year_of_admission = ["2020"]
    year_of_curriculum = []
    student_type = []
    status = []
    academic_disciplines = [str(academic_discipline.id)]
    scheduled_time = timezone.now()
    
    # Act
    emails, filter_description = ConfirmView.send_letters(
        email_template.id, branch_filter, year_of_admission, year_of_curriculum,
        student_type, status, academic_disciplines, scheduled_time
    )
    
    # Assert
    assert len(emails) == 1  # Only one student matches all filters
    assert len(filter_description) == 4  # Branch filter + Year filter + Academic discipline filter + count message


# Tests for ConfirmView.handle_test_email method
@pytest.mark.django_db
def test_confirm_view_handle_test_email(client, curator, email_template):
    """Test the ConfirmView.handle_test_email method."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:confirm_send_letters")
    form_data = {
        "email_template": email_template.id,
        "test_email": "test@example.com",
        "submit_test": "1"
    }
    
    # Act
    with patch.object(SendView, '_send_emails', return_value=1) as mock_send_emails:
        response = client.post(url, form_data)
    
    # Assert
    assert response.status_code == 302
    assert response.url == reverse("staff:exports")
    mock_send_emails.assert_called_once_with(["test@example.com"], email_template.name, is_test=True)
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "Test sending" in str(messages[0])


# Tests for ConfirmView.handle_send_emails method
@pytest.mark.django_db
def test_confirm_view_handle_send_emails(client, curator, email_template, branch, academic_discipline):
    """Test the ConfirmView.handle_send_emails method."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:confirm_send_letters")
    form_data = {
        "email_template": email_template.id,
        "branch": [str(branch.id)],
        "academic_disciplines": [str(academic_discipline.id)],
        "submit_send": "1"
    }
    
    # Act
    with patch.object(ConfirmView, 'send_letters', return_value=(["test@example.com"], ["Test filter"])) as mock_send_letters:
        response = client.post(url, form_data)
    
    # Assert
    assert response.status_code == 200  # Renders the confirmation template
    mock_send_letters.assert_called_once()
    assert 'form' in response.context
    assert isinstance(response.context['form'], ConfirmSendLettersForm)
    assert response.context['form'].emails == ["test@example.com"]


# Tests for ConfirmView.process_valid_form method
@pytest.mark.django_db
def test_confirm_view_process_valid_form_test_email(client, curator, email_template):
    """Test the ConfirmView.process_valid_form method with test email."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:confirm_send_letters")
    form_data = {
        "email_template": email_template.id,
        "test_email": "test@example.com",
        "submit_test": "1"
    }
    
    # Act
    with patch.object(SendView, '_send_emails', return_value=1) as mock_send_emails:
        response = client.post(url, form_data)
    
    # Assert
    assert response.status_code == 302
    assert response.url == reverse("staff:exports")
    mock_send_emails.assert_called_once()
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "Test sending" in str(messages[0])


@pytest.mark.django_db
def test_confirm_view_process_valid_form_send_emails(client, curator, email_template, branch, academic_discipline):
    """Test the ConfirmView.process_valid_form method with send emails."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:confirm_send_letters")
    form_data = {
        "email_template": email_template.id,
        "branch": [str(branch.id)],
        "academic_disciplines": [str(academic_discipline.id)],
        "submit_send": "1"
    }
    
    # Act
    with patch.object(ConfirmView, 'send_letters', return_value=(["test@example.com"], ["Test filter"])) as mock_send_letters:
        response = client.post(url, form_data)
    
    # Assert
    assert response.status_code == 200  # Renders the confirmation template
    mock_send_letters.assert_called_once()
    assert 'form' in response.context
    assert isinstance(response.context['form'], ConfirmSendLettersForm)
    assert response.context['form'].emails == ["test@example.com"]


# Tests for ConfirmView.process_invalid_form method
@pytest.mark.django_db
def test_confirm_view_process_invalid_form(client, curator):
    """Test the ConfirmView.process_invalid_form method."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:confirm_send_letters")
    form_data = {
        "email_template": "",  # Required field
        "submit_send": "1"
    }
    
    # Act
    response = client.post(url, form_data)
    
    # Assert
    assert response.status_code == 302
    assert response.url == reverse("staff:exports")
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "Email template" in str(messages[0])


# Tests for SendView.post method
@pytest.mark.django_db
def test_send_view_post_confirm_send(client, curator, email_template):
    """Test the SendView.post method with confirm_send."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:send_letters")
    post_data = {
        "confirm_send": "1",
        "email_template_id": email_template.id,
        "recipients_display": "test@example.com"
    }
    
    # Act
    with patch.object(SendView, '_send_emails', return_value=1) as mock_send_emails:
        response = client.post(url, post_data)
    
    # Assert
    assert response.status_code == 302
    assert response.url == reverse("staff:exports")
    mock_send_emails.assert_called_once()
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "Successfully scheduled" in str(messages[0])


@pytest.mark.django_db
def test_send_view_post_cancel_send(client, curator):
    """Test the SendView.post method with cancel_send."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:send_letters")
    post_data = {
        "cancel_send": "1"
    }
    
    # Act
    response = client.post(url, post_data)
    
    # Assert
    assert response.status_code == 302
    assert response.url == reverse("staff:exports")
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "Email sending canceled" in str(messages[0])


@pytest.mark.django_db
def test_send_view_post_no_action(client, curator):
    """Test the SendView.post method with no action."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:send_letters")
    post_data = {}  # No action specified
    
    # Act
    response = client.post(url, post_data)
    
    # Assert
    assert response.status_code == 302
    assert response.url == reverse("staff:exports")
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "No action specified" in str(messages[0])


# Tests for SendView.handle_confirm_send method
@pytest.mark.django_db
def test_send_view_handle_confirm_send(client, curator, email_template):
    """Test the SendView.handle_confirm_send method."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:send_letters")
    post_data = {
        "confirm_send": "1",
        "email_template_id": email_template.id,
        "recipients_display": "test@example.com"
    }
    
    # Act
    with patch.object(SendView, '_send_emails', return_value=1) as mock_send_emails:
        response = client.post(url, post_data)
    
    # Assert
    assert response.status_code == 302
    assert response.url == reverse("staff:exports")
    mock_send_emails.assert_called_once_with(["test@example.com"], email_template.name, '')
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "Successfully scheduled" in str(messages[0])


# Test error handling in SendView.handle_confirm_send
@pytest.mark.django_db
def test_send_view_handle_confirm_send_error(client, curator):
    """Test error handling in SendView.handle_confirm_send method."""
    # Arrange
    client.login(user_model=curator)
    url = reverse("staff:send_letters")
    post_data = {
        "confirm_send": "1",
        "email_template_id": 999,  # Non-existent template ID
        "recipients_display": "test@example.com"
    }
    
    # Act
    response = client.post(url, post_data)
    
    # Assert
    assert response.status_code == 302
    assert response.url == reverse("staff:exports")
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "Ошибка при отправке писем" in str(messages[0])
