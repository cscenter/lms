from django.views import generic

from news.models import News

class NewsDetailView(generic.DetailView):
    model = News

class NewsListView(generic.ListView):
    model = News

class NewsCreateView(generic.CreateView):
    model = News

class NewsUpdateView(generic.UpdateView):
    model = News
