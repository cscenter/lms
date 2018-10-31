import random
from random import randint

import factory

from core.factories import EmailTemplateFactory
from learning.factories import CourseFactory
from surveys.constants import FieldType
from surveys.models import CourseOfferingSurvey, Form, Field, FormSubmission, \
    FieldEntry, FieldChoice


class FormFactory(factory.DjangoModelFactory):
    class Meta:
        model = Form

    title = factory.Sequence(lambda n: "Form Title %03d" % n)
    slug = factory.Sequence(lambda n: "form-slug-%03d" % n)


class FieldFactory(factory.DjangoModelFactory):
    class Meta:
        model = Field

    form = factory.SubFactory(FormFactory)
    label = factory.Sequence(lambda n: "Label %03d" % n)
    field_type = factory.Iterator([FieldType.TEXT, FieldType.TEXTAREA,
                                   FieldType.CHECKBOX_MULTIPLE,
                                   FieldType.RADIO_MULTIPLE])

    @factory.post_generation
    def choices(self, create, extracted, **kwargs):
        if not create:
            return
        if isinstance(extracted, list):
            for choice in extracted:
                self.choices.add(choice)
        else:
            if self.has_choices():
                for i in range(0, randint(2, 6)):
                    FieldChoiceFactory(field=self)


class FieldChoiceFactory(factory.DjangoModelFactory):
    class Meta:
        model = FieldChoice

    field = factory.SubFactory(FieldFactory)
    value = factory.Sequence(lambda n: str(n + 1))
    label = factory.Sequence(lambda n: "Choice %03d" % n)


class CourseOfferingSurveyFactory(factory.DjangoModelFactory):
    class Meta:
        model = CourseOfferingSurvey

    form = factory.SubFactory(FormFactory)
    course_offering = factory.SubFactory(CourseFactory)
    type = factory.Iterator([
        c for c, n in CourseOfferingSurvey._meta.get_field('type').choices
    ])
    email_template = factory.SubFactory(
        EmailTemplateFactory,
        name=factory.LazyAttribute(lambda o: f"survey-{o.factory_parent.type}"))


class FormSubmissionFactory(factory.DjangoModelFactory):
    class Meta:
        model = FormSubmission

    form = factory.SubFactory(FormFactory)

    @factory.post_generation
    def entries(self, create, extracted, **kwargs):
        if not create:
            return

        if isinstance(extracted, list):
            for entry in extracted:
                self.entries.add(entry)
        else:
            for field in self.form.fields.all():
                opts = dict(form=self.form, submission=self, field_id=field.pk)
                if field.has_choices():
                    choices = [c.value for c in field.choices.all()]
                    k = random.randrange(0, len(choices))
                    if not k and field.required:
                        k = 1
                    for v in random.sample(choices, k):
                        opts["is_choice"] = True
                        opts["value"] = v
                        FieldEntryFactory(**opts)
                else:
                    FieldEntryFactory(**opts)


class FieldEntryFactory(factory.DjangoModelFactory):
    class Meta:
        model = FieldEntry

    form = factory.SubFactory(FormFactory)
    submission = factory.SubFactory(FormSubmissionFactory)
    field_id = factory.Sequence(lambda n: n)
    value = factory.Faker('sentence', nb_words=4)
