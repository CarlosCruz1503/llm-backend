## RAG Evaluation

## 1. What are we going to do?

We are going to embbed a knowledge base of a restaurant and we will use diferrent configurations in:
    - Chunk Size
    - Chunk Overlap Size
    - Top k chunks selected
    - Threshold
    - Rerank active/not active

This will allow us to compare the different results provided by this variations in configurations,
with this we are going to know which are the best configurations and settings for a project like this (This is a experimental exercise and have educational purposes)

For this experiments we are going to use for search and for embed the models configured via the `GEMINI_AI_MODEL` and `GEMINI_EMBEDDING_MODEL` env vars (see `.env`), and the knowledge database of files to be used will be in `rag/evaluation/data/testset_files`

## 2. How are we going to do this ?

It is quite simple, with a service called `EvaluationService` (`rag/services/evaluation.py`) we upload all the files with the configuration defined for the experiment being run, this service then asks all the questions listed in `rag/evaluation/dataset.json` and the results of each question are recorded and scored in `rag/evaluation/results/{experiment_name}_evaluation_results.json`.

Document embedding still goes through the normal async pipeline (`web` queues Celery tasks that `celery_worker` processes), so the chunk/overlap/token_model chosen for the experiment are passed explicitly through that pipeline (task args, not global state) — see `rag/services/document.py`, `rag/tasks.py` and `rag/services/evaluation.py`. `EvaluationService` blocks (`wait_for_processing`) until every uploaded document reaches a terminal status (`completed`/`failed`) before it starts asking questions, since search needs the embeddings to already exist. Search itself runs synchronously in the same process.

To generate the file `rag/evaluation/results/{experiment_name}_evaluation_results.json` it is necessary to:
1. Run in the server the commands `make reset_db` and `make migrate` — this is for cleaning the DB and assuring a clean run of the tests.
2. Run the script for the experiment that we want, these scripts are in `rag/evaluation/scripts/{experiment_name}.py`:
   ```bash
   docker exec -it core_prompt python manage.py shell -c "exec(open('rag/evaluation/scripts/experiment_A.py').read())"
   ```
   (swap `experiment_A.py` for `experiment_B.py` / `experiment_C.py` to run the other configurations)
3. Once `rag/evaluation/results/{experiment_name}_evaluation_results.json` is generated, open it and fill in `manual_calification` (a score you assign) and set `manual_calification_setted` to `true` for each question — this is a manual grading pass on top of the automatic `is_match` (fetched document vs. expected document) check, since matching the right source document doesn't guarantee the generated answer itself is good.
4. Compare the `evaluation_config` + scored `results` across `experiment_A_evaluation_results.json`, `experiment_B_evaluation_results.json` and `experiment_C_evaluation_results.json` to decide which configuration works best for this project.

### Designed experiments:

#### Experiment A (Small values)
- token_model = cl100k_base
- chunk_size = 50
- overlap = 10
- top_k = 3
- threshold = disabled
- reranker = disabled

### Experiment B (Medium values)
- token_model = cl100k_base
- chunk_size = 200
- overlap = 40
- top_k = 5
- threshold = 0.4
- reranker = disabled

### Experiment C (Medium values Reranked)
- token_model = cl100k_base
- chunk_size = 200
- overlap = 40
- top_k = 10
- threshold = 0.4
- reranker = enabled

### Knowledge Base

The evaluation dataset contains six documents representing the
knowledge base of a fictional restaurant.

| Document | Content |
|---|---|
| Menu | Dishes, prices, ingredients and beverages |
| Hours & Reservations | Opening hours and reservation policies |
| Policies | Pets, dress code, outside food and outdoor seating |
| Payments & Events | Payments, location, parking and private events |
| Dietary & Allergens | Vegetarian, vegan, gluten-free and allergens |
| Sustainability | Suppliers, waste, energy and water practices |

The documents intentionally contain information distributed across
multiple documents in order to test multi-document retrieval.

### Evaluation Dataset

```
rag/evaluation/
├── README.md
├── dataset.json
├── data/
│   └── testset_files/
├── scripts/
│   ├── experiment_A.py
│   ├── experiment_B.py
│   └── experiment_C.py
└── results/
    ├── experiment_A_evaluation_results.json
    ├── experiment_B_evaluation_results.json
    └── experiment_C_evaluation_results.json
```
