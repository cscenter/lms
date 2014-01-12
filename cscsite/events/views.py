from django.views import generic

from events.models import Event

class EventDetailView(generic.DetailView):
    model = Event

class EventListView(generic.ListView):
    model = Event

class EventCreateView(generic.CreateView):
    model = Event

class EventUpdateView(generic.UpdateView):
    model = Event
