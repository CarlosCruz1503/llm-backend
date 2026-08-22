import logging
from abc import ABC

from rag.constants import DocumentStatusChoices
from rag.models.document import DocumentModel
from rag.services.chunks import create_and_save_chunks
from rag.services.pdf import process_difficult_pdf

logger = logging.getLogger(__name__)


class DocumentService(ABC):

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


class ChunkService(ABC):

    def process_chunks(self, document_id):
        try:
            document = DocumentModel.objects.get(pk=document_id)
            document.status = DocumentStatusChoices.CHUNKING
            document.save(update_fields=["status"])

            chunks = create_and_save_chunks(document)

            document.status = DocumentStatusChoices.EMBEDDING
            document.save(update_fields=["status"])
            return chunks
        except Exception:
            logger.exception("Failed to generate document chunks")
            raise
