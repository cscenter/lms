import factory

from core.tests.factories import BranchFactory
from study_programs.models import AcademicDiscipline, StudyProgram, \
    StudyProgramCourseGroup


class AcademicDisciplineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AcademicDiscipline

    name = factory.Sequence(lambda n: "Study area %03d" % n)
    code = factory.Sequence(lambda n: "p%01d" % n)


class StudyProgramFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudyProgram

    year = 2018
    academic_discipline = factory.SubFactory(AcademicDisciplineFactory)
    branch = factory.SubFactory(BranchFactory)


class StudyProgramCourseGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudyProgramCourseGroup

    study_program = factory.SubFactory(StudyProgramFactory)

    @factory.post_generation
    def courses(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for course in extracted:
                self.courses.add(course)
