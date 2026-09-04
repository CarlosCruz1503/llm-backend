import logging

from celery import chord, shared_task

from prompting.services.client import create_client_for_embedding
from rag.constants import DocumentStatusChoices
from rag.models.document import DocumentModel
from rag.models.document_chunk import DocumentChunkModel
from rag.services.document import ChunkService, DocumentService

logger = logging.getLogger(__name__)


@shared_task
def add(x, y):
    return x + y


@shared_task(bind=True,
             max_retries=3,
             retry_backoff=4)
def task_process_document(self, document_id: int, chunk_model=None, chunk_size=None, chunk_overlap=None) -> int:
    # Returns the document's id rather than the DocumentModel instance
    # itself: Celery stores every task's return value in the result backend
    # via JSON, and a Django model instance isn't JSON-serializable (it
    # fails with kombu.exceptions.EncodeError once the task tries to report
    # itself done).
    #
    # chunk_model/chunk_size/chunk_overlap are optional overrides (used by
    # the RAG evaluation experiments) forwarded to task_create_and_process_chunks.
    # They travel as serialized task args through the broker, so — unlike
    # mutating a module/class attribute in the caller's process — they
    # actually reach whichever process runs the celery worker.
    try:
        document_service = DocumentService()
        document = document_service.process_document(document_id)
        if document.text_extracted:
            task_create_and_process_chunks.delay(
                document.id, chunk_model=chunk_model, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        return document.id
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(f"Extraction of PDF content for document {document_id} failed permanently after max retries: {exc}")
            document = DocumentModel.objects.get(pk=document_id)
            document.text_extracted = False
            document.error = f"Error: {exc}"
            document.status = DocumentStatusChoices.FAILED
            document.save(update_fields=["text_extracted", "error", "status"])
            return document.id
        raise self.retry(exc=exc, countdown=10)


@shared_task(bind=True,
             max_retries=3,
             retry_backoff=4)
def task_create_and_process_chunks(self, document_id: int, chunk_model=None, chunk_size=None, chunk_overlap=None) -> None:
    chunk_service = ChunkService()
    try:
        chunks = chunk_service.process_chunks(document_id, model=chunk_model, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        # `chord` fires task_finalize_document once every task_process_chunk
        # in the group has finished, whether they succeeded or not — that's
        # the only reliable signal that embedding generation is actually
        # done, since the chunks are otherwise processed independently and
        # in parallel.
        chord(
            (task_process_chunk.s(chunk.id, document_id) for chunk in chunks),
            task_finalize_document.s(document_id),
        ).apply_async()
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(f"Chunking of document {document_id} failed permanently after max retries: {exc}")
            document = DocumentModel.objects.get(pk=document_id)
            document.error = f"Error: {exc}"
            document.status = DocumentStatusChoices.FAILED
            document.save(update_fields=["error", "status"])
            return
        raise self.retry(exc=exc, countdown=10)


@shared_task(bind=True,
             max_retries=3,
             retry_backoff=4)
def task_process_chunk(self, chunk_id: int, document_id: int) -> bool:
    try:
        chunk = DocumentChunkModel.objects.get(pk=chunk_id)
        client = create_client_for_embedding(chunk.provider, chunk.text)
        response = client.embed_content()
        chunk.embedding = response
        chunk.save(update_fields=["embedding"])
        return True
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            # `chunk` may not be bound if DocumentChunkModel.objects.get()
            # itself is what raised (e.g. the row was deleted, or a DB
            # hiccup) — re-fetch by id rather than assuming it exists, so
            # this final-failure path can't itself crash with an
            # UnboundLocalError and mask the real error.
            document = DocumentModel.objects.get(pk=document_id)
            document.error = f"Error: {exc}"
            logger.error(f"Chunk {chunk_id} failed permanently to be processed after max retries {exc}")
            document.save(update_fields=["error"])

            chunk = DocumentChunkModel.objects.filter(pk=chunk_id).first()
            if chunk is not None:
                chunk.error_embedding = f"Error: {exc}"
                chunk.save(update_fields=["error_embedding"])
            return False

        # Re-raise the retry
        raise self.retry(exc=exc, countdown=10)


@shared_task
def task_finalize_document(chunk_results: list[bool], document_id: int) -> None:
    """Chord callback for task_create_and_process_chunks: `chunk_results` is
    the list of every task_process_chunk return value (True/False), in the
    same order the chunks were queued in.
    """
    document = DocumentModel.objects.get(pk=document_id)
    if all(chunk_results):
        document.status = DocumentStatusChoices.COMPLETED
    else:
        document.status = DocumentStatusChoices.FAILED
        if not document.error:
            document.error = "One or more chunks failed to generate embeddings."
    document.save(update_fields=["status", "error"])
