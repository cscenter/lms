import factory
from factory.fuzzy import FuzzyInteger

from learning.factories import SemesterFactory
from learning.projects.models import Project, ProjectStudent, Report
from users.factories import UserFactory


class ProjectFactory(factory.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: "Test student project %03d" % n)
    description = factory.Sequence(lambda n: ("Test student project "
                                              "description %03d" % n))
    supervisor = factory.Sequence(lambda n: "Test supervisor %03d" % n)
    project_type = 'practice'
    semester = factory.SubFactory(SemesterFactory)

    @factory.post_generation
    def students(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for student in extracted:
                ProjectStudentFactory(student=student, project=self)

    @factory.post_generation
    def reviewers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for reviewer in extracted:
                self.reviewers.add(reviewer)


class ProjectStudentFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProjectStudent

    student = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    supervisor_grade = FuzzyInteger(-15, 15)
    presentation_grade = FuzzyInteger(0, 10)


class ReportFactory(factory.DjangoModelFactory):
    class Meta:
        model = Report

    project_student = factory.SubFactory(ProjectStudentFactory)

