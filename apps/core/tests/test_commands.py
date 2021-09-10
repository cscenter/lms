import pytest

from django.core import management

from core.models import SiteConfiguration
from core.tests.factories import SiteFactory


@pytest.mark.django_db
def test_update_site_configuration(settings):
    site = SiteFactory(domain='super.new.domain')
    settings.SITE_ID = site.pk
    expected_email_host = 'smtp.example.com'
    expected_email_password = 'email_password'
    use_tls_ssl = True
    email_port = 444
    default_email_from = 'default@example.com'
    email_host_user = 'user'
    settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    settings.EMAIL_HOST = expected_email_host
    settings.EMAIL_HOST_PASSWORD = expected_email_password
    settings.EMAIL_USE_TLS = use_tls_ssl
    settings.EMAIL_USE_SSL = use_tls_ssl
    settings.EMAIL_PORT = email_port
    settings.EMAIL_HOST_USER = email_host_user
    settings.DEFAULT_FROM_EMAIL = default_email_from
    management.call_command("update_site_configuration")
    assert SiteConfiguration.objects.filter(site_id=settings.SITE_ID).exists()
    model_configuration = SiteConfiguration.objects.filter(site_id=settings.SITE_ID).get()
    assert model_configuration.email_host == expected_email_host
    assert model_configuration.email_host_password != expected_email_password
    assert SiteConfiguration.decrypt(model_configuration.email_host_password) == expected_email_password
    assert model_configuration.email_port == email_port
    assert model_configuration.email_use_tls == use_tls_ssl
    assert model_configuration.email_use_ssl == use_tls_ssl
    assert model_configuration.email_host_user == email_host_user
    assert model_configuration.default_from_email == default_email_from
