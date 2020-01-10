from urllib.parse import urlparse

from django.conf import settings
from django.test import Client, TestCase
from django.utils.functional import Promise

from learning.settings import Branches

if settings.LMS_SUBDOMAIN:
    _SERVER_NAME = f"{settings.LMS_SUBDOMAIN}.{settings.TEST_DOMAIN}"
else:
    _SERVER_NAME = settings.TEST_DOMAIN


class TestClient(Client):
    def login(self, user_model, **credentials):
        if user_model is None:
            return super().login(**credentials)
        else:
            # If user model were created with UserFactory with
            # attached `raw_password`
            return super().login(username=user_model.username,
                                 password=user_model.raw_password)

    def _base_environ(self, **request):
        env = super()._base_environ(**request)
        if 'SERVER_NAME' not in request:
            # Override default server name `testserver`
            env['SERVER_NAME'] = settings.TEST_DOMAIN
        return env

    def get(self, path, *args, **kwargs):
        """
        Since URL resolving depends on subdomain value
        (see `core.middleware.SubdomainURLRoutingMiddleware`) we should
        emulate the originating host of the request (see `HttpRequest.get_host`)
        Achieve this by providing HTTP_HOST or overriding SERVER_NAME.

        We could override HTTP_HOST value but it won't be overriding
        """
        if "HTTP_HOST" not in kwargs:
            if isinstance(path, Promise):
                path = str(path)
            parsed_url = urlparse(path)
            if settings.LMS_SUBDOMAIN and parsed_url.netloc.startswith(settings.LMS_SUBDOMAIN):
                kwargs["SERVER_NAME"] = _SERVER_NAME
        return super().get(path, *args, **kwargs)

    def post(self, path, *args, **kwargs):
        """
        Since URL resolving depends on subdomain value
        (see `core.middleware.SubdomainURLRoutingMiddleware`) we should
        emulate the originating host of the request (see `HttpRequest.get_host`)
        Achieve this by overriding SERVER_NAME.

        Note:
            Don't use HTTP_HOST with `follow=True`. Internally
            `_handle_redirects` overrides `SERVER_NAME` and passing
            HTTP_HOST without any modification. Since HTTP_HOST has a
            higher precedence on host determination, it could break subdomain
            detection. (if any url in a redirect chain depends on subdomain
            but this subdomain value is different from the HTTP_HOST
            subdomain value)
            Test client uses only relative part of the url by discarding domain
            part (just a fun fact to know)
        """
        if "HTTP_HOST" not in kwargs:
            # FIXME: better way to customize url_resolve from django.shortcuts
            # FIXME: by replacing `django.urls.reverse` with core.urls.reverse
            if isinstance(path, Promise):
                path = str(path)
            parsed_url = urlparse(path)
            if settings.LMS_SUBDOMAIN and parsed_url.netloc.startswith(settings.LMS_SUBDOMAIN):
                kwargs["SERVER_NAME"] = _SERVER_NAME
        return super().post(path, *args, **kwargs)


class CSCTestCase(TestCase):
    client_class = TestClient

    def assertLoginRedirect(self, url):
        # Cast `next` value to the relative path since
        # after successful login we redirect to the same domain.
        path = urlparse(url).path
        expected_path = "{}?next={}".format(settings.LOGIN_URL, path)
        self.assertRedirects(self.client.get(url), expected_path)

    def assertPOSTLoginRedirect(self, url, form):
        # Cast `next` value to the relative path since
        # after successful login we redirect to the same domain.
        path = urlparse(url).path
        expected_path = "{}?next={}".format(settings.LOGIN_URL, path)
        self.assertRedirects(self.client.post(url, form), expected_path)

    def assertRedirects(self, response, expected_url, *args, **kwargs):
        """
        Note that `fetch_redirect_response` will be broken if
        `expected_url` has absolute path since testing client always returns
        relative path for `response.url` (see `assertRedirects` for details)
        """
        # FIXME:disable for abs path only?
        kwargs['fetch_redirect_response'] = False
        super().assertRedirects(response, expected_url, *args, **kwargs)
