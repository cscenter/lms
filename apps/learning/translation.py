from modeltranslation.decorators import register
from modeltranslation.translator import TranslationOptions

from learning.models import StudentGroup


@register(StudentGroup)
class StudentGroupTranslationOptions(TranslationOptions):
    fields = ('name',)
