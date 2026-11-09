# v1 pilot: what it measured, and why it was misleading

These are the results of the first version of the evaluation harness, kept for reference. The knowledge base and scripts used for this run are in git history at commit `b7ca4f8` (`rag/evaluation/data/testset_files/` and `rag/evaluation/scripts/experiment_{A,B,C}.py`).

## Configurations

| | Chunk size / overlap | top_k | Threshold | Reranker |
|---|---|---|---|---|
| A | 50 / 10 | 3 | disabled | off |
| B | 200 / 40 | 5 | 0.4 | off |
| C | 200 / 40 | 10 | 0.4 | on |

## Results (the 16 questions all three runs share)

| | A | B | C |
|---|---|---|---|
| Avg manual score (1-5) | 3.69 | 4.38 | **4.56** |
| Answers scored 5 | 7 | 10 | **14** |
| Answers scored 2 or less | 4 | **0** | 2 |
| LLM cited the expected document | 7/12 | 10/12 | 10/12 |
| Avg tokens per query | **1,175** | 1,997 | 3,558 |

At face value, C (reranked) is the best configuration, at 3x the token cost of A. That conclusion doesn't hold, for these reasons:

1. **The knowledge base was too small for retrieval to matter.** All nine PDFs together were 1,644 tokens, and each document was 135 to 270 tokens. At chunk size 200, one chunk was about one whole document, so the corpus was around a dozen chunks. With top_k = 10, configuration C sent almost the entire knowledge base to the LLM on every question. Its scores measured "put everything in the prompt", not retrieval quality.

2. **The reranker only reordered.** It scored the 10 retrieved chunks and sorted them, but all 10 still reached the LLM. The context, and the cost, were the same as without it.

3. **"Retrieval recall" came from the LLM.** `retrieved_documents` and `is_match` were built from `chunk_list` and `chunk_id`, which are fields in the JSON *the LLM writes*. They measured what the model said it used, not what pgvector returned.

4. **Several variables changed at once.** A to B changed chunk size, overlap, top_k and the threshold together; B to C changed top_k and the reranker. No single improvement can be attributed to any one setting.

5. **Grading was inconsistent.** The sustainability question was labelled unanswerable, but the menu mentions locally sourced ingredients: B answered that and got 3, while A and C correctly refused and got 1. On the dairy question, one complete list scored 5 and a one-dish answer scored 2, which graded answer completeness rather than retrieval.

6. **Small and unrepeated.** 16 questions, one run each, one grader. The 0.18-point gap between B and C is 3 points in total.

## What changed in v2

- 20-document knowledge base (~8k tokens) with distractors: a second location, an archived policy, a winter menu, a staff-only dress code.
- Retrieval is logged from pgvector (`SearchModel.retrieved_chunks`), not taken from the LLM's output.
- The reranker keeps only `rerank_top_n` of a larger candidate pool.
- A retrieval sweep changes one variable at a time, without LLM calls; only a few finalists get full answers.
- Answers are graded by an LLM judge with a fixed rubric (a correct refusal scores 5), with manual overrides.
