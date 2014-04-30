from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from sorl.thumbnail.admin import AdminImageMixin

from core.admin import UbereditorMixin
from users.models import CSCUser


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


class CSCUserAdmin(AdminImageMixin, UbereditorMixin, UserAdmin):
    form = CSCUserChangeForm
    add_form = CSCUserCreationForm

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ['last_name', 'first_name', 'patronymic',
                                      'photo', 'note', 'enrolment_year',
                                      'graduation_year']}),
        ('Permissions', {'fields': ['is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions']}),
        ('Important dates', {'fields': ['last_login', 'date_joined']})]


admin.site.register(CSCUser, CSCUserAdmin)
