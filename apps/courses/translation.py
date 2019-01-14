from modeltranslation.decorators import register
from modeltranslation.translator import TranslationOptions

from courses.models import MetaCourse, Course


@register(MetaCourse)
class MetaCourseTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
    fallback_values = '-- sorry, no translation provided --'


@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = ('description',)
