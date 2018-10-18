import pytest

from surveys.constants import FieldType, STATUS_PUBLISHED
from surveys.factories import CourseOfferingSurveyFactory, FieldFactory, \
    FieldEntryFactory, FieldChoiceFactory
from surveys.forms import FormBuilder
from surveys.models import FormSubmission, FieldEntry
from surveys.reports import SurveySubmissionsReport


@pytest.mark.django_db
def test_field_model_to_export_value():
    field = FieldFactory(field_type=FieldType.CHECKBOX_MULTIPLE, choices=[])
    choices = FieldChoiceFactory.create_batch(5, field=field)
    field.refresh_from_db()
    assert field.choices.count() == len(choices)
    entries = [FieldEntryFactory(is_choice=True, field_id=field.pk,
                                 value=c.value)
               for c in choices[:2]]
    export_value = field.to_export_value(entries)
    assert export_value is not None
    assert len(export_value) == 2


@pytest.mark.django_db
def test_field_radio_button_to_db_value(rf):
    field = FieldFactory(field_type=FieldType.RADIO_MULTIPLE, choices=[])
    choices = FieldChoiceFactory.create_batch(5, field=field)
    first_choice = choices[0]
    # For testing `to_db_value` we should generate `cleaned_data`
    entry = FieldEntryFactory(field_id=field.pk, value=first_choice.value)
    survey = CourseOfferingSurveyFactory()
    survey.form.fields.add(field)
    request = rf.request()
    form = FormBuilder(survey, data=request.POST, instance=entry.submission)
    # Disable form field or it doesn't populate cleaned_data with initial value
    form.fields[field.name].disabled = True
    assert form.is_valid()
    cleaned_value = form.cleaned_data[field.name]
    db_value = field.to_db_value(cleaned_value)
    assert len(db_value) == 1
    v, is_choice = db_value[0]
    assert is_choice, "is_choice should be set for radio button value"
    assert v == first_choice.value


@pytest.mark.django_db
def test_field_text_to_db_value(rf):
    field = FieldFactory(field_type=FieldType.TEXTAREA)
    # For testing `to_db_value` we should generate `cleaned_data`
    entry = FieldEntryFactory(field_id=field.pk, value="value")
    survey = CourseOfferingSurveyFactory()
    survey.form.fields.add(field)
    request = rf.request()
    form = FormBuilder(survey, data=request.POST, instance=entry.submission)
    # Disable form field or it doesn't populate cleaned_data with initial value
    form.fields[field.name].disabled = True
    assert form.is_valid()
    cleaned_value = form.cleaned_data[field.name]
    db_value = field.to_db_value(cleaned_value)
    assert len(db_value) == 1
    v, is_choice = db_value[0]
    assert not is_choice
    assert v == "value"


@pytest.mark.django_db
def test_field_checkbox_to_db_value(rf):
    field = FieldFactory(field_type=FieldType.CHECKBOX_MULTIPLE, choices=[])
    choices = FieldChoiceFactory.create_batch(5, field=field)
    choice1, choice2, *_ = choices
    # For testing `to_db_value` we should generate `cleaned_data`
    entry = FieldEntryFactory(field_id=field.pk, value=choice1.value,
                              is_choice=True)
    FieldEntryFactory(field_id=field.pk, value=choice2.value,
                      submission=entry.submission, is_choice=True)
    survey = CourseOfferingSurveyFactory()
    survey.form.fields.add(field)
    request = rf.request()
    form = FormBuilder(survey, data=request.POST, instance=entry.submission)
    # Disable form field or it doesn't populate cleaned_data with initial value
    form.fields[field.name].disabled = True
    assert form.is_valid()
    cleaned_value = form.cleaned_data[field.name]
    db_value = field.to_db_value(cleaned_value)
    assert len(db_value) == 2
    assert all(is_choice for v, is_choice in db_value)
    values = set(v for v, _ in db_value)
    assert values == {choice1.value, choice2.value}


@pytest.mark.django_db
def test_field_checkbox_with_note_to_db_value(rf):
    field = FieldFactory(field_type=FieldType.CHECKBOX_MULTIPLE_WITH_NOTE,
                         choices=[])
    choices = FieldChoiceFactory.create_batch(5, field=field)
    choice1, choice2, *_ = choices
    # For testing `to_db_value` we should generate `cleaned_data`
    entry = FieldEntryFactory(field_id=field.pk, value=choice1.value,
                              is_choice=True)
    FieldEntryFactory(field_id=field.pk, value=choice2.value,
                      submission=entry.submission, is_choice=True)
    survey = CourseOfferingSurveyFactory()
    survey.form.fields.add(field)
    request = rf.request()
    form = FormBuilder(survey, data=request.POST, instance=entry.submission)
    # Disable form field or it doesn't populate cleaned_data with initial value
    form.fields[field.name].disabled = True
    assert form.is_valid()
    cleaned_value = form.cleaned_data[field.name]
    db_value = field.to_db_value(cleaned_value)
    assert len(db_value) == 2
    assert all(is_choice for v, is_choice in db_value)
    values = set(v for v, _ in db_value)
    assert values == {choice1.value, choice2.value}
    # Add note
    FieldEntryFactory(field_id=field.pk, value="note", is_choice=False,
                      submission=entry.submission)
    survey.refresh_from_db()
    form = FormBuilder(survey, data=request.POST, instance=entry.submission)
    # Disable form field or it doesn't populate cleaned_data with initial value
    form.fields[field.name].disabled = True
    assert form.is_valid()
    cleaned_value = form.cleaned_data[field.name]
    db_value = field.to_db_value(cleaned_value)
    assert len(db_value) == 3
    checkbox1, checkbox2, note = db_value
    v, is_choice = checkbox1
    assert is_choice
    assert v == choice1.value
    v, is_choice = checkbox2
    assert is_choice
    assert v == choice2.value
    v, is_choice = note
    assert not is_choice
    assert v == "note"


@pytest.mark.django_db
def test_smoke_survey_form_save(client):
    field = FieldFactory(field_type=FieldType.CHECKBOX_MULTIPLE_WITH_NOTE,
                         choices=[])
    choices = FieldChoiceFactory.create_batch(5, field=field)
    choice1, choice2, *_ = choices
    form = {
        f'{field.name}_0': choice1.value,
        f'{field.name}_1': choice2.value,
    }
    survey = CourseOfferingSurveyFactory()
    survey.form.fields.add(field)
    survey.form.status = STATUS_PUBLISHED
    survey.form.save()
    response = client.post(survey.get_absolute_url(), form)
    assert response.status_code == 302
    assert FormSubmission.objects.count() == 1
    assert FieldEntry.objects.count() == 2


@pytest.mark.django_db
def test_report_survey(client):
    field1 = FieldFactory(field_type=FieldType.CHECKBOX_MULTIPLE_WITH_NOTE,
                          label="Field 1", order=20, choices=[])
    choices = FieldChoiceFactory.create_batch(5, field=field1)
    choice1, choice2, *_ = choices
    field2 = FieldFactory(field_type=FieldType.RADIO_MULTIPLE,
                          label="Field 2", order=10, choices=[])
    radio_choice, *_ = FieldChoiceFactory.create_batch(5, field=field2)
    form = {
        f'{field1.name}_0': [choice1.value, choice2.value],
        f'{field1.name}_1': 'note',
        f'{field2.name}': radio_choice.value,
    }
    survey1, survey2 = CourseOfferingSurveyFactory.create_batch(2)
    survey1.form.fields.add(field1)
    survey1.form.fields.add(field2)
    survey1.form.status = STATUS_PUBLISHED
    survey1.form.save()
    response = client.post(survey1.get_absolute_url(), form)
    assert response.status_code == 302
    assert FormSubmission.objects.count() == 1
    assert FieldEntry.objects.count() == 4
    report = SurveySubmissionsReport(survey1)
    assert len(report.db_fields) == 2
    assert report.headers == ["Field 2", "Field 1"]
    data = list(report.data)
    assert len(data) == 1
    field2_val, field1_val = data[0]
    assert choice1.label in field1_val
    assert choice2.label in field1_val
    assert "note" in field1_val
    assert radio_choice.label in field2_val
