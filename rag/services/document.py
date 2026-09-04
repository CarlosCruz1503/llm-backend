import logging

from prompting.constants import DEFAULT_OVERLAP_TOKENS_FOR_CHUNK, DEFAULT_TOKEN_MODEL, MAX_TOKENS_FOR_CHUNK
from rag.constants import DocumentStatusChoices
from rag.models.document import DocumentModel
from rag.services.chunks import create_and_save_chunks
from rag.services.pdf import process_difficult_pdf

logger = logging.getLogger(__name__)


class DocumentService:

    def process_document(self, document_id):
        document = DocumentModel.objects.get(pk=document_id)
        document.status = DocumentStatusChoices.EXTRACTING
        document.save(update_fields=["status"])
        self.extract_content(document)
        return document

    def extract_content(self, document):
        try:
            page_size, pdf_text = process_difficult_pdf(document.file)

            document.page_size = page_size
            document.text_content = pdf_text
            document.text_extracted = True
            document.save(update_fields=["page_size", "text_content", "text_extracted"])
        except Exception as e:
            # A PDF parsing failure is deterministic (the same file will
            # always fail the same way), so this is recorded as a final
            # FAILED rather than left for the task to retry.
            document.text_extracted = False
            document.error = str(e)
            document.status = DocumentStatusChoices.FAILED
            document.save(update_fields=["text_extracted", "error", "status"])
            logger.exception("Failed to extract PDF content")


class ChunkService:

    def process_chunks(self, document_id, model=None, chunk_size=None, chunk_overlap=None):
        try:
            document = DocumentModel.objects.get(pk=document_id)
            document.status = DocumentStatusChoices.CHUNKING
            document.save(update_fields=["status"])

            # Callers (e.g. RAG evaluation experiments) may pass explicit
            # overrides; falling back to the env-backed defaults keeps normal
            # API usage unchanged.
            chunks = create_and_save_chunks(
                document,
                model=model if model is not None else DEFAULT_TOKEN_MODEL,
                chunk_size=chunk_size if chunk_size is not None else MAX_TOKENS_FOR_CHUNK,
                chunk_overlap=chunk_overlap if chunk_overlap is not None else DEFAULT_OVERLAP_TOKENS_FOR_CHUNK,
            )

            document.status = DocumentStatusChoices.EMBEDDING
            document.save(update_fields=["status"])
            return chunks
        except Exception:
            logger.exception("Failed to generate document chunks")
            raise
