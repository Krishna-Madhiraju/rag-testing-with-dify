"""
Score evaluation results with RAGAS metrics.

What this script does:
  Reads a completed run CSV (from run_evaluation.py + score_results.py),
  runs the four standard RAGAS metrics against the in-scope rows,
  and saves per-row scores plus a summary.

The four metrics:
  Faithfulness      — are all claims in the answer supported by the retrieved context?
                      Detects hallucination statement by statement.
  Answer Relevancy  — does the answer actually address the question?
                      Uses embedding similarity, not a reference answer.
  Context Precision — were the retrieved chunks actually useful? Rank-weighted.
                      Penalises noisy retrieval.
  Context Recall    — did the retriever find everything needed for the reference answer?
                      Catches missed chunks.

LLM judge and embeddings:
  This script uses Claude (via ANTHROPIC_API_KEY — the same key as score_results.py)
  as the RAGAS judge, and a free local sentence-transformers model for the
  embedding-based Answer Relevancy metric. No OpenAI key or spend required.

Prerequisites:
  python3.11 -m pip install ragas sentence-transformers anthropic

Setup:
  Add ANTHROPIC_API_KEY=sk-ant-... to your .env file (same key used by score_results.py).

Usage:
  python3.11 golden-dataset/ragas_eval.py                        # scores runs/run-001.csv
  python3.11 golden-dataset/ragas_eval.py runs/run-002.csv       # scores a different file
  python3.11 golden-dataset/ragas_eval.py --metrics faith,rel    # subset of metrics

Metric shortcodes:
  faith   = Faithfulness
  rel     = Answer Relevancy
  prec    = Context Precision
  rec     = Context Recall
  (default: all four)

Output:
  golden-dataset/runs/ragas-scores.csv   — per-row RAGAS scores
  golden-dataset/runs/ragas-summary.md   — averages by query type

Notes on cost:
  The Claude judge calls cost a small amount per row per metric (Haiku pricing).
  The local embedding model (sentence-transformers/all-MiniLM-L6-v2) runs on your
  machine and is free, but downloads ~90 MB the first time it's used.
"""

import csv
import math
import os
import sys

# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------
args = sys.argv[1:]
METRIC_FILTER = None
INPUT_FILE_ARG = None
for a in args:
    if a.startswith("--metrics="):
        METRIC_FILTER = a.split("=", 1)[1].split(",")
    elif not a.startswith("--"):
        INPUT_FILE_ARG = a

INPUT_FILE = INPUT_FILE_ARG or "golden-dataset/runs/run-001.csv"
OUTPUT_SCORES = os.path.join(os.path.dirname(INPUT_FILE), "ragas-scores.csv")
OUTPUT_SUMMARY = os.path.join(os.path.dirname(INPUT_FILE), "ragas-summary.md")

# --------------------------------------------------------------------------
# Load .env
# --------------------------------------------------------------------------
def load_dotenv(path=".env"):
    here = os.path.dirname(os.path.abspath(globals().get("__file__", "")))
    repo_root_env = os.path.join(os.path.dirname(here), path)
    for candidate in (path, repo_root_env):
        if not os.path.exists(candidate):
            continue
        with open(candidate, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        break

load_dotenv()

# --------------------------------------------------------------------------
# Compatibility shim: recent langchain-community releases dropped the
# chat_models.vertexai submodule, but ragas 0.4.x still imports ChatVertexAI
# at module load time for an unused legacy type-check list. We don't use
# VertexAI, so a stub class satisfies the import without needing Google's SDK.
# --------------------------------------------------------------------------
import sys as _sys
import types as _types
try:
    import langchain_community.chat_models.vertexai  # noqa: F401
except ModuleNotFoundError:
    _stub = _types.ModuleType("langchain_community.chat_models.vertexai")
    _stub.ChatVertexAI = type("ChatVertexAI", (), {})
    _sys.modules["langchain_community.chat_models.vertexai"] = _stub

# --------------------------------------------------------------------------
# Dependency check
# --------------------------------------------------------------------------
try:
    from ragas import evaluate
    from ragas.dataset_schema import EvaluationDataset
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.llms import llm_factory
    # ragas.embeddings.HuggingfaceEmbeddings (the legacy, sync-only wrapper that would
    # otherwise match the answer_relevancy/faithfulness metrics used below) ships
    # incomplete in ragas 0.4.3 — it never implements the required aembed_query/
    # aembed_documents methods, so it can't even be instantiated. Instead we use
    # LangChain's own local HuggingFace embeddings class (which gets working async
    # methods for free via LangChain's base Embeddings executor default) and adapt it
    # with ragas's LangchainEmbeddingsWrapper.
    from langchain_community.embeddings import HuggingFaceEmbeddings as LCHuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
except ImportError as e:
    sys.exit(f"Missing dependency: {e}\nRun: pip install ragas sentence-transformers anthropic")

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit("Missing: pip install anthropic")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_KEY or "your-key" in ANTHROPIC_KEY:
    sys.exit(
        "ANTHROPIC_API_KEY not set.\n"
        "This script uses Claude as the RAGAS judge (same key as score_results.py).\n"
        "Add ANTHROPIC_API_KEY=sk-ant-... to your .env file and re-run."
    )

# --------------------------------------------------------------------------
# Row filters
# --------------------------------------------------------------------------
# These query types have no reference answer — skip Context Precision/Recall
# They also cannot be assessed for hallucination the same way as in-scope rows
OUT_OF_SCOPE_TYPES = {"out-of-scope", "fictitious-entity", "adversarial"}
IN_SCOPE_TYPES = {"factual", "paraphrase", "multi-hop", "comparative"}


def parse_chunks(pipe_separated: str) -> list:
    """
    Convert the pipe-separated retrieved_chunks field from the CSV back into
    a list of strings that RAGAS expects for 'retrieved_contexts'.
    """
    if not pipe_separated:
        return []
    return [c.strip() for c in pipe_separated.split("|") if c.strip()]


# --------------------------------------------------------------------------
# Build RAGAS dataset
# --------------------------------------------------------------------------
def build_ragas_dataset(rows: list) -> tuple:
    """
    Convert golden-dataset run rows into a RAGAS EvaluationDataset.

    Returns (dataset, original_indices) so results can be mapped back to rows.
    Only includes in-scope rows that have both an actual_answer and retrieved chunks.
    """
    samples, original_indices = [], []

    for i, row in enumerate(rows):
        qt = row.get("query_type", "").strip().lower()
        actual = row.get("actual_answer", "").strip()
        chunks = parse_chunks(row.get("retrieved_chunks", ""))
        reference = row.get("reference_answer", "").strip()

        if qt not in IN_SCOPE_TYPES:
            continue
        if not actual:
            continue
        if not chunks:
            continue

        samples.append({
            "user_input": row["question"],
            "response": actual,
            "retrieved_contexts": chunks,
            "reference": reference,
        })
        original_indices.append(i)

    dataset = EvaluationDataset.from_list(samples)
    return dataset, original_indices


# --------------------------------------------------------------------------
# Metric selection
# --------------------------------------------------------------------------
ALL_METRICS = {
    "faith": faithfulness,
    "rel": answer_relevancy,
    "prec": context_precision,
    "rec": context_recall,
}

METRIC_COL_NAMES = {
    "faithfulness": "ragas_faithfulness",
    "answer_relevancy": "ragas_answer_relevancy",
    "context_precision": "ragas_context_precision",
    "context_recall": "ragas_context_recall",
}


def select_metrics() -> list:
    if METRIC_FILTER:
        selected = []
        for key in METRIC_FILTER:
            key = key.strip()
            if key not in ALL_METRICS:
                sys.exit(f"Unknown metric shortcode: '{key}'. Valid: {', '.join(ALL_METRICS)}")
            selected.append(ALL_METRICS[key])
        return selected
    return list(ALL_METRICS.values())


# --------------------------------------------------------------------------
# Summary report
# --------------------------------------------------------------------------
def write_summary(rows_with_scores: list, scored_indices: set) -> None:
    lines = [
        "# RAGAS Evaluation Summary\n",
        f"Input: {INPUT_FILE}\n",
        f"Judge LLM: Claude (claude-haiku-4-5-20251001) | Embeddings: local sentence-transformers/all-MiniLM-L6-v2\n",
        f"Rows evaluated: {len(scored_indices)} in-scope rows with actual answers\n",
    ]

    # Per-metric averages
    score_cols = [c for c in rows_with_scores[0].keys() if c.startswith("ragas_")]
    lines.append("\n## Average Scores (in-scope rows)\n")
    for col in score_cols:
        vals = []
        for r in rows_with_scores:
            v = r.get(col, "")
            try:
                fv = float(v)
                if not math.isnan(fv):
                    vals.append(fv)
            except (ValueError, TypeError):
                pass
        avg = sum(vals) / len(vals) if vals else None
        label = col.replace("ragas_", "").replace("_", " ").title()
        lines.append(f"{label:30s} {avg:.3f}" if avg is not None else f"{label:30s} n/a")

    # Per query-type breakdown
    lines.append("\n## By Query Type\n")
    types = sorted({r.get("query_type", "") for r in rows_with_scores if r.get("query_type")})
    for qt in types:
        subset = [r for r in rows_with_scores if r.get("query_type") == qt]
        if not subset:
            continue
        lines.append(f"\n### {qt} ({len(subset)} rows)")
        for col in score_cols:
            vals = []
            for r in subset:
                try:
                    fv = float(r.get(col, ""))
                    if not math.isnan(fv):
                        vals.append(fv)
                except (ValueError, TypeError):
                    pass
            avg = sum(vals) / len(vals) if vals else None
            label = col.replace("ragas_", "").replace("_", " ").title()
            lines.append(f"  {label:30s} {avg:.3f}" if avg is not None else f"  {label:30s} n/a")

    summary = "\n".join(lines)
    print("\n" + summary)
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"\nSummary saved to {OUTPUT_SUMMARY}")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    if not os.path.exists(INPUT_FILE):
        sys.exit(
            f"File not found: {INPUT_FILE}\n"
            "Run run_evaluation.py first to generate results."
        )

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        base_fieldnames = reader.fieldnames or []

    print(f"Loaded {len(rows)} rows from {INPUT_FILE}")

    metrics = select_metrics()
    metric_names = [m.name for m in metrics]
    print(f"Metrics: {', '.join(metric_names)}")

    ragas_dataset, original_indices = build_ragas_dataset(rows)
    n_scoreable = len(original_indices)

    if n_scoreable == 0:
        sys.exit(
            "No scoreable rows found.\n"
            "Make sure run_evaluation.py has been run and actual_answer + retrieved_chunks are filled in."
        )

    print(f"Scoring {n_scoreable} in-scope rows (out-of-scope rows are skipped)...")
    print("Judge: Claude (claude-haiku-4-5-20251001)  |  Embeddings: local sentence-transformers (first run downloads ~90MB)")
    print("This will take a couple of minutes.\n")

    judge_llm = llm_factory("claude-haiku-4-5-20251001", provider="anthropic", client=Anthropic(api_key=ANTHROPIC_KEY))
    # Anthropic's API rejects requests that set both temperature and top_p, but
    # ragas's InstructorModelArgs defaults both. Drop top_p to keep temperature only.
    judge_llm.model_args.pop("top_p", None)
    local_embeddings = LangchainEmbeddingsWrapper(
        LCHuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    )

    result = evaluate(ragas_dataset, metrics=metrics, llm=judge_llm, embeddings=local_embeddings)
    result_df = result.to_pandas()

    # Add RAGAS score columns to original rows
    for col in result_df.columns:
        if col not in ("user_input", "response", "retrieved_contexts", "reference"):
            canonical = METRIC_COL_NAMES.get(col, f"ragas_{col}")
            for df_idx, row_idx in enumerate(original_indices):
                val = result_df.at[df_idx, col]
                rows[row_idx][canonical] = round(float(val), 4) if val is not None else ""

    # Ensure all rows have the RAGAS columns (unscorable rows get blank)
    scored_indices = set(original_indices)
    ragas_new_cols = [c for c in rows[original_indices[0]].keys() if c.startswith("ragas_")]
    for i, row in enumerate(rows):
        if i not in scored_indices:
            for col in ragas_new_cols:
                row.setdefault(col, "n/a")

    # Write output CSV
    new_fieldnames = list(base_fieldnames) + [c for c in ragas_new_cols if c not in base_fieldnames]
    with open(OUTPUT_SCORES, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Per-row RAGAS scores saved to {OUTPUT_SCORES}")
    write_summary(rows, scored_indices)


if __name__ == "__main__":
    main()
