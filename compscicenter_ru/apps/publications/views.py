from django.core.cache import cache
from django.db.models import Prefetch, prefetch_related_objects
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView
from vanilla import TemplateView

from compscicenter_ru.utils import TabList, Tab
from core.utils import bucketize
from projects.constants import ProjectTypes

from projects.models import Project
from publications.models import ProjectPublication, RecordedEvent
from users.models import User


class ProjectPublicationView(DetailView):
    context_object_name = "project"
    template_name = "compscicenter_ru/publications/project.html"

    def get_queryset(self):
        participants = Prefetch(
            "students",
            queryset=(User.objects
                      .only("id", "first_name", "last_name", "patronymic",
                            "photo", "cropbox_data")
                      .select_related("graduate_profile")
                      .order_by("last_name")))
        projects = Prefetch(
            "projects",
            queryset=(Project.objects.prefetch_related(participants))
        )
        return ProjectPublication.objects.prefetch_related(projects)


class RecordedEventView(DetailView):
    context_object_name = "recorded_event"
    slug_url_kwarg = "slug"
    template_name = "compscicenter_ru/publications/recorded_event.html"

    def get_queryset(self):
        return RecordedEvent.objects.get_queryset()


def _prefetch_project_participants():
    participants = Prefetch(
        "students",
        queryset=(User.objects
                  .only("id", "first_name", "last_name", "patronymic",
                        "photo", "cropbox_data")))
    projects = Prefetch("projects",
                        queryset=(Project.objects
                                  .prefetch_related(participants)))
    return projects


class ProjectsListView(TemplateView):
    template_name = "compscicenter_ru/projects/project_list.html"

    def get_context_data(self, **kwargs):
        tabs = TabList()
        selected_tab = self.request.GET.get('type', ProjectTypes.practice)
        qs = (ProjectPublication.published
              .prefetch_related(_prefetch_project_participants())
              .order_by('title'))
        project_publications = bucketize(qs, key=lambda p: p.type)
        for i, project_type in enumerate(project_publications):
            if project_type == ProjectTypes.practice:
                tab_name = _("Practices")
            elif project_type == ProjectTypes.research:
                tab_name = _("Research Works")
            else:
                tab_name = ProjectTypes.labels[project_type]
            tab = Tab(target=project_type, name=tab_name,
                      url=f"{self.request.path}?type={project_type}")
            tabs.add(tab)
            if project_type == selected_tab:
                tabs.set_active(project_type)
        return {
            "tabs": tabs,
            "project_publications": project_publications
        }


def get_random_project_publications(count, cache_key, **filters):
    """Returns reviews from graduated students with photo"""
    project_publications = cache.get(cache_key)
    if project_publications is None:
        participants = _prefetch_project_participants()
        project_publications = (ProjectPublication.published
                                .filter(**filters)
                                .prefetch_related(participants)
                                .order_by('?'))[:count]
        cache.set(cache_key, project_publications, 3600)
    return project_publications


PUBLICATIONS_CACHE_KEY_PREFIX = 'project_publications'


class ProjectPracticeView(TemplateView):
    template_name = "compscicenter_ru/projects/project_practice.html"

    def get_context_data(self, **kwargs):
        type_ = ProjectTypes.practice
        cache_key = f"{PUBLICATIONS_CACHE_KEY_PREFIX}_{type_}"
        samples = get_random_project_publications(3, cache_key, type=type_)
        return {
            "sample_projects": samples
        }


class ProjectResearchWorkView(TemplateView):
    template_name = "compscicenter_ru/projects/project_research.html"

    def get_context_data(self, **kwargs):
        type_ = ProjectTypes.research
        cache_key = f"{PUBLICATIONS_CACHE_KEY_PREFIX}_{type_}"
        samples = get_random_project_publications(3, cache_key, type=type_)
        return {
            "sample_projects": samples
        }
