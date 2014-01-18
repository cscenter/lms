from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from sorl.thumbnail.admin import AdminImageMixin

from core.models import CSCUser

class CSCUserCreationForm(UserCreationForm):
    class Meta:
        model = CSCUser
        fields = ('username',)

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            self._meta.model._default_manager.get(username=username)
        except self._meta.model.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages["duplicate_username"])

class CSCUserChangeForm(UserChangeForm):
    class Meta:
        model = CSCUser

    # TODO: test this
    def clean(self):
        data = self.cleaned_data
        if data['is_student'] and data['enrolment_year'] is None:
            raise ValidationError(_("CSCUser|enrolment year should be provided "
                                    "for students"))
        return data


class CSCUserAdmin(AdminImageMixin, UserAdmin):
    form = CSCUserChangeForm
    add_form = CSCUserCreationForm

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ['last_name', 'first_name', 'patronymic',
                                      'photo', 'note']}),
        ('Current status', {'fields': ['is_teacher', 'is_student',
                                       'enrolment_year']}),
        ('Permissions', {'fields': ['is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions']}),
        ('Important dates', {'fields': ['last_login', 'date_joined']})
        ]

admin.site.register(CSCUser, CSCUserAdmin)
