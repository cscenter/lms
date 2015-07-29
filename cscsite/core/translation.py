from modeltranslation.translator import register, TranslationOptions
from .models import City


@register(City)
class CityTranslationOptions(TranslationOptions):
    fields = ('name',)
    fallback_values = '-- sorry, no translation provided --'
