from django import forms

from surveys.widgets import SurveyFreeAnswer, OptionalChoiceWidget, \
    SurveyCheckboxSelectMultiple


class SurveyChoiceField(forms.ChoiceField):
    def __init__(self, *, free_answer=None, default=None, **kwargs):
        super().__init__(**kwargs)
        self.free_answer = free_answer
        self.default = default


class SurveyMultipleChoiceField(forms.MultipleChoiceField):
    widget = SurveyCheckboxSelectMultiple

    def __init__(self, *, free_answer=None, default=None, **kwargs):
        super().__init__(**kwargs)
        self.free_answer = free_answer
        self.default = default


class SurveyFreeAnswerField(forms.CharField):
    widget = SurveyFreeAnswer


class SurveyMultipleChoiceFreeAnswerField(forms.MultiValueField):
    def __init__(self, choices, **kwargs):
        """
        Sets the two fields as not required but will enforce that (at least)
        one is set in compress
        """
        fields = (SurveyMultipleChoiceField(choices=choices, required=False),
                  SurveyFreeAnswerField(required=False))
        self.widget = OptionalChoiceWidget(widgets=[f.widget for f in fields])
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list):
        return data_list
