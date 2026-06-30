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

Prerequisites:
  python3.11 -m pip install "ragas<0.2" datasets openai langchain-openai

  Requires OPENAI_API_KEY in your .env file (RAGAS uses OpenAI internally for
  its LLM judge calls). The same key you use for Dify works here.

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
  RAGAS makes one or more LLM calls per sample per metric. With 21 rows and
  four metrics you will spend roughly $0.02–$0.05 on gpt-4o-mini. Context
  Precision and Context Recall also require a reference answer — out-of-scope
  and fictitious-entity rows are skipped for those two metrics.
"""

import csv
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
# Dependency check
# --------------------------------------------------------------------------
try:
    from datasets import Dataset
except ImportError:
    sys.exit("Missing: pip install datasets")

try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
except ImportError:
    sys.exit('Missing: pip install "ragas<0.2"')

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_KEY or "your-key" in OPENAI_KEY:
    sys.exit(
        "OPENAI_API_KEY not set.\n"
        "RAGAS uses OpenAI internally for its LLM judge calls.\n"
        "Add OPENAI_API_KEY=sk-... to your .env file and re-run."
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
    a list of strings that RAGAS expects for 'contexts'.
    """
    if not pipe_separated:
        return []
    return [c.strip() for c in pipe_separated.split("|") if c.strip()]


# --------------------------------------------------------------------------
# Build RAGAS dataset
# --------------------------------------------------------------------------
def build_ragas_dataset(rows: list) -> tuple[Dataset, list[int]]:
    """
    Convert golden-dataset run rows into a HuggingFace Dataset for RAGAS.

    Returns (dataset, original_indices) so results can be mapped back to rows.
    Only includes in-scope rows that have both an actual_answer and retrieved chunks.
    """
    questions, answers, contexts, ground_truths, original_indices = [], [], [], [], []

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

        questions.append(row["question"])
        answers.append(actual)
        contexts.append(chunks)
        ground_truths.append(reference)
        original_indices.append(i)

    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

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
                vals.append(float(v))
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
                    vals.append(float(r.get(col, "")))
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
    print("This will make several OpenAI API calls — allow 30–90 seconds.\n")

    result = evaluate(ragas_dataset, metrics=metrics)
    result_df = result.to_pandas()

    # Add RAGAS score columns to original rows
    ragas_cols = [c for c in result_df.columns if c in METRIC_COL_NAMES or c in metric_names]
    for col in result_df.columns:
        if col not in ("question", "answer", "contexts", "ground_truth"):
            canonical = METRIC_COL_NAMES.get(col, f"ragas_{col}")
            for df_idx, row_idx in enumerate(original_indices):
                rows[row_idx][canonical] = round(float(result_df.at[df_idx, col]), 4) if result_df.at[df_idx, col] is not None else ""

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
