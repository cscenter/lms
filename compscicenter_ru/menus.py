import re

from django.conf import settings
from django.utils.translation import pgettext_lazy
from menu import Menu, MenuItem as _MenuItem
from core.urls import reverse

from users.constants import AcademicRoles

# FIXME: как используется `budge` - чекаем
# FIXME: `for_staff` - сделать что-то умнее? curators_only?

PRIVATE = settings.PRIVATE_SUBDOMAIN


class MenuItem(_MenuItem):
    visible_to = None
    selected_patterns = None
    excluded_patterns = None

    def check(self, request):
        """Evaluate if we should be visible for this request"""
        if self.visible_to is not None:
            user_groups = request.user.get_cached_groups()
            self.visible = bool(user_groups.intersection(self.visible_to))
        # FIXME: show students section to active students only
        if callable(self.check_func):
            self.visible = self.check_func(request)

    def match_url(self, request):
        """match url determines if this is selected"""
        matched = False
        url = self.url
        # Relative URL means related view available on any subdomain
        if not url.startswith('http'):
            # For a correct comparison menu url with current path append scheme
            url = request.build_absolute_uri(location=url)
        current_path = request.build_absolute_uri()
        if self.exact_url:
            if re.match("%s$" % (url,), current_path):
                matched = True
        elif re.match("%s" % url, current_path):
            matched = True
        if not matched and self.selected_patterns is not None:
            for pattern in self.selected_patterns:
                # Deep copy for compiled regexp works in python 3.7+
                if re.compile(pattern.strip()).match(current_path):
                    matched = True
        elif matched and self.excluded_patterns is not None:
            for pattern in self.excluded_patterns:
                if re.compile(pattern.strip()).match(current_path):
                    matched = False
        return matched


public_menu = [
    MenuItem(
        pgettext_lazy("menu", "О центре"),
        # FIXME: что делать с такими штуками?
        '/about/',
        weight=10,
        children=[
            MenuItem(pgettext_lazy("menu", "Цели и история"), '/about/', weight=20),
            MenuItem(pgettext_lazy("menu", "Программа"), reverse('syllabus'), weight=30),
            MenuItem(pgettext_lazy("menu", "Команда"), reverse('orgs'), weight=40),
            MenuItem(pgettext_lazy("menu", "Преподаватели"), reverse('teachers'), weight=50),
            MenuItem(pgettext_lazy("menu", "Выпускники"), reverse('alumni'), weight=60, selected_patterns=[r"^/2016/$"]),
            MenuItem(pgettext_lazy("menu", "Отзывы"), reverse('testimonials'), weight=70),
        ],
        selected_patterns=[
            r"^/events/"
        ]),
    MenuItem(
        pgettext_lazy("menu", "Курсы"),
        '/courses/',
        weight=20,
        excluded_patterns=[
            r"^/courses/.*/assignments/add$",
            r"^/courses/.*/assignments/\d+/edit$"
        ]),
    MenuItem(pgettext_lazy("menu", "Онлайн"), '/online/', weight=30, children=[
        MenuItem(pgettext_lazy("menu", "Онлайн-курсы"), '/online/', weight=10),
        MenuItem(pgettext_lazy("menu", "Онлайн-программы"), 'https://code.stepik.org/', weight=20, is_external=True),
        MenuItem(pgettext_lazy("menu", "Видео"), '/videos/', weight=30),
    ]),
    MenuItem(pgettext_lazy("menu", "Лекторий"), 'https://open.compscicenter.ru/', weight=40, is_external=True),
    MenuItem(pgettext_lazy("menu", "Поступление"), '/enrollment/', weight=50, children=[
        MenuItem(pgettext_lazy("menu", "Поступающим"), '/enrollment/', weight=10),
        MenuItem(pgettext_lazy("menu", "Подать заявку"), '/application/closed/', weight=20),
        MenuItem(pgettext_lazy("menu", "Программа для поступления"), '/enrollment/program/', weight=30),
        MenuItem(pgettext_lazy("menu", "Вопросы и ответы"), '/faq/', weight=40),
    ]),
]

common_menu = [menu_item for menu_item in public_menu if menu_item.weight < 50]
for item in common_menu:
    # This is OK that we mutate `public_menu`
    item.weight -= 500

private_menu = common_menu + [
    MenuItem(
        pgettext_lazy("menu", "Обучение"),
        reverse('study:assignment_list', subdomain=PRIVATE),
        weight=10,
        children=[
            MenuItem(pgettext_lazy("menu", "Задания"), '/learning/assignments/', weight=10, budge='assignments_student'),
            MenuItem(pgettext_lazy("menu", "Моё расписание"), '/learning/timetable/', weight=20, selected_patterns=[r" ^/learning/calendar/"]),
            MenuItem(pgettext_lazy("menu", "Календарь"), '/learning/full-calendar/', weight=30),
            MenuItem(pgettext_lazy("menu", "Мои курсы"), '/learning/courses/', weight=40),
            MenuItem(pgettext_lazy("menu", "Библиотека"), '/learning/library/', weight=50),
            MenuItem(pgettext_lazy("menu", "Полезное"), '/learning/useful/', weight=60),
            MenuItem(pgettext_lazy("menu", "Кодекс чести"), '/hc/', weight=70),
            MenuItem(pgettext_lazy("menu", "Проекты организаторов"), '/learning/internships/', weight=80),
        ],
        visible_to=[
            AcademicRoles.STUDENT_CENTER,
            AcademicRoles.VOLUNTEER,
        ],
        css_classes='for-students'),
    MenuItem(
        pgettext_lazy("menu", "Преподавание"),
        reverse('teaching:assignment_list', subdomain=PRIVATE),
        weight=20,
        children=[
            MenuItem(
                pgettext_lazy("menu", "Задания"),
                '/teaching/assignments/',
                weight=10,
                budge='assignments_teacher',
                selected_patterns=[
                    r"^/courses/.*/assignments/add$",
                    r"^/courses/.*/assignments/\d+/edit$"
                ]),
            MenuItem(
                pgettext_lazy("menu", "Расписание"),
                '/teaching/timetable/',
                weight=20,
                selected_patterns=[r" ^/teaching/calendar/"]),
            MenuItem(
                pgettext_lazy("menu", "Календарь"),
                '/teaching/full-calendar/',
                weight=30),
            MenuItem(
                pgettext_lazy("menu", "Мои курсы"),
                reverse("teaching:course_list", subdomain=PRIVATE),
                weight=40,
                budge='courseoffering_news'),
            MenuItem(
                pgettext_lazy("menu", "Ведомости"),
                '/teaching/marks/',
                weight=50),
        ],
        visible_to=[
            AcademicRoles.TEACHER_CENTER
        ],
        css_classes='for-teachers'),
    MenuItem(
        pgettext_lazy("menu", "Набор"),
        reverse('admission:interviews'),
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Собеседования"), '/admission/interviews/', weight=10),
            MenuItem(pgettext_lazy("menu", "Анкеты"), '/admission/applicants/', weight=20, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Результаты"), '/admission/results/', weight=30, for_staff=True),
        ],
        visible_to=[
            AcademicRoles.INTERVIEWER
        ]),
    MenuItem(
        pgettext_lazy("menu", "Проекты"),
        "/projects/reports/",
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Отчеты"), '/projects/reports/', weight=10, selected_patterns=[r"^/projects/\d+/report/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Проекты"), '/projects/available/', weight=20, selected_patterns=[r"^/projects/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Все проекты"), '/projects/all/', weight=30, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Все отчеты"), '/projects/reports-all/', weight=40, for_staff=True),
        ],
        visible_to=[
            AcademicRoles.PROJECT_REVIEWER
        ])
]

for item in public_menu:
    Menu.add_item("menu_public", item)

for item in private_menu:
    Menu.add_item("menu_private", item)
