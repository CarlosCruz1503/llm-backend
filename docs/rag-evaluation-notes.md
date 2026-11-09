# Evaluating a RAG pipeline: notes, findings and lessons

This document records how the retrieval-augmented search in this project was evaluated: what the first attempt got wrong, how the evaluation was rebuilt, what the measurements show, and the reasoning behind each decision. Results still to come are marked **pending**.

- Harness and how to run it: [`rag/evaluation/README.md`](../rag/evaluation/README.md)
- Generated tables: [`rag/evaluation/results/REPORT.md`](../rag/evaluation/results/REPORT.md)

## Contents

1. [Summary](#1-summary)
2. [The system under test](#2-the-system-under-test)
3. [The first attempt and why it was misleading](#3-the-first-attempt-and-why-it-was-misleading)
4. [Rebuilding the evaluation](#4-rebuilding-the-evaluation)
5. [How to read the metrics](#5-how-to-read-the-metrics)
6. [Retrieval results](#6-retrieval-results)
7. [Why small chunks win here](#7-why-small-chunks-win-here)
8. [Overlap is not context: contextual chunk headers](#8-overlap-is-not-context-contextual-chunk-headers)
9. [Generation results (pending)](#9-generation-results-pending)
10. [Engineering problems found along the way](#10-engineering-problems-found-along-the-way)
11. [Limitations](#11-limitations)
12. [Next experiments](#12-next-experiments)
13. [Glossary](#13-glossary)
14. [Log](#14-log)

---

## 1. Summary

- **The first evaluation picked the wrong winner.** It reported "reranked, top 10" as best. In fact the knowledge base was so small that top 10 sent almost all of it to the LLM, the reranker didn't remove anything, and "retrieval recall" was read from the LLM's own answer instead of from the database.
- **Measure retrieval and generation separately.** Retrieval quality can be measured without calling the LLM. That made it possible to compare 24 configurations on a free tier of 20 LLM requests a day.
- **Small chunks (128 tokens) with top 3 gave the best retrieval per token:** every answerable question got a relevant document, with 96% recall and ~350 tokens of context. Whole-document chunks matched that recall at 3x the tokens. Medium chunks (256) were the worst at every small top-k.
- **The reranker wasn't worth it here:** a small gain in ranking, at 400x to 2,500x the retrieval latency on CPU, and it did not filter outdated documents.
- **A distance threshold looks able to detect unanswerable questions:** on 128-token chunks every answerable question's best match was closer than every unanswerable one's.
- **Chunk overlap does not carry document-level context.** A chunk from the middle of an archived policy doesn't say "archived". Contextual chunk headers (prefixing each chunk with its document title and section) are being tested to fix that.

## 2. The system under test

A Django REST API with a synchronous search endpoint (`POST /api/search/`):

1. Embed the question (Gemini embeddings, 1,024 dimensions).
2. Fetch the nearest chunks from PostgreSQL + pgvector (cosine distance, optional threshold, top-k).
3. Optionally rerank them with a local cross-encoder (`jina-reranker-v2-base-multilingual` via fastembed) and keep the best few.
4. Ask the LLM (Gemini) to answer from those chunks, with a schema-validated JSON response.

Documents are ingested asynchronously: PDF → text (pdfplumber) → token chunks (chonkie + tiktoken) → one embedding per chunk, orchestrated with Celery.

The knowledge base belongs to a fictional restaurant, The Garden Table, so every fact is known and every question has a checkable answer.

## 3. The first attempt and why it was misleading

The first version (kept in [`results/v1_pilot/`](../rag/evaluation/results/v1_pilot/README.md)) compared three configurations over 9 PDFs and 16 questions:

| | Chunk / overlap | top_k | Threshold | Reranker | Avg manual score | Avg tokens |
|---|---|---|---|---|---|---|
| A | 50 / 10 | 3 | off | off | 3.69 | 1,175 |
| B | 200 / 40 | 5 | 0.4 | off | 4.38 | 1,997 |
| C | 200 / 40 | 10 | 0.4 | on | **4.56** | 3,558 |

C looked best. It wasn't a meaningful result, for six reasons:

1. **The knowledge base was too small.** All 9 documents together were 1,644 tokens. At chunk size 200, one chunk was about one document, so the whole corpus was around a dozen chunks and top 10 sent almost all of it. C measured "put everything in the prompt".
2. **The reranker only reordered.** It sorted the 10 chunks by relevance and still sent all 10. Same context, same cost, extra latency.
3. **"Recall" came from the LLM.** The retrieved documents were read from the `chunk_list` field of the LLM's JSON answer. That measured what the model *said* it used, not what retrieval returned.
4. **Several settings changed at once.** A → B changed chunk size, overlap, top-k and threshold together, so no improvement could be attributed to any one of them.
5. **Inconsistent grading.** A question labelled unanswerable (sustainability) was partly answerable from the menu, so a correct partial answer scored 3 while correct refusals scored 1.
6. **Too small to separate B from C.** The 0.18-point gap is 3 points in total over 16 questions.

**Lessons:**
- Measure retrieval at the source.
- A reranker has to cut the candidate list, not just reorder it.
- Change one variable at a time.
- Make the corpus large enough that retrieval has real choices to make.
- Write the grading rubric down before grading.

## 4. Rebuilding the evaluation

### 4.1 A knowledge base with traps

20 documents, about 8,000 tokens in total (250–550 tokens each). They are written in Markdown (`rag/evaluation/data/kb_source/`) and rendered to PDF, so they can be reviewed and diffed like code. Some documents exist to trip up retrieval, because real knowledge bases are full of near-duplicates and stale files:

| Trap | Why it's hard |
|---|---|
| `policies_archive_2024` vs `restaurant_policies` | Same topics, different fees: corkage $15 vs $20, free cake vs $3 per person |
| `riverside_location` vs Downtown documents | A second location with different hours, no dogs on the terrace, no brunch |
| `seasonal_winter_menu` vs `restaurant_menu` | Salmon is $24 in winter, $21 otherwise |
| `staff_handbook_excerpt` | Describes a dress code for **staff**; nothing describes one for guests |

### 4.2 A labelled dataset

20 questions, each with the expected answer, the documents that contain it, and the distractors that look relevant but aren't:

| Type | Count | Example |
|---|---|---|
| Single document | 8 | "When is weekend brunch served?" |
| Multi-hop | 5 | "Seated dinner for 30: private room or what?" (events + catering) |
| Conflict | 4 | "How much is corkage?" (current policy vs 2024 archive) |
| Unanswerable | 3 | "Is there a dress code for guests?" (only the staff one exists) |

### 4.3 Two stages, because of a 20-requests-a-day quota

**Stage 1, retrieval sweep (no LLM calls).**
- Each chunking setting is a separate corpus, embedded once.
- The 20 questions are embedded once and cached, because a question's vector doesn't depend on chunking or top-k.
- Any number of retrieval configurations can then be compared with database queries alone. The reranker runs locally.

**Stage 2, generation (a few finalists).**
- Each finalist answers all 20 questions through the real API code path: 20 LLM requests, one finalist per day.
- Runs are resumable. Each answer is saved as it arrives, and a failed request (usually the quota) stops the run so the next run continues from there.
- One extra request grades every answer with an LLM judge using a fixed rubric: a correct "not available" on an unanswerable question scores 5, and an invented answer scores 1. Manual scores override the judge.

### 4.4 Changes to the application itself

The evaluation needed some changes in the application, which are improvements in their own right:

- **`SearchModel.retrieved_chunks`** stores what retrieval actually returned (rank, document, distance, rerank score) on every search. The LLM's own claim (`chunk_list`) is kept next to it.
- **The reranker narrows the candidates.** With the reranker enabled, `top_k` is the candidate pool and only `RERANK_TOP_N` chunks reach the LLM.
- **Retrieval is a separate function** (`retrieve_chunks`) that can run without the LLM.

## 5. How to read the metrics

There are 17 answerable questions, so one question is worth about 6 percentage points: **88% = 15/17, 94% = 16/17.** A one-question difference is close to noise.

All retrieval metrics are **document-level**: they ask whether the right *document* arrived, not whether the exact sentence did.

| Metric | Question it answers | Good |
|---|---|---|
| **Hit** | Did at least one correct document reach the LLM? | high |
| **Recall** | Did *all* needed documents arrive? This matters for multi-hop questions. | high |
| **MRR** | How high was the first correct chunk ranked? 1.0 = always first, 0.5 = usually second. | high |
| **Distractor rate** | Of the 13 questions with a trap document, how often the trap also arrived | low, but see 6.5 |
| **Context tokens** | Tokens sent to the LLM per question (the cost) | low |
| **Chunks on unanswerable** | How much noise the LLM gets when there's no answer | low |
| **Latency** | Retrieval time only, without the LLM | low |

## 6. Retrieval results

First sweep, 24 configurations, embeddings from `gemini-embedding-2`. The three corpora have 78, 42 and 22 chunks (chunk sizes 128, 256 and 512). Full table: [`REPORT.md`](../rag/evaluation/results/REPORT.md).

### 6.1 Small chunks with top 3 are the best value

| Config | Hit | Recall | MRR | Distractor | Context tokens |
|---|---|---|---|---|---|
| chunk128, top 1 | 88% | 64% | 0.88 | 23% | 118 |
| **chunk128, top 3** | **100%** | **96%** | **0.93** | 46% | **352** |
| chunk128, top 8 | 100% | 98% | 0.93 | 92% | 940 |
| chunk256, top 1 | 76% | 55% | 0.76 | 31% | 182 |
| chunk256, top 3 | 88% | 81% | 0.81 | 46% | 588 |
| chunk512, top 1 | 88% | 64% | 0.88 | 23% | 364 |
| chunk512, top 3 | 100% | 98% | 0.93 | 69% | 1,075 |
| chunk512, top 8 | 100% | 100% | 0.93 | 100% | 2,857 |

Above top 3, recall barely moves while tokens and distractors keep growing.

### 6.2 Medium chunks (256) are the worst at small top-k

chunk256 is not between 128 and 512: it's below both at top 1 and top 3. It misses two questions at top 3:
- **Q15**, "What time does the Downtown location close on Sundays?": the Riverside document ranks first and the right document doesn't appear.
- **Q17**, "Is there a fee to bring my own birthday cake?": the kids menu (which mentions birthday cakes) and the 2024 archive outrank the current policy.

Section 7 explains why.

### 6.3 The reranker isn't worth its cost here

| | Hit | Recall | MRR | Latency |
|---|---|---|---|---|
| chunk128, top 3 | 100% | 96% | 0.93 | 5.7 ms |
| chunk128, 20 candidates → rerank → 3 | 100% | 96% | 0.96 | 2,465 ms |
| chunk128, top 1 | 88% | 64% | 0.88 | 4.8 ms |
| chunk128, 20 candidates → rerank → 1 | 94% | 70% | 0.94 | 2,502 ms |
| chunk512, 20 candidates → rerank → 3 | 100% | 95% | 0.94 | 13,593 ms |

- It improves the *first* position slightly, but at 3 chunks recall is unchanged.
- It costs seconds per query on CPU, more for longer chunks, because a cross-encoder reads the question together with every candidate.
- **It doesn't understand "outdated".** With the reranker, the 2024 archive still reaches the LLM for the corkage and cake questions, and the staff handbook for the dress-code and head-chef questions. A cross-encoder scores *topical relevance*, and an archived corkage rule is perfectly relevant to a corkage question.

### 6.4 A distance threshold could detect unanswerable questions

Cosine distance of the best match for each question, on chunk128:

- All 17 answerable questions: **0.187 – 0.266**
- All 3 unanswerable questions: **0.296 – 0.315**

A threshold in the gap (about 0.28) would give the LLM no context at all for unanswerable questions, which makes "I don't know" the natural answer. On chunk256 the gap doesn't exist: a threshold of 0.30 removed the unanswerable questions' context but also lost Q15, whose correct chunk sat at 0.297. **Pending:** thresholds 0.27, 0.28 and 0.29 on chunk128. With only 3 unanswerable questions this is a promising signal, not a proven setting.

### 6.5 A high distractor rate isn't automatically bad

For conflict questions, the right document and the trap usually arrive together (the current corkage rule *and* the 2024 one). Retrieval can't settle that; the LLM has to choose. That's why the generation stage matters.

### 6.6 The weakest question

Q9 (dog + patio + vegan, multi-hop) has 33% recall on chunk128 top 3. That's partly a labelling issue: the FAQ it retrieves answers the whole question on its own.

## 7. Why small chunks win here

**An embedding is roughly the average meaning of the whole chunk.** One chunk gets one vector. If the chunk covers one topic, the vector points clearly at that topic. If it covers six, it points somewhere in the middle and matches no single question well.

The chunk that contains the Downtown Sunday hours, at each size:

| Chunk size | What else is in that chunk |
|---|---|
| 128 | Opening hours, Reservations (~2 sections) |
| 256 | Opening hours, Reservations, cancellation fee, Pets, start of Outdoor seating (~5 sections) |
| 512 | The whole document (10 sections) |

The questions are short and ask about one fact. A 128-token chunk is about one section of these documents, so question and chunk are about the same amount of information.

**Why 512 also does well:** at 512 each chunk is a whole document (22 chunks for 20 documents). Those vectors are averages too, but the documents have clearly different topics, so picking the right one out of 20 is easy. The metrics are also document-level, so they don't penalize a 450-token chunk for being mostly irrelevant to the question. That cost shows up in context tokens instead (3x).

**Why 256 gets the worst of both:** it's too big to be focused, and too small to be the whole document. Only the first chunk of a document contains its title. The second half of "Restaurant Policies" is a list of pets, patio, corkage and cake rules that doesn't even say whose policies they are, so a question about Downtown Sunday hours can lose to the Riverside document.

**This depends on document length.** These documents are 250–550 tokens. With 10-page PDFs, 512 tokens wouldn't be a whole document and would behave like 256 does here. A more general way to put it: chunks should match how much text a typical question needs. Big chunks only work when they happen to line up with whole, single-topic documents.

## 8. Overlap is not context: contextual chunk headers

### 8.1 The problem

At chunk size 128, the archived policy splits into 4 chunks:

```
chunk 1: [ title · "ARCHIVED DOCUMENT... superseded..." · Opening hours (2024) ]
chunk 2: [ ...end of chunk 1... · Reservations · Pets · Patio · Bringing your own wine ]
chunk 3: [ ...end of chunk 2... · corkage fee was $15 · Outside food and cakes · Payments ]
chunk 4: [ ...end of chunk 3... · Why the policies changed ]
```

The chunk with "corkage fee was $15" **doesn't contain the word "ARCHIVED"**. The only clue the LLM gets is "(2024)" in the section headings. At 256 and 512 the warning is inside the chunk.

### 8.2 Why overlap and top-k don't fix it

- **Overlap copies only the last few tokens of the previous chunk** (24 tokens at chunk size 128). The warning is at the *start* of chunk 1; only the *end* of chunk 1 (the opening hours) is copied into chunk 2. Overlap exists so that a sentence cut at a boundary appears whole in one chunk. It provides local continuity, about one sentence.
- **Top-k ranks every chunk by distance to the question, not to each other.** Chunks from the same document don't pull each other in. Chunk 1 ("archived notice + opening hours 2024") is far from "How much is corkage?", so it rarely makes the top 3. The slots go to the chunks that mention corkage, without the warning.

### 8.3 Contextual chunk headers

Before embedding a chunk, add a short line saying where it comes from:

```
Document: The Garden Table - Restaurant Policies 2024 (ARCHIVED)
Section: Bringing your own wine (2024)
---
Guests could bring their own wine. The corkage fee was $15 per bottle, with no limit...
```

The header is part of every chunk of the document, so it helps at two stages:

| Stage | Without a header | With a header |
|---|---|---|
| Retrieval | A mid-document chunk ("pets, patio, corkage, cake…") doesn't know it belongs to "Restaurant Policies (Downtown)" | The vector includes the document's identity, so Downtown questions should match Downtown documents |
| Generation | The LLM sees "$15 corkage" and "$20 corkage" with no way to tell which is current | The LLM sees "(ARCHIVED)" on the $15 chunk |

How it compares with related techniques:

| Technique | Solves | Cost |
|---|---|---|
| Overlap | Sentences cut at a boundary (local context) | Slightly more chunks |
| **Contextual headers** | Which document, section and status a chunk belongs to (global context) | ~15–30 tokens per chunk, no LLM calls |
| Neighbor expansion: retrieve a small chunk, send it with its neighbors | Answers that span two chunks | More context tokens |
| LLM-written context: an LLM writes 1–2 sentences situating each chunk (Anthropic's "Contextual Retrieval") | Same as headers, richer | One LLM call per chunk (78 for chunk128): impossible on this quota |
| Metadata filtering, e.g. exclude `status=archived` at query time | Outdated documents, completely | Needs structured metadata per document |

Overlap and headers address different scopes and work best together: overlap for local context, headers for global context.

### 8.4 Implementation

`rag/services/chunks.py:build_chunk_headers`:
- **Document title:** the first line of the extracted text. If the first line ends with a connector ("and", "of", …) and the next line looks like a heading, the two are joined, because long titles wrap in the PDF ("…Location, Parking and" / "Transport").
- **Section:** the heading in effect where the chunk starts. That's the context the chunk is missing; a heading *inside* the chunk is already part of its text. A heading is a short line that starts with a capital letter or digit, isn't a bullet and doesn't end like a sentence. This was checked by hand on all 20 documents.
- **Storage:** the header lives in its own field (`DocumentChunkModel.header`), so the raw chunk text is unchanged. `contextual_text` (header + text) is what gets embedded, reranked and sent to the LLM.
- **Cost accounting:** header tokens are counted in "context tokens", so the comparison with plain chunks is fair.
- **Opt-in:** enabled per corpus (`contextual_headers=True`); the API default is unchanged.

**Pending:**
- Retrieval sweep on `chunk128_ctx` and `chunk256_ctx`. Prediction: chunk256 improves the most, since its nameless half-document chunks gain a title.
- Generation finalist `small_chunks_ctx`, compared with `small_chunks` and `whole_docs` on the conflict questions (Q14–Q17).

## 9. Generation results (pending)

Four finalists, one per day:

| Experiment | Retrieval | Question it answers |
|---|---|---|
| `small_chunks` | chunk128, top 3 | Does the best retrieval-per-token setting also give good answers? |
| `whole_docs` | chunk512, top 3 | Does 3x the context (with "ARCHIVED" visible) help on conflicts? |
| `small_chunks_threshold` | chunk128, top 3, threshold 0.28 | Does giving no context on unanswerable questions improve refusals without losing real answers? |
| `small_chunks_ctx` | chunk128 + headers, top 3 | Do headers give small chunks the context they're missing? |

What would count as evidence:
- If `small_chunks` misses Q14 or Q17 because the archived chunk had no warning, and `whole_docs` or `small_chunks_ctx` gets them right, that confirms the context tradeoff and that headers fix it cheaply.
- If `small_chunks_threshold` scores 5 on all three unanswerable questions without losing answerable ones, the threshold is useful.

## 10. Engineering problems found along the way

1. **Configuration that never reached the worker.** In an early version, chunking settings were changed by modifying module variables in the process that queued the tasks. Celery workers are separate processes and never saw the change. The fix was to pass chunk settings explicitly as task arguments.
2. **A shared code path broke search.** A change to support tool calling for the chat agent made the Gemini provider always call `available_tools.get_tools_schemas()`, which crashed for search, where there are no tools. It also gave every call the agent's system prompt. Tools and the agent prompt now apply to chat only.
3. **A batched embedding call returned fewer vectors than texts, and nothing noticed.** With `gemini-embedding-2`, a list of 18 strings came back as fewer vectors. My guess is that the model merged them; this wasn't confirmed against the API. The code paired texts and vectors with `zip`, which silently stops at the shorter list, and the bug surfaced later as a confusing `KeyError`. Now each text goes in its own request entry, the count is checked, the pairing is strict, and there's a one-by-one fallback.
4. **Filtered vector search can return fewer than k results.** All corpora live in one table and are filtered by document. With an HNSW index, pgvector applies the filter *after* scanning about `ef_search` (40) candidates, so a filtered top-k can come back short. The corpora are small, so the evaluation sets `hnsw.ef_search = 1000`, which makes the search effectively exact.
5. **Free-tier quotas shape the design.** 20 generation requests a day means: cache everything that can be cached (query vectors, corpora), separate free retrieval measurement from paid generation, make runs resumable, grade in one batched judge request, and allow the judge to use another model's quota.

## 11. Limitations

- **Small sample.** 17 answerable and 3 unanswerable questions, one run per configuration. Differences of one or two questions are noise.
- **Synthetic, short documents.** The findings about chunk size depend on 250–550-token documents (section 7).
- **Document-level metrics.** They don't check whether the exact passage arrived, and they don't penalize large chunks for irrelevant text (only token cost does).
- **The judge is an LLM**, of the same family as the answering model, and may be lenient toward it. Its grades should be spot-checked.
- **Mid-word chunk boundaries.** The token chunker splits at token counts, sometimes mid-word ("…00 AM to 10:30 PM"). That adds noise to every configuration equally, but a sentence-aware chunker could change the picture.

## 12. Next experiments

- Contextual headers (in progress, section 8).
- A threshold-based "no answer" path in the API itself, using the measured distance gap.
- Sentence- or heading-aware chunking instead of fixed token windows.
- Metadata filtering for document status (`archived`) and location.
- Neighbor expansion for multi-hop questions (Q9, Q11).
- A longer, real-world-length corpus to check whether "small chunks win" still holds.

## 13. Glossary

- **Embedding:** a vector (here 1,024 numbers) representing a text's meaning. Similar meanings give nearby vectors.
- **Cosine distance:** how far apart two vectors point. 0 means identical direction; lower means closer.
- **Chunk:** a piece of a document that gets its own embedding. **Chunk size** is measured in tokens; **overlap** is how many tokens consecutive chunks share.
- **Top-k:** how many of the nearest chunks are retrieved.
- **Bi-encoder vs cross-encoder:** the embedding model encodes question and chunk *separately* (fast, can precompute). A cross-encoder reranker reads them *together* (more precise, much slower, nothing precomputed).
- **Reranker:** a second, more expensive model that re-scores retrieved candidates so only the best are kept.
- **Hit / Recall / MRR:** see section 5.
- **Distractor:** a document that looks relevant but would give a wrong answer (outdated, other location, other season).
- **HNSW / ef_search:** pgvector's approximate nearest-neighbor index, and how many candidates it examines per search.

## 14. Log

| Date | Step |
|---|---|
| 2026-10-27 | Reviewed the pilot (A/B/C) and found the six problems in section 3 |
| 2026-10-28 | Rebuilt the harness: real retrieval logging, reranker that narrows, 20-document knowledge base with traps, 20-question dataset, two-stage evaluation |
| 2026-10-29 | Fixed batched query embeddings with `gemini-embedding-2` (section 10.3) |
| 2026-10-30 | First retrieval sweep (24 configurations): section 6 |
| 2026-11-08 | Analyzed why chunk size 128 wins (section 7); added a chunk128 threshold sweep, four generation finalists and contextual chunk headers (section 8) |
