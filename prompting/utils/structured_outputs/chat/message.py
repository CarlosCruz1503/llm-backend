from pydantic import BaseModel, Field

class messageOutputModel(BaseModel):
    
    text: str = Field(description="The response to the question or the conclusion of the message")
    words_count: int = Field(description="The quantity of words used in the text")
    language:str = Field(description="The language in which is written the text")