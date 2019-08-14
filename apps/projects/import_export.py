
from django.conf import settings
from import_export import resources, fields, widgets

from projects.models import ProjectStudent


class ProjectStudentAdminRecordResource(resources.ModelResource):
    semester = fields.Field(column_name='Семестр',
                            attribute='project__semester')
    branch = fields.Field(column_name='Отделение',
                          attribute='project__branch')
    project = fields.Field(column_name='Проект', attribute='project')
    student = fields.Field(column_name='Студент', attribute='student')
    total_score = fields.Field(column_name='Суммарный балл',
                               attribute='total_score')
    final_grade = fields.Field(column_name='Финальная оценка',
                               attribute='get_final_grade_display')
    presentation_grade = fields.Field(column_name='Оценка за презентацию',
                                      attribute='presentation_grade')
    supervisor_grade = fields.Field(column_name='Оценка руководителя',
                                    attribute='supervisor_grade')
    is_external = fields.Field(column_name='Внешний проект',
                               attribute='project__get_is_external_display')

    class Meta:
        model = ProjectStudent
        skip_unchanged = True
        fields = (
            "semester",
            "student",
            "project",
            "total_score",
            "final_grade",
            "presentation_grade",
            "supervisor_grade",
            "is_external",
            "branch",
        )
        export_order = fields

