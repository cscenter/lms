from django.apps import apps
from django.utils import translation


def send_activation_email(site_id, registration_profile_id, language_code):
    Site = apps.get_model('sites', 'Site')
    RegistrationProfile = apps.get_model('registration', 'RegistrationProfile')
    site = Site.objects.get(pk=site_id)
    translation.activate(language_code)
    reg_profile = RegistrationProfile.objects.get(pk=registration_profile_id)
    reg_profile.send_activation_email(site)
