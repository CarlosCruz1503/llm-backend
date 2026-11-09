# RAG evaluation report

Generated 2026-10-30T02:36:22+00:00 by `python manage.py rag_eval report`.

## Retrieval sweep (no LLM calls)

20 questions, embeddings from `gemini-embedding-2`. Hit / recall / MRR are over answerable questions, at document level. *Distractor* = an outdated or look-alike document was in the context. *Ctx tokens* = tokens sent to the LLM per question.

| Config | Hit | Recall | MRR | Distractor | Ctx tokens | Chunks on unanswerable | Latency ms |
|---|---|---|---|---|---|---|---|
| `chunk128_k1` (chunk128, top 1) | 88% | 64% | 0.88 | 23% | 118 | 1.0 | 4.8 |
| `chunk128_k3` (chunk128, top 3) | 100% | 96% | 0.93 | 46% | 352 | 3.0 | 5.7 |
| `chunk128_k5` (chunk128, top 5) | 100% | 98% | 0.93 | 69% | 588 | 5.0 | 6.3 |
| `chunk128_k8` (chunk128, top 8) | 100% | 98% | 0.93 | 92% | 940 | 8.0 | 6.9 |
| `chunk256_k1` (chunk256, top 1) | 76% | 55% | 0.76 | 31% | 182 | 1.0 | 6.0 |
| `chunk256_k3` (chunk256, top 3) | 88% | 81% | 0.81 | 46% | 588 | 3.0 | 4.8 |
| `chunk256_k5` (chunk256, top 5) | 100% | 92% | 0.84 | 77% | 970 | 5.0 | 5.3 |
| `chunk256_k8` (chunk256, top 8) | 100% | 98% | 0.84 | 92% | 1616 | 8.0 | 6.2 |
| `chunk512_k1` (chunk512, top 1) | 88% | 64% | 0.88 | 23% | 364 | 1.0 | 4.2 |
| `chunk512_k3` (chunk512, top 3) | 100% | 98% | 0.93 | 69% | 1075 | 3.0 | 5.5 |
| `chunk512_k5` (chunk512, top 5) | 100% | 100% | 0.93 | 92% | 1836 | 5.0 | 5.7 |
| `chunk512_k8` (chunk512, top 8) | 100% | 100% | 0.93 | 100% | 2857 | 8.0 | 6.7 |
| `chunk128_rerank20to1` (chunk128, top 20 -> rerank -> 1) | 94% | 70% | 0.94 | 23% | 120 | 1.0 | 2501.5 |
| `chunk128_rerank20to3` (chunk128, top 20 -> rerank -> 3) | 100% | 96% | 0.96 | 54% | 374 | 3.0 | 2464.9 |
| `chunk128_rerank20to5` (chunk128, top 20 -> rerank -> 5) | 100% | 98% | 0.96 | 92% | 620 | 5.0 | 2688.4 |
| `chunk256_rerank20to1` (chunk256, top 20 -> rerank -> 1) | 82% | 61% | 0.82 | 31% | 223 | 1.0 | 5242.7 |
| `chunk256_rerank20to3` (chunk256, top 20 -> rerank -> 3) | 100% | 95% | 0.90 | 54% | 637 | 3.0 | 5165.6 |
| `chunk256_rerank20to5` (chunk256, top 20 -> rerank -> 5) | 100% | 100% | 0.90 | 77% | 1053 | 5.0 | 4865.0 |
| `chunk512_rerank20to1` (chunk512, top 20 -> rerank -> 1) | 88% | 64% | 0.88 | 31% | 342 | 1.0 | 12829.2 |
| `chunk512_rerank20to3` (chunk512, top 20 -> rerank -> 3) | 100% | 95% | 0.94 | 62% | 1107 | 3.0 | 13592.7 |
| `chunk512_rerank20to5` (chunk512, top 20 -> rerank -> 5) | 100% | 98% | 0.94 | 77% | 1830 | 5.0 | 14455.6 |
| `chunk256_k8_thr0.30` (chunk256, top 8, threshold 0.3) | 94% | 89% | 0.83 | 69% | 825 | 0.0 | 12.3 |
| `chunk256_k8_thr0.35` (chunk256, top 8, threshold 0.35) | 100% | 98% | 0.84 | 92% | 1477 | 6.0 | 12.1 |
| `chunk256_k8_thr0.40` (chunk256, top 8, threshold 0.4) | 100% | 98% | 0.84 | 92% | 1616 | 8.0 | 10.2 |

### Can a distance threshold detect unanswerable questions?

Mean cosine distance of the top-1 chunk (lower = closer).

| Corpus | Answerable | Unanswerable |
|---|---|---|
| chunk128 | 0.224 | 0.307 |
| chunk256 | 0.236 | 0.312 |
| chunk512 | 0.243 | 0.316 |
