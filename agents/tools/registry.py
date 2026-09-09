from agents.tools.base import BaseTool


class ToolsRegistry:
    
    tools:[BaseTool] = []
    
    def __init__(self, tools):
        self.tools = tools

    def get_tools_schemas(self):
        
        schemas = []
        for tool in self.tools:
            schemas.append(tool().schema())
        
        return schemas 

    def tools_execution(self, tool_name, execution_params):
        for tool in self.tools:
            tool_instance = tool()
            if tool_instance.get_name() in tool_name:
                return tool_instance.execute(**execution_params)

        raise TypeError("The function to execute doesnt exists")