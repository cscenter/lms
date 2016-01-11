from __future__ import absolute_import, unicode_literals, print_function

from django.conf import settings

# this urls will be used to redirect from '/learning/' and '/teaching/'
LEARNING_BASE = getattr(settings, 'LEARNING_BASE', 'assignment_list_student')
TEACHING_BASE = getattr(settings, 'LEARNING_BASE', 'assignment_list_teacher')

# Assignment types constances
ASSIGNMENT_TASK_ATTACHMENT = 0
ASSIGNMENT_COMMENT_ATTACHMENT = 1