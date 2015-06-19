from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from sorl.thumbnail.admin import AdminImageMixin

from core.admin import UbereditorMixin
from users.models import CSCUser, CSCUserReference, \
    OnlineCourseRecord, SHADCourseRecord


class CSCUserCreationForm(UserCreationForm):
    # FIXME (Sergey Zh): Guess this Meta class has no effect!
    class Meta:
        model = CSCUser
        fields = ('username',)
        error_messages = {
            'duplicate_username': _("Username must be unique"),
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            self._meta.model._default_manager.get(username=username)
        except self._meta.model.DoesNotExist:
            return username
        raise ValidationError(self.Meta.error_messages["duplicate_username"])


class CSCUserChangeForm(UserChangeForm):
    class Meta:
        fields = '__all__'
        model = CSCUser


class OnlineCourseRecordAdmin(admin.StackedInline):
    model = OnlineCourseRecord


class SHADCourseRecordAdmin(admin.StackedInline):
    model = SHADCourseRecord


class CSCUserAdmin(AdminImageMixin, UbereditorMixin, UserAdmin):
    form = CSCUserChangeForm
    add_form = CSCUserCreationForm
    change_form_template = 'loginas/change_form.html'
    ordering = ['last_name', 'first_name']
    inlines = [OnlineCourseRecordAdmin, SHADCourseRecordAdmin]
    readonly_fields = ['comment_changed_at', 'comment_last_author',
                       'last_login', 'date_joined']

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {'fields': ['last_name', 'first_name', 
                                         'patronymic', 'gender',
                                         'photo', 'note', 'enrollment_year',
                                         'graduation_year',
                                         'csc_review']}),
        (_('Permissions'), {'fields': ['is_active', 'is_staff', 'is_superuser',
                                       'groups', 'is_center_student',
                                       'user_permissions']}),
        (_('External services'), {'fields': ['yandex_id', 'stepic_id']}),
        (_('Student info record'),
         {'fields': ['nondegree', 'status', 'study_programs', 'university',
                     'workplace', 'uni_year_at_enrollment', 'phone',
                     'comment', 'comment_changed_at', 'comment_last_author']}),
        (_('Important dates'), {'fields': ['last_login', 'date_joined']})]

    def save_model(self, request, obj, form, change):
        obj.save(edit_author=request.user)


admin.site.register(CSCUser, CSCUserAdmin)
admin.site.register(CSCUserReference)
