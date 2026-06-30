"""
Score evaluation results with BLEU, ROUGE-L, and GPTScore (LLM-as-Judge).

What this script does:
  - Reads a completed run CSV (produced by run_evaluation.py)
  - Computes BLEU and ROUGE-L for in-scope rows (factual, paraphrase, multi-hop)
  - Calls Claude as a judge to score Faithfulness and Relevance (GPTScore)
  - Writes the scores back into the CSV and prints a summary

Prerequisites:
    python3.11 -m pip install rouge-score nltk anthropic

    NLTK downloads a small tokeniser on first run (~3 MB). This is automatic.
    Run the script with the same Python you pip-installed into (python3.11 on this machine).

Setup:
    Add ANTHROPIC_API_KEY=sk-ant-... to your .env file.
    (Only needed if you want GPTScore. Use --no-gpt to skip it.)

Usage:
    python scripts/score_results.py                        # scores results/run-001.csv
    python scripts/score_results.py results/run-002.csv   # scores a different file
    python scripts/score_results.py --no-gpt              # BLEU + ROUGE only
    python scripts/score_results.py --gpt-only            # GPTScore only (re-score existing)

Output:
    The input CSV is updated in place.
    A summary is printed at the end and saved to results/scores.md.

How the metrics work:
    BLEU      — n-gram precision: fraction of word sequences in the actual answer
                that also appear in the reference. Fast, free, purely lexical.
                Blind spot: paraphrases score low even when semantically correct.

    ROUGE-L   — longest common subsequence F1: more flexible than BLEU on word order
                and gives partial credit for covering the right topics.
                Blind spot: still lexical — synonyms score zero.

    GPTScore  — Claude rates faithfulness (1–5) and relevance (1–5).
                Catches hallucinations and correct paraphrases that BLEU misses.
                Blind spot: costs money, slightly non-deterministic.
"""

import csv
import json
import os
import sys
import time

# --------------------------------------------------------------------------
# Dependency check — give a helpful error rather than a cryptic ImportError
# --------------------------------------------------------------------------
MISSING = []
try:
    import nltk
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
except ImportError:
    MISSING.append("nltk")

try:
    from rouge_score import rouge_scorer as rouge_lib
except ImportError:
    MISSING.append("rouge-score")

if MISSING:
    sys.exit(
        f"Missing packages: {', '.join(MISSING)}\n"
        "Run:  pip install rouge-score nltk anthropic"
    )

# Download NLTK tokeniser data silently on first run
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)


# --------------------------------------------------------------------------
# Argument parsing (keeping it simple — no argparse dependency)
# --------------------------------------------------------------------------
args = sys.argv[1:]
NO_GPT = "--no-gpt" in args
GPT_ONLY = "--gpt-only" in args
INPUT_FILE = next((a for a in args if not a.startswith("--")), "golden-dataset/runs/run-001.csv")

# --------------------------------------------------------------------------
# Load .env (same minimal loader as run_evaluation.py)
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
# BLEU
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# ROUGE-L
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# GPTScore — Claude as judge
# --------------------------------------------------------------------------
IN_SCOPE_TYPES = {"factual", "paraphrase", "multi-hop", "comparative"}
OUT_OF_SCOPE_TYPES = {"out-of-scope", "fictitious-entity", "adversarial"}

IN_SCOPE_PROMPT = """\
You are a quality evaluator for a RAG (Retrieval-Augmented Generation) HR chatbot.

Question asked: {question}

Context retrieved by the system:
{retrieved_chunks}

System answer:
{actual_answer}

Reference answer (what the ideal answer should say):
{reference_answer}

Rate the system answer on two dimensions:

Faithfulness (1–5): Does the answer contain ONLY information supported by the retrieved context?
  5 = every claim in the answer is directly grounded in the retrieved context
  4 = nearly all claims are grounded; one minor detail is vague
  3 = mostly grounded, but one fact appears to come from outside the context
  2 = several claims lack support in the context
  1 = answer contains significant fabricated content not in the context

Relevance (1–5): Does the answer actually address the question that was asked?
  5 = directly and completely answers the question
  4 = answers the question but omits a minor detail the reference includes
  3 = partially answers the question — misses something materially important
  2 = addresses a related but different question
  1 = does not address the question at all

Reply with JSON only, no explanation outside the JSON:
{{"faithfulness": <integer 1-5>, "relevance": <integer 1-5>, "notes": "<one sentence: what is right or wrong about this answer>"}}"""

OUT_OF_SCOPE_PROMPT = """\
You are evaluating an HR RAG chatbot on how it handles questions outside its knowledge base.

Question asked: {question}

System answer:
{actual_answer}

This question is intentionally out of scope — it asks about something not covered by the handbook. The correct behaviour is for the system to clearly say it cannot find the answer in the available documents.

Rate refusal quality on two dimensions:

Faithfulness (1–5): Did the system correctly limit itself to what the document says?
  5 = system clearly stated the topic is not covered in the handbook
  4 = system acknowledged the limitation but was slightly vague
  3 = system hedged without clearly declining
  2 = system partially fabricated an answer while noting uncertainty
  1 = system gave a confident, fabricated answer as if it were fact (critical failure)

Relevance (1–5): Did the system acknowledge the question while explaining the limitation?
  5 = acknowledged the question and clearly explained the scope limitation
  3 = gave a generic "I don't know" without acknowledging the question
  1 = ignored the question entirely or answered a different question

Reply with JSON only:
{{"faithfulness": <integer 1-5>, "relevance": <integer 1-5>, "notes": "<one sentence: did it refuse correctly or hallucinate?>"}}"""


def gpt_score(row: dict, client) -> tuple[str, str]:
    """
    Call Claude to score one row. Returns (score_string, notes).
    score_string is formatted as "F:{f}/R:{r}" e.g. "F:4/R:5".
    """
    query_type = row.get("query_type", "").strip().lower()
    question = row.get("question", "")
    actual_answer = row.get("actual_answer", "")

    if not actual_answer:
        return "", "No actual answer to evaluate"

    if query_type in OUT_OF_SCOPE_TYPES:
        prompt = OUT_OF_SCOPE_PROMPT.format(
            question=question,
            actual_answer=actual_answer,
        )
    else:
        retrieved = row.get("retrieved_chunks", "") or "(not available)"
        reference = row.get("reference_answer", "")
        prompt = IN_SCOPE_PROMPT.format(
            question=question,
            retrieved_chunks=retrieved,
            actual_answer=actual_answer,
            reference_answer=reference,
        )

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()

        # Strip markdown code fences if the model wraps in them
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        data = json.loads(text)
        f = data.get("faithfulness", "?")
        r = data.get("relevance", "?")
        notes = data.get("notes", "")
        return f"F:{f}/R:{r}", notes

    except json.JSONDecodeError as e:
        return "error", f"JSON parse failed: {e} | raw: {text[:120]}"
    except Exception as e:
        return "error", str(e)


# --------------------------------------------------------------------------
# Scoring logic — decides which rows get which metrics
# --------------------------------------------------------------------------
def should_score_lexical(row: dict) -> bool:
    """BLEU and ROUGE only make sense for in-scope rows with a reference answer."""
    qt = row.get("query_type", "").strip().lower()
    return qt in IN_SCOPE_TYPES and bool(row.get("reference_answer")) and bool(row.get("actual_answer"))


# --------------------------------------------------------------------------
# Summary report
# --------------------------------------------------------------------------
def print_and_save_summary(rows: list, output_file: str) -> None:
    in_scope = [r for r in rows if r.get("query_type", "").lower() in IN_SCOPE_TYPES]
    out_scope = [r for r in rows if r.get("query_type", "").lower() in OUT_OF_SCOPE_TYPES]

    def avg(values):
        vals = [float(v) for v in values if v not in ("", "error", None)]
        return round(sum(vals) / len(vals), 3) if vals else None

    def gpt_avg(rows_subset, component):
        """component: 0=faithfulness, 1=relevance"""
        scores = []
        for r in rows_subset:
            s = r.get("gpt_score", "")
            if s and s != "error" and "/" in s:
                try:
                    parts = s.split("/")
                    scores.append(float(parts[component].split(":")[1]))
                except (IndexError, ValueError):
                    pass
        return round(sum(scores) / len(scores), 2) if scores else None

    bleu_avg = avg(r.get("bleu_score") for r in in_scope)
    rouge_avg = avg(r.get("rouge_score") for r in in_scope)
    faith_avg = gpt_avg(in_scope, 0)
    relev_avg = gpt_avg(in_scope, 1)

    # Hallucination rate: out-of-scope rows where faithfulness ≤ 2
    hall_rows = []
    for r in out_scope:
        s = r.get("gpt_score", "")
        if s and s != "error" and "/" in s:
            try:
                f = int(s.split("/")[0].split(":")[1])
                if f <= 2:
                    hall_rows.append(r)
            except (IndexError, ValueError):
                pass
    hall_rate = f"{len(hall_rows)}/{len(out_scope)}" if out_scope else "n/a"

    lines = [
        "# Evaluation Scores\n",
        f"Input file: {output_file}\n",
        f"Total rows: {len(rows)} ({len(in_scope)} in-scope, {len(out_scope)} out-of-scope/adversarial)\n",
        "\n## Generation Scores (in-scope rows)\n",
        f"Average BLEU:            {bleu_avg if bleu_avg is not None else 'n/a'}",
        f"Average ROUGE-L:         {rouge_avg if rouge_avg is not None else 'n/a'}",
        f"GPTScore Faithfulness:   {faith_avg if faith_avg is not None else 'n/a'} / 5",
        f"GPTScore Relevance:      {relev_avg if relev_avg is not None else 'n/a'} / 5",
        "\n## Hallucination Rate (out-of-scope + fictitious-entity + adversarial rows)\n",
        f"Rows where system hallucinated (GPTScore faithfulness ≤ 2): {hall_rate}",
        "\n## Per-row GPTScore breakdown\n",
        f"{'#':<4} {'Type':<20} {'GPT Score':<12} Notes",
        "-" * 80,
    ]

    for i, r in enumerate(rows, 1):
        qt = r.get("query_type", "")
        score = r.get("gpt_score", "")
        notes = r.get("gpt_notes", "")
        q = r.get("question", "")[:50]
        lines.append(f"{i:<4} {qt:<20} {score:<12} {notes[:60]}")

    summary = "\n".join(lines)
    print("\n" + summary)

    scores_path = os.path.join(os.path.dirname(output_file), "scores.md")
    with open(scores_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"\nSummary saved to {scores_path}")


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
        fieldnames = reader.fieldnames

    total = len(rows)
    print(f"Loaded {total} rows from {INPUT_FILE}")

    # --- BLEU + ROUGE-L ---
    if not GPT_ONLY:
        print("\nComputing BLEU and ROUGE-L...")
        for i, row in enumerate(rows, 1):
            if should_score_lexical(row):
                row["bleu_score"] = bleu(row["reference_answer"], row["actual_answer"])
                row["rouge_score"] = rouge_l(row["reference_answer"], row["actual_answer"])
                print(f"  [{i:02d}/{total}] BLEU={row['bleu_score']:.3f}  ROUGE-L={row['rouge_score']:.3f}  {row['question'][:60]}")
            else:
                # Out-of-scope rows: lexical metrics don't apply
                row.setdefault("bleu_score", "n/a")
                row.setdefault("rouge_score", "n/a")

        # Save after BLEU/ROUGE so progress is not lost if GPT errors
        with open(INPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print("BLEU and ROUGE-L scores saved.")

    # --- GPTScore ---
    if not NO_GPT:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key or "your-key" in api_key:
            print(
                "\nSkipping GPTScore: ANTHROPIC_API_KEY not set.\n"
                "Add it to your .env file and re-run without --no-gpt."
            )
        else:
            try:
                import anthropic
            except ImportError:
                sys.exit("anthropic package not installed. Run: pip install anthropic")

            client = anthropic.Anthropic(api_key=api_key)
            print(f"\nRunning GPTScore (Claude as judge) on {total} rows...")

            for i, row in enumerate(rows, 1):
                q_short = row.get("question", "")[:60]
                print(f"  [{i:02d}/{total}] {row.get('query_type', ''):18s} {q_short}")
                score, notes = gpt_score(row, client)
                row["gpt_score"] = score
                row["gpt_notes"] = notes
                print(f"           → {score}  {notes[:70]}")

                # Save incrementally after each row
                with open(INPUT_FILE, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

                # Gentle pacing to stay within API rate limits
                if i < total:
                    time.sleep(0.5)

    print_and_save_summary(rows, INPUT_FILE)


if __name__ == "__main__":
    main()
