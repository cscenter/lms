import factory

from core.tests.factories import SiteFactory
from info_blocks.models import InfoBlock, InfoBlockTag


class InfoBlockTagFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Tag {n}')
    slug = factory.Sequence(lambda n: f'slug_{n}')

    class Meta:
        model = InfoBlockTag


class InfoBlockFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: f'Title {n}')
    content = factory.Sequence(lambda n: f'Content {n}')
    sort = factory.Sequence(lambda n: n + 1)
    site = factory.SubFactory(SiteFactory)

    class Meta:
        model = InfoBlock

    @factory.post_generation
    def tags(self, create, extracted):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)
