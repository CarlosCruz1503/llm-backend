from myapp.constants import ProviderChoices, TokenModelChoices
from rag.services.evaluation import EvaluationService

###############################################################################################################
#                                                                                                             #
#   REMEMBER: TO HAVE A CLEAR DATABASE FOR EXPERIMENTS RUN THE COMMANDS: `make reset-db` AND `make migrate`    #
#                                                                                                             #
###############################################################################################################

# Experiment C (medium values, reranked) — see rag/evaluation/README.md
RESULTS_FILE_NAME = 'experiment_C_evaluation_results.json'

DEFAULT_TOKEN_MODEL = TokenModelChoices.cl100k_base
MAX_TOKENS_FOR_CHUNK = 200
DEFAULT_OVERLAP_TOKENS_FOR_CHUNK = 40
DEFAULT_TOP_K_RETRIEVE_SIZE = 10
COSINE_DISTANCE_THRESHOLD = 0.4
RERANKER_ENABLE = True


def execute_dataset():

    evaluation = EvaluationService(
        provider=ProviderChoices.GEMINI,
        DEFAULT_TOKEN_MODEL=DEFAULT_TOKEN_MODEL,
        MAX_TOKENS_FOR_CHUNK=MAX_TOKENS_FOR_CHUNK,
        DEFAULT_OVERLAP_TOKENS_FOR_CHUNK=DEFAULT_OVERLAP_TOKENS_FOR_CHUNK,
        DEFAULT_TOP_K_RETRIEVE_SIZE=DEFAULT_TOP_K_RETRIEVE_SIZE,
        COSINE_DISTANCE_THRESHOLD=COSINE_DISTANCE_THRESHOLD,
        RERANKER_ENABLE=RERANKER_ENABLE,
        RESULTS_FILE_NAME=RESULTS_FILE_NAME
    )

    # These configs are passed explicitly into each DocumentSerializer/
    # SearchSerializer call (via `context`) and, for chunking, forwarded as
    # real Celery task arguments all the way to the celery_worker process —
    # so they actually take effect, unlike monkeypatching module/class
    # attributes in this process.
    document_ids = evaluation.embed_dataset_files()

    # Embedding still runs asynchronously on celery_worker: block here until
    # every document is COMPLETED/FAILED before running the search queries.
    evaluation.wait_for_processing(document_ids)

    ## This will generate an evaluation result json
    evaluation.search_dataset_questions()


execute_dataset()
