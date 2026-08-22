from enum import Enum

from pydantic import BaseModel
from prompting.schemas.prompt import (
    SummarizeOutputModel,
    classifyOutputModel,
    keyWordsOutputModel
)

class PromptType(str, Enum):
    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    EXTRACT_KEYWORDS = "extract_keywords"

class PROMPTS:
    name: str
    prompt: str
    structured_output: BaseModel
    
    def __init__(self, name,prompt,structured_output):
        self.name = name
        self.prompt = prompt
        self.structured_output = structured_output

SYSTEM_PROMPTS: dict[PROMPTS]= {
    PromptType.SUMMARIZE: PROMPTS(
        PromptType.SUMMARIZE, 
            """
            You are an expert text summarizer.

            Return a concise summary preserving the most important ideas.
            Do not add information that is not present in the text.
            """, 
        SummarizeOutputModel),  
    PromptType.CLASSIFY:PROMPTS(
        PromptType.CLASSIFY,
        """
                You are a text classification assistant.

                Classify the provided text into one category.

                Possible categories:
                - Technology
                - Finance
                - Healthcare
                - Education
                - Sports
                - Politics
                - Entertainment
                - Other

                Return only the category name.
        """,
        classifyOutputModel)
    ,
    PromptType.EXTRACT_KEYWORDS: PROMPTS(
        PromptType.EXTRACT_KEYWORDS,
        """"
            Extract the most relevant keywords from the text.

            Requirements:
            - Return between 5 and 10 keywords.
            - Avoid duplicates.
            - Keep keywords concise.
            - Return them as a comma-separated list.
        """,
        keyWordsOutputModel
    )
    
}