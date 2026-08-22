from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class Category(str, Enum):
    NOVEL = "Novel"
    FANTASY = "Fantasy"
    SCIENCE_FICTION = "Science Fiction"
    MYSTERY = "Mystery"
    HISTORICAL_FICTION = "Historical Fiction"
    BIOGRAPHY = "Biography"
    AUTOBIOGRAPHY = "Autobiography"
    POETRY = "Poetry"
    DRAMA = "Drama"
    
class Classification(str, Enum):
    TECHNOLOGY = "Technology"
    FINANCE = "Finance"
    HEALTHCARE = "Healthcare"
    EDUCATION = "Education"
    SPORTS = "Sports"
    POLITICS = "Politics"
    ENTERTAINMENT = "Entertainment"
    OTHER = "Other"
    
    
class SummarizeOutputModel(BaseModel):

    text: str = Field(description="The summary of the the text")
    category: Category = Field(description="The category of the the text")
    words_count: int = Field(description="The quantity of words used in the text")
    language:str = Field(description="The language in which is written the text")
    
    
class classifyOutputModel(BaseModel):
    text: Classification = Field(description="The classification of the the text")
    words_count: int = Field(description="The quantity of words used in the text")
    language:str = Field(description="The language in which is written the text")
    
class keyWordsOutputModel(BaseModel):
    text: str = Field(description="The key_words of the the text separed by ','")
    words_count: int = Field(description="The quantity of words used in the text")
    language:str = Field(description="The language in which is written the text")
    