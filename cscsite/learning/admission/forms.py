# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from core.views import ReadOnlyFieldsMixin
from learning.admission.models import Interview, Comment, Applicant


class InterviewCommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ["text", "score", "interview", "interviewer"]
        widgets = {
            'interview': forms.HiddenInput(),
            'interviewer': forms.HiddenInput(),
            'score': forms.Select(choices=(
                (-2, "Плох"),
                (-1, "Так себе"),
                (0, "Середина"),
                (1, "Хорош"),
                (2, "Отлично")))
        }

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('text', 'score'),
            Div(Submit('save', _('Save')), css_class="pull-right"))
        self.interviewer = kwargs.pop("interviewer", None)
        self.interview_id = kwargs.pop("interview_id", None)
        super(InterviewCommentForm, self).__init__(*args, **kwargs)

    def clean_interviewer(self):
        interviewer = self.cleaned_data['interviewer']
        if interviewer != self.interviewer:
            raise ValidationError(
                "You have permissions to create/update only own comments")
        return interviewer

    def clean_interview(self):
        interview = self.cleaned_data['interview']
        if str(interview.pk) != self.interview_id:
            raise ValidationError(
                "Submitted interview id not match GET-value")
        return interview


class ApplicantForm(ReadOnlyFieldsMixin, forms.ModelForm):
    readonly_fields = "__all__"

    class Meta:
        model = Applicant
        exclude = ("campaign", "first_name", "last_name", "second_name",
                   "status", "admin_note", "yandex_id_normalize")
