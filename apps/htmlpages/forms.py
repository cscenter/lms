from django import forms
from django.conf import settings
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from htmlpages.models import HtmlPage


class HtmlpageForm(forms.ModelForm):
    url = forms.RegexField(label=_("URL"), max_length=100, regex=r'^[-\w/\.~]+$',
        help_text=_("Example: '/about/contact/'. Make sure to have leading"
                    " and trailing slashes."),
        error_messages={
            "invalid": _("This value must contain only letters, numbers,"
                         " dots, underscores, dashes, slashes or tildes."),
        },
    )

    class Meta:
        model = HtmlPage
        fields = '__all__'

    def clean_url(self):
        url = self.cleaned_data['url']
        if not url.startswith('/'):
            raise forms.ValidationError(
                gettext("URL is missing a leading slash."),
                code='missing_leading_slash',
            )
        if (settings.APPEND_SLASH and
                'django.middleware.common.CommonMiddleware' in settings.MIDDLEWARE and
                not url.endswith('/')):
            raise forms.ValidationError(
                gettext("URL is missing a trailing slash."),
                code='missing_trailing_slash',
            )
        return url

    def clean(self):
        url = self.cleaned_data.get('url', None)
        sites = self.cleaned_data.get('sites', None)

        same_url = HtmlPage.objects.filter(url=url)
        if self.instance.pk:
            same_url = same_url.exclude(pk=self.instance.pk)

        if sites and same_url.filter(sites__in=sites).exists():
            for site in sites:
                if same_url.filter(sites=site).exists():
                    raise forms.ValidationError(
                        _('Htmlpage with url %(url)s already exists for site %(site)s'),
                        code='duplicate_url',
                        params={'url': url, 'site': site},
                    )

        return super(HtmlpageForm, self).clean()
