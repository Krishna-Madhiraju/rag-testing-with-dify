"""
Score evaluation results with BLEU and ROUGE-L (lexical n-gram metrics).

What this script does:
  - Reads a completed run CSV (produced by run_evaluation.py) — read-only,
    this script never modifies golden-dataset/runs/run-001.csv.
  - Computes BLEU and ROUGE-L for in-scope rows (factual, paraphrase, multi-hop,
    comparative). Out-of-scope/adversarial rows have no reference answer to
    compare against, so lexical metrics don't apply to them.
  - Writes its own scored CSV and summary into golden-dataset/bleu-rouge/results/.

Prerequisites:
    python3.11 -m pip install rouge-score nltk

    NLTK downloads a small tokeniser on first run (~3 MB). This is automatic.

Usage:
    python3.11 golden-dataset/bleu-rouge/score_bleu_rouge.py                    # scores runs/run-001.csv
    python3.11 golden-dataset/bleu-rouge/score_bleu_rouge.py runs/run-002.csv   # scores a different file

Output:
    golden-dataset/bleu-rouge/results/run-001-scores.csv
    golden-dataset/bleu-rouge/results/summary.md

How the metrics work:
    BLEU      — n-gram precision: fraction of word sequences in the actual answer
                that also appear in the reference. Fast, free, purely lexical.
                Blind spot: paraphrases score low even when semantically correct.

    ROUGE-L   — longest common subsequence F1: more flexible than BLEU on word order
                and gives partial credit for covering the right topics.
                Blind spot: still lexical — synonyms score zero.
"""

import csv
import os
import sys

try:
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
except ImportError:
    sys.exit("Missing: nltk\nRun: pip install nltk")

try:
    from rouge_score import rouge_scorer as rouge_lib
except ImportError:
    sys.exit("Missing: rouge-score\nRun: pip install rouge-score")

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)

# --------------------------------------------------------------------------
# Paths — run from the repo root: python3.11 golden-dataset/bleu-rouge/score_bleu_rouge.py
# --------------------------------------------------------------------------
args = sys.argv[1:]
INPUT_FILE = args[0] if args else "golden-dataset/runs/run-001.csv"
OUTPUT_DIR = "golden-dataset/bleu-rouge/results"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "run-001-scores.csv")
OUTPUT_SUMMARY = os.path.join(OUTPUT_DIR, "summary.md")

IN_SCOPE_TYPES = {"factual", "paraphrase", "multi-hop", "comparative"}
OUT_OF_SCOPE_TYPES = {"out-of-scope", "fictitious-entity", "adversarial"}


def bleu(reference: str, candidate: str) -> float:
    """Sentence-level BLEU with add-1 smoothing (handles short sentences)."""
    if not reference or not candidate:
        return 0.0
    ref_tokens = nltk.word_tokenize(reference.lower())
    cand_tokens = nltk.word_tokenize(candidate.lower())
    smoother = SmoothingFunction().method1
    try:
        return round(sentence_bleu([ref_tokens], cand_tokens, smoothing_function=smoother), 4)
    except Exception:
        return 0.0


_rouge = rouge_lib.RougeScorer(["rougeL"], use_stemmer=True)


def rouge_l(reference: str, candidate: str) -> float:
    """ROUGE-L F1 score (longest common subsequence)."""
    if not reference or not candidate:
        return 0.0
    try:
        scores = _rouge.score(reference, candidate)
        return round(scores["rougeL"].fmeasure, 4)
    except Exception:
        return 0.0


def should_score(row: dict) -> bool:
    """BLEU and ROUGE only make sense for in-scope rows with a reference answer."""
    qt = row.get("query_type", "").strip().lower()
    return qt in IN_SCOPE_TYPES and bool(row.get("reference_answer")) and bool(row.get("actual_answer"))


def write_summary(rows: list) -> None:
    in_scope = [r for r in rows if r.get("query_type", "").lower() in IN_SCOPE_TYPES]

    def avg(values):
        vals = [float(v) for v in values if v not in ("", "n/a", None)]
        return round(sum(vals) / len(vals), 3) if vals else None

    bleu_avg = avg(r.get("bleu_score") for r in in_scope)
    rouge_avg = avg(r.get("rouge_score") for r in in_scope)

    lines = [
        "# BLEU / ROUGE-L Scores\n",
        f"Input file: {INPUT_FILE}\n",
        f"Total rows: {len(rows)} ({len(in_scope)} in-scope, "
        f"{len(rows) - len(in_scope)} out-of-scope/adversarial — lexical metrics skipped)\n",
        "\n## Averages (in-scope rows)\n",
        f"Average BLEU:      {bleu_avg if bleu_avg is not None else 'n/a'}",
        f"Average ROUGE-L:   {rouge_avg if rouge_avg is not None else 'n/a'}",
        "\n## Per-row scores\n",
        f"{'#':<4} {'Type':<14} {'BLEU':<8} {'ROUGE-L':<8} Question",
        "-" * 90,
    ]
    for i, r in enumerate(rows, 1):
        qt = r.get("query_type", "")
        b = r.get("bleu_score", "")
        rg = r.get("rouge_score", "")
        q = r.get("question", "")[:50]
        lines.append(f"{i:<4} {qt:<14} {str(b):<8} {str(rg):<8} {q}")

    summary = "\n".join(lines)
    print("\n" + summary)
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"\nSummary saved to {OUTPUT_SUMMARY}")


def main():
    if not os.path.exists(INPUT_FILE):
        sys.exit(f"File not found: {INPUT_FILE}\nRun run_evaluation.py first to generate results.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    print(f"Loaded {total} rows from {INPUT_FILE}")
    print("Computing BLEU and ROUGE-L...")

    out_rows = []
    for i, row in enumerate(rows, 1):
        out_row = {
            "question": row.get("question", ""),
            "query_type": row.get("query_type", ""),
            "reference_answer": row.get("reference_answer", ""),
            "actual_answer": row.get("actual_answer", ""),
        }
        if should_score(row):
            out_row["bleu_score"] = bleu(row["reference_answer"], row["actual_answer"])
            out_row["rouge_score"] = rouge_l(row["reference_answer"], row["actual_answer"])
            print(f"  [{i:02d}/{total}] BLEU={out_row['bleu_score']:.3f}  ROUGE-L={out_row['rouge_score']:.3f}  {row['question'][:60]}")
        else:
            out_row["bleu_score"] = "n/a"
            out_row["rouge_score"] = "n/a"
        out_rows.append(out_row)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["question", "query_type", "reference_answer", "actual_answer", "bleu_score", "rouge_score"])
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"\nScores saved to {OUTPUT_CSV}")

    write_summary(out_rows)


if __name__ == "__main__":
    main()
