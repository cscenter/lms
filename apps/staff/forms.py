import csv
import datetime
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Row, Submit

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.urls import reverse
from core.widgets import DateInputTextWidget
from users.models import User, StudentProfile


class GraduationForm(forms.Form):
    graduated_on = forms.DateField(
        label=_("Date of Graduation"),
        widget=DateInputTextWidget(attrs={'class': 'datepicker'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Div('graduated_on', css_class="col-xs-4"),
            ),
            FormActions(Submit('submit', 'Сгенерировать профили'))
        )


class MergeUsersForm(forms.Form):
    major_email = forms.EmailField(
        label=_("Major User email")
    )
    minor_email = forms.EmailField(
        label=_("Minor User email")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_action = reverse("staff:merge_users")
        self.helper.layout = Layout(
            Row(
                Div('major_email', css_class="col-xs-4"),
                Div('minor_email', css_class="col-xs-4"),
            ),
            FormActions(Submit('submit', _('Merge Users'),
                               onclick="return confirm('Вы уверены? Это действие нельзя обратить');"))
        )

    def clean_major_email(self):
        major_email = self.cleaned_data.get('major_email')
        if not User.objects.filter(email__iexact=major_email).exists():
            raise ValidationError(_("There is no User with this email"))
        return major_email

    def clean_minor_email(self):
        minor_email = self.cleaned_data.get('minor_email')
        if not User.objects.filter(email__iexact=minor_email).exists():
            raise ValidationError(_("There is no User with this email"))
        return minor_email

    def clean(self):
        major_email = self.cleaned_data.get('major_email')
        minor_email = self.cleaned_data.get('minor_email')
        if major_email == minor_email:
            raise ValidationError(_("Emails must not be the same"))

class BadgeNumberFromCSVForm(forms.Form):
    csv_file = forms.FileField(label=_('CSV file'), required=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_action = reverse("staff:badge_number_from_csv")
        self.helper.layout = Layout(
            Row(
                Div('csv_file', css_class="col-xs-4"),
            ),
            FormActions(Submit('submit', _('Fill in badge numbers')))
        )

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
        except Exception as e:
            raise ValidationError(_(f"File read error: {str(e)}"))
        
        headers = reader.fieldnames
        required_columns = {"Почта", "Номер пропуска"}
        if not required_columns.issubset(set(headers)):
            raise ValidationError(_('CSV file must contain "Email" and "Badge number" columns'))
        csv_file.seek(0)
        return csv_file


class ExportForDiplomas(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get all years where there are graduates
        self.graduated_years = self.get_graduated_years()
        year_choices = [(year, str(year)) for year in self.graduated_years]
        
        self.fields['graduated_year'] = forms.ChoiceField(
            label=_("Year of Graduation"),
            choices=year_choices
        )
        
        self.helper = FormHelper(self)
        self.helper.form_action = reverse("staff:export_for_electronic_diplomas")
        self.helper.layout = Layout(
            Row(
                Div('graduated_year', css_class="col-xs-4"),
            ),
            FormActions(Submit('submit', _('Dowload CSV')))
        )

    def get_graduated_years(self):
        """
        Get all years in which there are graduates.
        """
        # Get distinct year_of_curriculum values from StudentProfile
        # Optimize by only selecting the year_of_curriculum field and filtering by site
        current_year = datetime.datetime.now().year
        curriculum_years = StudentProfile.objects.filter(
            year_of_curriculum__isnull=False, 
            year_of_curriculum__lte=current_year-2,
            status=""
        ).values('year_of_curriculum').distinct().values_list('year_of_curriculum', flat=True)
        
        return sorted([year + 2 for year in curriculum_years], reverse=True)

    def clean(self):
        try:
            graduated_year = int(self.cleaned_data.get('graduated_year'))
            if graduated_year not in self.graduated_years:
                raise ValidationError(_("Not supported graduation year"))
        except (ValueError, TypeError):
            raise ValidationError(_("Invalid year format"))
