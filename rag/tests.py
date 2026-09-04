from django.test import TestCase

from rag.constants import DocumentStatusChoices
from rag.models.document import DocumentModel
from rag.tasks import task_finalize_document, task_process_chunk


def _create_document(**overrides):
    defaults = {
        "file": "documents/test.pdf",
        "file_name": "test.pdf",
        "file_size": 1234.0,
    }
    defaults.update(overrides)
    return DocumentModel.objects.create(**defaults)


class TaskFinalizeDocumentTests(TestCase):
    """Chord callback for the chunk-embedding fan-out (see rag/tasks.py and
    README > The RAG pipeline) — the only place a document's terminal status
    actually gets set once every chunk has been processed.
    """

    def test_marks_completed_when_every_chunk_succeeded(self):
        document = _create_document(status=DocumentStatusChoices.EMBEDDING)

        task_finalize_document([True, True, True], document.id)

        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatusChoices.COMPLETED)
        self.assertIsNone(document.error)

    def test_marks_failed_when_any_chunk_failed(self):
        document = _create_document(status=DocumentStatusChoices.EMBEDDING)

        task_finalize_document([True, False, True], document.id)

        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatusChoices.FAILED)
        self.assertTrue(document.error)

    def test_does_not_overwrite_a_more_specific_existing_error(self):
        document = _create_document(
            status=DocumentStatusChoices.EMBEDDING,
            error="Chunk 7 failed permanently: quota exceeded",
        )

        task_finalize_document([True, False], document.id)

        document.refresh_from_db()
        self.assertEqual(document.error, "Chunk 7 failed permanently: quota exceeded")


class TaskProcessChunkFinalFailureTests(TestCase):
    """Regression test: on the final retry, the failure path used to
    reference `chunk` even when the exception came from the very lookup
    that would have bound it (DocumentChunkModel.objects.get()) — raising
    UnboundLocalError and masking the real error instead of recording it on
    the document (see rag/tasks.py::task_process_chunk).
    """

    def test_missing_chunk_is_handled_without_crashing(self):
        document = _create_document(status=DocumentStatusChoices.EMBEDDING)
        missing_chunk_id = 999999

        original_max_retries = task_process_chunk.max_retries
        task_process_chunk.max_retries = 0  # force the final-failure branch immediately
        try:
            result = task_process_chunk.apply(args=(missing_chunk_id, document.id)).get(propagate=False)
        finally:
            task_process_chunk.max_retries = original_max_retries

        self.assertFalse(result)
        document.refresh_from_db()
        self.assertTrue(document.error)
