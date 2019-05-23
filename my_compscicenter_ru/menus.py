from django.utils.translation import pgettext_lazy
from menu import Menu

from core.menu import MenuItem
from core.urls import reverse
from users.constants import AcademicRoles

top_menu = [
    MenuItem(
        pgettext_lazy("menu", "Courses"),
        reverse("course_list"),
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
            MenuItem(pgettext_lazy("menu", "Библиотека"), '/learning/library/', weight=50),
            MenuItem(pgettext_lazy("menu", "Полезное"), '/learning/useful/', weight=60),
            MenuItem(pgettext_lazy("menu", "Кодекс чести"), '/learning/hc/', weight=70),
            MenuItem(pgettext_lazy("menu", "Проекты организаторов"), '/learning/internships/', weight=80),
        ],
        visible_to=[
            AcademicRoles.STUDENT_CENTER,
            AcademicRoles.VOLUNTEER,
        ],
        css_classes='for-students'),
    MenuItem(
        pgettext_lazy("menu", "Преподавание"),
        reverse('teaching:assignment_list'),
        weight=20,
        children=[
            MenuItem(
                pgettext_lazy("menu", "Задания"),
                reverse('teaching:assignment_list'),
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
        reverse('projects:report_list_reviewers'),
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Отчеты"), '/projects/reports/', weight=10, selected_patterns=[r"^/projects/\d+/reports/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Проекты"), '/projects/available/', weight=20, selected_patterns=[r"^/projects/\d+/$"]),
            MenuItem(pgettext_lazy("menu", "Все проекты"), '/projects/all/', weight=30, for_staff=True),
            MenuItem(pgettext_lazy("menu", "Все отчеты"), '/projects/reports-all/', weight=40, for_staff=True),
        ],
        visible_to=[
            AcademicRoles.PROJECT_REVIEWER
        ]),
    MenuItem(
        pgettext_lazy("menu", "Курирование"),
        reverse('staff:course_markssheet_staff_dispatch'),
        weight=40,
        children=[
            MenuItem(pgettext_lazy("menu", "Ведомости"), reverse('staff:course_markssheet_staff_dispatch'), weight=10),
            MenuItem(pgettext_lazy("menu", "Поиск студентов"), reverse('staff:student_search'), weight=20),
            MenuItem(pgettext_lazy("menu", "Файлы"), reverse('staff:exports'), weight=30),
            MenuItem(pgettext_lazy("menu", "Полезное"), reverse('staff:staff_warehouse'), weight=40),
            MenuItem(pgettext_lazy("menu", "Фейсбук"), reverse('staff:student_faces'), weight=50),
            MenuItem(pgettext_lazy("menu", "Пересечения"), reverse('staff:course_participants_intersection'), weight=60),
        ],
        for_staff=True,
        css_classes='for-staff'),
]


for item in top_menu:
    Menu.add_item("menu_private", item)
