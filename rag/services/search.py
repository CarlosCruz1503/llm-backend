import logging
from functools import lru_cache

from pgvector.django import CosineDistance

from myapp.constants import DEFAULT_TOP_K_RETRIEVE_SIZE, RERANK_TOP_N, RERANKER_MODEL, COSINE_DISTANCE_THRESHOLD
from agents.services.client import create_client_for_embedding, create_client_for_search, save_client_reponse_for_search
from rag.constants import RERANKER_ENABLED
from rag.models.document_chunk import DocumentChunkModel

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_reranker():
    # Deferred import: loading fastembed (and the cross-encoder weights it
    # pulls in) is expensive, and only worker processes that actually handle
    # search requests need it. `lru_cache` memoizes the result, so this only
    # runs once per process (on the first search) instead of once per
    # request, and concurrent first-calls are serialized rather than racing
    # to load the model twice.
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    logger.info("Loading reranker model %s", RERANKER_MODEL)
    return TextCrossEncoder(model_name=RERANKER_MODEL)


def retrieve_chunks(query_text, query_embedding, top_k=None, threshold=None, reranker_enabled=None,
                    rerank_top_n=None, document_ids=None) -> list[dict]:
    """Ranked chunks for a query, without calling the LLM.

    Without the reranker, returns the `top_k` nearest chunks under the cosine
    distance threshold. With it, `top_k` is the candidate pool: the reranker
    scores the pool and only the best `rerank_top_n` are kept, so the context
    sent to the LLM shrinks instead of just being reordered.

    `document_ids` restricts the search to a set of documents (the evaluation
    keeps one corpus per chunking configuration in the same table).
    """
    top_k = top_k if top_k is not None else DEFAULT_TOP_K_RETRIEVE_SIZE
    distance_threshold = float(threshold) if threshold is not None else float(COSINE_DISTANCE_THRESHOLD)
    use_reranker = reranker_enabled if reranker_enabled is not None else RERANKER_ENABLED

    queryset = DocumentChunkModel.objects.select_related("document")
    if document_ids is not None:
        queryset = queryset.filter(document_id__in=document_ids)

    nearest = (
        queryset.annotate(distance=CosineDistance("embedding", query_embedding))
        .filter(distance__lte=distance_threshold)
        .order_by("distance")[:top_k]
    )
    chunks = [
        {
            "document_name": chunk.document.file_name,
            "cosine_distance": chunk.distance,
            "chunk_text": chunk.contextual_text,
            "chunk_id": chunk.id,
            "score": None,
        }
        for chunk in nearest
    ]

    if use_reranker and chunks:
        reranker = _get_reranker()
        scores = reranker.rerank(query=query_text, documents=[c["chunk_text"] for c in chunks])
        for chunk, score in zip(chunks, scores):
            chunk["score"] = float(score)
        chunks.sort(key=lambda c: c["score"], reverse=True)
        chunks = chunks[:rerank_top_n if rerank_top_n is not None else RERANK_TOP_N]

    return chunks


class SearchService:

    # top_k/threshold/reranker_enabled/rerank_top_n/document_ids are optional
    # overrides (used by the RAG evaluation experiments to compare
    # configurations); None falls back to the env-backed defaults, so normal
    # callers are unaffected. `query_embedding` skips the embedding call when
    # the caller already has the vector (the evaluation caches them).
    def execute(self, search, top_k=None, threshold=None, reranker_enabled=None, rerank_top_n=None,
                document_ids=None, query_embedding=None):

        if query_embedding is not None:
            search.search_embedding = query_embedding
        else:
            self.embbed_search(search)

        top_k_chunks = self.get_top_k_embeddings(
            search,
            top_limit=top_k,
            threshold=threshold,
            reranker_enabled=reranker_enabled,
            rerank_top_n=rerank_top_n,
            document_ids=document_ids,
        )
        search.retrieved_chunks = [
            {
                "rank": rank,
                "chunk_id": chunk["chunk_id"],
                "document_name": chunk["document_name"],
                "cosine_distance": chunk["cosine_distance"],
                "score": chunk["score"],
            }
            for rank, chunk in enumerate(top_k_chunks, start=1)
        ]

        return self.get_search_response(search, top_k_chunks)
    
    def embbed_search(self, search):
        try:
            client = create_client_for_embedding(search.provider, search.text)
            response = client.embed_content()
            search.search_embedding = response
        except Exception as e:
            logger.exception("Failed to get a response from the LLM provider")
            search.error = f"Error: {e}"
            search.save()
            raise

    def get_top_k_embeddings(self, search, top_limit=None, threshold=None, reranker_enabled=None,
                             rerank_top_n=None, document_ids=None) -> list[dict]:
        try:
            return retrieve_chunks(
                search.text,
                search.search_embedding,
                top_k=top_limit,
                threshold=threshold,
                reranker_enabled=reranker_enabled,
                rerank_top_n=rerank_top_n,
                document_ids=document_ids,
            )
        except Exception as e:
            logger.exception("Failed to retrieve/re-rank the top-k chunks")
            search.error = f"Error: {e}"
            search.save()
            raise

    def get_search_response(self, search, top_k_chunks):
        try:
            client = create_client_for_search(search.provider, search.text, top_k_chunks)
            response = client.execute(is_search=True)
            return save_client_reponse_for_search(search, response)
        except Exception as e:
            logger.exception("Failed to get a response from the LLM provider")
            search.error = f"Error: {e}"
            search.save()
            raise
