import pytest
from django.core.cache import cache

from core.urls import reverse
from learning.tests.factories import AcademicDisciplineFactory, \
    GraduateProfileFactory
from users.tests.factories import GraduateFactory


# TODO: test context
@pytest.mark.django_db
def test_testimonials_smoke(client):
    GraduateProfileFactory(testimonial='test', photo='stub.JPG')
    response = client.get(reverse('testimonials'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_menu_selected_patterns(rf):
    from compscicenter_ru.menus import Menu
    from core.menu import MenuItem
    menu_name = 'test_menu'
    menu_items = [
        MenuItem("Item1", '/about/', weight=10,
                 selected_patterns=[r"^/events/"]),
        MenuItem("Item2", '/about2/', weight=20,
                 selected_patterns=[r"^http://compscicenter.ru/events2/"]),
        MenuItem("Item3", '/about3/', weight=30,
                 selected_patterns=[r"^http://externaldomain.ru/events/"]),
    ]
    for menu_item in menu_items:
        Menu.add_item(menu_name, menu_item)
    env = {
        'PATH_INFO': '/events/1/',
        'SERVER_NAME': 'compscicenter.ru',
        'wsgi.url_scheme': 'http'
    }
    request = rf.request(**env)
    assert request.get_full_path() == '/events/1/'
    processed_menu = Menu.process(request, name=menu_name)
    assert len(processed_menu) == 3
    processed_menu_item = processed_menu[0]
    assert processed_menu_item.weight == 10
    assert processed_menu_item.visible
    assert processed_menu_item.selected
    env['PATH_INFO'] = '/events2/'
    env['SERVER_NAME'] = 'subdomain.compscicenter.ru'
    request = rf.request(**env)
    processed_menu = Menu.process(request, name=menu_name)
    assert not any(item.selected for item in processed_menu)
    env['SERVER_NAME'] = 'compscicenter.ru'
    request = rf.request(**env)
    processed_menu = Menu.process(request, name=menu_name)
    assert processed_menu[1].selected


# TODO: test alumni api
@pytest.mark.django_db
def test_alumni(client):
    url_alumni_all = reverse('alumni')
    response = client.get(url_alumni_all)
    assert response.status_code == 200
    json_data = response.context_data['app_data']
    assert json_data['props']['years'] == [{'label': 2013, 'value': 2013}]
    assert not json_data['props']['areas']
    graduated = GraduateFactory(graduation_year=2015)
    cache.delete('cscenter_last_graduation_year')
    response = client.get(url_alumni_all)
    assert response.status_code == 200
    json_data = response.context_data['app_data']
    assert len(json_data['props']['years']) == 3
    assert json_data['props']['years'][0]['value'] == 2015
    assert json_data['state']['year'] == json_data['props']['years'][0]
    a = AcademicDisciplineFactory()
    response = client.get(url_alumni_all)
    json_data = response.context_data['app_data']
    assert json_data['props']['areas'] == [{'label': a.name, 'value': a.code}]
