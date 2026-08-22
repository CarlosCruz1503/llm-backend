from rest_framework import viewsets

from rest_framework.permissions import IsAuthenticated
from rag.models.search import SearchModel
from rag.serializers.search import SearchSerializer

class SearchViewSet(viewsets.ModelViewSet):
    
    queryset = SearchModel.objects.all()
    
    serializer_class = SearchSerializer
    
    permission_classes = [IsAuthenticated]