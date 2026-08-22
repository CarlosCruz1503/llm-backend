import logging
from abc import ABC
from functools import lru_cache

from pgvector.django import CosineDistance

from prompting.constants import DEFAULT_TOP_K_RETRIEVE_SIZE, RERANKER_MODEL, COSINE_DISTANCE_THRESHOLD
from prompting.services.client import create_client_for_embedding, create_client_for_search, save_client_reponse_for_search
from rag.models.document_chunk import DocumentChunkModel
from rag.schemas.search import SearchSchema

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


class SearchService(ABC):
    
    def execute(self, search):
        
        self.embbed_search(search)
        
        top_k_chunks = self.get_top_k_embeddings(search, top_limit=DEFAULT_TOP_K_RETRIEVE_SIZE)

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

    def get_top_k_embeddings(self, search, top_limit) -> list[SearchSchema]:
        try:
            chunks_with_distance = DocumentChunkModel.objects.annotate(
                distance=CosineDistance("embedding", search.search_embedding)
            )
            filter_chunks = chunks_with_distance.filter(distance__lte=COSINE_DISTANCE_THRESHOLD).order_by("distance")[:top_limit]

            top_k_chunks = [
                {
                    "document_name": chunk.document.file_name,
                    "cosine_distance": chunk.distance,
                    "chunk_text": chunk.text,
                    "chunk_id": chunk.id,
                    "score": 0,
                }
                for chunk in filter_chunks
            ]

            re_rank_top = self.re_rank_top_k(search, top_k_chunks)

            for index, score in enumerate(re_rank_top, start=0):
                top_k_chunks[index]["score"] = score

            top_k_chunks.sort(key=lambda x: x["score"], reverse=True)

            return top_k_chunks
        except Exception as e:
            logger.exception("Failed to retrieve/re-rank the top-k chunks")
            search.error = f"Error: {e}"
            search.save()
            raise

    def re_rank_top_k(self, search, top_k_chunks):
        reranker = _get_reranker()

        query = search.text

        # Format as pairs of [query, passage]
        sentence_pairs = [p["chunk_text"] for p in top_k_chunks]
        # Compute relevance scores
        results = reranker.rerank(query=query, documents=sentence_pairs)
        return list(results)

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