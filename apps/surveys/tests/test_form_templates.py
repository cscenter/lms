import json

import pytest
from bs4 import BeautifulSoup

from surveys.forms import FormBuilder
from surveys.templatetags.form_utils import render_form
from surveys.tests.factories import FieldFactory, CourseSurveyFactory


@pytest.mark.django_db
def test_form_field_conditional_logic_escaping():
    # Conditional logic object should contain "scope": "field" to be rendered
    conditional_logic = [
        {
            "action_type": "show",
            "rules": [],
            "scope": "field"
        }
    ]

    field = FieldFactory(conditional_logic=conditional_logic)
    survey = CourseSurveyFactory()
    survey.form.fields.add(field)
    form = FormBuilder(survey)
    rendered_form = render_form(form)

    field_div = BeautifulSoup(rendered_form, "html.parser").find("div")
    field_data_logic = json.loads(field_div.get("data-logic"))
    assert field_data_logic == conditional_logic