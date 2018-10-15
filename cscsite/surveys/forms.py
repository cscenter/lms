from collections import defaultdict

from django import forms
from django.db.models import Prefetch

from surveys.constants import FIELD_CLASSES, FieldType
from surveys.models import FieldEntry, FormSubmission, Form, Field, FieldChoice


class FormBuilder(forms.ModelForm):
    field_entry_model = FieldEntry

    class Meta:
        model = FormSubmission
        exclude = ("form", "created")

    def __init__(self, form_instance: Form, *args, **kwargs):
        """Creates form field for each db_field of the given Form instance."""
        self.form_instance = form_instance
        p = Prefetch("choices", queryset=FieldChoice.objects.order_by("order"))
        self.db_fields = (form_instance.fields.visible()
                          .order_by("order")
                          .prefetch_related(p))

        # If a FormSubmission instance is given to edit, stores it's field
        # values for using as initial data.
        field_entries = defaultdict(list)
        if kwargs.get("instance"):
            for field_entry in kwargs["instance"].entries.all():
                field_entries[field_entry.field_id].append(field_entry)
        initial = kwargs.pop("initial", {})

        super().__init__(*args, **kwargs)
        # Create form field for each db field
        for db_field in self.db_fields:
            field_key = db_field.name
            field_class = FIELD_CLASSES[db_field.field_type]
            field_args = {
                "label": db_field.label,
                "required": db_field.required,
                "help_text": db_field.help_text,
                "error_messages": db_field.error_messages
            }
            field_widget = db_field.get_widget()
            if field_widget is not None:
                field_args["widget"] = field_widget
            choices = db_field.field_choices
            if choices is not None:
                field_args["choices"] = choices
            # If a form model instance is given (eg we're editing a form
            # response), then use the instance's value for the field.
            if db_field.id in field_entries:
                entries = field_entries[db_field.id]
                initial_val = db_field.to_field_value(entries)
            else:
                # An explicit "initial" dict has been provided
                initial_val = initial.get(field_key)
            if initial_val:
                self.initial[field_key] = initial_val

            new_field = field_class(**field_args)
            # Link form field with db model instance
            new_field.db_field = db_field
            # Set field visibility based on conditional logic
            new_field.is_hidden = (db_field.visibility == db_field.HIDDEN)
            needs_to_recalculate = self.is_bound or field_key in self.initial
            if (needs_to_recalculate and new_field.is_hidden and
                    db_field.conditional_logic):
                for logic in db_field.conditional_logic:
                    if (logic.get('scope') != 'field' or
                            logic.get('action_type') != 'show'):
                        continue
                    if (not logic.get('rules') or
                            not isinstance(logic['rules'], list)):
                        continue
                    for r in logic['rules']:
                        if not r.get('field_name') or not r.get('value'):
                            continue
                        expected_values = r.get('value')
                        if not isinstance(expected_values, list):
                            expected_values = [expected_values]
                        field_name = Field.get_field_name(r.get('field_name'))
                        selected_values = None
                        if self.is_bound and field_name in self.data:
                            selected_values = self.data.getlist(field_name)
                        elif not self.is_bound:
                            selected_values = self.initial.get(field_name)
                            if not selected_values:
                                continue
                            related_field = self.fields[field_name].db_field
                            if related_field.field_type == FieldType.CHECKBOX_MULTIPLE_WITH_NOTE:
                                selected_values, *_ = selected_values
                        if not selected_values:
                            continue
                        if set(selected_values).intersection(str(v) for v in
                                                             expected_values):
                            new_field.is_hidden = False
                            break
            if new_field.is_hidden:
                new_field.required = False
            self.fields[field_key] = new_field
            # Add identifying CSS classes to the db_field
            # FIXME: удалить? никак не используется сейчас вроде
            css_class = field_class.__name__.lower()
            if db_field.required:
                css_class += " required"
            new_field.widget.attrs["class"] = css_class
            # Crutch
            if not db_field.show_label and db_field.field_type == FieldType.TEXTAREA:
                new_field.widget.attrs['rows'] = 6
            placeholder = db_field.get_placeholder()
            if placeholder:
                new_field.widget.attrs["placeholder"] = placeholder

    def save(self, **kwargs):
        """
        Get/create a FormEntry instance and assign submitted values to
        related FieldEntry instances for each form field.
        """
        submission = super().save(commit=False)
        submission.form = self.form_instance
        submission.save()
        entry_fields = []
        for db_field in self.db_fields:
            field_key = db_field.name
            cleaned_value = self.cleaned_data[field_key]
            values = db_field.prepare_field_value(cleaned_value)
            for value, is_choice in values:
                data = {
                    "submission": submission,
                    "form_id": self.form_instance.id,
                    "field_id": db_field.id,
                    "value": value,
                    "is_choice": is_choice
                    # FIXME: add meta
                }
                entry_fields.append(self.field_entry_model(**data))
        if entry_fields:
            self.field_entry_model.objects.bulk_create(entry_fields)
        return submission

