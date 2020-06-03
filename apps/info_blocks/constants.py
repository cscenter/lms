from django.utils.translation import ugettext_lazy as _


class CurrentInfoBlockTags:
    """
    These tags are used to display relevant items in current views for useful, honor code and internships.
    Need to be kept in sync with actual DB values, will be removed in favor of tabs in the new design.
    """
    USEFUL = _("Infoblock|Useful")
    HONOR_CODE = _("Infoblock|Honor Code")
    INTERNSHIP = _("Infoblock|Internships")
