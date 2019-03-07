from rest_framework.generics import CreateAPIView

from admission.api.serializers import ApplicantSerializer


class ApplicantCreateAPIView(CreateAPIView):
    serializer_class = ApplicantSerializer
