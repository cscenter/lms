import pytest
from rest_framework.exceptions import ValidationError

from universities.selectors import faculties_queryset, universities_queryset
from universities.tests.factories import CityFactory, FacultyFactory, UniversityFactory


@pytest.mark.django_db
def test_selector_universities_list():
    assert not universities_queryset().exists()
    city1, city2 = CityFactory.create_batch(2)
    university1 = UniversityFactory(city=city1)
    university2 = UniversityFactory(city=city2)
    assert universities_queryset().count() == 2
    assert universities_queryset(filters={'city': city1.pk}).count() == 1
    assert list(universities_queryset(filters={'city': city1.pk})) == [university1]


@pytest.mark.django_db
def test_selector_faculties_list():
    assert not faculties_queryset().exists()
    university1, university2 = UniversityFactory.create_batch(2)
    faculty1 = FacultyFactory(university=university1)
    faculty2 = FacultyFactory(university=university2)
    assert faculties_queryset().count() == 2
    with pytest.raises(ValidationError):
        faculties_queryset(filters={'university': university1})
    assert faculties_queryset(filters={'university': -1}).count() == 0
    assert faculties_queryset(filters={'university': university1.pk}).count() == 1
    assert list(faculties_queryset(filters={'university': university1.pk})) == [faculty1]
