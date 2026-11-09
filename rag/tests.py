from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from myapp.constants import DEFAULT_EMBEDDING_DIMENTIONS
from rag.constants import DocumentStatusChoices
from rag.models.document import DocumentModel
from rag.models.document_chunk import DocumentChunkModel
from rag.models.search import SearchModel
from rag.services.chunks import build_chunk_headers, create_and_save_chunks, document_title
from rag.services.evaluation import score_retrieval, summarize_retrieval
from rag.services.search import SearchService, retrieve_chunks
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


def _vector(*leading):
    """An embedding whose first values are `leading` and the rest zeros."""
    values = [*leading] + [0.0] * (int(DEFAULT_EMBEDDING_DIMENTIONS) - len(leading))
    return values


def _create_chunk(document, text, embedding, token_size=50):
    return DocumentChunkModel.objects.create(
        document=document, text=text, sequence=1, token_model="cl100k_base",
        token_size=str(token_size), token_overlap="0", embedding=embedding,
    )


class RetrieveChunksTests(TestCase):
    """Retrieval without the LLM (rag/services/search.py:retrieve_chunks)."""

    def setUp(self):
        self.menu = _create_document(file_name="menu.pdf")
        self.policies = _create_document(file_name="policies.pdf")
        # Distances from the query (1, 0): near < middle < far.
        self.near = _create_chunk(self.menu, "near", _vector(1.0, 0.1))
        self.middle = _create_chunk(self.policies, "middle", _vector(1.0, 0.6))
        self.far = _create_chunk(self.menu, "far", _vector(0.0, 1.0))
        self.query = _vector(1.0, 0.0)

    def test_returns_top_k_nearest_in_distance_order(self):
        chunks = retrieve_chunks("q", self.query, top_k=2, threshold=2.0, reranker_enabled=False)

        self.assertEqual([c["chunk_id"] for c in chunks], [self.near.id, self.middle.id])
        self.assertEqual(chunks[0]["document_name"], "menu.pdf")

    def test_threshold_drops_distant_chunks(self):
        chunks = retrieve_chunks("q", self.query, top_k=3, threshold=0.5, reranker_enabled=False)

        self.assertNotIn(self.far.id, [c["chunk_id"] for c in chunks])

    def test_document_ids_restricts_the_search(self):
        chunks = retrieve_chunks("q", self.query, top_k=3, threshold=2.0, reranker_enabled=False,
                                 document_ids=[self.policies.id])

        self.assertEqual([c["chunk_id"] for c in chunks], [self.middle.id])

    @patch("rag.services.search._get_reranker")
    def test_reranker_reorders_the_pool_and_keeps_only_top_n(self, get_reranker):
        # Scores follow the pool order (near, middle, far): the reranker prefers "far".
        get_reranker.return_value.rerank.return_value = iter([0.1, 0.5, 0.9])

        chunks = retrieve_chunks("q", self.query, top_k=3, threshold=2.0, reranker_enabled=True, rerank_top_n=2)

        self.assertEqual([c["chunk_id"] for c in chunks], [self.far.id, self.middle.id])
        self.assertEqual([c["score"] for c in chunks], [0.9, 0.5])


class SearchServiceRetrievedChunksTests(TestCase):
    """The search records what retrieval returned, not what the LLM says it used."""

    def setUp(self):
        User.objects.create_superuser("admin", "admin@example.com", "pass")
        document = _create_document(file_name="menu.pdf")
        self.chunk = _create_chunk(document, "near", _vector(1.0, 0.1))

    @patch("rag.services.search.create_client_for_search")
    def test_saves_retrieved_chunks_and_skips_embedding_when_vector_given(self, create_client):
        create_client.return_value.execute.return_value = {
            "input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "status": "Completed",
            "response_code": 200, "id": "req-1", "output": "answer",
            # The LLM claims a chunk that retrieval never returned.
            "output_dict": {"chunk_id": "", "distance_top_chunk": "0.1", "chunk_list": [{"chunk_id": 999}]},
        }
        search = SearchModel.objects.create(text="q")

        with patch("rag.services.search.create_client_for_embedding") as embed:
            SearchService().execute(search, top_k=1, threshold=2.0, reranker_enabled=False,
                                    query_embedding=_vector(1.0, 0.0))
            embed.assert_not_called()

        search.refresh_from_db()
        self.assertEqual(len(search.retrieved_chunks), 1)
        self.assertEqual(search.retrieved_chunks[0]["chunk_id"], self.chunk.id)
        self.assertEqual(search.retrieved_chunks[0]["rank"], 1)
        self.assertEqual(search.chunk_list, [{"chunk_id": 999}])


class ScoreRetrievalTests(TestCase):

    QUESTION = {
        "relevant_documents": ["policies.pdf", "menu.pdf"],
        "distractor_documents": ["archive.pdf"],
    }

    def _chunks(self, *documents):
        return [
            {"chunk_id": index, "document_name": name, "cosine_distance": 0.1 * index}
            for index, name in enumerate(documents, start=1)
        ]

    def test_scores_rank_recall_distractors_and_context_size(self):
        chunks = self._chunks("archive.pdf", "policies.pdf", "policies.pdf")

        result = score_retrieval(self.QUESTION, chunks, {1: 40, 2: 60, 3: 50})

        self.assertTrue(result["hit"])
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["reciprocal_rank"], 0.5)
        self.assertTrue(result["distractor_retrieved"])
        self.assertEqual(result["context_tokens"], 150)
        self.assertEqual(result["documents"], ["archive.pdf", "policies.pdf"])

    def test_miss_scores_zero(self):
        result = score_retrieval(self.QUESTION, self._chunks("other.pdf"), {})

        self.assertFalse(result["hit"])
        self.assertEqual(result["reciprocal_rank"], 0.0)

    def test_unanswerable_question_has_no_hit_metrics(self):
        result = score_retrieval({"relevant_documents": []}, self._chunks("other.pdf"), {})

        self.assertIsNone(result["hit"])
        self.assertIsNone(result["recall"])
        self.assertIsNone(result["distractor_retrieved"])

    def test_summary_averages_answerable_only(self):
        rows = [
            {"type": "single", **score_retrieval(self.QUESTION, self._chunks("menu.pdf"), {})},
            {"type": "single", **score_retrieval(self.QUESTION, self._chunks("other.pdf"), {})},
            {"type": "unanswerable", **score_retrieval({"relevant_documents": []}, self._chunks("x.pdf", "y.pdf"), {})},
        ]

        summary = summarize_retrieval(rows)

        self.assertEqual(summary["hit_rate"], 0.5)
        self.assertEqual(summary["mrr"], 0.5)
        self.assertEqual(summary["unanswerable_chunks"], 2)
        self.assertEqual(summary["recall_by_type"], {"single": 0.25})


ARCHIVE_TEXT = """The Garden Table - Restaurant Policies 2024 (ARCHIVED)
ARCHIVED DOCUMENT. These policies were superseded in 2026.
Opening hours (2024)
- Tuesday to Sunday: 12:00 PM to 9:00 PM
Bringing your own wine (2024)
Guests could bring their own wine. The corkage fee was $15 per bottle.
"""


class ContextualChunkHeaderTests(TestCase):
    """Contextual chunk headers (rag/services/chunks.py)."""

    def test_title_is_the_first_line(self):
        self.assertEqual(document_title(ARCHIVE_TEXT), "The Garden Table - Restaurant Policies 2024 (ARCHIVED)")

    def test_wrapped_title_is_joined(self):
        text = "The Garden Table Downtown - Location, Parking and\nTransport\nAddress\n214 Alder Street.\n"

        self.assertEqual(document_title(text), "The Garden Table Downtown - Location, Parking and Transport")

    def test_header_names_the_document_and_the_section_in_effect_at_chunk_start(self):
        corkage = ARCHIVE_TEXT.index("Guests could")
        chunks = [SimpleNamespace(start_index=0), SimpleNamespace(start_index=corkage)]

        headers = build_chunk_headers(ARCHIVE_TEXT, chunks)

        self.assertEqual(headers[0], "Document: The Garden Table - Restaurant Policies 2024 (ARCHIVED)")
        self.assertEqual(
            headers[1],
            "Document: The Garden Table - Restaurant Policies 2024 (ARCHIVED)\nSection: Bringing your own wine (2024)",
        )

    def test_chunks_store_the_header_and_embed_it_with_the_text(self):
        document = _create_document(file_name="archive.pdf", text_content=ARCHIVE_TEXT)

        chunks = create_and_save_chunks(document, "cl100k_base", chunk_size=20, chunk_overlap=0, contextual_headers=True)

        last = chunks[-1]
        self.assertIn("(ARCHIVED)", last.header)
        self.assertNotIn("ARCHIVED", last.text)
        self.assertEqual(last.contextual_text, f"{last.header}\n---\n{last.text}")

    def test_chunks_have_no_header_by_default(self):
        document = _create_document(file_name="archive.pdf", text_content=ARCHIVE_TEXT)

        chunks = create_and_save_chunks(document, "cl100k_base", chunk_size=20, chunk_overlap=0)

        self.assertTrue(all(chunk.header is None for chunk in chunks))
        self.assertEqual(chunks[0].contextual_text, chunks[0].text)

