import os
from unittest.mock import MagicMock
import pytest
from learning.models import SubmissionAttachment
from learning.tasks import convert_assignment_submission_ipynb_file_to_html
from learning.tests.factories import AssignmentCommentFactory

@pytest.mark.django_db
def test_convert_assignment_submission_ipynb_file_to_html_success(mocker):
    submission_comment = AssignmentCommentFactory()
    mock_get_field = mocker.patch('learning.tasks.SubmissionAttachment._meta.get_field')
    mock_convert = mocker.patch('learning.tasks.convert_ipynb_to_html')
    origin_name = os.path.splitext(os.path.basename(submission_comment.attached_file.name))[0]

    mock_storage = MagicMock()
    mock_storage.exists.return_value = False
    mock_get_field.return_value.storage = mock_storage

    mock_convert.return_value = "html_content"

    convert_assignment_submission_ipynb_file_to_html(assignment_submission_id=submission_comment.pk)

    mock_convert.assert_called_once_with(submission_comment.attached_file, name=origin_name + '.html')
    

    assert len(SubmissionAttachment.objects.all()) == 1


@pytest.mark.django_db
def test_convert_assignment_submission_ipynb_file_to_html_already_have_file(mocker):
    submission_comment = AssignmentCommentFactory()
    mock_get_field = mocker.patch('learning.tasks.SubmissionAttachment._meta.get_field')
    mock_convert = mocker.patch('learning.tasks.convert_ipynb_to_html')

    mock_storage = MagicMock()
    mock_storage.exists.return_value = True
    mock_get_field.return_value.storage = mock_storage

    mock_convert.return_value = "html_content"

    convert_assignment_submission_ipynb_file_to_html(assignment_submission_id=submission_comment.pk)

    mock_convert.assert_not_called()

    assert len(SubmissionAttachment.objects.all()) == 0


@pytest.mark.django_db
def test_convert_assignment_submission_ipynb_file_to_html_cant_convert(mocker):
    submission_comment = AssignmentCommentFactory()
    mock_get_field = mocker.patch('learning.tasks.SubmissionAttachment._meta.get_field')
    mock_convert = mocker.patch('learning.tasks.convert_ipynb_to_html')
    origin_name = os.path.splitext(os.path.basename(submission_comment.attached_file.name))[0]

    mock_storage = MagicMock()
    mock_storage.exists.return_value = False
    mock_get_field.return_value.storage = mock_storage

    mock_convert.return_value = None

    convert_assignment_submission_ipynb_file_to_html(assignment_submission_id=submission_comment.pk)

    mock_convert.assert_called_once_with(submission_comment.attached_file, name=origin_name + '.html')

    assert len(SubmissionAttachment.objects.all()) == 0


@pytest.mark.django_db
def test_convert_assignment_submission_ipynb_file_to_html_dont_exist_comment(mocker):
    submission_comment = AssignmentCommentFactory()
    mock_get_field = mocker.patch('learning.tasks.SubmissionAttachment._meta.get_field')
    mock_convert = mocker.patch('learning.tasks.convert_ipynb_to_html')

    mock_storage = MagicMock()
    mock_storage.exists.return_value = True
    mock_get_field.return_value.storage = mock_storage

    mock_convert.return_value = "html_content"

    convert_assignment_submission_ipynb_file_to_html(assignment_submission_id=submission_comment.pk+1)

    mock_convert.assert_not_called()

    assert len(SubmissionAttachment.objects.all()) == 0