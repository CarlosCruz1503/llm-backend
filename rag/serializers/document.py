

from myapp.serializers.base import BaseSerializer
from rag.models.document import DocumentModel
from rest_framework import serializers

class DocumentSerializer(BaseSerializer):
    
    # file = serializers.FileField()
    
    
    class Meta: 
        model = DocumentModel
        fields= "__all__"
        read_only_fields = [
            "file_name","file_size", "number_of_pages", "deleted"
        ]
        
    # def create(self, validated_data):
        
    #     print("validated_data",validated_data)
    #     return super().create()
        