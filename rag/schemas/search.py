from pydantic import BaseModel, Field

class SearchSchema(BaseModel):

    
    document_name: str = Field(description="The name of the document where the chunk was extracted")
    cosine_distance: float = Field(description="The cosine distance between the search vector and the chunk")
    chunk_text: str = Field(description="The chunk text that was vectorized and compared with the vectorized search")
    chunk_id: str = Field(description="The ID of the chunk")
    score: float | None = Field(description="The Re rank score of the chunk")
    
class ResultCunkListSchema(BaseModel):
    
    chunk_id: int = Field(description="The Id of the chunk")  
    cosine_distance: float = Field(description="The cosine distance between the search vector and the chunk") 
    score: float | None = Field(description="The Re rank score of the chunk")
     
class ResultSearchSchema(BaseModel):
    
    text: str = Field(description="The response for the search of answer input")
    chunk_id: str = Field(description="The ID for the top chunk selected for the response, just return the id of the top one")
    distance_top_chunk: str = Field(description="The cosine distance with the selected chunk for the response")
    chunk_list: list[ResultCunkListSchema]
