from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import Group
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from registration.forms import RegistrationFormUniqueEmail
from users.models import CSCUser


class RegistrationUniqueEmailAndUsernameForm(RegistrationFormUniqueEmail):

    def clean_username(self):
        """
        Validate that the supplied username is unique for the
        site.
        """
        if CSCUser.objects.filter(username__iexact=self.cleaned_data['username']):
            raise ValidationError(_("This username is already in use. Please supply a different username."))
        return self.cleaned_data['username']

    def save(self, commit=True):
        user = super(RegistrationUniqueEmailAndUsernameForm, self).save(commit=False)
        if commit:
            user.save()
        # Note: It's ok save user here, even commit=False
        user.save()
        group = Group.objects.get(pk=CSCUser.group_pks.STUDENT_CLUB)
        user.groups.add(group)
        return user
