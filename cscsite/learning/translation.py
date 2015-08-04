from modeltranslation.translator import register, TranslationOptions
from .models import Course, CourseOffering


@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
    fallback_values = '-- sorry, no translation provided --'


@register(CourseOffering)
class CourseOfferingTranslationOptions(TranslationOptions):
    fields = ('description',)
