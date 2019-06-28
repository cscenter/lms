import factory
import pytz

from announcements.models import Announcement, AnnouncementTag

__all__ = ('AnnouncementTagFactory', 'AnnouncementFactory', )


class AnnouncementTagFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Tag %03d" % n)
    slug = factory.Sequence(lambda n: "slug-%03d" % n)

    class Meta:
        model = AnnouncementTag


class AnnouncementFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Announcement %03d" % n)
    short_description = factory.Sequence(lambda n: "Short description %03d" % n)
    publish_end_at = factory.Faker('future_datetime', end_date="+30d",
                                   tzinfo=pytz.UTC)

    class Meta:
        model = Announcement

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)
