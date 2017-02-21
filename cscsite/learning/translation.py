from modeltranslation.translator import register, TranslationOptions

from learning.models import AreaOfStudy
from .models import Course, CourseOffering


@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
    fallback_values = '-- sorry, no translation provided --'


@register(CourseOffering)
class CourseOfferingTranslationOptions(TranslationOptions):
    fields = ('description',)


@register(AreaOfStudy)
class AreaOfStudyTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
