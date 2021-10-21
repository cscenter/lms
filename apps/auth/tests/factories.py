import factory

from auth.models import ConnectedAuthService
from users.tests.factories import UserFactory


class ConnectedAuthServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ConnectedAuthService

    user = factory.SubFactory(UserFactory)
    provider = factory.Iterator(['gerrit', 'github'])
    uid = factory.LazyAttributeSequence(lambda o, n: f"{o.provider}-{n}")
