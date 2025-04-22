import csv
from datetime import datetime
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Row, Submit, Fieldset, Column
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.urls import reverse
from core.widgets import DateInputTextWidget
from learning.settings import StudentStatuses
from staff.utils import get_academic_discipline_choices, get_admission_year_choices, get_branche_choices, get_curriculum_year_choices, get_email_template_choices
from users.models import User, StudentTypes, StudentProfile


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
        self.request = kwargs.pop('request')
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
        current_year = timezone.now().year
            
        curriculum_years = StudentProfile.objects.filter(
            site=self.request.site,
            year_of_curriculum__lte=current_year-2,
            status=""
        ).distinct('year_of_curriculum').values_list('year_of_curriculum', flat=True)
        
        return sorted([year + 2 for year in curriculum_years], reverse=True)

    def clean(self):
        try:
            graduated_year = int(self.cleaned_data.get('graduated_year'))
            if graduated_year not in self.graduated_years:
                raise ValidationError(_("Not supported graduation year"))
        except (ValueError, TypeError):
            raise ValidationError(_("Invalid year format"))
    

class ConfirmSendLettersForm(forms.Form):
    """
    Form for confirming email sending.
    This form is used to display the confirmation page and handle the confirmation/cancellation.
    """
    email_template_id = forms.CharField(widget=forms.HiddenInput())
    scheduled_time = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    # These fields are just for display, not for actual form submission
    base_info_display = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly', 
            'style': 'border: none; background-color: #f8f9fa; font-weight: bold; font-size: 1.2em; padding: 10px; border-radius: 5px;'
        })
    )
    filter_description_display = forms.CharField(
        label=_("Filters"),
        required=False,
        initial="",
        widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': 5, 'style': 'border: none; background-color: #f8f9fa; height: 150px;'})
    )
    recipients_display = forms.CharField(
        label=_("Recipients"),
        required=False,
        widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': 10, 'style': 'border: none; background-color: #f8f9fa;'})
    )
    template_display = forms.CharField(
        label=_("Template"),
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'style': 'border: none; background-color: #f8f9fa;'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper(self)
        self.helper.form_action = reverse("staff:send_letters")

        self.helper.layout = Layout(
            
            Fieldset(_('Confirmation'),
                Row(
                    Div('base_info_display', css_class="col-xs-12"),
                ),
                Row(
                    Div('filter_description_display', css_class="col-xs-12"),
                ),
                Row(
                    Div('recipients_display', css_class="col-xs-12"),
                ),
                Row(
                    Div('template_display', css_class="col-xs-12"),
                ),
                # Hidden fields
                'email_template_id',
                'scheduled_time',
            ),
            Row(
                Column(
                    FormActions(
                        Submit('confirm_send', _('Confirm and Send'), css_class='btn-primary'),
                    ),
                    css_class='col-md-3'
                ),
                Column(
                    FormActions(
                        Submit('cancel_send', _('Cancel'), css_class='btn-secondary', formmethod='post'),
                    ),
                    css_class='col-md-2'
                ),
            )
        )
    
    def get_emails(self):
        """
        Get all emails from the form.
        """
        if self.cleaned_data.get('recipients_display'):
            return [email.strip() for email in self.cleaned_data['recipients_display'].split('\n') if email.strip()]


class SendLettersForm(forms.Form):
    branch = forms.MultipleChoiceField(
        label=_("Branch"),
        widget=forms.CheckboxSelectMultiple,
        choices=get_branche_choices,
        required=False
    )
    type = forms.MultipleChoiceField(
        label=_("Student type"),
        widget=forms.CheckboxSelectMultiple,
        choices=StudentTypes.choices,
        required=False
    )
    year_of_admission = forms.MultipleChoiceField(
        label=_("Admission year"),
        widget=forms.CheckboxSelectMultiple,
        choices=get_admission_year_choices,
        required=False
    )
    year_of_curriculum = forms.MultipleChoiceField(
        label=_("Curriculum year"),
        widget=forms.CheckboxSelectMultiple,
        choices=get_curriculum_year_choices,
        required=False
    )
    status = forms.MultipleChoiceField(
        label=_("Status"),
        widget=forms.CheckboxSelectMultiple,
        choices=(("studying", _("Studying")),) + StudentStatuses.choices,
        required=False
    )
    academic_disciplines = forms.MultipleChoiceField(
        label=_("Fields of study"),
        widget=forms.CheckboxSelectMultiple,
        choices=get_academic_discipline_choices,
        required=False
    )
    email_template = forms.ChoiceField(
        label=_("Email template"),
        choices=get_email_template_choices,
        required=True
    )
    test_email = forms.EmailField(
        label=_("Test email"),
        required=False
    )
    scheduled_time = forms.DateTimeField(
        label=_("Schedule sending time"),
        required=False,
        # Initial value will be set in __init__
    )
    action = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time:
            if scheduled_time <= timezone.now():
                scheduled_time = None
            elif not timezone.is_naive(scheduled_time):
                naive_dt = datetime(
                    scheduled_time.year, scheduled_time.month, scheduled_time.day,
                    scheduled_time.hour, scheduled_time.minute
                )
                scheduled_time = self.tz.localize(naive_dt)
            else:
                scheduled_time = timezone.make_aware(scheduled_time, self.tz)
        
        return scheduled_time
    
    def clean_status(self):
        """Convert 'studying' back to empty string."""
        statuses = self.cleaned_data.get('status', [])
        return ["" if s == "studying" else s for s in statuses]
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        self.tz = self.request.user.time_zone if self.request.user.time_zone else settings.DEFAULT_TIMEZONE
        local_time = timezone.localtime(timezone.now(), self.tz)
        self.fields['scheduled_time'].initial = local_time.strftime('%d.%m.%Y %H:%M')
        self.fields['scheduled_time'].help_text = f"Временная зона {getattr(self.tz, 'zone', str(self.tz))} {datetime.now(self.tz).strftime('%z')[:3]}"
        
        self.helper = FormHelper(self)
        self.helper.form_action = reverse("staff:confirm_send_letters")
        self.helper.layout = Layout(
            Fieldset(_('Filters'),
                Row(
                    Div('branch', css_class="col-xs-4"),
                    Div('year_of_admission', css_class="col-xs-4"),
                    Div('year_of_curriculum', css_class="col-xs-4"),
                ),
                Row(
                    Div('type', css_class="col-xs-4"),
                    Div('status', css_class="col-xs-4"),
                    Div('academic_disciplines', css_class="col-xs-4"),
                ),
            ),
            Row(
                Column(
                    Fieldset(_('Testing letter'),
                        Row(
                            Div('test_email', css_class="col-xs-12"),
                        ),
                        FormActions(Submit('submit_test', _('Send for testing')))
                    ),
                    css_class="col-md-6"
                ),
                Column(
                    Fieldset(_('Sending letter'),
                        Row(
                            Div('email_template', css_class="col-xs-12"),
                        ),
                        Row(
                            Div('scheduled_time', css_class="col-xs-12"),
                        ),
                        FormActions(Submit('submit_send', _('Ready to send')))
                    ),
                    css_class="col-md-6"
                )
            )
        )
