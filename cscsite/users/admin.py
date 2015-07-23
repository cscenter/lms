# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from sorl.thumbnail.admin import AdminImageMixin
from import_export import resources, fields, widgets
from import_export.admin import ImportExportModelAdmin


from core.admin import UbereditorMixin
from learning.constants import GRADES, SEMESTER_TYPES
from .models import CSCUser, CSCUserReference, \
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


# Customize widgets
class GradeWidget(widgets.Widget):
    MAPPING = {v.lower(): k for k, v in GRADES._display_map.iteritems()}

    def clean(self, value):
        if value in self.MAPPING:
            return self.MAPPING[value]

        raise NotImplementedError('Undefinded GradeWidget MAPPING value' +
                                   unicode(value))

    def render(self, value):
        for k, v in self.MAPPING.iteritems():
            if value == v:
                return k


class SemesterWidget(widgets.Widget):
    MAPPING = {v.lower(): k for k, v in SEMESTER_TYPES._display_map.iteritems()}

    def clean(self, value):
        from learning.models import Semester
        data = value.split()
        if len(data) != 2:
            raise NotImplementedError('Undefinded SemesterWidget value')
        type, year = data
        if type in self.MAPPING:
            type = self.MAPPING[type]
        return Semester.objects.get(type=type, year=year).pk


    def render(self, value):
        # TODO: not implemented for export
        return value


class SHADCourseRecordResource(resources.ModelResource):
    student_id = fields.Field(column_name='student_id', attribute='student',
                           widget=widgets.ForeignKeyWidget(CSCUser))
    grade = fields.Field(column_name='grade', attribute='grade',
                           widget=GradeWidget())
    semester = fields.Field(column_name='semester', attribute='semester_id',
                           widget=SemesterWidget())

    class Meta:
        model = SHADCourseRecord
        fields = ('id', 'student_id', 'name', 'teachers', 'semester', 'grade')
        skip_unchanged = True

    def get_instance(self, instance_loader, row):
        """Allow import when id column not specified"""
        import_ids = self.get_import_id_fields()
        if set(import_ids).issubset(row.keys()):
            return instance_loader.get_instance(row)
        return False


class SHADCourseRecordResourceAdmin(ImportExportModelAdmin):
    resource_class = SHADCourseRecordResource
    pass


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
                                       'groups', 'user_permissions']}),
        (_('External services'), {'fields': ['yandex_id', 'stepic_id']}),
        (_('Student info record'),
         {'fields': ['status', 'study_programs', 'university',
                     'workplace', 'uni_year_at_enrollment', 'phone',
                     'comment', 'comment_changed_at', 'comment_last_author']}),
        (_('Important dates'), {'fields': ['last_login', 'date_joined']})]

    def save_model(self, request, obj, form, change):
        obj.save(edit_author=request.user)

admin.site.register(CSCUser, CSCUserAdmin)
admin.site.register(CSCUserReference)
admin.site.register(SHADCourseRecord, SHADCourseRecordResourceAdmin)
