from modeltranslation.translator import register, TranslationOptions

from study_programs.models import AreaOfStudy


@register(AreaOfStudy)
class AreaOfStudyTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
