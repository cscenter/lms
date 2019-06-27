from django.views.generic import DetailView

from publications.models import ProjectPublication, RecordedEvent


class ProjectPublicationView(DetailView):
    context_object_name = "project"
    template_name = "compscicenter_ru/publications/project.html"

    def get_queryset(self):
        return ProjectPublication.objects.prefetch_related("projects")


class RecordedEventView(DetailView):
    context_object_name = "recorded_event"
    slug_url_kwarg = "slug"
    template_name = "compscicenter_ru/publications/recorded_event.html"

    def get_queryset(self):
        return RecordedEvent.objects.get_queryset()
