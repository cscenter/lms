import smtplib
import socket

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.mail.utils import DNS_NAME
from django.core.mail.backends.smtp import EmailBackend


class SSLEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False
        try:
            self.connection = smtplib.SMTP_SSL(
                self.host, self.port, local_hostname=DNS_NAME.get_fqdn())
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except (smtplib.SMTPException, socket.error):
            if not self.fail_silently:
                raise


class EmailOrUsernameModelBackend(ModelBackend):

    def authenticate(self, username=None, password=None, **kwargs):
        # XXX this is fine, since @ is not allowed in usernames.
        field = "email" if "@" in username else "username"
        user_model = get_user_model()
        try:
            user = user_model.objects.get(**{field: username})
            if user.check_password(password):
                return user
        except user_model.DoesNotExist:
            # See comment in 'ModelBackend#authenticate'.
            user_model().set_password(password)
