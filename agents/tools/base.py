from abc import ABC, abstractmethod

class BaseTool(ABC):

    name: str
    description: str
    
    @abstractmethod
    def get_name(self, **kwargs):
        pass

    @abstractmethod
    def execute(self, **kwargs):
        pass

    @abstractmethod
    def schema(self):
        pass
        
