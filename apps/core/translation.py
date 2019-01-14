from modeltranslation.translator import register, TranslationOptions
from .models import City


@register(City)
class CityTranslationOptions(TranslationOptions):
    fields = ('name', 'abbr',)
    fallback_values = '-- sorry, no translation provided --'
