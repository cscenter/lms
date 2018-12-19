from modeltranslation.translator import register, TranslationOptions

from learning.models import AreaOfStudy


@register(AreaOfStudy)
class AreaOfStudyTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
