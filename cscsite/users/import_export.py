# -*- coding: utf-8 -*-

import string
import random

from django.db.models import Q
from import_export import resources, fields, widgets

from learning.settings import GRADES, SEMESTER_TYPES
from .models import CSCUser, SHADCourseRecord


# Customize widgets
class GradeWidget(widgets.Widget):
    MAPPING = {v.lower(): k for k, v in GRADES._display_map.items()}

    def clean(self, value, row=None, *args, **kwargs):
        if value in self.MAPPING:
            return self.MAPPING[value]
        raise NotImplementedError(f'Undefinded GradeWidget MAPPING '
                                  f'value {value}')

    def render(self, value, obj=None):
        for k, v in self.MAPPING.items():
            if value == v:
                return k


class SemesterWidget(widgets.Widget):
    MAPPING = {v.lower(): k for k, v in SEMESTER_TYPES._display_map.items()}

    def clean(self, value, row=None, *args, **kwargs):
        from learning.models import Semester
        data = value.split()
        if len(data) != 2:
            raise NotImplementedError('Undefinded SemesterWidget value')
        type, year = data
        if type in self.MAPPING:
            type = self.MAPPING[type]
        return Semester.objects.get(type=type, year=year).pk

    def render(self, value, obj=None):
        # TODO: not implemented for export
        return value


class ImportWithEmptyIdMixin(object):
    def get_instance(self, instance_loader, row):
        """Allow import when id column not specified"""
        import_ids = self.get_import_id_fields()
        if set(import_ids).issubset(row.keys()):
            return instance_loader.get_instance(row)
        return False


class SHADCourseRecordResource(ImportWithEmptyIdMixin, resources.ModelResource):
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


class UserCourseWidget(widgets.Widget):
    MAPPING = {v.lower(): k for k, v in CSCUser.COURSES._display_map.items()}

    def clean(self, value):
        # Replace non-breaking space and tabs with common white space
        value  = value.replace(u'\xa0', u' ')
        if value in self.MAPPING:
            return self.MAPPING[value]
        raise ValueError('UserCourseWidget: undefinded value ' + unicode(value))

    def render(self, value):
        return value


class UserEmailWidget(widgets.Widget):
    def clean(self, value):
        # Check email and username are unique
        if '@' not in value:
            raise ValueError('Wrong email?')
        username = value.split('@')[0]
        if CSCUser.objects.filter(Q(email=value) | Q(username=username)).count():
            raise ValueError('UserEmailWidget: not inique email or username ')
        return value

    def render(self, value):
        return value


class UserGenderWidget(widgets.Widget):
    def clean(self, value):
        if "м" in value:
            value = "M"
        if "ж" in value:
            value = "F"
        if value not in ["M", "F"]:
            value = ""
        return value

    def render(self, value):
        return value


class CSCUserRecordResource(ImportWithEmptyIdMixin, resources.ModelResource):
    uni_year_at_enrollment = fields.Field(column_name='uni_year_at_enrollment',
                                          attribute='uni_year_at_enrollment',
                                          widget=UserCourseWidget())
    email = fields.Field(column_name='email', attribute='email',
                         widget=UserEmailWidget())

    gender = fields.Field(column_name='gender', attribute='gender',
                          widget=UserGenderWidget())

    class Meta:
        model = CSCUser
        fields = (
            'id', 'username', 'first_name', 'patronymic', 'last_name',
            'email', 'university', 'uni_year_at_enrollment', 'phone',
            'yandex_id', 'stepic_id', 'gender', 'note',
        )
        skip_unchanged = True
        import_id_fields = ['id', 'email']

    def before_save_instance(self, instance, dry_run):
        if not instance.username:
            instance.username = instance.email.split('@')[0]
        raw_password = ''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.digits) for _ in range(10))
        instance.set_password(raw_password)
