import pytest
import requests
from unittest.mock import patch
from grading.api.yandex_contest import YandexContestAPI, Unavailable, ContestAPIError, ResponseStatus


class MockResponse:
    def __init__(self, status_code, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise requests.exceptions.HTTPError(response=self)

    def json(self):
        return self._json_data

@pytest.mark.parametrize("req_method",
                         ['get', 'post'])
def test_request_and_check_success(req_method):
    """Тест успешного запроса."""
    url = "https://example.com"
    with patch(f"requests.{req_method}") as mock:
        mock.return_value = MockResponse(status_code=200, text="Success")
        response = YandexContestAPI.request_and_check(url, method=req_method)
        assert response.status_code == 200
        assert response.text == "Success"

def test_request_and_check_unsupported_method():
    """Тест неподдерживаемого метода."""
    url = "https://example.com"
    with pytest.raises(AssertionError):
        YandexContestAPI.request_and_check(url, method="put")

@pytest.mark.parametrize("side_effect",
                         [requests.ConnectionError("Connection failed"),
                          requests.Timeout("Request timed out")])
def test_request_and_check_connection_error(side_effect):
    """Тест ошибки соединения."""
    url = "https://example.com"
    with patch("requests.get") as mock_get:
        mock_get.side_effect = side_effect
        with pytest.raises(Unavailable):
            YandexContestAPI.request_and_check(url, method="get")

def test_request_and_check_http_error_4xx():
    """Тест HTTP ошибки 4xx."""
    url = "https://example.com"
    with patch("requests.get") as mock_get:
        mock_get.return_value = MockResponse(status_code=404, text="Not Found")
        with pytest.raises(ContestAPIError) as exc_info:
            YandexContestAPI.request_and_check(url, method="get")
        assert exc_info.value.code == 404
        assert "Not Found" in exc_info.value.message

def test_request_and_check_http_error_5xx():
    """Тест HTTP ошибки 5xx."""
    url = "https://example.com"
    with patch("requests.get") as mock_get:
        mock_get.return_value = MockResponse(status_code=500, text="Internal Server Error")
        with pytest.raises(Unavailable):
            YandexContestAPI.request_and_check(url, method="get")
