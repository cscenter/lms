from urllib.parse import urlparse

from django.conf import settings
from django.test import Client
from django.utils.functional import Promise

from core.tests.settings import TEST_DOMAIN
from core.urls import reverse

if settings.LMS_SUBDOMAIN:
    _SERVER_NAME = f"{settings.LMS_SUBDOMAIN}.{TEST_DOMAIN}"
else:
    _SERVER_NAME = TEST_DOMAIN


class TestClient(Client):
    def login(self, user_model, **credentials):
        if user_model is None:
            return super().login(**credentials)
        else:
            # If user model were created with UserFactory with
            # attached `raw_password`
            return super().login(username=user_model.username,
                                 password=user_model.raw_password)

    def get_api_token(self, user):
        url = reverse("auth-api:v1:token_obtain",
                      subdomain=settings.LMS_SUBDOMAIN)
        credentials = {
            'login': user.email,
            'password': user.raw_password
        }
        response = self.post(url, credentials)
        return response.data['secret_token']

    def _base_environ(self, **request):
        # TODO: Client in django-stubs does not define _base_environ.
        env = super()._base_environ(**request)  # type: ignore
        if 'SERVER_NAME' not in request:
            # Override default server name `testserver`
            env['SERVER_NAME'] = TEST_DOMAIN
        return env

    def _patch_extra(self, path, extra):
        if "HTTP_HOST" not in extra:
            # FIXME: better way to customize url_resolve from django.shortcuts
            # FIXME: by replacing `django.urls.reverse` with core.urls.reverse
            if isinstance(path, Promise):
                path = str(path)
            parsed_url = urlparse(path)
            if settings.LMS_SUBDOMAIN and parsed_url.netloc.startswith(settings.LMS_SUBDOMAIN):
                extra["SERVER_NAME"] = _SERVER_NAME

    def get(self, path, *args, **kwargs):
        """
        Since URL resolving depends on subdomain value
        (see `core.middleware.SubdomainURLRoutingMiddleware`) we should
        emulate the originating host of the request (see `HttpRequest.get_host`)
        Achieve this by providing HTTP_HOST or overriding SERVER_NAME.

        We could override HTTP_HOST value but it won't be overriding
        """
        self._patch_extra(path, kwargs)
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
        self._patch_extra(path, kwargs)
        return super().post(path, *args, **kwargs)

    def patch(self, path, *args, **kwargs):
        self._patch_extra(path, kwargs)
        return super().patch(path, *args, **kwargs)

    def put(self, path, *args, **kwargs):
        self._patch_extra(path, kwargs)
        return super().put(path, *args, **kwargs)
