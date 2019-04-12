from django.views.generic import DetailView

from publications.models import ProjectPublication


class ProjectPublicationView(DetailView):
    context_object_name = "project"
    template_name = "compscicenter_ru/projects/project_publication.html"

    def get_queryset(self):
        return ProjectPublication.objects.prefetch_related("projects")
