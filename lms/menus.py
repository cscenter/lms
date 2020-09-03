"""
This file describes general top menu structure used in the LMS.

Unnecessary menu items can be excluded for a certain site by adding
EXCLUDE_MENU_ITEMS to the settings. EXCLUDE_MENU_ITEMS should be a list
containing tags of menu items to be excluded, e.g. 'admission' to exclude
the whole first-level menu item, or 'learning:library' to exclude item child.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import pgettext_lazy
from menu import Menu

from core.menu import MenuItem
from core.urls import reverse

top_menu = [
    MenuItem(
        pgettext_lazy("menu", "Courses"),
        reverse("course_list", subdomain=settings.LMS_SUBDOMAIN),
        weight=10,
        tag="courses",
        excluded_patterns=[
            r"^/courses/.*/assignments/add$",
            r"^/courses/.*/assignments/\d+/edit$"
        ]),
    MenuItem(
        pgettext_lazy("menu", "Обучение"),
        reverse('study:assignment_list'),
        weight=10,
        tag="learning",
        children=[
            MenuItem(pgettext_lazy("menu", "Задания"), '/learning/assignments/', weight=10, tag="assignments", budge='assignments_student'),
            MenuItem(pgettext_lazy("menu", "Моё расписание"), '/learning/timetable/', weight=20, tag="timetable", selected_patterns=[r" ^/learning/calendar/"]),
            MenuItem(pgettext_lazy("menu", "Календарь"), '/learning/full-calendar/', weight=30, tag="full-calendar"),
            MenuItem(pgettext_lazy("menu", "Мои курсы"), '/learning/courses/', weight=40, tag="courses"),
            MenuItem(pgettext_lazy("menu", "Библиотека"), '/learning/library/', weight=50, tag="library"),
            MenuItem(pgettext_lazy("menu", "Полезное"), '/learning/useful/', weight=60, tag="useful"),
            MenuItem(pgettext_lazy("menu", "Кодекс чести"), '/learning/hc/', weight=70, tag="hc"),
            MenuItem(pgettext_lazy("menu", "Проекты организаторов"), '/learning/internships/', weight=80, tag="internships"),
        ],
        permissions=(
            "learning.view_study_menu",
        ),
        css_classes='for-students'),
    MenuItem(
        pgettext_lazy("menu", "Преподавание"),
        reverse('teaching:assignment_list'),
        weight=20,
        tag="teaching",
        children=[
            MenuItem(
                pgettext_lazy("menu", "Задания"),
                reverse('teaching:assignment_list'),
                weight=10,
                tag="assignments",
                budge='assignments_teacher',
                selected_patterns=[
                    r"^/courses/.*/assignments/add$",
                    r"^/courses/.*/assignments/\d+/edit$"
                ]),
            MenuItem(
                pgettext_lazy("menu", "Расписание"),
                reverse('teaching:timetable'),
                weight=20,
                tag="timetable",
                selected_patterns=[r"^/teaching/calendar/"]),
            MenuItem(
                pgettext_lazy("menu", "Календарь"),
                reverse('teaching:calendar_full'),
                weight=30,
                tag="calendar_full"),
            MenuItem(
                pgettext_lazy("menu", "Мои курсы"),
                reverse("teaching:course_list"),
                weight=40,
                tag="course_list",
                budge='courseoffering_news'),
            MenuItem(
                pgettext_lazy("menu", "Ведомости"),
                reverse('teaching:gradebook_list'),
                weight=50,
                tag="gradebook_list"),
        ],
        permissions=(
            "learning.view_teaching_menu",
        ),
        css_classes='for-teachers'),
    MenuItem(
        pgettext_lazy("menu", "Набор"),
        reverse('admission:interviews'),
        weight=30,
        tag="admission",
        children=[
            MenuItem(pgettext_lazy("menu", "Собеседования"), '/admission/interviews/', weight=10, tag="interviews"),
            MenuItem(pgettext_lazy("menu", "Анкеты"), '/admission/applicants/', weight=20, tag="applicants", for_staff=True),
            MenuItem(pgettext_lazy("menu", "Результаты"), '/admission/results/', weight=30, tag="results", for_staff=True),
        ],
        permissions=(
            "learning.view_admission_menu",
        ),
    ),
    MenuItem(
        pgettext_lazy("menu", "Проекты"),
        reverse('projects:report_list_reviewers'),
        weight=30,
        tag="projects",
        children=[
            MenuItem(pgettext_lazy("menu", "Отчеты"), '/projects/reports/', weight=10, tag="reports", selected_patterns=[r"^/projects/\d+/reports/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Проекты"), '/projects/available/', weight=20, tag="available", selected_patterns=[r"^/projects/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Все проекты"), '/projects/all/', weight=30, tag="all", for_staff=True),
            MenuItem(pgettext_lazy("menu", "Все отчеты"), '/projects/reports-all/', weight=40, tag="reports-all", for_staff=True),
        ],
        permissions=(
            "learning.view_projects_menu",
        ),
    ),
    MenuItem(
        pgettext_lazy("menu", "Курирование"),
        reverse('staff:gradebook_list'),
        weight=40,
        tag="staff",
        children=[
            MenuItem(pgettext_lazy("menu", "Ведомости"), reverse('staff:gradebook_list'), weight=10, tag="gradebook_list"),
            MenuItem(pgettext_lazy("menu", "Поиск студентов"), reverse('staff:student_search'), weight=20, tag="student_search"),
            MenuItem(pgettext_lazy("menu", "Файлы"), reverse('staff:exports'), weight=30, tag="exports"),
            MenuItem(pgettext_lazy("menu", "Полезное"), reverse('staff:staff_warehouse'), weight=40, tag="staff_warehouse"),
            MenuItem(pgettext_lazy("menu", "Фейсбук"), reverse('staff:student_faces'), weight=50, tag="student_faces"),
            MenuItem(pgettext_lazy("menu", "Пересечения"), reverse('staff:course_participants_intersection'), weight=60, tag="course_participants_intersection"),
        ],
        for_staff=True,
        css_classes='for-staff'),
]


exclude_items = getattr(settings, "EXCLUDE_MENU_ITEMS", None)
if not exclude_items:
    for item in top_menu:
        Menu.add_item("menu_private", item)
else:
    parsed_exclude_items = {}
    for item in exclude_items:
        first_level_tag, _, second_level_tag = item.partition(':')
        if not first_level_tag or ':' in second_level_tag:
            raise ImproperlyConfigured(f'Menu item {item} cannot be excluded '
                                       f'due to syntax error in the tag.')
        if not first_level_tag in parsed_exclude_items:
            parsed_exclude_items[first_level_tag] = []
        parsed_exclude_items[first_level_tag].append(second_level_tag or None)
    for item in top_menu:
        if item.tag in parsed_exclude_items:
            # Exclude the whole MenuItem
            if None in parsed_exclude_items[item.tag]:
                continue
            # Otherwise try to exclude children
            children = {child.tag: child for child in item.children}
            for tag in parsed_exclude_items[item.tag]:
                if tag in children:
                    del children[tag]
                else:
                    raise ImproperlyConfigured(f"Cannot exclude menu item "
                                               f"{item.tag}:{tag} - no such "
                                               f"item.")
            # Remove excluded children from the item and add to the menu
            item.children = [child for child in item.children
                             if child in children.values()]
        Menu.add_item("menu_private", item)
