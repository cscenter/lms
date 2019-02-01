class Redirect(Exception):
    def __init__(self, to, **kwargs):
        self.to = to
        self.kwargs = kwargs
