from modeltranslation.translator import register, TranslationOptions

from learning.models import AreaOfStudy
from .models import MetaCourse, CourseOffering


@register(MetaCourse)
class CourseTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
    fallback_values = '-- sorry, no translation provided --'


@register(CourseOffering)
class CourseOfferingTranslationOptions(TranslationOptions):
    fields = ('description',)


@register(AreaOfStudy)
class AreaOfStudyTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
