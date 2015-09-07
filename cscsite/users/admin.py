# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from sorl.thumbnail.admin import AdminImageMixin
from import_export.admin import ImportExportMixin, ImportMixin

from core.admin import UbereditorMixin
from .models import CSCUser, CSCUserReference, \
    OnlineCourseRecord, SHADCourseRecord
from .import_export import SHADCourseRecordResource, CSCUserRecordResource


class CSCUserCreationForm(UserCreationForm):
    # FIXME (Sergey Zh): Guess this Meta class has no effect?
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

    def clean(self):
        cleaned_data = super(CSCUserChangeForm, self).clean()
        enrollment_year = cleaned_data.get('enrollment_year')
        groups = [x.pk for x in cleaned_data.get('groups', [])]
        if self.instance.group_pks.STUDENT_CENTER in groups \
           and enrollment_year is None:
            self.add_error('enrollment_year', ValidationError(
                _("CSCUser|enrollment year should be provided for students")))

        if self.instance.group_pks.VOLUNTEER in groups \
           and enrollment_year is None:
            self.add_error('enrollment_year', ValidationError(
                _("CSCUser|enrollment year should be provided for volunteers")))

        graduation_year = cleaned_data.get('graduation_year')
        if self.instance.group_pks.GRADUATE_CENTER in groups \
           and graduation_year is None:
            self.add_error('graduation_year', ValidationError(
                _("CSCUser|graduation year should be provided for graduates")))


class OnlineCourseRecordAdmin(admin.StackedInline):
    model = OnlineCourseRecord


class SHADCourseRecordAdmin(admin.StackedInline):
    model = SHADCourseRecord


class CSCUserAdmin(AdminImageMixin, UbereditorMixin, UserAdmin):
    form = CSCUserChangeForm
    add_form = CSCUserCreationForm
    change_form_template = 'admin/user_change_form.html'
    ordering = ['last_name', 'first_name']
    inlines = [OnlineCourseRecordAdmin, SHADCourseRecordAdmin]
    readonly_fields = ['comment_changed_at', 'comment_last_author',
                       'last_login', 'date_joined']
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 
        'is_staff')

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {'fields': ['last_name', 'first_name',
                                         'patronymic', 'gender',
                                         'photo', 'note', 'enrollment_year',
                                         'graduation_year',
                                         'csc_review']}),
        (_('Permissions'), {'fields': ['is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions']}),
        (_('External services'), {'fields': ['yandex_id', 'stepic_id']}),
        (_('Student info record'),
         {'fields': ['status', 'study_programs', 'university',
                     'workplace', 'uni_year_at_enrollment', 'phone',
                     'comment', 'comment_changed_at', 'comment_last_author']}),
        (_('Important dates'), {'fields': ['last_login', 'date_joined']})]

    def save_model(self, request, obj, form, change):
        obj.save(edit_author=request.user)


class SHADCourseRecordResourceAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SHADCourseRecordResource
    pass


class CSCUserRecordResourceAdmin(ImportMixin, CSCUserAdmin):
    resource_class = CSCUserRecordResource
    pass

admin.site.register(CSCUser, CSCUserRecordResourceAdmin)
admin.site.register(CSCUserReference)
admin.site.register(SHADCourseRecord, SHADCourseRecordResourceAdmin)
