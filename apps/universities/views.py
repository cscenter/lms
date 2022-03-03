from typing import Any, List, Type

from rest_framework import serializers
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.views import APIBaseView
from core.http import APIRequest
from universities.models import City, Faculty, University
from universities.selectors import faculties_queryset, universities_queryset


class CityList(APIBaseView):
    authentication_classes: List[Type[BaseAuthentication]] = []
    permission_classes = (AllowAny,)

    class OutputSerializer(serializers.ModelSerializer):
        name = serializers.CharField(source='display_name')

        class Meta:
            model = City
            fields = ('id', 'name')

    def get(self, request: APIRequest, **kwargs: Any):
        queryset = City.objects.order_by('order', 'display_name')
        data = self.OutputSerializer(queryset, many=True).data
        return Response(data)


class UniversityList(APIBaseView):
    authentication_classes: List[Type[BaseAuthentication]] = []
    permission_classes = (AllowAny,)

    class FilterSerializer(serializers.Serializer):
        city = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        name = serializers.CharField(source='display_name')

        class Meta:
            model = University
            fields = ('id', 'city', 'name')

    def get(self, request: APIRequest, **kwargs: Any):
        filters_serializer = self.FilterSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)
        universities = universities_queryset(filters=filters_serializer.validated_data)
        data = self.OutputSerializer(universities, many=True).data
        return Response(data)


class FacultyList(APIBaseView):
    authentication_classes: List[Type[BaseAuthentication]] = []
    permission_classes = (AllowAny,)

    class FilterSerializer(serializers.Serializer):
        university = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        name = serializers.CharField(source='display_name')

        class Meta:
            model = Faculty
            fields = ('id', 'university', 'name')

    def get(self, request: APIRequest, **kwargs: Any):
        filters_serializer = self.FilterSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)
        faculties = faculties_queryset(filters=filters_serializer.validated_data)
        data = self.OutputSerializer(faculties, many=True).data
        return Response(data)
