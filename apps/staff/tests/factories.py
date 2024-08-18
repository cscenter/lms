import factory.fuzzy
from learning.settings import StudentStatuses
from study_programs.tests.factories import AcademicDisciplineFactory
from users.models import StudentStatusLog, StudentAcademicDisciplineLog
from users.tests.factories import StudentProfileFactory, CuratorFactory

__all__ = ('StudentStatusLogFactory', 'StudentAcademicDisciplineLogFactory')

class StudentStatusLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentStatusLog

    status = factory.fuzzy.FuzzyChoice([x for x, _ in StudentStatuses.choices])
    entry_author = factory.SubFactory(CuratorFactory)

    @factory.lazy_attribute
    def student_profile(self):
        return StudentProfileFactory(status=self.status)

class StudentAcademicDisciplineLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentAcademicDisciplineLog

    academic_discipline = factory.SubFactory(AcademicDisciplineFactory)
    entry_author = factory.SubFactory(CuratorFactory)

    @factory.lazy_attribute
    def student_profile(self):
        return StudentProfileFactory(academic_disciplines=[self.academic_discipline])

