# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _, pgettext

def dummy_for_makemessages():
    """
    This function allows manage makemessages to find the forecast types for translation.
    Removing this code causes makemessages to comment out those PO entries, so don't do that
    unless you find a better way to do this
    """
    # cscenter menu translation
    pgettext('menu', 'About CSC')
    pgettext('menu', 'Syllabus')
    pgettext('menu', 'Courses')
    pgettext('menu', 'Organizers')
    pgettext('menu', 'Professors')
    pgettext('menu', 'Alumni')

    pgettext('menu', 'Online courses')
    pgettext('menu', 'Online')
    pgettext('menu', 'Video')

    pgettext('menu', 'Lyceum')

    pgettext('menu', 'Learning')
    pgettext('menu', 'Assignments')
    pgettext('menu', 'My timetable')
    pgettext('menu', 'Calendar')
    pgettext('menu', 'My courses')
    pgettext('menu', 'Library')
    pgettext('menu', 'Tips')

    pgettext('menu', 'Supervision')
    pgettext('menu', 'Student search')
    pgettext('menu', 'Generate diplomas')
    pgettext('menu', 'Exports')

    pgettext('menu', 'Teaching')
    pgettext('menu', 'Assignments')
    pgettext('menu', 'Timetable')
    pgettext('menu', 'Calendar')
    pgettext('menu', 'Marks sheet')

    pgettext('menu', 'Enrollment')
    pgettext('menu', 'Information')
    pgettext('menu', 'Application')

    pgettext('menu', 'Contacts')

    # In club we have 2 languages menu version. No translation needed here.
