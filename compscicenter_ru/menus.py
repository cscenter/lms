from django.conf import settings
from django.utils.translation import pgettext_lazy

from core.menu import MenuItem
from core.urls import reverse, reverse_lazy
from menu import Menu

PRIVATE = settings.LMS_SUBDOMAIN
PUBLIC_DOMAIN = reverse('index')[:-1]  # remove trailing slash

public_menu = [
    MenuItem(
        "Направления",
        reverse('syllabus_list'),
        weight=10,
        selected_patterns=[
            r"^/events/"
        ]),
    MenuItem(
        pgettext_lazy("menu", "Courses"),
        reverse("course_list"),
        weight=20
    ),
    MenuItem(
        pgettext_lazy("menu", "Online Education"),
        PUBLIC_DOMAIN + '/online/',
        weight=30,
        children=[
            MenuItem(pgettext_lazy("menu", "Online courses"), reverse('online_courses:list'), weight=10),
            MenuItem(pgettext_lazy("menu", "Online programs"), 'https://code.stepik.org/', weight=20, is_external=True),
            MenuItem(pgettext_lazy("menu", "Video Records"), reverse('video_list'), weight=30),
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
        reverse_lazy('teachers'),
        weight=60,
        children=[
            MenuItem(pgettext_lazy("menu", "Teachers"), reverse_lazy('teachers'), weight=10),
            MenuItem(pgettext_lazy("menu", "Alumni"), reverse_lazy('alumni'), weight=20, selected_patterns=[r"^/2016/$"]),
            MenuItem(pgettext_lazy("menu", "Testimonials"), reverse_lazy('testimonials'), weight=30),
            MenuItem(pgettext_lazy("menu", "Team"), reverse_lazy('team'), weight=40),
            MenuItem(pgettext_lazy("menu", "History"), reverse_lazy('history'), weight=50),
        ],
        selected_patterns=[
            r"^/events/"
        ])
]


for item in public_menu:
    Menu.add_item("menu_public", item)
