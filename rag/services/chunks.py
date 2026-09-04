import logging

import tiktoken
from chonkie import TokenChunker
from rag.models.document import DocumentModel
from rag.models.document_chunk import DocumentChunkModel

logger = logging.getLogger(__name__)


def generate_chunks(text:str, model:str, chunk_size:int, chunk_overlap:int) -> list:
    
    tokenizer = tiktoken.get_encoding(model)
    
    # Set a chunk size of n tokens with a n token overlap
    chunker = TokenChunker(
        tokenizer=tokenizer, 
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap
    )
    
    chunks = chunker.chunk(text)
    
    return chunks 

def create_and_save_chunks(document: DocumentModel, model, chunk_size, chunk_overlap):

    logger.debug(
        "Chunking document %s with token_model=%s chunk_size=%s chunk_overlap=%s",
        document.id, model, chunk_size, chunk_overlap,
    )

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