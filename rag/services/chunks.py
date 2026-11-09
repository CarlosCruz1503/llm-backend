import logging
import re

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

# A section heading in extracted PDF text: a short line that starts with a
# capital or digit, is not a bullet and does not end like a sentence.
_HEADING = re.compile(r"^[A-Z0-9].{1,58}$")
_TITLE_CONNECTORS = ("and", "or", "of", "the", "for", "-", ",")


def _is_heading(line: str) -> bool:
    return bool(_HEADING.match(line)) and not line.endswith((".", ",", ":", ";"))


def document_title(text: str) -> str:
    """First line of the document, joined with the next one when a long title
    wrapped (the first line then ends with a connector such as "and")."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    title = lines[0]
    if len(lines) > 1 and title.endswith(_TITLE_CONNECTORS) and _is_heading(lines[1]):
        title = f"{title} {lines[1]}"
    return title


def build_chunk_headers(text: str, chunks: list) -> list[str]:
    """A "Document: <title> / Section: <heading>" header for every chunk.

    The section is the heading in effect where the chunk starts, which is the
    context the chunk text itself is missing (a heading inside the chunk is
    already part of its text). Embedding and answering with this header lets a
    chunk from the middle of a document still say which document, and which
    status (e.g. ARCHIVED), it belongs to.
    """
    title = document_title(text)
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    title_lines = 1 if title == first_line else 2
    headings = []  # (character offset, heading)
    offset, seen_lines = 0, 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped:
            seen_lines += 1
            if seen_lines > title_lines and _is_heading(stripped):
                headings.append((offset, stripped))
        offset += len(line)

    headers = []
    for chunk in chunks:
        section = None
        for heading_offset, heading in headings:
            if heading_offset > chunk.start_index:
                break
            section = heading
        header = f"Document: {title}"
        if section:
            header += f"\nSection: {section}"
        headers.append(header)
    return headers


def create_and_save_chunks(document: DocumentModel, model, chunk_size, chunk_overlap, contextual_headers=False):

    logger.debug(
        "Chunking document %s with token_model=%s chunk_size=%s chunk_overlap=%s contextual_headers=%s",
        document.id, model, chunk_size, chunk_overlap, contextual_headers,
    )

    chunks = generate_chunks(document.text_content, model, chunk_size, chunk_overlap )
    # Stored apart from `text`; task_process_chunk embeds `contextual_text` (header + text).
    headers = build_chunk_headers(document.text_content, chunks) if contextual_headers else [None] * len(chunks)
    chunks_created =[]
    for index, (chunk, header) in enumerate(zip(chunks, headers), start=1):
        chunks_created.append(DocumentChunkModel.objects.create(
            provider=document.provider,
            document=document,
            text=chunk.text,
            header=header,
            sequence=index,
            token_model=model,
            token_size=chunk.token_count,
            token_overlap=chunk_overlap
        ))
    return chunks_created