import pytest
import pytz
from datetime import datetime
from django.conf import settings
from django.contrib.messages import get_messages
from django.utils import timezone
from unittest.mock import patch, MagicMock

from core.tests.factories import EmailTemplateFactory, BranchFactory
from core.urls import reverse
from post_office.models import EmailTemplate
from staff.views.send_letters_view import SendLettersView
from study_programs.tests.factories import AcademicDisciplineFactory
from users.tests.factories import CuratorFactory, StudentProfileFactory, StudentFactory
from learning.settings import StudentStatuses


@pytest.mark.django_db
class TestSendLettersView:
    """
    Tests for the SendLettersView class.
    """
    
    @pytest.fixture
    def curator(self):
        """Create a curator user for testing."""
        return CuratorFactory()
    
    @pytest.fixture
    def email_template(self):
        """Create an email template for testing."""
        return EmailTemplateFactory()
    
    @pytest.fixture
    def branch(self):
        """Create a branch for testing."""
        return BranchFactory()
    
    @pytest.fixture
    def academic_discipline(self):
        """Create an academic discipline for testing."""
        return AcademicDisciplineFactory()
    
    @pytest.fixture
    def student_profiles(self, branch, academic_discipline):
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
    
    @pytest.mark.parametrize("data,expected_count", [
        (None, 2),  # No scheduled time
        ("2023-01-01T12:00:00+03:00", 2),  # ISO format string
        (timezone.now(), 2),  # Timezone aware datetime
    ])
    @patch('staff.views.send_letters_view.mail.send')
    def test_send_emails(self, mock_send, data, expected_count, email_template):
        """Test the _send_emails method."""
        # Arrange
        emails = ["test1@example.com", "test2@example.com"]
        
        # Act
        result = SendLettersView._send_emails(emails, email_template.name, data)
        
        # Assert
        assert result == expected_count
        assert mock_send.call_count == expected_count
    
    def test_send_letters_no_filters(self, student_profiles, email_template):
        """Test the send_letters method with no filters."""
        # Arrange
        branch = []
        year_of_admission = []
        year_of_curriculum = []
        student_type = []
        status = []
        academic_disciplines = []
        scheduled_time = timezone.now()
        
        # Act
        emails, filter_description = SendLettersView.send_letters(
            email_template.id, branch, year_of_admission, year_of_curriculum,
            student_type, status, academic_disciplines, scheduled_time
        )
        
        # Assert
        assert len(emails) == 5  # All students
        assert len(filter_description) == 1  # Only the count message
    
    def test_send_letters_with_branch_filter(self, student_profiles, email_template, branch):
        """Test the send_letters method with branch filter."""
        # Arrange
        branch_filter = [str(branch.id)]
        year_of_admission = []
        year_of_curriculum = []
        student_type = []
        status = []
        academic_disciplines = []
        scheduled_time = timezone.now()
        
        # Act
        emails, filter_description = SendLettersView.send_letters(
            email_template.id, branch_filter, year_of_admission, year_of_curriculum,
            student_type, status, academic_disciplines, scheduled_time
        )
        
        # Assert
        assert len(emails) == 5  # All students belong to the branch
        assert len(filter_description) == 2  # Branch filter + count message
    
    def test_send_letters_with_status_filter(self, student_profiles, email_template):
        """Test the send_letters method with status filter."""
        # Arrange
        branch = []
        year_of_admission = []
        year_of_curriculum = []
        student_type = []
        status = [StudentStatuses.ACADEMIC_LEAVE]
        academic_disciplines = []
        scheduled_time = timezone.now()
        
        # Act
        emails, filter_description = SendLettersView.send_letters(
            email_template.id, branch, year_of_admission, year_of_curriculum,
            student_type, status, academic_disciplines, scheduled_time
        )
        
        # Assert
        assert len(emails) == 1  # Only one student has ACADEMIC_LEAVE status
        assert len(filter_description) == 2  # Status filter + count message
    
    def test_send_letters_with_year_of_admission_filter(self, student_profiles, email_template):
        """Test the send_letters method with year_of_admission filter."""
        # Arrange
        branch = []
        year_of_admission = ["2020"]
        year_of_curriculum = []
        student_type = []
        status = []
        academic_disciplines = []
        scheduled_time = timezone.now()
        
        # Act
        emails, filter_description = SendLettersView.send_letters(
            email_template.id, branch, year_of_admission, year_of_curriculum,
            student_type, status, academic_disciplines, scheduled_time
        )
        
        # Assert
        assert len(emails) == 1  # Only one student has year_of_admission=2020
        assert len(filter_description) == 2  # Year filter + count message
    
    def test_send_letters_with_year_of_curriculum_filter(self, student_profiles, email_template):
        """Test the send_letters method with year_of_curriculum filter."""
        # Arrange
        branch = []
        year_of_admission = []
        year_of_curriculum = ["2022"]
        student_type = []
        status = []
        academic_disciplines = []
        scheduled_time = timezone.now()
        
        # Act
        emails, filter_description = SendLettersView.send_letters(
            email_template.id, branch, year_of_admission, year_of_curriculum,
            student_type, status, academic_disciplines, scheduled_time
        )
        
        # Assert
        assert len(emails) == 1  # Only one student has year_of_curriculum=2022
        assert len(filter_description) == 2  # Year filter + count message
    
    def test_send_letters_with_academic_disciplines_filter(self, student_profiles, email_template, academic_discipline):
        """Test the send_letters method with academic_disciplines filter."""
        # Arrange
        branch = []
        year_of_admission = []
        year_of_curriculum = []
        student_type = []
        status = []
        academic_disciplines = [str(academic_discipline.id)]
        scheduled_time = timezone.now()
        
        # Act
        emails, filter_description = SendLettersView.send_letters(
            email_template.id, branch, year_of_admission, year_of_curriculum,
            student_type, status, academic_disciplines, scheduled_time
        )
        
        # Assert
        assert len(emails) == 5  # All students have the academic discipline
        assert len(filter_description) == 2  # Academic discipline filter + count message
    
    def test_send_letters_with_multiple_filters(self, student_profiles, email_template, branch, academic_discipline):
        """Test the send_letters method with multiple filters."""
        # Arrange
        branch_filter = [str(branch.id)]
        year_of_admission = ["2020"]
        year_of_curriculum = []
        student_type = []
        status = []
        academic_disciplines = [str(academic_discipline.id)]
        scheduled_time = timezone.now()
        
        # Act
        emails, filter_description = SendLettersView.send_letters(
            email_template.id, branch_filter, year_of_admission, year_of_curriculum,
            student_type, status, academic_disciplines, scheduled_time
        )
        
        # Assert
        assert len(emails) == 1  # Only one student matches all filters
        assert len(filter_description) == 4  # Branch filter + Year filter + Academic discipline filter + count message
    
    @pytest.mark.parametrize("post_data,expected_redirect", [
        ({"confirm_send": "1"}, "staff:exports"),
        ({"cancel_send": "1"}, "staff:exports"),
        ({}, "staff:exports"),  # Default case for GET request
    ])
    def test_dispatch(self, client, curator, post_data, expected_redirect):
        """Test the dispatch method."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        
        # Act
        response = client.post(url, post_data)
        
        # Assert
        assert response.status_code == 302
        assert response.url == reverse(expected_redirect)
    
    def test_dispatch_with_session_data(self, client, curator):
        """Test the dispatch method with session data."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        session = client.session
        session['emails'] = ["test@example.com"]
        session['filter_description'] = ["Test filter"]
        session.save()
        
        # Act
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert 'emails' in response.context
        assert response.context['email_count'] == 1
    
    def test_handle_confirm_send(self, client, curator, email_template):
        """Test the handle_confirm_send method."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        session = client.session
        session['email_template_id'] = email_template.id
        session['emails'] = ["test@example.com"]
        session['scheduled_time'] = None
        session.save()
        
        # Act
        with patch.object(SendLettersView, '_send_emails', return_value=1) as mock_send_emails:
            response = client.post(url, {"confirm_send": "1"})
        
        # Assert
        assert response.status_code == 302
        assert response.url == reverse("staff:exports")
        mock_send_emails.assert_called_once()
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "Успешно запланирована" in str(messages[0])
    
    def test_handle_cancel_send(self, client, curator):
        """Test the handle_cancel_send method."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        session = client.session
        session['email_template_id'] = 1
        session['emails'] = ["test@example.com"]
        session.save()
        
        # Act
        response = client.post(url, {"cancel_send": "1"})
        
        # Assert
        assert response.status_code == 302
        assert response.url == reverse("staff:exports")
        assert 'email_template_id' not in client.session
        assert 'emails' not in client.session
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "Отправка писем отменена" in str(messages[0])
    
    def test_show_confirmation_page(self, client, curator):
        """Test the show_confirmation_page method."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        session = client.session
        session['emails'] = ["test@example.com"]
        session['filter_description'] = ["Test filter"]
        session.save()
        
        # Act
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert 'emails' in response.context
        assert response.context['email_count'] == 1
    
    def test_post_valid_form_test_email(self, client, curator, email_template):
        """Test the post method with a valid form for test email."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        form_data = {
            "email_template": email_template.id,
            "test_email": "test@example.com",
            "submit_test": "1"
        }
        
        # Act
        with patch.object(SendLettersView, '_send_emails', return_value=1) as mock_send_emails:
            response = client.post(url, form_data)
        
        # Assert
        assert response.status_code == 302
        assert response.url == reverse("staff:exports")
        mock_send_emails.assert_called_once()
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "Тестовая отправка" in str(messages[0])
    
    def test_post_valid_form_send_emails(self, client, curator, email_template, branch, academic_discipline):
        """Test the post method with a valid form for sending emails."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        form_data = {
            "email_template": email_template.id,
            "branch": [str(branch.id)],
            "academic_disciplines": [str(academic_discipline.id)],
            "submit_send": "1"
        }
        
        # Act
        with patch.object(SendLettersView, 'send_letters', return_value=(["test@example.com"], ["Test filter"])) as mock_send_letters:
            response = client.post(url, form_data)
        
        # Assert
        assert response.status_code == 302
        assert response.url == reverse("staff:send_letters")
        mock_send_letters.assert_called_once()
        assert 'email_template_id' in client.session
        assert 'emails' in client.session
        assert 'filter_description' in client.session
    
    def test_post_invalid_form(self, client, curator):
        """Test the post method with an invalid form."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
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
    
    def test_handle_test_email(self, client, curator, email_template):
        """Test the handle_test_email method."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        form_data = {
            "email_template": email_template.id,
            "test_email": "test@example.com",
            "submit_test": "1"
        }
        
        # Act
        with patch.object(SendLettersView, '_send_emails', return_value=1) as mock_send_emails:
            response = client.post(url, form_data)
        
        # Assert
        assert response.status_code == 302
        assert response.url == reverse("staff:exports")
        mock_send_emails.assert_called_once_with(["test@example.com"], email_template.name)
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert "Тестовая отправка" in str(messages[0])
    
    def test_handle_send_emails(self, client, curator, email_template, branch, academic_discipline):
        """Test the handle_send_emails method."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
        form_data = {
            "email_template": email_template.id,
            "branch": [str(branch.id)],
            "academic_disciplines": [str(academic_discipline.id)],
            "submit_send": "1"
        }
        
        # Act
        with patch.object(SendLettersView, 'send_letters', return_value=(["test@example.com"], ["Test filter"])) as mock_send_letters:
            response = client.post(url, form_data)
        
        # Assert
        assert response.status_code == 302
        assert response.url == reverse("staff:send_letters")
        mock_send_letters.assert_called_once()
        assert client.session['email_template_id'] == str(email_template.id)
        assert client.session['emails'] == ["test@example.com"]
        assert client.session['filter_description'] == ["Test filter"]
    
    def test_process_invalid_form(self, client, curator):
        """Test the process_invalid_form method."""
        # Arrange
        client.login(curator)
        url = reverse("staff:send_letters")
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
