from modeltranslation.translator import register, TranslationOptions

from study_programs.models import AcademicDiscipline


@register(AcademicDiscipline)
class AcademicDisciplineTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
