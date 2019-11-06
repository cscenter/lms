from django.conf import settings
from rest_framework import serializers

from core.models import Branch


class BranchSerializer(serializers.ModelSerializer):
    is_club = serializers.SerializerMethodField()

    def get_is_club(self, obj):
        return obj.site_id == settings.CLUB_SITE_ID

    class Meta:
        model = Branch
        fields = ("id", "code", 'is_club')
