import pytest
from learning.tests.factories import AssignmentCommentFactory
from files.utils import ConvertError, convert_ipynb_to_html
from django.core.files.base import ContentFile


@pytest.mark.django_db
def test_convert_ipynb_to_html_success(mocker, settings):

    settings.USE_CLOUD_STORAGE = False
    mock_exporter = mocker.patch("files.utils.HTMLExporter")
    mock_exporter.return_value.from_filename.return_value = ('<html></html>', None)
    submission_comment = AssignmentCommentFactory()
    submission_comment.attached_file.name = 'test.ipynb'


    result = convert_ipynb_to_html(submission_comment.attached_file)


    assert isinstance(result, ContentFile)
    assert result.name.endswith('.html')


@pytest.mark.django_db
def test_convert_ipynb_to_html_not_found(mocker, settings):

    settings.USE_CLOUD_STORAGE = False
    mock_exporter = mocker.patch("files.utils.HTMLExporter")
    mock_exporter.return_value.from_filename.side_effect = FileNotFoundError()
    submission_comment = AssignmentCommentFactory()
    submission_comment.attached_file.name = 'test.ipynb'

    with pytest.raises(ConvertError):
        convert_ipynb_to_html(submission_comment.attached_file)


@pytest.mark.django_db
def test_convert_ipynb_to_html_cloud_storage_success(mocker, settings):

    settings.USE_CLOUD_STORAGE = True
    mock_exporter = mocker.patch("files.utils.HTMLExporter")
    mock_exporter.return_value.from_file.return_value = ('<html></html>', None)
    mock_request_get = mocker.patch("files.utils.requests.get")
    mock_request_get.return_value.__enter__.return_value.raw = 'raw_content'
    submission_comment = AssignmentCommentFactory()
    submission_comment.attached_file.name = 'test.ipynb'


    result = convert_ipynb_to_html(submission_comment.attached_file)


    assert isinstance(result, ContentFile)
    assert result.name.endswith('.html')

@pytest.mark.django_db
def test_convert_ipynb_to_html_cloud_storage_not_found(mocker, settings):

    settings.USE_CLOUD_STORAGE = True
    mock_exporter = mocker.patch("files.utils.HTMLExporter")
    mock_exporter.return_value.from_file.side_effect = FileNotFoundError()
    mock_request_get = mocker.patch("files.utils.requests.get")
    mock_request_get.return_value.__enter__.return_value.raw = 'raw_content'
    submission_comment = AssignmentCommentFactory()
    submission_comment.attached_file.name = 'test.ipynb'

    with pytest.raises(ConvertError):
        convert_ipynb_to_html(submission_comment.attached_file)