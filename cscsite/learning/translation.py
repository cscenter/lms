from modeltranslation.translator import register, TranslationOptions

from learning.models import AreaOfStudy
from courses.models import MetaCourse, Course


@register(MetaCourse)
class MetaCourseTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
    fallback_values = '-- sorry, no translation provided --'


@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = ('description',)


@register(AreaOfStudy)
class AreaOfStudyTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
