from django.core.files.uploadedfile import SimpleUploadedFile
from myapp.constants import ProviderChoices
from rag.constants import DocumentStatusChoices
from rag.models.document import DocumentModel
from rag.models.document_chunk import DocumentChunkModel
from rag.models.search import SearchModel
from rag.serializers.document import DocumentSerializer
import os
import logging
import time
import json
from rag.serializers.search import SearchSerializer

logger = logging.getLogger(__name__)

# Terminal states for the async extract/chunk/embed pipeline (see rag/tasks.py) —
# wait_for_processing() polls until every document reaches one of these.
_DOCUMENT_TERMINAL_STATUSES = {DocumentStatusChoices.COMPLETED, DocumentStatusChoices.FAILED}

FILES_PATH = './rag/evaluation/data/testset_files'
JSON_PATH = './rag/evaluation/dataset.json'
OUTPUT_JSON_PATH = './rag/evaluation/results'

class EvaluationService:
    
    provider:ProviderChoices = ProviderChoices.GEMINI
    DEFAULT_TOKEN_MODEL:str
    MAX_TOKENS_FOR_CHUNK: int
    DEFAULT_OVERLAP_TOKENS_FOR_CHUNK: int
    DEFAULT_TOP_K_RETRIEVE_SIZE: int
    COSINE_DISTANCE_THRESHOLD: int # Equivalent to disable 
    RERANKER_ENABLE: bool
    RESULTS_FILE_NAME:str
    
    def __init__(self,provider, DEFAULT_TOKEN_MODEL, MAX_TOKENS_FOR_CHUNK, DEFAULT_OVERLAP_TOKENS_FOR_CHUNK, DEFAULT_TOP_K_RETRIEVE_SIZE, COSINE_DISTANCE_THRESHOLD, RERANKER_ENABLE, RESULTS_FILE_NAME):
        self.provider=provider
        self.DEFAULT_TOKEN_MODEL= DEFAULT_TOKEN_MODEL
        self.MAX_TOKENS_FOR_CHUNK = MAX_TOKENS_FOR_CHUNK
        self.DEFAULT_OVERLAP_TOKENS_FOR_CHUNK=DEFAULT_OVERLAP_TOKENS_FOR_CHUNK
        self.DEFAULT_TOP_K_RETRIEVE_SIZE=DEFAULT_TOP_K_RETRIEVE_SIZE
        self.COSINE_DISTANCE_THRESHOLD=COSINE_DISTANCE_THRESHOLD
        self.RERANKER_ENABLE=RERANKER_ENABLE
        self.RESULTS_FILE_NAME=RESULTS_FILE_NAME
    
    def embed_dataset_files(self):
        onlyfiles = [f for f in os.listdir(FILES_PATH) if os.path.isfile(os.path.join(FILES_PATH, f))]

        # Forwarded as explicit task args through task_process_document ->
        # task_create_and_process_chunks (see rag/tasks.py), so this actually
        # reaches the celery_worker process — unlike mutating ChunkService's
        # class attributes or rag.services.document's module globals, which
        # only ever affected this process.
        chunk_config = {
            "model": self.DEFAULT_TOKEN_MODEL,
            "chunk_size": self.MAX_TOKENS_FOR_CHUNK,
            "chunk_overlap": self.DEFAULT_OVERLAP_TOKENS_FOR_CHUNK,
        }

        document_ids = []
        for file_name in onlyfiles:
            file_path = os.path.join(FILES_PATH, file_name)

            # Open in binary mode ('rb') so DRF handles file buffers properly
            with open(file_path, "rb") as f:
                uploaded_file = SimpleUploadedFile(
                    name=file_name,
                    content=f.read(),
                    content_type="application/pdf"  # Adjust MIME type if necessary
                )

                data = {
                    "provider": self.provider,
                    "file": uploaded_file
                }

                # Pass uploaded files
                document_serializer = DocumentSerializer(data=data, context={"chunk_config": chunk_config})
                document_serializer.is_valid(raise_exception=True)
                document = document_serializer.save()
                document_ids.append(document.id)

                logger.info(f"Successfully queued file {file_name} with provider {self.provider}")

        return document_ids

    def wait_for_processing(self, document_ids, timeout=600, poll_interval=5):
        """Blocks until every document in `document_ids` reaches a terminal
        status (COMPLETED/FAILED) in the async pipeline, or `timeout` seconds
        elapse. Call this between embed_dataset_files() and
        search_dataset_questions() — the embedding step is still processed
        asynchronously by celery_worker, so search would otherwise run
        against a database with no (or partial) embeddings yet.
        """
        deadline = time.monotonic() + timeout
        pending = set(document_ids)

        while pending and time.monotonic() < deadline:
            statuses = dict(
                DocumentModel.objects.filter(pk__in=pending).values_list("id", "status")
            )
            pending = {doc_id for doc_id, status in statuses.items() if status not in _DOCUMENT_TERMINAL_STATUSES}
            if pending:
                time.sleep(poll_interval)

        if pending:
            logger.warning(f"Timed out waiting for documents to finish processing: {sorted(pending)}")
        else:
            logger.info("All documents finished processing (completed or failed).")

        failed = DocumentModel.objects.filter(pk__in=document_ids, status=DocumentStatusChoices.FAILED)
        for document in failed:
            logger.warning(f"Document {document.id} ({document.file_name}) failed: {document.error}")

    def search_dataset_questions(self):
        # Open and load the input dataset JSON file
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            questions_json = json.load(file)
        
        results = []

        # Store metadata/configuration parameters used during evaluation
        config_metadata = {
        "provider": self.provider,
        "default_token_model":self.DEFAULT_TOKEN_MODEL,
        "max_tokens_for_chunk": self.MAX_TOKENS_FOR_CHUNK,
        "default_overlap_tokens_for_chunk": self.DEFAULT_OVERLAP_TOKENS_FOR_CHUNK,
        "default_top_k_retrieve_size": self.DEFAULT_TOP_K_RETRIEVE_SIZE,
        "cosine_distance_threshold": self.COSINE_DISTANCE_THRESHOLD,
        "reranker_enable": self.RERANKER_ENABLE,
        }

        # Forwarded to SearchSerializer -> SearchService.execute() so this
        # experiment's retrieval configuration is actually applied (search
        # runs synchronously in this same process, so this alone would have
        # been enough — no celery involved on this path).
        search_config = {
            "top_k": self.DEFAULT_TOP_K_RETRIEVE_SIZE,
            "threshold": self.COSINE_DISTANCE_THRESHOLD,
            "reranker_enabled": self.RERANKER_ENABLE,
        }

        for item in questions_json:
            query_id = item.get("id")
            text = item["query"]
            category = item.get("category")
            expected_topics = item.get("expected_topics", [])
            expected_docs = item.get("relevant_documents", [])
            
            data = {
                "text": text,
                "provider": self.provider
            }
            
            search_serializer = SearchSerializer(data=data, context={"search_config": search_config})
            search_serializer.is_valid(raise_exception=True)
            search_result: SearchModel = search_serializer.save()
            response = search_result.response

            # Safely fetch fetched document name from top_chunk
            fetched_doc = None
            if hasattr(search_result, "top_chunk") and search_result.top_chunk:
                fetched_doc = getattr(search_result.top_chunk.document, "file_name", None)

            distance_top_chunk = getattr(search_result, "distance_top_chunk", None)

            # chunk_list holds every chunk_id from the top_k retrieved set
            # (not just the one the LLM picked as its answer's source), so
            # this captures whether the right document was actually
            # *retrieved* even when the LLM cited a different chunk as its
            # top pick — retrieval recall vs. LLM chunk-selection are
            # different failure modes, and is_match alone only measures the
            # latter.
            retrieved_chunk_ids = [
                c.get("chunk_id") for c in (search_result.chunk_list or []) if c.get("chunk_id") is not None
            ]
            chunk_id_to_doc = dict(
                DocumentChunkModel.objects.filter(pk__in=retrieved_chunk_ids).values_list("id", "document__file_name")
            )
            retrieved_documents = list(dict.fromkeys(
                chunk_id_to_doc[chunk_id] for chunk_id in retrieved_chunk_ids if chunk_id in chunk_id_to_doc
            ))
            any_relevant_document_retrieved = (
                any(doc in expected_docs for doc in retrieved_documents) if expected_docs else None
            )

            logger.info(
                f"Successfully search processed: question: {text} with provider {self.provider}, "
                f"result={response}, relevant_document expected={expected_docs}, "
                f"relevant document fetched={fetched_doc}, distance_top_chunk={distance_top_chunk}, "
                f"retrieved_documents={retrieved_documents}"
            )

            # Record individual query result
            results.append({
                "id": query_id,
                "category": category,
                "query": text,
                "expected_topics": expected_topics,
                "expected_documents": expected_docs,
                "fetched_document": fetched_doc,
                "distance_top_chunk": distance_top_chunk,
                "retrieved_documents": retrieved_documents,
                "any_relevant_document_retrieved": any_relevant_document_retrieved,
                "generated_response": response,
                "is_match": fetched_doc in expected_docs if expected_docs and fetched_doc else None,
                "input_tokens": search_result.input_tokens,
                "output_tokens": search_result.output_tokens,
                "total_tokens": search_result.total_tokens,
                "manual_calification":0,
                "manual_calification_setted":False
            })

            # Basic rate-limiting pause between LLM calls.
            time.sleep(120)

        # Output payload containing config and results
        output_payload = {
            "evaluation_config": config_metadata,
            "total_questions": len(results),
            "results": results
        }
        OUTPUT_PATH = f"{OUTPUT_JSON_PATH}/{self.RESULTS_FILE_NAME}"
        # Write results out to a JSON file
        with open(OUTPUT_PATH, "w", encoding="utf-8") as out_file:
            json.dump(output_payload, out_file, indent=4, ensure_ascii=False)

        logger.info(f"Evaluation finished! Results saved to {OUTPUT_PATH}")