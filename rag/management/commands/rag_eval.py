from django.core.management.base import BaseCommand, CommandError

from rag.constants import EVAL_JUDGE_MODEL
from rag.evaluation.experiments import CORPORA, GENERATION_EXPERIMENTS
from rag.services import evaluation


class Command(BaseCommand):
    help = (
        "RAG evaluation. `corpora` embeds the knowledge base for every chunking config, "
        "`retrieval` runs the LLM-free sweep, `generate <experiment>` answers the dataset "
        "(resumable, 1 LLM request per question), `judge <experiment>` grades it in 1 request, "
        "`report` rebuilds results/REPORT.md."
    )

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest="action", required=True)
        actions.add_parser("corpora")
        actions.add_parser("retrieval")

        generate = actions.add_parser("generate")
        generate.add_argument("experiment", choices=sorted(GENERATION_EXPERIMENTS))
        generate.add_argument("--max-requests", type=int, default=20, help="LLM requests to spend in this run")
        generate.add_argument("--sleep", type=float, default=15, help="seconds between LLM requests")

        judge = actions.add_parser("judge")
        judge.add_argument("experiment", choices=sorted(GENERATION_EXPERIMENTS))
        judge.add_argument("--model", default=EVAL_JUDGE_MODEL, help="judge model (default: EVAL_JUDGE_MODEL or GEMINI_AI_MODEL)")

        actions.add_parser("report")

    def handle(self, *args, **options):
        try:
            getattr(self, f"handle_{options['action']}")(options)
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

    def handle_corpora(self, options):
        evaluation.require_superuser()
        for corpus in CORPORA.values():
            document_ids = evaluation.ensure_corpus(corpus)
            self.stdout.write(f"{corpus.key}: {len(document_ids)} documents ready")

    def handle_retrieval(self, options):
        payload = evaluation.run_retrieval_sweep()
        self.stdout.write(f"{len(payload['summaries'])} retrieval configs evaluated -> {evaluation.SWEEP_PATH}")
        self._report()

    def handle_generate(self, options):
        run, requests_made = evaluation.run_generation(
            options["experiment"], max_requests=options["max_requests"], sleep_seconds=options["sleep"]
        )
        total = len(evaluation.load_dataset())
        self.stdout.write(
            f"{options['experiment']}: {len(run['results'])}/{total} answered, {requests_made} LLM requests used this run"
        )
        if len(run["results"]) < total:
            self.stdout.write("Not finished. Run the same command again (e.g. tomorrow) to resume.")
        self._report()

    def handle_judge(self, options):
        graded, missing = evaluation.run_judge(options["experiment"], model=options["model"])
        self.stdout.write(f"{options['experiment']}: {graded} answers graded in 1 LLM request")
        if missing:
            self.stdout.write(f"The judge skipped questions {missing}; run judge again to grade them.")
        self._report()

    def handle_report(self, options):
        self._report()

    def _report(self):
        self.stdout.write(f"Report -> {evaluation.build_report()}")
