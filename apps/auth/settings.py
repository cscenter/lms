from django.conf import settings

# FIXME: Normalize template paths
EMAIL_RESTORE_PASSWORD_SUBJECT = getattr(settings, 'EMAIL_RESTORE_PASSWORD_SUBJECT', 'registration/password_reset_subject.txt')
EMAIL_RESTORE_PASSWORD_BODY = getattr(settings, 'EMAIL_RESTORE_PASSWORD_BODY', 'emails/password_reset.html')

EMAIL_ACTIVATION_SUBJECT = getattr(settings, 'ACTIVATION_EMAIL_SUBJECT', 'registration/activation_email_subject.txt')
EMAIL_ACTIVATION_BODY = getattr(settings, 'ACTIVATION_EMAIL_BODY', 'registration/activation_email.txt')
