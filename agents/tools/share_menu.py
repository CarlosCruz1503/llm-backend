from google.genai import types

from agents.tools.base import BaseTool
from restaurant.services.menu import MenuService
from restaurant.services.restaurant import get_default_restaurant


class ShareMenuTool(BaseTool):

    name: str = "share_menu"

    description: str = "This functions is to return the menu of this restaurant"

    def get_name(self):
        return self.name

    def execute(self):
        restaurant = get_default_restaurant()
        if restaurant is None:
            return "Sorry, the menu isn't available right now."
        return MenuService().get_formatted_menu(restaurant)

    def schema(self):
        function = types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema={}
        )
        return types.Tool(function_declarations=[function])
