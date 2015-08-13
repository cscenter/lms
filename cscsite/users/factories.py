# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import factory

from django.contrib.auth.models import Group

from users.models import CSCUser


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = CSCUser

    username = factory.Sequence(lambda n: "testuser%03d" % n)
    gender = factory.Iterator([CSCUser.GENDER_MALE, CSCUser.GENDER_FEMALE])
    password = "test123foobar@!"
    email = factory.Sequence(lambda n: "user%03d@foobar.net" % n)
    first_name = factory.Sequence(lambda n: "Ivan%03d" % n)
    last_name = factory.Sequence(lambda n: "Petrov%03d" % n)

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for group in extracted:
                if isinstance(group, int):
                    group_add = Group.objects.get(pk=group)
                else:
                    group_add = Group.objects.get(name=group)
                self.groups.add(group_add)

    @factory.post_generation
    def raw_password(self, create, extracted, **kwargs):
        if not create:
            return
        raw_password = self.password
        self.set_password(raw_password)
        self.save()
        self.raw_password = raw_password
