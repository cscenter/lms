from modeltranslation.translator import TranslationOptions, register

from .models import Branch, City


@register(City)
class CityTranslationOptions(TranslationOptions):
    fields = ('name', 'abbr',)
    fallback_values = '-- sorry, no translation provided --'


@register(Branch)
class BranchTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = ('ru', 'en')
