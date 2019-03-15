import re

from django.utils.translation import pgettext_lazy
from menu import Menu
from menu import MenuItem as _MenuItem


class MenuItem(_MenuItem):
    """
    Note:
        Only one item would be considered as selected.
        The last one in case of ambiguity.
    """
    for_staff = False
    visible_to = None
    # Additional check that item should be selected
    # Affects the parent visibility if `MENU_SELECT_PARENTS` setting is enabled
    # FIXME: remove relative patterns support? Or add the same to the excluded_patterns?
    selected_patterns = None
    excluded_patterns = None

    def __init__(self, title, url, **kwargs):
        super().__init__(title, url, **kwargs)
        if self.selected_patterns is not None:
            self.selected_patterns = [p.strip() for p in self.selected_patterns]
        if self.excluded_patterns is not None:
            self.excluded_patterns = [p.strip() for p in self.excluded_patterns]

    def check(self, request):
        """Evaluate if we should be visible for this request"""
        if self.visible_to is not None:
            user_groups = request.user.get_cached_groups()
            self.visible = bool(user_groups.intersection(self.visible_to))
        if callable(self.check_func):
            self.visible = self.check_func(request)
        if self.for_staff and not request.user.is_curator:
            self.visible = False

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
                # Relative path means pattern applicable to any subdomain
                if pattern.startswith('^/'):
                    pattern = (r"^" + request.build_absolute_uri(location='/') +
                               pattern[2:])
                # Deep copy for compiled regexp works in python 3.7+
                if re.compile(pattern).match(current_path):
                    matched = True
        elif matched and self.excluded_patterns is not None:
            for pattern in self.excluded_patterns:
                if re.compile(pattern).match(current_path):
                    matched = False
        return matched


public_menu = [
    MenuItem(
        pgettext_lazy("menu", "О центре"),
        '/v2/pages/about/',
        weight=10,
        children=[
            MenuItem(pgettext_lazy("menu", "Цели и история"), '/v2/pages/about_new/', weight=20),
            MenuItem(pgettext_lazy("menu", "История"), '/v2/pages/history/', weight=20),
            MenuItem(pgettext_lazy("menu", "Программа"), '/v2/pages/programs/', weight=30),
            MenuItem(pgettext_lazy("menu", "Команда"), '/v2/pages/team/', weight=40),
            MenuItem(pgettext_lazy("menu", "Преподаватели"), '/v2/pages/teachers/', weight=50),
            MenuItem(pgettext_lazy("menu", "Выпускники"), '/v2/pages/alumni/', weight=60, selected_patterns=[r"^/2016/$"]),
            MenuItem(pgettext_lazy("menu", "Отзывы"), '/v2/pages/testimonials/', weight=70),
        ],
        selected_patterns=[
            r'^/v2/pages/about_new/',
            r'^/v2/pages/history/',
            r'^/v2/pages/programs/',
            r'^/v2/pages/team/',
            r'^/v2/pages/teachers/',
            r'^/v2/pages/alumni/',
            r"^/events/"
        ]),
    MenuItem(
        pgettext_lazy("menu", "Курсы"),
        '/v2/pages/courses/',
        weight=20,
        excluded_patterns=[
            r"^/courses/.*/assignments/add$",
            r"^/courses/.*/assignments/\d+/edit$"
        ]),
    MenuItem(
        pgettext_lazy("menu", "Онлайн"),
        '/v2/pages/online_courses/',
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Онлайн-курсы"), '/v2/pages/online_courses/', weight=10),
            MenuItem(pgettext_lazy("menu", "Онлайн-программы"), 'https://code.stepik.org/', weight=20, is_external=True),
            MenuItem(pgettext_lazy("menu", "Видео"), '/v2/pages/video_archive/', weight=30),
        ],
        selected_patterns=[
            r'^/v2/pages/online_courses/',
            r'^/v2/pages/video_archive/',
        ]),

    MenuItem(
        pgettext_lazy("menu", "Лекторий"),
        'https://open.compscicenter.ru/',
        weight=40,
        is_external=True),
    MenuItem(
        pgettext_lazy("menu", "Поступление"),
        '/v2/pages/enrollment/',
        weight=50,
        children=[
            MenuItem(pgettext_lazy("menu", "Поступающим"), '/v2/pages/enrollment/', weight=10),
            MenuItem(pgettext_lazy("menu", "Подать заявку"), '/v2/pages/application/', weight=20),
            MenuItem(pgettext_lazy("menu", "Программа для поступления"), '/v2/pages/enrollment/program/', weight=30),
            MenuItem(pgettext_lazy("menu", "Вопросы и ответы"), '/v2/pages/faq/', weight=40),
        ],
        selected_patterns=[
            r'^/v2/pages/enrollment/',
            r'^/v2/pages/faq/',
        ]),
    # Private part (my.* domain)
    MenuItem(
        pgettext_lazy("menu", "Обучение"),
        '/v2/pages/learning/',
        weight=10,
        children=[
            MenuItem(pgettext_lazy("menu", "Задания"), '/learning/assignments/', weight=10, budge='assignments_student'),
            MenuItem(pgettext_lazy("menu", "Моё расписание"), '/learning/timetable/', weight=20, selected_patterns=[r" ^/learning/calendar/"]),
            MenuItem(pgettext_lazy("menu", "Календарь"), '/learning/full-calendar/', weight=30),
            MenuItem(pgettext_lazy("menu", "Мои курсы"), '/learning/courses/', weight=40),
            MenuItem(pgettext_lazy("menu", "Библиотека"), '/learning/library/', weight=50),
            MenuItem(pgettext_lazy("menu", "Полезное"), '/learning/useful/', weight=60),
            MenuItem(pgettext_lazy("menu", "Кодекс чести"), '/learning/hc/', weight=70),
            MenuItem(pgettext_lazy("menu", "Проекты организаторов"), '/learning/internships/', weight=80),
        ],
        css_classes='for-students'),
    MenuItem(
        pgettext_lazy("menu", "Преподавание"),
        '#',
        weight=20,
        children=[
            MenuItem(
                pgettext_lazy("menu", "Задания"),
                '#',
                weight=10,
                budge='assignments_teacher',
                selected_patterns=[
                    r"^/courses/.*/assignments/add$",
                    r"^/courses/.*/assignments/\d+/edit$"
                ]),
            MenuItem(
                pgettext_lazy("menu", "Расписание"),
                '#',
                weight=20,
                selected_patterns=[r"^/teaching/calendar/"]),
            MenuItem(
                pgettext_lazy("menu", "Календарь"),
                '#',
                weight=30),
            MenuItem(
                pgettext_lazy("menu", "Мои курсы"),
                '#',
                weight=40,
                budge='courseoffering_news'),
            MenuItem(
                pgettext_lazy("menu", "Ведомости"),
                '#',
                weight=50),
        ],
        visible_to=[
        ],
        css_classes='for-teachers'),
    MenuItem(
        pgettext_lazy("menu", "Набор"),
        '#',
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Собеседования"), '/admission/interviews/', weight=10),
            MenuItem(pgettext_lazy("menu", "Анкеты"), '/admission/applicants/', weight=20, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Результаты"), '/admission/results/', weight=30, for_staff=True),
        ],
        visible_to=[
        ]),
    MenuItem(
        pgettext_lazy("menu", "Проекты"),
        '#',
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Отчеты"), '/projects/reports/', weight=10, selected_patterns=[r"^/projects/\d+/report/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Проекты"), '/projects/available/', weight=20, selected_patterns=[r"^/projects/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Все проекты"), '/projects/all/', weight=30, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Все отчеты"), '/projects/reports-all/', weight=40, for_staff=True),
        ],
        visible_to=[
        ]),
    MenuItem(
        pgettext_lazy("menu", "Компоненты"),
        '/v2/components/',
        weight=50),
]


for item in public_menu:
    Menu.add_item("menu", item)
