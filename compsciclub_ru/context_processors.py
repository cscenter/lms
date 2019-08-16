from django.conf import settings

from core.models import Branch

BRANCHES = {}


def get_branches(request):
    if not BRANCHES:
        qs = Branch.objects.filter(site_id=request.site.id).order_by('order')
        for branch in qs:
            if branch.code != settings.DEFAULT_BRANCH_CODE:
                sub_domain = branch.code + "."
            else:
                sub_domain = ""
            branch.url = "{}://{}{}/".format(request.scheme, sub_domain,
                                             request.site.domain, '/')
            BRANCHES[branch.code] = branch
    return {
        "BRANCH_LIST": BRANCHES.values()
    }
