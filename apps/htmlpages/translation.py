from modeltranslation.translator import TranslationOptions, register

from .models import HtmlPage


@register(HtmlPage)
class HtmlPagesTranslationOptions(TranslationOptions):
    fields = ('title', 'content',)
    fallback_values = '-- sorry, no translation provided --'
