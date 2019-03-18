from modeltranslation.decorators import register
from modeltranslation.translator import TranslationOptions

from courses.models import MetaCourse, Course


@register(MetaCourse)
class MetaCourseTranslationOptions(TranslationOptions):
    fields = ('name', 'description', 'short_description')


@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = ('description',)
