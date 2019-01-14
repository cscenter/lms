
from django.conf import settings
from import_export import resources, fields, widgets

from learning.projects.models import ProjectStudent


class CityWidget(widgets.Widget):
    def render(self, value, obj=None):
        """Don't forget to `select_related` city_id"""
        return str(settings.CITIES.get(value.project.city_id, value))


class ProjectStudentAdminRecordResource(resources.ModelResource):
    semester = fields.Field(column_name='Семестр',
                            attribute='project__semester')
    city = fields.Field(column_name='Город', attribute='project__city_id',
                        widget=CityWidget)
    project = fields.Field(column_name='Проект', attribute='project')
    student = fields.Field(column_name='Студент', attribute='student')
    total_score = fields.Field(column_name='Суммарный балл',
                               attribute='total_score')
    final_grade = fields.Field(column_name='Финальная оценка',
                               attribute='get_final_grade_display')
    report_score = fields.Field(column_name='Балл за отчет',
                                attribute='report__final_score')
    presentation_grade = fields.Field(column_name='Оценка за презентацию',
                                      attribute='presentation_grade')
    supervisor_grade = fields.Field(column_name='Оценка руководителя',
                                    attribute='supervisor_grade')
    is_external = fields.Field(column_name='Внешний проект',
                               attribute='project__get_is_external_display')

    class Meta:
        model = ProjectStudent
        skip_unchanged = True
        fields = [
            "semester",
            "student",
            "project",
            "total_score",
            "final_grade",
            "report_score",
            "presentation_grade",
            "supervisor_grade",
            "is_external",
            "city",
        ]
        export_order = fields
