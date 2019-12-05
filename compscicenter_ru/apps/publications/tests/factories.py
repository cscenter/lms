import factory

from projects.constants import ProjectTypes
from publications.models import ProjectPublication


class ProjectPublicationFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProjectPublication

    title = factory.Sequence(lambda n: "Project Publication %03d" % n)
    slug = factory.Sequence(lambda n: "slug-%03d" % n)
    type = ProjectTypes.practice

    @factory.post_generation
    def authors(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for author in extracted:
                self.authors.add(author)

    @factory.post_generation
    def projects(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for project in extracted:
                self.projects.add(project)
