import pytest
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.utils import timezone

from api.models import ExternalServiceToken
from admission.tests.factories import CampaignFactory


@pytest.fixture
def mock_yadisk_client():
    with patch('yadisk.Client') as mock_client:
        # Configure mock for Yandex.Disk client
        mock_instance = MagicMock()
        mock_instance.check_token.return_value = True
        
        # Configure exists method to return True for root directories to avoid recursion
        # but False for some directories to ensure mkdir is called
        def exists_side_effect(path):
            return path in ['/ysda']
        
        mock_instance.exists.side_effect = exists_side_effect
        mock_client.return_value = mock_instance
        
        # Configure context manager
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        
        yield mock_instance


@pytest.mark.django_db
def test_daily_dump_to_yandex_disk_command(mock_yadisk_client):
    # Create token for Yandex.Disk
    ExternalServiceToken.objects.create(
        service_tag="syrop_yandex_disk",
        access_key="test_token"
    )
    
    # Create current campaign
    current_year = timezone.now().year
    CampaignFactory(year=current_year, current=True)
    
    call_command('daily_dump_to_yandex_disk')
    
    # Check that client was created with correct token
    from yadisk import Client
    Client.assert_called_once()
    # Check that token was verified
    mock_yadisk_client.check_token.assert_called_once()
    
    # Check that parent directories were created
    mock_yadisk_client.mkdir.assert_called()
    
    
    # Check that files were uploaded
    assert mock_yadisk_client.upload.call_count == 2  # Should be two upload calls
    
    # Check upload paths
    today = timezone.now().date().isoformat()
    expected_paths = [
        f"/ysda/daily_applicant_status_logs/applicant_status_logs_{today}.csv",
        f"/ysda/daily_applicant_reports/applicant_year_report_{current_year}_{today}.csv"
    ]
    
    # Extract paths from upload calls
    actual_paths = [call[0][1] for call in mock_yadisk_client.upload.call_args_list]
    
    # Check that paths match
    assert set(actual_paths) == set(expected_paths)