from django.conf import settings

# XXX: Try to avoid using settings below and provide local variables for domain-specific tests
TEST_DOMAIN = getattr(settings, 'TEST_DOMAIN', 'compscicenter.ru')
TEST_DOMAIN_ID = getattr(settings, 'TEST_DOMAIN_ID', 1)
ANOTHER_DOMAIN = getattr(settings, 'ANOTHER_DOMAIN', 'compsciclub.ru')
ANOTHER_DOMAIN_ID = getattr(settings, 'ANOTHER_DOMAIN_ID', 2)
CLUB_SITE = getattr(settings, 'CLUB_SITE', 'compsciclub.ru')
CLUB_SITE_ID = getattr(settings, 'CLUB_SITE_ID', 3)
