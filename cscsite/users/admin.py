from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.forms import ValidationError

from sorl.thumbnail.admin import AdminImageMixin

from core.admin import UbereditorMixin
from users.models import CSCUser, StudentInfo


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
        raise ValidationError(self.error_messages["duplicate_username"])


class CSCUserChangeForm(UserChangeForm):
    class Meta:
        model = CSCUser


class StudentInfoAdmin(admin.StackedInline):
    model = StudentInfo
    fk_name = 'student'
    readonly_fields = ['comment_changed', 'comment_last_author']


class CSCUserAdmin(AdminImageMixin, UbereditorMixin, UserAdmin):
    form = CSCUserChangeForm
    add_form = CSCUserCreationForm
    ordering = ['last_name', 'first_name']
    inlines = [StudentInfoAdmin]

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ['last_name', 'first_name', 'patronymic',
                                      'photo', 'note', 'enrollment_year',
                                      'graduation_year',
                                      'csc_review']}),
        ('Permissions', {'fields': ['is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions']}),
        ('External services', {'fields': ['yandex_id', 'stepic_id']}),
        ('Important dates', {'fields': ['last_login', 'date_joined']})]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for instance in instances:
            if isinstance(instance, StudentInfo):
                instance.save(edit_author=request.user)
            else:
                instance.save()


admin.site.register(CSCUser, CSCUserAdmin)
