"""Configurations compared by `python manage.py rag_eval`.

Retrieval configs are cheap (no LLM calls), so the sweep changes one variable
at a time across many of them. Generation experiments cost one LLM request per
question, so only a few finalists are run, one per day on the free tier.
"""
from dataclasses import dataclass

from myapp.constants import TokenModelChoices


@dataclass(frozen=True)
class Corpus:
    key: str
    chunk_size: int
    chunk_overlap: int
    token_model: str = TokenModelChoices.cl100k_base
    # Prefix every chunk with "Document: <title> / Section: <heading>" before
    # embedding it and sending it to the LLM.
    contextual_headers: bool = False


@dataclass(frozen=True)
class RetrievalConfig:
    name: str
    corpus: str
    top_k: int
    # None disables the cosine distance threshold.
    threshold: float | None = None
    # With the reranker on, top_k is the candidate pool and rerank_top_n chunks are kept.
    reranker: bool = False
    rerank_top_n: int | None = None


# ~20% overlap at every size. The knowledge base documents are 250-550 tokens,
# so chunk512 is close to "one chunk per document".
CORPORA = {
    corpus.key: corpus
    for corpus in [
        Corpus("chunk128", chunk_size=128, chunk_overlap=24),
        Corpus("chunk256", chunk_size=256, chunk_overlap=48),
        Corpus("chunk512", chunk_size=512, chunk_overlap=96),
        # Same chunking with contextual headers: does knowing the document help?
        Corpus("chunk128_ctx", chunk_size=128, chunk_overlap=24, contextual_headers=True),
        Corpus("chunk256_ctx", chunk_size=256, chunk_overlap=48, contextual_headers=True),
    ]
}

RERANK_POOL = 20


def _retrieval_sweep():
    configs = []
    # 1. Chunk size x top_k, nothing else.
    for corpus in CORPORA:
        for k in (1, 3, 5, 8):
            configs.append(RetrievalConfig(f"{corpus}_k{k}", corpus, top_k=k))
    # 2. Reranker: pull RERANK_POOL candidates, keep n. Compare with `{corpus}_k{n}`
    #    above, which sends the same number of chunks without reranking. Plain
    #    corpora only: the first sweep showed it isn't worth its latency here.
    for corpus in ("chunk128", "chunk256", "chunk512"):
        for n in (1, 3, 5):
            configs.append(RetrievalConfig(
                f"{corpus}_rerank{RERANK_POOL}to{n}", corpus, top_k=RERANK_POOL, reranker=True, rerank_top_n=n,
            ))
    # 3. Distance threshold on a generous top_k: does it cut noise for unanswerable questions?
    for threshold in (0.30, 0.35, 0.40):
        configs.append(RetrievalConfig(f"chunk256_k8_thr{threshold:.2f}", "chunk256", top_k=8, threshold=threshold))
    # 4. Threshold on the best corpus: on chunk128 every answerable top-1 distance was
    #    <= 0.266 and every unanswerable one >= 0.296 in the first sweep.
    for threshold in (0.27, 0.28, 0.29):
        configs.append(RetrievalConfig(f"chunk128_k3_thr{threshold:.2f}", "chunk128", top_k=3, threshold=threshold))
    return configs


RETRIEVAL_SWEEP = _retrieval_sweep()

# Finalists for the full answer + judge evaluation, chosen from the retrieval
# sweep; each run is 20 LLM requests. The reranker is left out: it matched plain
# top-k recall at 400-2500x the retrieval latency.
GENERATION_EXPERIMENTS = {
    config.name: config
    for config in [
        # Best retrieval per token: 100% hit, 96% recall, ~350 context tokens.
        RetrievalConfig("small_chunks", "chunk128", top_k=3),
        # Same recall at ~3x the tokens; whole documents keep headers such as "ARCHIVED".
        RetrievalConfig("whole_docs", "chunk512", top_k=3),
        # small_chunks, but unanswerable questions should get no context at all.
        RetrievalConfig("small_chunks_threshold", "chunk128", top_k=3, threshold=0.28),
        # small_chunks where every chunk names its document and section (e.g. "... 2024 (ARCHIVED)").
        RetrievalConfig("small_chunks_ctx", "chunk128_ctx", top_k=3),
    ]
}
