

from agents.tools.registry import ToolsRegistry
from agents.tools.create_reservation import CreateReservationTool
from agents.tools.share_menu import ShareMenuTool
from myapp.constants import ProviderChoices

from agents.services.client import create_client_for_agent
from agents.services.agents.base import BaseAgent

RestaurantTools = ToolsRegistry(tools=[CreateReservationTool, ShareMenuTool])

class RestaurantAgent(BaseAgent):
    
    tools = RestaurantTools
    
    def __init__(self) -> None:
        pass
    
    # def execute(self, content: str, provider: ProviderChoices = ProviderChoices.GEMINI ):
        
    #     client = create_client_for_agent(provider=provider, 
    #                                      content=content, 
    #                                      available_tools=self.tools)
        
    #     client.execute_agent_run()
        
        