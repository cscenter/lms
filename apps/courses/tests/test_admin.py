import pytest
from bs4 import BeautifulSoup

from core.admin import get_admin_url
from core.urls import reverse
from courses.models import Assignment
from courses.tests.factories import CourseFactory
from learning.settings import Branches


@pytest.mark.django_db
def test_assignment_admin_view(settings, admin_client):
    # Datetime widget formatting depends on locale, change it
    settings.LANGUAGE_CODE = 'ru'
    co_in_spb = CourseFactory(branch__code=Branches.SPB)
    co_in_nsk = CourseFactory(branch__code=Branches.NSK)
    form_data = {
        "course": "",
        "deadline_at_0": "29.06.2017",
        "deadline_at_1": "00:00:00",
        "title": "title",
        "text": "text",
        "passing_score": "3",
        "maximum_score": "5",
        "weight": "1.00",
        "_continue": "save_and_continue"
    }
    # Test with empty branch aware field
    add_url = reverse('admin:courses_assignment_add')
    response = admin_client.post(add_url, form_data)
    assert response.status_code == 200
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    # Send valid data
    form_data["course"] = co_in_spb.pk
    response = admin_client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    message = list(response.context['messages'])[0]
    assert 'success' in message.tags
    assert Assignment.objects.count() == 1
    assignment = Assignment.objects.first()
    # In SPB we have msk timezone (UTC +3)
    # In DB we store datetime values in UTC
    assert assignment.deadline_at.day == 28
    assert assignment.deadline_at.hour == 21
    assert assignment.deadline_at.minute == 0
    # Admin widget shows localized time
    change_url = get_admin_url(assignment)
    response = admin_client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    date_input = widget.find('input', {"name": 'deadline_at_0'})
    assert date_input.get('value') == '29.06.2017'
    # We can't update course offering through admin interface
    response = admin_client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    assert assignment.course_id == co_in_spb.pk
    # But do it manually to test widget
    assignment.course = co_in_nsk
    assignment.save()
    form_data["deadline_at_1"] = "00:00:00"
    response = admin_client.post(change_url, form_data)
    assignment.refresh_from_db()
    response = admin_client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '00:00:00'
    assert assignment.deadline_at.hour == 17  # UTC +7 in nsk
    assert assignment.deadline_at.minute == 0
    # Update course and deadline time
    assignment.course = co_in_spb
    assignment.save()
    form_data["deadline_at_1"] = "06:00:00"
    response = admin_client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    response = admin_client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '06:00:00'
    assert assignment.deadline_at.hour == 3
    assert assignment.deadline_at.minute == 0
    # Update course offering and deadline, but choose values when
    # UTC time shouldn't change
    assignment.course = co_in_nsk
    assignment.save()
    form_data["deadline_at_1"] = "10:00:00"
    response = admin_client.post(change_url, form_data)
    assert response.status_code == 302
    assignment.refresh_from_db()
    response = admin_client.get(change_url)
    widget_html = response.context['adminform'].form['deadline_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'deadline_at_1'})
    assert time_input.get('value') == '10:00:00'
    assert assignment.deadline_at.hour == 3
    assert assignment.deadline_at.minute == 0
    assert assignment.course_id == co_in_nsk.pk