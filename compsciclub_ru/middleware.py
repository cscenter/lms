from django.conf import settings

from core.models import Branch


class CurrentBranchMiddleware:
    """
    Middleware that sets `branch` attribute to request object based on
    subdomain value.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow to add the missing branch through the admin interface
        if not request.path.startswith(settings.ADMIN_URL):
            request.branch = Branch.objects.get_current(request)
        return self.get_response(request)
