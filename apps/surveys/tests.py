import datetime

import pytest

from courses.factories import CourseFactory, CourseClassFactory
from surveys.constants import FieldType, STATUS_PUBLISHED
from surveys.factories import CourseSurveyFactory, FieldFactory, \
    FieldEntryFactory, FieldChoiceFactory, FormSubmissionFactory
from surveys.forms import FormBuilder
from surveys.models import FormSubmission, FieldEntry, Field
from surveys.reports import SurveySubmissionsReport, SurveySubmissionsStats, \
    PollOptionResult


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
    survey = CourseSurveyFactory()
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
    survey = CourseSurveyFactory()
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
    survey = CourseSurveyFactory()
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
    survey = CourseSurveyFactory()
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
    survey = CourseSurveyFactory()
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
    survey1, survey2 = CourseSurveyFactory.create_batch(2)
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


@pytest.mark.django_db
def test_conditional_logic_prefill_class(mocker):
    # Fix year and term
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    today_fixed = datetime.datetime(2018, month=3, day=8, hour=13, minute=0,
                                    tzinfo=datetime.timezone.utc)
    mocked_timezone.return_value = today_fixed
    co = CourseFactory.create(city_id='spb')
    past = today_fixed - datetime.timedelta(days=3)
    future = today_fixed + datetime.timedelta(days=3)
    class1 = CourseClassFactory(course=co, date=past)
    # Don't forget to set local time for `ends_at` (+3)
    class2 = CourseClassFactory(course=co, date=today_fixed,
                                ends_at=datetime.time(hour=12, minute=0))
    seminar1 = CourseClassFactory(course=co, date=today_fixed,
                                  ends_at=datetime.time(hour=12, minute=0),
                                  type='seminar')
    # This one ends later than `current` moment
    class3 = CourseClassFactory(course=co, date=today_fixed,
                                ends_at=datetime.time(hour=21, minute=0))
    class4 = CourseClassFactory(course=co, date=future)
    survey = CourseSurveyFactory(course=co, form_id=None)
    assert hasattr(survey, "form")
    assert survey.form.fields.count() > 0
    # Field that should be prefilled with passed lectures
    field = (Field.objects
             .filter(
                form_id=survey.form_id,
                label__icontains="Возможно, некоторые темы остались"))
    assert field.count() == 1
    lectures = [c.label for c in field.first().choices.all()]
    assert len(lectures) == 2
    assert class1.name in lectures
    assert class2.name in lectures
    assert class3.name not in lectures


@pytest.mark.django_db
def test_submission_stats():
    field_radio = FieldFactory(
        field_type=FieldType.RADIO_MULTIPLE,
        label="Field 2", order=10, choices=[])
    radio_choices = FieldChoiceFactory.create_batch(
        3, field=field_radio)
    radio_choice, radio_choice2, *_ = radio_choices
    field_checkboxes_with_note = FieldFactory(
        field_type=FieldType.CHECKBOX_MULTIPLE_WITH_NOTE,
        label="Field 1", order=20, choices=[])
    choices = FieldChoiceFactory.create_batch(
        3, field=field_checkboxes_with_note)
    checkbox1, checkbox2, checkbox3 = choices
    survey1, survey2 = CourseSurveyFactory.create_batch(2)
    survey1.form.fields.add(field_checkboxes_with_note)
    survey1.form.fields.add(field_radio)
    survey1.form.status = STATUS_PUBLISHED
    survey1.form.save()
    report = SurveySubmissionsStats(survey1)
    stats = report.calculate()
    assert stats["total_submissions"] == 0
    assert len(stats["fields"]) == survey1.form.fields.count()
    submission1 = FormSubmissionFactory(form=survey1.form, entries=[])
    # Add entries for radio buttons type field
    FieldEntryFactory(form=survey1.form, submission=submission1,
                      field_id=field_radio.pk, value=radio_choice.value,
                      is_choice=True)
    stats = report.calculate()
    assert stats["total_submissions"] == 1
    assert len(stats["fields"]) == survey1.form.fields.count()
    radio_stats = stats["fields"][field_radio]
    assert isinstance(radio_stats, dict)
    assert len(radio_stats) == 2
    assert "choices" in radio_stats
    assert "notes" in radio_stats
    assert len(radio_stats["notes"]) == 0
    assert len(radio_stats["choices"]) == len(radio_choices)
    assert all(isinstance(c, PollOptionResult) for c in radio_stats["choices"])
    stats_choice1, stats_choice2, stats_choice3 = radio_stats["choices"]
    assert stats_choice1.value == radio_choice.label
    assert stats_choice1.total == 1
    assert stats_choice1.answers == 1
    assert stats_choice1.percentage == '100'
    assert stats_choice2.value == radio_choice2.label
    assert stats_choice2.total == 1
    assert stats_choice2.answers == 0
    assert stats_choice2.percentage == '0'
    assert stats_choice3.total == 1
    assert stats_choice3.answers == 0
    # Add answers for checkboxes with note type field
    submission2 = FormSubmissionFactory(form=survey1.form, entries=[])
    FieldEntryFactory(form=survey1.form, submission=submission1,
                      field_id=field_checkboxes_with_note.pk,
                      value=checkbox2.value,
                      is_choice=True)
    FieldEntryFactory(form=survey1.form, submission=submission2,
                      field_id=field_checkboxes_with_note.pk,
                      value=checkbox2.value,
                      is_choice=True)
    FieldEntryFactory(form=survey1.form, submission=submission2,
                      field_id=field_checkboxes_with_note.pk,
                      value=checkbox1.value,
                      is_choice=True)
    FieldEntryFactory(form=survey1.form, submission=submission1,
                      field_id=field_checkboxes_with_note.pk,
                      value='note',
                      is_choice=False)
    stats = report.calculate()
    assert stats["total_submissions"] == 2
    assert len(stats["fields"]) == survey1.form.fields.count()
    checkboxes_stats = stats["fields"][field_checkboxes_with_note]
    assert isinstance(checkboxes_stats, dict)
    assert len(checkboxes_stats["notes"]) == 1
    assert ("note", checkbox2.label) == checkboxes_stats["notes"][0]
    stats_choice1, stats_choice2, stats_choice3 = checkboxes_stats["choices"]
    assert stats_choice1.value == checkbox2.label
    assert stats_choice1.total == 2
    assert stats_choice1.answers == 2
    assert stats_choice1.percentage == '100'
    assert stats_choice2.value == checkbox1.label
    assert stats_choice2.total == 2
    assert stats_choice2.answers == 1
    assert stats_choice2.percentage == '50'
    assert stats_choice3.total == 2
    assert stats_choice3.answers == 0
    assert stats_choice3.percentage == '0'
