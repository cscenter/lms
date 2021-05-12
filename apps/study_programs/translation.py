from modeltranslation.translator import TranslationOptions, register

from study_programs.models import AcademicDiscipline


@register(AcademicDiscipline)
class AcademicDisciplineTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
