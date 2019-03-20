from django.conf import settings
from django.utils.translation import pgettext_lazy
from menu import Menu

from core.menu import MenuItem
from core.urls import reverse

PRIVATE = settings.LMS_SUBDOMAIN
PUBLIC_DOMAIN = reverse('index')[:-1]  # remove trailing slash

public_menu = [
    MenuItem(
        pgettext_lazy("menu", "Programs"),
        reverse('on_campus_programs'),
        weight=10,
        children=[
            MenuItem(pgettext_lazy("menu", "On Campus"), reverse('on_campus_programs'), weight=20),
            MenuItem(pgettext_lazy("menu", "Distance"), reverse('distance_program'), weight=30),
        ],
        selected_patterns=[
            r"^/events/"
        ]),
    MenuItem(
        pgettext_lazy("menu", "Courses"),
        PUBLIC_DOMAIN + '/courses/',
        weight=20,
        excluded_patterns=[
            r"^/courses/.*/assignments/add$",
            r"^/courses/.*/assignments/\d+/edit$"
        ]),
    MenuItem(
        pgettext_lazy("menu", "Online Education"),
        PUBLIC_DOMAIN + '/online/',
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Online courses"), reverse('online_courses:list'), weight=10),
            MenuItem(pgettext_lazy("menu", "Online programs"), 'https://code.stepik.org/', weight=20, is_external=True),
            MenuItem(pgettext_lazy("menu", "Video"), reverse('course_video_list'), weight=30),
            MenuItem(pgettext_lazy("menu", "Lecture Hall"), 'https://open.compscicenter.ru/', weight=40, is_external=True),
        ]),
    MenuItem(
        pgettext_lazy("menu", "Admission"),
        PUBLIC_DOMAIN + '/application/',
        weight=50,
        children=[
            MenuItem(pgettext_lazy("menu", "Apply"), PUBLIC_DOMAIN + '/application/', weight=20),
            MenuItem(pgettext_lazy("menu", "Checklist"), PUBLIC_DOMAIN + '/enrollment/checklist/', weight=20),
            MenuItem(pgettext_lazy("menu", "Program for Admission"), PUBLIC_DOMAIN + '/enrollment/program/', weight=30),
            MenuItem(pgettext_lazy("menu", "FAQ"), reverse('faq'), weight=40),
        ]),
    MenuItem(
        pgettext_lazy("menu", "About"),
        reverse('history'),
        weight=60,
        children=[
            MenuItem(pgettext_lazy("menu", "History"), reverse('history'),
                     weight=20),
            MenuItem(pgettext_lazy("menu", "Team"), reverse('team'), weight=40),
            MenuItem(pgettext_lazy("menu", "Teachers"), reverse('teachers'),
                     weight=50),
            MenuItem(pgettext_lazy("menu", "Alumni"), reverse('alumni'),
                     weight=60, selected_patterns=[r"^/2016/$"]),
            MenuItem(pgettext_lazy("menu", "Testimonials"),
                     reverse('testimonials'), weight=70),
        ],
        selected_patterns=[
            r"^/events/"
        ]),
]


for item in public_menu:
    Menu.add_item("menu_public", item)
