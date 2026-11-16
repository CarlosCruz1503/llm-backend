# RAG Evaluation

Which chunk size, overlap, top_k, distance threshold and reranker setting works best for *your* documents? This harness answers that with measurements instead of guesses, within a free-tier quota of about 20 LLM requests per day. It ships with a sample knowledge base (a fictional restaurant), and you can swap in your own: see [Evaluate your own documents](#evaluate-your-own-documents).

The first version of this evaluation gave a misleading result; [`results/v1_pilot/README.md`](results/v1_pilot/README.md) explains why and what this version does differently. The full story, findings and reasoning are in [`docs/rag-evaluation-notes.md`](../../docs/rag-evaluation-notes.md).

## Evaluate your own documents

### 1. Documents

Put your PDFs in `data/testset_files/` and remove the sample ones. Every PDF in that folder is part of the knowledge base. Alternatively, write the documents as Markdown in `data/kb_source/` and run `make eval_kb` to render them.

Contextual headers use each document's first line as its title, and short lines that don't end with a period as section headings. That fits most business documents (a title, then sections). If yours are laid out differently, adjust `document_title` and `_is_heading` in `rag/services/chunks.py`.

### 2. Questions

Write 15–30 questions in `dataset.json`. Use questions your users would really ask, and label them honestly: the labels are what everything is scored against.

```json
{
  "id": 1,
  "type": "single",
  "query": "Do you deliver on Sundays?",
  "expected_answer": "Yes, from 12:00 to 20:00, within 5 km.",
  "relevant_documents": ["delivery.pdf"],
  "distractor_documents": ["delivery_2023_archived.pdf"],
  "should_answer": true
}
```

| Field | Meaning |
|---|---|
| `id` | Unique number |
| `type` | `single`, `multi_hop`, `conflict` or `unanswerable`. The report shows one column per type. |
| `query` | The question, as a user would write it |
| `expected_answer` | What a correct answer says. The judge compares against this. |
| `relevant_documents` | File names that contain the answer. Empty for unanswerable questions. |
| `distractor_documents` | Optional: files that look relevant but would give a wrong answer (old versions, other locations…) |
| `should_answer` | `false` when the documents don't contain the answer |

Include a few questions that your documents *can't* answer: they check whether the model admits it instead of inventing something.

### 3. Configurations

`experiments.py` defines three things:

```python
CORPORA = {          # how documents are chunked; each corpus is embedded once
    corpus.key: corpus
    for corpus in [
        Corpus("chunk256_ctx", chunk_size=256, chunk_overlap=48, contextual_headers=True),
        Corpus("chunk512", chunk_size=512, chunk_overlap=96),
    ]
}
# RETRIEVAL_SWEEP: every retrieval setting to compare for free (corpus, top_k, threshold, reranker)
# GENERATION_EXPERIMENTS: the few finalists that get real answers, graded by the judge
GENERATION_EXPERIMENTS = {
    "headers": RetrievalConfig("headers", "chunk256_ctx", top_k=3),
    "whole_docs": RetrievalConfig("whole_docs", "chunk512", top_k=3),
}
```

### 4. Run

```bash
make eval_retrieval                 # free: compares every retrieval setting
make eval_generate EXP=headers      # 1 LLM request per question; resumes if it stops
make eval_judge EXP=headers         # 1 request for all answers
```

Results are in `results/REPORT.md`. Start with the retrieval table: the configurations that get the relevant documents into the context with the fewest tokens are your finalists. Then compare their answer scores.

Notes:
- Changing a document re-embeds only that document. A removed document is dropped from each corpus the next time that corpus is used.
- Each corpus is embedded through the free tier's embedding quota (30,000 tokens per minute). If it hits the limit, the tasks wait and retry; if some documents still fail, run the command again.
- With 20 generation requests a day, plan one finalist per day, or set `EVAL_JUDGE_MODEL` to a different model so judging doesn't use the same quota.

## Sample knowledge base

20 synthetic documents about The Garden Table, a fictional restaurant with two locations (~8k tokens in total). The Markdown files in `data/kb_source/` are the source of truth; `scripts/build_kb.py` renders them to the PDFs in `data/testset_files/` that go through the real ingestion pipeline.

Some documents are there to trip up retrieval:

| Trap | Documents |
|---|---|
| Outdated policy with different fees and rules | `policies_archive_2024` vs `restaurant_policies` |
| Second location with different hours, rules and services | `riverside_location` vs `restaurant_policies`, `location_and_parking` |
| Seasonal menu with different prices | `seasonal_winter_menu` vs `restaurant_menu` |
| Dress code that applies to staff, not guests | `staff_handbook_excerpt` |

## Sample dataset

`dataset.json` has 20 questions, each with an `expected_answer`, the `relevant_documents` that contain the answer and the `distractor_documents` that look relevant but aren't:

| Type | Count | Tests |
|---|---|---|
| `single` | 8 | The answer is in one document |
| `multi_hop` | 5 | The answer needs two documents (e.g. events + catering) |
| `conflict` | 4 | A distractor gives a different, wrong answer (archived fee, winter price, other location) |
| `unanswerable` | 3 | The knowledge base doesn't say; the right answer is "not available" |

## How it works

### Stage 1: retrieval sweep (no LLM calls)

Each chunking setting is a separate corpus (`chunk128`, `chunk256`, `chunk512`, about 20% overlap, plus `chunk128_ctx` and `chunk256_ctx` with contextual chunk headers) embedded once through the normal Celery pipeline. The 20 questions are embedded in one batched request and cached in `.cache/`. Every configuration in `experiments.py` is then evaluated against pgvector directly, one variable at a time:

- chunk size x top_k (1, 3, 5, 8)
- reranker: 20 candidates reranked down to 1, 3 or 5, compared with plain top-k at the same number of chunks
- distance threshold (0.30, 0.35, 0.40) on chunk256 top-8, and (0.27, 0.28, 0.29) on chunk128 top-3
- contextual chunk headers: every chunk is prefixed with `Document: <title> / Section: <heading>` before embedding and in what the LLM receives (`rag/services/chunks.py`)

Metrics, at document level, from what retrieval actually returned:

- **Hit:** at least one relevant document is in the context.
- **Recall:** fraction of the relevant documents in the context (matters for multi-hop).
- **MRR:** how high the first relevant chunk is ranked.
- **Distractor rate:** a trap document is in the context.
- **Context tokens:** tokens sent to the LLM per question, the cost side.
- **Chunks on unanswerable:** how much noise reaches the LLM when there is no answer.

### Stage 2: generation and judge (a few finalists)

The finalists in `GENERATION_EXPERIMENTS` answer all 20 questions through the real search path (`SearchSerializer` -> `SearchService`), using the cached query vectors, so each question costs exactly one LLM request. Every answer is saved as soon as it arrives. If a request fails (usually the daily quota), the run stops without recording that question and resumes from there on the next run.

A single judge request then grades all answers 1-5 against `expected_answer` with a fixed rubric: a correct refusal on an unanswerable question scores 5, and an invented answer scores 1. Set `manual_score` on any result to override the judge; the report uses your score when present.

## Running it

Prerequisites: the stack is up (`make up`), migrations are applied, a superuser exists (`make superuser`; rows created by management commands are assigned to it), and `GEMINI_API_KEY` is set.

```bash
# Day 1: embed the corpora and run the free retrieval sweep
make eval_retrieval                 # python manage.py rag_eval retrieval

# Look at results/REPORT.md, then set the finalists in experiments.py

# Day 2+: one finalist per day (20 requests):
# small_chunks, whole_docs, small_chunks_threshold, medium_chunks_ctx
make eval_generate EXP=small_chunks     # rerun to resume if it stops early
make eval_judge EXP=small_chunks        # 1 request; set EVAL_JUDGE_MODEL to use another model's quota

make eval_report                    # rebuild results/REPORT.md
```

To change the knowledge base, edit `data/kb_source/*.md` and run `make eval_kb`. Corpora re-embed only the files that changed.

## Files

```
rag/evaluation/
├── README.md
├── experiments.py              # corpora, retrieval sweep and generation finalists
├── dataset.json                # 20 labelled questions
├── data/
│   ├── kb_source/              # knowledge base, Markdown (source of truth)
│   └── testset_files/          # rendered PDFs (make eval_kb)
├── scripts/build_kb.py
├── .cache/                     # gitignored: document ids in your DB, query vectors
└── results/
    ├── REPORT.md               # generated summary tables
    ├── retrieval_sweep.json
    ├── generation/<experiment>.json
    └── v1_pilot/               # first version, kept for comparison
```

## Caveats

- 20 questions and a single run per configuration: treat small differences as noise.
- The judge is the same model family as the answering model and may be lenient toward it; spot-check its grades.
- The evaluation corpora live in the same tables as API uploads, so a plain `/api/search/` on the same database searches them too.
