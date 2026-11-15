# RAG evaluation report

Generated 2026-11-13T02:06:11+00:00 by `python manage.py rag_eval report`.

## Retrieval sweep (no LLM calls)

20 questions, embeddings from `gemini-embedding-2`. Hit / recall / MRR are over answerable questions, at document level. *Distractor* = an outdated or look-alike document was in the context. *Ctx tokens* = tokens sent to the LLM per question.

| Config | Hit | Recall | MRR | Distractor | Ctx tokens | Chunks on unanswerable | Latency ms |
|---|---|---|---|---|---|---|---|
| `chunk128_k1` (chunk128, top 1) | 88% | 64% | 0.88 | 23% | 118 | 1.0 | 5.2 |
| `chunk128_k3` (chunk128, top 3) | 100% | 96% | 0.93 | 46% | 352 | 3.0 | 5.8 |
| `chunk128_k5` (chunk128, top 5) | 100% | 98% | 0.93 | 69% | 588 | 5.0 | 6.0 |
| `chunk128_k8` (chunk128, top 8) | 100% | 98% | 0.93 | 92% | 940 | 8.0 | 6.5 |
| `chunk256_k1` (chunk256, top 1) | 76% | 55% | 0.76 | 31% | 182 | 1.0 | 4.8 |
| `chunk256_k3` (chunk256, top 3) | 88% | 81% | 0.81 | 46% | 588 | 3.0 | 5.9 |
| `chunk256_k5` (chunk256, top 5) | 100% | 92% | 0.84 | 77% | 970 | 5.0 | 8.0 |
| `chunk256_k8` (chunk256, top 8) | 100% | 98% | 0.84 | 92% | 1616 | 8.0 | 6.9 |
| `chunk512_k1` (chunk512, top 1) | 88% | 64% | 0.88 | 23% | 364 | 1.0 | 4.2 |
| `chunk512_k3` (chunk512, top 3) | 100% | 98% | 0.93 | 69% | 1075 | 3.0 | 4.6 |
| `chunk512_k5` (chunk512, top 5) | 100% | 100% | 0.93 | 92% | 1836 | 5.0 | 5.2 |
| `chunk512_k8` (chunk512, top 8) | 100% | 100% | 0.93 | 100% | 2857 | 8.0 | 6.1 |
| `chunk128_ctx_k1` (chunk128_ctx, top 1) | 94% | 70% | 0.94 | 15% | 136 | 1.0 | 4.9 |
| `chunk128_ctx_k3` (chunk128_ctx, top 3) | 100% | 92% | 0.96 | 62% | 405 | 3.0 | 5.0 |
| `chunk128_ctx_k5` (chunk128_ctx, top 5) | 100% | 98% | 0.96 | 85% | 673 | 5.0 | 6.5 |
| `chunk128_ctx_k8` (chunk128_ctx, top 8) | 100% | 98% | 0.96 | 100% | 1064 | 8.0 | 8.1 |
| `chunk256_ctx_k1` (chunk256_ctx, top 1) | 94% | 70% | 0.94 | 15% | 257 | 1.0 | 5.6 |
| `chunk256_ctx_k3` (chunk256_ctx, top 3) | 100% | 98% | 0.97 | 38% | 676 | 3.0 | 5.0 |
| `chunk256_ctx_k5` (chunk256_ctx, top 5) | 100% | 98% | 0.97 | 85% | 1118 | 5.0 | 6.6 |
| `chunk256_ctx_k8` (chunk256_ctx, top 8) | 100% | 98% | 0.97 | 92% | 1833 | 8.0 | 7.5 |
| `chunk128_rerank20to1` (chunk128, top 20 -> rerank -> 1) | 94% | 70% | 0.94 | 23% | 120 | 1.0 | 2261.1 |
| `chunk128_rerank20to3` (chunk128, top 20 -> rerank -> 3) | 100% | 96% | 0.96 | 54% | 374 | 3.0 | 2226.0 |
| `chunk128_rerank20to5` (chunk128, top 20 -> rerank -> 5) | 100% | 98% | 0.96 | 92% | 620 | 5.0 | 2487.0 |
| `chunk256_rerank20to1` (chunk256, top 20 -> rerank -> 1) | 82% | 61% | 0.82 | 31% | 223 | 1.0 | 5229.6 |
| `chunk256_rerank20to3` (chunk256, top 20 -> rerank -> 3) | 100% | 95% | 0.90 | 54% | 637 | 3.0 | 5273.6 |
| `chunk256_rerank20to5` (chunk256, top 20 -> rerank -> 5) | 100% | 100% | 0.90 | 77% | 1053 | 5.0 | 5290.1 |
| `chunk512_rerank20to1` (chunk512, top 20 -> rerank -> 1) | 88% | 64% | 0.88 | 31% | 342 | 1.0 | 10591.2 |
| `chunk512_rerank20to3` (chunk512, top 20 -> rerank -> 3) | 100% | 95% | 0.94 | 62% | 1107 | 3.0 | 11726.8 |
| `chunk512_rerank20to5` (chunk512, top 20 -> rerank -> 5) | 100% | 98% | 0.94 | 77% | 1830 | 5.0 | 12240.3 |
| `chunk256_k8_thr0.30` (chunk256, top 8, threshold 0.3) | 94% | 89% | 0.83 | 69% | 825 | 0.0 | 5.8 |
| `chunk256_k8_thr0.35` (chunk256, top 8, threshold 0.35) | 100% | 98% | 0.84 | 92% | 1477 | 6.0 | 7.3 |
| `chunk256_k8_thr0.40` (chunk256, top 8, threshold 0.4) | 100% | 98% | 0.84 | 92% | 1616 | 8.0 | 7.1 |
| `chunk128_k3_thr0.27` (chunk128, top 3, threshold 0.27) | 94% | 84% | 0.91 | 38% | 252 | 0.0 | 6.3 |
| `chunk128_k3_thr0.28` (chunk128, top 3, threshold 0.28) | 94% | 84% | 0.91 | 38% | 265 | 0.0 | 4.9 |
| `chunk128_k3_thr0.29` (chunk128, top 3, threshold 0.29) | 94% | 90% | 0.91 | 38% | 292 | 0.0 | 5.0 |

### Can a distance threshold detect unanswerable questions?

Mean cosine distance of the top-1 chunk (lower = closer).

| Corpus | Answerable | Unanswerable |
|---|---|---|
| chunk128 | 0.224 | 0.307 |
| chunk256 | 0.236 | 0.312 |
| chunk512 | 0.243 | 0.316 |
| chunk128_ctx | 0.221 | 0.314 |
| chunk256_ctx | 0.236 | 0.327 |

## Generation (answer + LLM judge)

Score is 1-5: your `manual_score` when set, otherwise the judge's.

| Experiment | Answered | Avg score | Single | Multi-hop | Conflict | Unanswerable | Hallucinations | False refusals | Avg tokens | Avg latency s |
|---|---|---|---|---|---|---|---|---|---|---|
| `medium_chunks_ctx` (chunk256_ctx, top 3) | 20 | 4.95 | 5.00 | 4.80 | 5.00 | 5.00 | 0 | 0 | 1677 | 147.5 |
| `small_chunks` (chunk128, top 3) | 20 | 4.60 | 4.12 | 4.80 | 5.00 | 5.00 | 0 | 1 | 1384 | 5.2 |
| `small_chunks_threshold` (chunk128, top 3, threshold 0.29) | 20 | 4.55 | 4.50 | 4.80 | 4.00 | 5.00 | 0 | 2 | 1222 | 64.4 |
| `whole_docs` (chunk512, top 3) | 20 | 5.00 | 5.00 | 5.00 | 5.00 | 5.00 | 0 | 0 | 2043 | 4.9 |

### Per question

| Q | Type | medium_chunks_ctx | small_chunks | small_chunks_threshold | whole_docs |
|---|---|---|---|---|---|
| 1. What vegetarian main courses are on the regular menu? | single | 5 | 5 | 5 | 5 |
| 2. How far do you deliver and how much is the delivery fee? | single | 5 | 5 | 5 | 5 |
| 3. How many people fit in the private dining room and what is the minimum spend on a Saturday? | single | 5 | 3 | 5 | 5 |
| 4. How do I earn and redeem points in the loyalty program? | single | 5 | 5 | 5 | 5 |
| 5. What does the restaurant do with food waste? | single | 5 | 4 | 5 | 5 |
| 6. Is the Downtown restaurant wheelchair accessible? | single | 5 | 5 | 5 | 5 |
| 7. When is weekend brunch served? | single | 5 | 5 | 5 | 5 |
| 8. What is the minimum number of guests for catering and how much notice do you need? | single | 5 | 1 | 1 | 5 |
| 9. At the Downtown restaurant, can I bring my dog, sit outside and order a vegan main course? | multi_hop | 5 | 5 | 5 | 5 |
| 10. Which desserts have no nuts in the recipe, and how much do they cost? | multi_hop | 4 | 4 | 4 | 5 |
| 11. I want a seated company dinner for 30 people. Can I use the private dining room, or what are my options? | multi_hop | 5 | 5 | 5 | 5 |
| 12. Can I use a gift card to pay for a delivery order? | multi_hop | 5 | 5 | 5 | 5 |
| 13. Can my kids order from the kids menu during weekend brunch, and what is included? | multi_hop | 5 | 5 | 5 | 5 |
| 14. How much is the corkage fee if I bring my own wine? | conflict | 5 | 5 | 5 | 5 |
| 15. What time does the Downtown location close on Sundays? | conflict | 5 | 5 | 1 | 5 |
| 16. How much does the grilled salmon cost on the regular menu? | conflict | 5 | 5 | 5 | 5 |
| 17. Is there a fee to bring my own birthday cake? | conflict | 5 | 5 | 5 | 5 |
| 18. Is there a dress code for guests? | unanswerable | 5 | 5 | 5 | 5 |
| 19. Do you have live music on weekends? | unanswerable | 5 | 5 | 5 | 5 |
| 20. What is the name of the head chef? | unanswerable | 5 | 5 | 5 | 5 |
