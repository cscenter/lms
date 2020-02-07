from modeltranslation.translator import register, TranslationOptions
from .models import City, Branch


@register(City)
class CityTranslationOptions(TranslationOptions):
    fields = ('name', 'abbr',)
    fallback_values = '-- sorry, no translation provided --'


@register(Branch)
class BranchTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = ('ru', 'en')

