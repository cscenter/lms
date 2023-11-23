from django.conf import settings
from django.utils.translation import pgettext_lazy

from core.menu import MenuItem
from core.urls import reverse
from menu import Menu

top_menu = [
    MenuItem(
        pgettext_lazy("menu", "Courses"),
        reverse("course_list", subdomain=settings.LMS_SUBDOMAIN),
        weight=10,
        excluded_patterns=[
            r"^/courses/.*/assignments/add$",
            r"^/courses/.*/assignments/\d+/edit$"
        ]),
    MenuItem(
        pgettext_lazy("menu", "Обучение"),
        reverse('study:assignment_list'),
        weight=10,
        children=[
            MenuItem(pgettext_lazy("menu", "Задания"), '/learning/assignments/', weight=10, budge='assignments_student'),
            MenuItem(pgettext_lazy("menu", "Моё расписание"), '/learning/timetable/', weight=20, selected_patterns=[r" ^/learning/calendar/"]),
            MenuItem(pgettext_lazy("menu", "Календарь"), '/learning/full-calendar/', weight=30),
            MenuItem(pgettext_lazy("menu", "Мои курсы"), '/learning/courses/', weight=40),
            MenuItem(pgettext_lazy("menu", "Полезное"), '/learning/useful/', weight=60),
            MenuItem(pgettext_lazy("menu", "Кодекс чести"), '/learning/hc/', weight=70),
            MenuItem(pgettext_lazy("menu", "Программы обучения"), '/learning/programs/', weight=70),
            MenuItem(pgettext_lazy("menu", "Проекты организаторов"), '/learning/internships/', weight=80),
        ],
        permissions=(
            "learning.view_study_menu",
        ),
        css_classes='for-students'),
    MenuItem(
        pgettext_lazy("menu", "Преподавание"),
        reverse('teaching:assignments_check_queue'),
        weight=20,
        children=[
            MenuItem(
                pgettext_lazy("menu", "Очередь проверки"),
                reverse('teaching:assignments_check_queue'),
                weight=10,
                budge='assignments_teacher',
                selected_patterns=[
                    r"^/courses/.*/assignments/add$",
                    r"^/courses/.*/assignments/\d+/edit$"
                ]),
            MenuItem(
                pgettext_lazy("menu", "Расписание"),
                reverse('teaching:timetable'),
                weight=20,
                selected_patterns=[r"^/teaching/calendar/"]),
            MenuItem(
                pgettext_lazy("menu", "Календарь"),
                reverse('teaching:calendar_full'),
                weight=30),
            MenuItem(
                pgettext_lazy("menu", "Мои курсы"),
                reverse("teaching:course_list"),
                weight=40,
                budge='courseoffering_news'),
            MenuItem(
                pgettext_lazy("menu", "Ведомости"),
                reverse('teaching:gradebook_list'),
                weight=50),
        ],
        permissions=(
            "learning.view_teaching_menu",
        ),
        css_classes='for-teachers'),
    MenuItem(
        pgettext_lazy("menu", "Проекты"),
        reverse('projects:report_list_reviewers'),
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Отчеты"), '/projects/reports/', weight=10, selected_patterns=[r"^/projects/\d+/reports/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Проекты"), '/projects/available/', weight=20, selected_patterns=[r"^/projects/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Все проекты"), '/projects/all/', weight=30, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Все отчеты"), '/projects/reports-all/', weight=40, for_staff=True),
        ],
        permissions=(
            "learning.view_projects_menu",
        ),
    ),
    MenuItem(
        pgettext_lazy("menu", "Курирование"),
        reverse('staff:gradebook_list'),
        weight=40,
        children=[
            MenuItem(pgettext_lazy("menu", "Ведомости"), reverse('staff:gradebook_list'), weight=10),
            MenuItem(pgettext_lazy("menu", "Поиск студентов"), reverse('staff:student_search'), weight=20),
            MenuItem(pgettext_lazy("menu", "Файлы"), reverse('staff:exports'), weight=30, selected_patterns=[
                r"^/staff/reports/enrollment-invitations/"
            ]),
            MenuItem(pgettext_lazy("menu", "Полезное"), reverse('staff:staff_warehouse'), weight=40),
            MenuItem(pgettext_lazy("menu", "Фейсбук"), reverse('staff:student_faces'), weight=50),
            MenuItem(pgettext_lazy("menu", "Пересечения"), reverse('staff:course_participants_intersection'), weight=60),
        ],
        for_staff=True,
        css_classes='for-staff'),
    MenuItem(
        pgettext_lazy("menu", "Набор"),
        reverse('admission:interviews:list'),
        weight=50,
        children=[
            MenuItem(pgettext_lazy("menu", "Собеседования"), url=reverse('admission:interviews:list'), weight=5),
            MenuItem(pgettext_lazy("menu", "Анкеты"), '/admission/applicants/', weight=10, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Отправка приглашений"), url=reverse("admission:interviews:invitations:send"), weight=20, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Приглашения"), url=reverse("admission:interviews:invitations:list"), weight=20, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Результаты"), reverse("admission:results:dispatch"), weight=30, for_staff=True),
        ],
        permissions=(
            "learning.view_admission_menu",
        ),
    ),
]


for item in top_menu:
    Menu.add_item("menu_private", item)
