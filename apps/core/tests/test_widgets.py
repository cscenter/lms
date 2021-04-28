import pytest
from bs4 import BeautifulSoup

from core.widgets import AdminRichTextAreaWidget


@pytest.mark.django_db
def test_admin_ubertextarea():
    widget = AdminRichTextAreaWidget()
    rendered_widget = widget.render(name="test", value="widget_value")
    widget_dom = BeautifulSoup(rendered_widget, "html.parser").find('textarea')
    assert widget_dom.get('name') == "test"
    assert widget_dom.text == "widget_value"
