

from agents.tools.base import BaseTool
from agents.tools.create_reservation import CreateReservationTool
from myapp.constants import ProviderChoices
from rag.serializers.search import SearchSerializer
    
def search_resturant_information(question:str, provider:ProviderChoices = ProviderChoices.GEMINI):
        
    search_serializer = SearchSerializer(
        data={
                "text": question,
                "provider": provider
        }
    )
        
    if not search_serializer.is_valid():
        raise
    search = search_serializer.save()
        
    return search.response
