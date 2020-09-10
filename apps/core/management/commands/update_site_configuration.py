from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import SiteConfiguration


class Command(BaseCommand):
    help = 'Sync model-based site configuration with current environment configuration'

    def handle(self, *args, **options):
        SiteConfiguration.objects.update_or_create(
            site_id=settings.SITE_ID,
            defaults={
                "lms_subdomain": settings.LMS_SUBDOMAIN,
                "default_branch_code": settings.DEFAULT_BRANCH_CODE,
                "default_from_email": settings.DEFAULT_FROM_EMAIL,
                "email_host": settings.EMAIL_HOST,
                "email_host_password": SiteConfiguration.encrypt(settings.EMAIL_HOST_PASSWORD),
                "email_host_user": settings.EMAIL_HOST_USER,
                "email_port": settings.EMAIL_PORT,
                "email_use_tls": settings.EMAIL_USE_TLS,
                "email_use_ssl": settings.EMAIL_USE_SSL,
            }
        )
