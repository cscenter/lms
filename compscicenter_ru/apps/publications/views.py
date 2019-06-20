from django.views.generic import DetailView

from publications.models import ProjectPublication, OpenLecture


class ProjectPublicationView(DetailView):
    context_object_name = "project"
    template_name = "compscicenter_ru/publications/project.html"

    def get_queryset(self):
        return ProjectPublication.objects.prefetch_related("projects")


class OpenLectureView(DetailView):
    context_object_name = "open_lecture"
    slug_url_kwarg = "slug"
    template_name = "compscicenter_ru/publications/open_lecture.html"

    def get_queryset(self):
        return OpenLecture.objects.get_queryset()
