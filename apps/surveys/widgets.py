from django import forms


# FIXME: Хочется на весь сайт использовать эти виджеты, но не трогать админку

class SurveyTextarea(forms.Textarea):
    # template_name = 'surveys/forms/widgets/textarea.html'
    pass


class SurveyTextInput(forms.TextInput):
    # template_name = 'surveys/forms/widgets/text.html'
    pass


class SurveyNumberInput(forms.NumberInput):
    # template_name = 'surveys/forms/widgets/number.html'
    pass


class SurveyCheckboxInput(forms.CheckboxInput):
    # template_name = 'surveys/forms/widgets/checkbox.html'
    pass


class SurveyCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    # template_name = 'surveys/forms/widgets/checkbox_select.html'
    # option_template_name = 'surveys/forms/widgets/checkbox_option.html'
    pass


class SurveyRadioSelect(forms.RadioSelect):
    # template_name = 'surveys/forms/widgets/radio.html'
    # option_template_name = 'surveys/forms/widgets/radio_option.html'
    pass


class SurveyFreeAnswer(forms.Textarea):
    template_name = 'django/forms/widgets/free_answer.html'


class OptionalChoiceWidget(forms.MultiWidget):
    # template_name = 'surveys/forms/widgets/multiwidget.html'

    def decompress(self, value):
        return value if value else ["", ""]
