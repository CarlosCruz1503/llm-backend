from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rag.models.document import DocumentModel
from rag.serializers.document import DocumentSerializer
class DocumentViewSet(viewsets.ModelViewSet):
    
    permission_classes = [IsAuthenticated]
    
    queryset = DocumentModel.objects.all()
    
    serializer_class = DocumentSerializer
    # Essential parsers for handling file binary data
    parser_classes = [MultiPartParser, FormParser] 