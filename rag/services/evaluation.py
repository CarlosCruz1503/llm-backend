"""RAG evaluation harness, driven by `python manage.py rag_eval`.

Split in two stages so it fits a free-tier quota:

1. Retrieval sweep: query embeddings are requested once (one batched call)
   and cached, so comparing any number of chunking / top_k / reranker /
   threshold configurations costs no LLM requests at all.
2. Generation: a few finalist configurations answer every question through
   the real search pipeline (one LLM request per question). Runs are
   resumable, and a single judge request grades all answers afterwards.
"""
import hashlib
import json
import logging
import statistics
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import tiktoken
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from myapp.constants import (
    DEFAULT_EMBEDDING_DIMENTIONS,
    GEMINI_EMBEDDING_MODEL,
    GEMINI_MODEL,
    ProviderChoices,
    TokenModelChoices,
)
from prompting.factory.provider import factoryProvider
from rag.constants import DocumentStatusChoices
from rag.evaluation.experiments import CORPORA, GENERATION_EXPERIMENTS, RETRIEVAL_SWEEP, Corpus, RetrievalConfig
from rag.models.document import DocumentModel
from rag.models.document_chunk import DocumentChunkModel
from rag.schemas.evaluation import JudgeBatchSchema
from rag.serializers.document import DocumentSerializer
from rag.serializers.search import SearchSerializer
from rag.services.search import _get_reranker, retrieve_chunks

logger = logging.getLogger(__name__)

EVALUATION_DIR = Path(__file__).resolve().parent.parent / "evaluation"
KB_DIR = EVALUATION_DIR / "data" / "testset_files"
DATASET_PATH = EVALUATION_DIR / "dataset.json"
RESULTS_DIR = EVALUATION_DIR / "results"
GENERATION_DIR = RESULTS_DIR / "generation"
SWEEP_PATH = RESULTS_DIR / "retrieval_sweep.json"
REPORT_PATH = RESULTS_DIR / "REPORT.md"
# Machine-local state (document ids in this database, cached vectors): gitignored.
CACHE_DIR = EVALUATION_DIR / ".cache"

# Cosine distance is at most 2, so this disables the threshold.
DISABLED_THRESHOLD = 2.0

_TERMINAL_STATUSES = {DocumentStatusChoices.COMPLETED, DocumentStatusChoices.FAILED}

JUDGE_PROMPT = """
You are grading answers produced by a retrieval-augmented assistant for a restaurant called The Garden Table.
The input is a JSON list. For each item, compare `answer` with `expected_answer`.

Rubric:
- 5: correct and complete. Extra details are fine if they are true.
- 4: correct, with a minor omission.
- 3: partially correct: a key part is missing (for example one half of a two-part question).
- 2: mostly wrong, or uses outdated or wrong-location information (an archived policy, the winter price,
     the other location's hours) where the expected answer uses the current one.
- 1: wrong, invented, or a refusal when the answer exists.

Rules:
- When `answerable` is false, the right behavior is to say the information is not available.
  That is verdict "correct_refusal" with score 5. Inventing an answer is "hallucination" with score 1.
- When `answerable` is true and the answer says the information is not available, that is
  "false_refusal" with score 1.
- Judge only agreement with `expected_answer`, not style or length.

Return exactly one grade per item, using the item's `id`.
"""


# --- small helpers -------------------------------------------------------------------------------

def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _mean(values):
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 4) if values else None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_dataset() -> list[dict]:
    return _read_json(DATASET_PATH, [])


def require_superuser():
    # Management commands have no request user, so UserModel.save() falls back
    # to the first superuser for the not-null `user` FK.
    if not User.objects.filter(is_superuser=True).exists():
        raise RuntimeError("No superuser found. Create one first (`make superuser`).")


def _use_exact_vector_search():
    # All corpora share one table and are filtered by document id. With HNSW's
    # default ef_search (40) that filter runs after the index scan and can
    # return fewer than top_k rows. The corpora are a few hundred chunks, so an
    # exhaustive search is cheap and makes results exact.
    with connection.cursor() as cursor:
        cursor.execute("SET hnsw.ef_search = 1000")


# --- corpora -------------------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wait_for_documents(document_ids, timeout, poll_interval) -> set:
    deadline = time.monotonic() + timeout
    pending = set(document_ids)
    while pending and time.monotonic() < deadline:
        finished = DocumentModel.objects.filter(pk__in=pending, status__in=_TERMINAL_STATUSES).values_list("id", flat=True)
        pending -= set(finished)
        if pending:
            time.sleep(poll_interval)
    return pending


def ensure_corpus(corpus: Corpus, provider=ProviderChoices.GEMINI, timeout=900, poll_interval=5) -> list[int]:
    """Make sure every knowledge base PDF is embedded with this corpus' chunking.

    Each corpus is a separate set of DocumentModel rows; the mapping lives in
    .cache/corpora.json. Only new, changed or failed files are (re)uploaded,
    so rerunning after a quota error does not re-embed what already worked.
    """
    manifest_path = CACHE_DIR / "corpora.json"
    manifest = _read_json(manifest_path, {})
    entries = manifest.get(corpus.key, {})

    config = asdict(corpus)
    kept, to_upload = {}, []
    for path in sorted(KB_DIR.glob("*.pdf")):
        sha = _sha256(path)
        entry = entries.get(path.name)
        # Entries written before "config" was recorded were made with the current config.
        if entry and entry["sha256"] == sha and entry.get("config", config) == config and DocumentModel.objects.filter(
            pk=entry["document_id"], status=DocumentStatusChoices.COMPLETED
        ).exists():
            kept[path.name] = entry
        else:
            to_upload.append((path, sha))

    stale_ids = [entry["document_id"] for name, entry in entries.items() if name not in kept]
    DocumentModel.objects.filter(pk__in=stale_ids).delete()

    chunk_config = {
        "model": corpus.token_model,
        "chunk_size": corpus.chunk_size,
        "chunk_overlap": corpus.chunk_overlap,
        "contextual_headers": corpus.contextual_headers,
    }
    uploaded = {}
    for path, sha in to_upload:
        serializer = DocumentSerializer(
            data={
                "provider": provider,
                "file": SimpleUploadedFile(path.name, path.read_bytes(), content_type="application/pdf"),
            },
            context={"chunk_config": chunk_config},
        )
        serializer.is_valid(raise_exception=True)
        uploaded[path.name] = {"document_id": serializer.save().id, "sha256": sha, "config": config}

    if uploaded:
        logger.info("Corpus %s: embedding %s documents (%s already done)", corpus.key, len(uploaded), len(kept))
        _wait_for_documents([entry["document_id"] for entry in uploaded.values()], timeout, poll_interval)

    manifest[corpus.key] = {**kept, **uploaded}
    _write_json(manifest_path, manifest)

    document_ids = [entry["document_id"] for entry in manifest[corpus.key].values()]
    not_ready = DocumentModel.objects.filter(pk__in=document_ids).exclude(status=DocumentStatusChoices.COMPLETED)
    if not_ready.exists():
        details = ", ".join(f"{d.file_name} ({d.status}: {d.error})" for d in not_ready)
        raise RuntimeError(f"Corpus {corpus.key} is not ready: {details}. Rerun to retry only these files.")
    return document_ids


def _chunk_token_counts(document_ids) -> dict[int, int]:
    # Tokens the LLM receives per chunk, so contextual headers count toward the cost.
    encoder = tiktoken.get_encoding(TokenModelChoices.cl100k_base)
    rows = DocumentChunkModel.objects.filter(document_id__in=document_ids).values_list("id", "token_size", "header")
    return {
        chunk_id: int(size) + (len(encoder.encode(header + "\n---\n")) if header else 0)
        for chunk_id, size, header in rows
    }


# --- query embeddings ----------------------------------------------------------------------------

def embed_queries(questions, provider=ProviderChoices.GEMINI) -> dict[int, list[float]]:
    """Query vectors by question id, cached per embedding model.

    The query vector does not depend on chunking or retrieval settings, so the
    whole dataset is embedded once, in a single batched request.
    """
    cache_path = CACHE_DIR / "query_embeddings.json"
    cache = _read_json(cache_path, {})
    vectors = cache.setdefault(f"{provider}:{GEMINI_EMBEDDING_MODEL}:{DEFAULT_EMBEDDING_DIMENTIONS}", {})

    missing = [q["query"] for q in questions if q["query"] not in vectors]
    if missing:
        provider_class = factoryProvider(provider)
        try:
            embedded = provider_class(input=missing).embed_contents()
            logger.info("Embedded %s queries in one request", len(missing))
        except Exception:
            # Batch not supported (or not one vector per text): one request per query.
            logger.warning("Batched embedding failed; embedding %s queries one by one", len(missing), exc_info=True)
            embedded = [provider_class(input=text).embed_content() for text in missing]
        for text, vector in zip(missing, embedded, strict=True):
            vectors[text] = list(vector)
        _write_json(cache_path, cache)

    return {q["id"]: vectors[q["query"]] for q in questions} if questions else {}


# --- retrieval metrics ---------------------------------------------------------------------------

def score_retrieval(question: dict, chunks: list[dict], token_counts: dict[int, int]) -> dict:
    """Document-level retrieval metrics for one question.

    `chunks` is what retrieval returned (and what the LLM would see), in rank
    order. hit/recall/reciprocal_rank are None for unanswerable questions.
    """
    relevant = set(question["relevant_documents"])
    distractors = set(question.get("distractor_documents", []))
    ranked_documents = [chunk["document_name"] for chunk in chunks]
    retrieved = set(ranked_documents)

    result = {
        "documents": list(dict.fromkeys(ranked_documents)),
        "n_chunks": len(chunks),
        "context_tokens": sum(token_counts.get(chunk["chunk_id"], 0) for chunk in chunks),
        "top_distance": chunks[0]["cosine_distance"] if chunks else None,
        "distractor_retrieved": bool(distractors & retrieved) if distractors else None,
        "hit": None,
        "recall": None,
        "reciprocal_rank": None,
    }
    if relevant:
        first_rank = next((rank for rank, doc in enumerate(ranked_documents, start=1) if doc in relevant), None)
        result["hit"] = first_rank is not None
        result["recall"] = round(len(relevant & retrieved) / len(relevant), 4)
        result["reciprocal_rank"] = round(1 / first_rank, 4) if first_rank else 0.0
    return result


def summarize_retrieval(rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["hit"] is not None]
    unanswerable = [r for r in rows if r["hit"] is None]
    return {
        "hit_rate": _mean(float(r["hit"]) for r in answerable),
        "recall": _mean(r["recall"] for r in answerable),
        "mrr": _mean(r["reciprocal_rank"] for r in answerable),
        "distractor_rate": _mean(float(r["distractor_retrieved"]) for r in rows if r["distractor_retrieved"] is not None),
        "context_tokens": _mean(r["context_tokens"] for r in rows),
        "unanswerable_chunks": _mean(r["n_chunks"] for r in unanswerable),
        "top_distance_answerable": _mean(r["top_distance"] for r in answerable),
        "top_distance_unanswerable": _mean(r["top_distance"] for r in unanswerable),
        "latency_ms": _mean(r.get("latency_ms") for r in rows),
        "recall_by_type": {
            question_type: _mean(r["recall"] for r in answerable if r["type"] == question_type)
            for question_type in sorted({r["type"] for r in answerable})
        },
    }


def _retrieve(config: RetrievalConfig, text, embedding, document_ids):
    return retrieve_chunks(
        text,
        embedding,
        top_k=config.top_k,
        threshold=config.threshold if config.threshold is not None else DISABLED_THRESHOLD,
        reranker_enabled=config.reranker,
        rerank_top_n=config.rerank_top_n,
        document_ids=document_ids,
    )


def run_retrieval_sweep(configs=RETRIEVAL_SWEEP, provider=ProviderChoices.GEMINI) -> dict:
    require_superuser()
    questions = load_dataset()
    embeddings = embed_queries(questions, provider)
    corpus_ids = {key: ensure_corpus(CORPORA[key], provider) for key in sorted({c.corpus for c in configs})}
    token_counts = _chunk_token_counts([i for ids in corpus_ids.values() for i in ids])
    _use_exact_vector_search()
    if any(config.reranker for config in configs):
        _get_reranker()  # load the model up front so it isn't counted as latency

    summaries, details = [], {}
    for config in configs:
        rows = []
        for question in questions:
            started = time.perf_counter()
            chunks = _retrieve(config, question["query"], embeddings[question["id"]], corpus_ids[config.corpus])
            rows.append({
                "id": question["id"],
                "type": question["type"],
                **score_retrieval(question, chunks, token_counts),
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            })
        summaries.append({"config": asdict(config), **summarize_retrieval(rows)})
        details[config.name] = rows
        logger.info("Retrieval config %s done", config.name)

    payload = {
        "generated_at": _now(),
        "embedding_model": GEMINI_EMBEDDING_MODEL,
        "questions": len(questions),
        "corpora": {
            key: asdict(CORPORA[key]) | {"chunks": DocumentChunkModel.objects.filter(document_id__in=ids).count()}
            for key, ids in corpus_ids.items()
        },
        "summaries": summaries,
        "details": details,
    }
    _write_json(SWEEP_PATH, payload)
    return payload


# --- generation ----------------------------------------------------------------------------------

def run_generation(name, max_requests=20, sleep_seconds=15, provider=ProviderChoices.GEMINI) -> tuple[dict, int]:
    """Answer the dataset with one finalist configuration, resuming previous runs.

    Every answer is written to disk as soon as it arrives. A failed request
    (usually the daily quota) stops the run without recording that question,
    so the next run picks up exactly where this one stopped.
    """
    require_superuser()
    config = GENERATION_EXPERIMENTS[name]
    path = GENERATION_DIR / f"{name}.json"
    run = _read_json(path, None) or {
        "experiment": asdict(config),
        "provider": provider,
        "model": GEMINI_MODEL,
        "started_at": _now(),
        "results": {},
    }
    if run["experiment"] != asdict(config):
        raise RuntimeError(f"{path.name} was started with a different config. Rename the experiment or delete the file.")

    results = run["results"]
    pending = [q for q in load_dataset() if str(q["id"]) not in results]
    if not pending:
        return run, 0

    embeddings = embed_queries(pending, provider)
    document_ids = ensure_corpus(CORPORA[config.corpus], provider)
    token_counts = _chunk_token_counts(document_ids)
    _use_exact_vector_search()

    requests_made = 0
    for question in pending:
        if requests_made >= max_requests:
            break
        if requests_made:
            time.sleep(sleep_seconds)

        started = time.perf_counter()
        serializer = SearchSerializer(
            data={"text": question["query"], "provider": provider},
            context={"search_config": {
                "top_k": config.top_k,
                "threshold": config.threshold if config.threshold is not None else DISABLED_THRESHOLD,
                "reranker_enabled": config.reranker,
                "rerank_top_n": config.rerank_top_n,
                "document_ids": document_ids,
                "query_embedding": embeddings[question["id"]],
            }},
        )
        serializer.is_valid(raise_exception=True)
        search = serializer.save()
        requests_made += 1

        if search.error:
            logger.error("Question %s failed (%s). Stopping; rerun later to resume.", question["id"], search.error)
            break

        results[str(question["id"])] = {
            "id": question["id"],
            "type": question["type"],
            "query": question["query"],
            "expected_answer": question["expected_answer"],
            "should_answer": question["should_answer"],
            "answer": search.response,
            "retrieval": score_retrieval(question, search.retrieved_chunks, token_counts),
            "retrieved_chunks": search.retrieved_chunks,
            "cited_chunk_id": search.top_chunk_id,
            "input_tokens": search.input_tokens,
            "output_tokens": search.output_tokens,
            "total_tokens": search.total_tokens,
            "latency_s": round(time.perf_counter() - started, 2),
            "judge": None,
            "manual_score": None,
        }
        _write_json(path, run)

    return run, requests_made


def run_judge(name, model=None, provider=ProviderChoices.GEMINI) -> tuple[int, list[int]]:
    """Grade every ungraded answer of a generation run in a single LLM request."""
    path = GENERATION_DIR / f"{name}.json"
    run = _read_json(path, None)
    if run is None:
        raise RuntimeError(f"No generation results for {name}. Run `rag_eval generate {name}` first.")

    pending = [r for r in run["results"].values() if r["judge"] is None]
    if not pending:
        return 0, []

    items = [
        {
            "id": r["id"],
            "question": r["query"],
            "expected_answer": r["expected_answer"],
            "answerable": r["should_answer"],
            "answer": r["answer"],
        }
        for r in pending
    ]
    client = factoryProvider(provider)(
        input=json.dumps(items, indent=2, ensure_ascii=False),
        output_type=SimpleNamespace(structured_output=JudgeBatchSchema, prompt=JUDGE_PROMPT),
    )
    if model:
        client.model = model
    response = client.execute()

    grades = {grade["id"]: grade for grade in response["output_dict"]["grades"]}
    missing = []
    for result in pending:
        grade = grades.get(result["id"])
        if grade is None:
            missing.append(result["id"])
            continue
        result["judge"] = {
            "score": max(1, min(5, int(grade["score"]))),
            "verdict": grade["verdict"],
            "reason": grade["reason"],
            "model": response["model"],
        }
    run["judge_summary"] = response["output"]
    _write_json(path, run)
    return len(pending) - len(missing), missing


def final_score(result: dict):
    """Your manual score when set, otherwise the judge's."""
    if result.get("manual_score") is not None:
        return result["manual_score"]
    return result["judge"]["score"] if result.get("judge") else None


# --- report --------------------------------------------------------------------------------------

def _pct(value):
    return "-" if value is None else f"{value * 100:.0f}%"


def _num(value, digits=0):
    return "-" if value is None else f"{value:.{digits}f}"


def _describe(config: dict) -> str:
    parts = [config["corpus"]]
    if config["reranker"]:
        parts.append(f"top {config['top_k']} -> rerank -> {config['rerank_top_n']}")
    else:
        parts.append(f"top {config['top_k']}")
    if config["threshold"] is not None:
        parts.append(f"threshold {config['threshold']}")
    return ", ".join(parts)


def _retrieval_section(sweep: dict) -> list[str]:
    lines = [
        "## Retrieval sweep (no LLM calls)",
        "",
        f"{sweep['questions']} questions, embeddings from `{sweep['embedding_model']}`. "
        "Hit / recall / MRR are over answerable questions, at document level. "
        "*Distractor* = an outdated or look-alike document was in the context. "
        "*Ctx tokens* = tokens sent to the LLM per question.",
        "",
        "| Config | Hit | Recall | MRR | Distractor | Ctx tokens | Chunks on unanswerable | Latency ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in sweep["summaries"]:
        lines.append(
            f"| `{s['config']['name']}` ({_describe(s['config'])}) | {_pct(s['hit_rate'])} | {_pct(s['recall'])} | "
            f"{_num(s['mrr'], 2)} | {_pct(s['distractor_rate'])} | {_num(s['context_tokens'])} | "
            f"{_num(s['unanswerable_chunks'], 1)} | {_num(s['latency_ms'], 1)} |"
        )

    lines += [
        "",
        "### Can a distance threshold detect unanswerable questions?",
        "",
        "Mean cosine distance of the top-1 chunk (lower = closer).",
        "",
        "| Corpus | Answerable | Unanswerable |",
        "|---|---|---|",
    ]
    for s in sweep["summaries"]:
        config = s["config"]
        if config["top_k"] == 1 and not config["reranker"] and config["threshold"] is None:
            lines.append(f"| {config['corpus']} | {_num(s['top_distance_answerable'], 3)} | {_num(s['top_distance_unanswerable'], 3)} |")
    return lines


def _generation_section(runs: dict) -> list[str]:
    lines = [
        "## Generation (answer + LLM judge)",
        "",
        "Score is 1-5: your `manual_score` when set, otherwise the judge's.",
        "",
        "| Experiment | Answered | Avg score | Single | Multi-hop | Conflict | Unanswerable | Hallucinations | False refusals | Avg tokens | Avg latency s |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, run in runs.items():
        results = list(run["results"].values())
        verdicts = [r["judge"]["verdict"] for r in results if r.get("judge")]

        def by_type(question_type):
            return _mean(final_score(r) for r in results if r["type"] == question_type)

        lines.append(
            f"| `{name}` ({_describe(run['experiment'])}) | {len(results)} | {_num(_mean(final_score(r) for r in results), 2)} | "
            f"{_num(by_type('single'), 2)} | {_num(by_type('multi_hop'), 2)} | {_num(by_type('conflict'), 2)} | "
            f"{_num(by_type('unanswerable'), 2)} | {verdicts.count('hallucination')} | {verdicts.count('false_refusal')} | "
            f"{_num(_mean(r['total_tokens'] for r in results))} | {_num(_mean(r['latency_s'] for r in results), 1)} |"
        )

    names = list(runs)
    questions = {q["id"]: q for q in load_dataset()}
    lines += ["", "### Per question", "", "| Q | Type | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for question_id, question in questions.items():
        scores = []
        for name in names:
            result = runs[name]["results"].get(str(question_id))
            scores.append(_num(final_score(result)) if result else "-")
        lines.append(f"| {question_id}. {question['query']} | {question['type']} | " + " | ".join(scores) + " |")
    return lines


def build_report() -> Path:
    sweep = _read_json(SWEEP_PATH, None)
    runs = {path.stem: _read_json(path, {}) for path in sorted(GENERATION_DIR.glob("*.json"))}

    lines = ["# RAG evaluation report", "", f"Generated {_now()} by `python manage.py rag_eval report`.", ""]
    if sweep:
        lines += _retrieval_section(sweep) + [""]
    if runs:
        lines += _generation_section(runs) + [""]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH
