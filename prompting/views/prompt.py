from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework import viewsets
from ..serializers import PromptSerializers
from ..models import PromptModel

class PromptView(viewsets.ModelViewSet):
    """
    PromptView.
    """
    serializer_class = PromptSerializers
    queryset = PromptModel.objects.all()
