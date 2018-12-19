from django import forms
from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, \
    Button, Div, HTML
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from core.exceptions import Redirect
from core.forms import GradeField
from core.utils import is_club_site
from core.widgets import UbereditorWidget
from core.models import LATEX_MARKDOWN_ENABLED
from .models import AssignmentComment
from courses.models import Course

DROP_ATTACHMENT_LINK = """\
<a href="{0}"><i class="fa fa-trash-o"></i>&nbsp;{1}</a>"""
CANCEL_BUTTON = Button('cancel', _('Cancel'),
                       onclick='history.go(-1);',
                       css_class="btn btn-default")
SUBMIT_BUTTON = Submit('save', _('Save'))
CANCEL_SAVE_PAIR = Div(CANCEL_BUTTON, SUBMIT_BUTTON, css_class="pull-right")


class CourseEnrollmentForm(forms.Form):
    reason = forms.CharField(
        label=_("Почему вы выбрали этот курс?"),
        widget=forms.Textarea(),
        required=False)

    def __init__(self, request, course: Course, **kwargs):
        self.course = course
        self.request = request
        self._custom_errors = None
        super().__init__(**kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit('enroll', 'Записаться на курс'))

    def is_available(self):
        from learning.views.utils import get_student_city_code
        if self._custom_errors is not None:
            return not self._custom_errors
        self._custom_errors = []
        if not self.course.enrollment_is_open:
            error = ValidationError("Course enrollment should be active",
                                    code="deadline")
            self._custom_errors.append(error)
        if is_club_site() and not self.course.is_open:
            error = ValidationError("Club students can't enroll on center "
                                    "courses", code="permissions")
            self._custom_errors.append(error)
        city_code = get_student_city_code(self.request)
        if (not self.course.is_correspondence
                and city_code != self.course.get_city()):
            error = ValidationError("Students can enroll in on courses only "
                                    "from their city", code="permissions")
            self._custom_errors.append(error)
        # Reject if capacity limited and no places available
        # XXX: Race condition. Should be placed in save method
        if self.course.is_capacity_limited:
            if not self.course.places_left:
                msg = _("No places available, sorry")
                messages.error(self.request, msg, extra_tags='timeout')
                raise Redirect(to=self.course.get_absolute_url())
        return not self._custom_errors


class AssignmentCommentForm(forms.ModelForm):
    text = forms.CharField(
        label=_("Add comment"),
        help_text=_(LATEX_MARKDOWN_ENABLED),
        required=False,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true',
                                 'data-local-persist': 'true'}))
    attached_file = forms.FileField(
        label="",
        required=False,
        widget=forms.FileInput)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('text'),
            Div(Div('attached_file',
                    Div(Submit('save', _('Save')),
                        css_class='pull-right'),
                    css_class="form-inline"),
                css_class="form-group"))
        super(AssignmentCommentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = AssignmentComment
        fields = ['text', 'attached_file']

    def clean(self):
        cleaned_data = super(AssignmentCommentForm, self).clean()
        if (not cleaned_data.get("text")
                and not cleaned_data.get("attached_file")):
            raise forms.ValidationError(
                _("Either text or file should be non-empty"))

        return cleaned_data


class AssignmentModalCommentForm(forms.ModelForm):
    text = forms.CharField(
        label="",
        help_text=_(LATEX_MARKDOWN_ENABLED),
        required=False,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true'}))

    class Meta:
        model = AssignmentComment
        fields = ['text']

    def __init__(self, *args, **kwargs):
        super(AssignmentModalCommentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean(self):
        cleaned_data = super(AssignmentModalCommentForm, self).clean()
        if not cleaned_data.get("text"):
            raise forms.ValidationError(_("Text should be non-empty"))
        return cleaned_data


class AssignmentScoreForm(forms.Form):
    score = GradeField(required=False, label="")

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Hidden('grading_form', 'true'),
                Field('score', css_class='input-grade'),
                HTML("/" + str(kwargs.get('maximum_score'))),
                HTML("&nbsp;&nbsp;"),
                StrictButton('<i class="fa fa-floppy-o"></i>',
                             css_class="btn-primary",
                             type="submit"),
                css_class="form-inline"))
        if 'maximum_score' in kwargs:
            self.maximum_score = kwargs['maximum_score']
            self.helper['score'].update_attributes(max=self.maximum_score)
            del kwargs['maximum_score']
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score', None)
        if score and score > self.maximum_score:
            msg = _("Score can't be larger than maximum one ({0})")
            raise forms.ValidationError(msg.format(self.maximum_score))
        return cleaned_data
