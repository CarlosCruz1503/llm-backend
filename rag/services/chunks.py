import tiktoken
from chonkie import TokenChunker

from prompting.constants import DEFAULT_OVERLAP_TOKENS_FOR_CHUNK, DEFAULT_TOKEN_MODEL, MAX_TOKENS_FOR_CHUNK
from rag.models.document import DocumentModel
from rag.models.document_chunk import DocumentChunkModel

def generate_chunks(text:str, model:str,chunk_size:int, chunk_overlap:int )-> list:
    
    tokenizer = tiktoken.get_encoding(model)
    
    # Set a chunk size of 150 tokens with a 50-token overlap
    chunker = TokenChunker(
        tokenizer=tokenizer, 
        chunk_size=MAX_TOKENS_FOR_CHUNK, 
        chunk_overlap=DEFAULT_OVERLAP_TOKENS_FOR_CHUNK
    )
    
    chunks = chunker.chunk(text)
    
    return chunks

def create_and_save_chunks(document: DocumentModel, model=DEFAULT_TOKEN_MODEL, chunk_size= MAX_TOKENS_FOR_CHUNK, chunk_overlap=DEFAULT_OVERLAP_TOKENS_FOR_CHUNK):
    
    chunks = generate_chunks(document.text_content, model, chunk_size, chunk_overlap )
    chunks_created =[]
    for index, chunk in enumerate(chunks, start=1):
        chunks_created.append(DocumentChunkModel.objects.create(
            provider=document.provider,
            document=document,
            text=chunk.text,
            sequence=index,
            token_model=model,
            token_size=chunk.token_count,
            token_overlap=chunk_overlap
        ))
    return chunks_created