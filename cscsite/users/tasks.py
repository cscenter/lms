from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils import translation


html_email_template_name = None
email_template_name = 'emails/password_reset.html'
subject_template_name = 'registration/password_reset_subject.txt'


def send_restore_password_email(context, from_email, to_email, language_code):
    """
    Sends a django.core.mail.EmailMultiAlternatives to `to_email`.
    """
    translation.activate(language_code)
    subject = loader.render_to_string(subject_template_name, context)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    body = loader.render_to_string(email_template_name, context)
    email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
    if html_email_template_name is not None:
        html_email = loader.render_to_string(html_email_template_name, context)
        email_message.attach_alternative(html_email, 'text/html')
    email_message.send()
