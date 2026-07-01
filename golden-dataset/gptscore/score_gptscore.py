"""
Score evaluation results with GPTScore (LLM-as-Judge, using Claude).

What this script does:
  - Reads a completed run CSV (produced by run_evaluation.py) — read-only,
    this script never modifies golden-dataset/runs/run-001.csv.
  - Calls Claude as a judge to score Faithfulness and Relevance for every row
    (in-scope rows are judged on grounding/correctness; out-of-scope/adversarial
    rows are judged on whether the system correctly declined to answer).
  - Writes its own scored CSV and summary into golden-dataset/gptscore/results/.

Prerequisites:
    python3.11 -m pip install anthropic

Setup:
    Add ANTHROPIC_API_KEY=sk-ant-... to your .env file (repo root).

Usage:
    python3.11 golden-dataset/gptscore/score_gptscore.py                    # scores runs/run-001.csv
    python3.11 golden-dataset/gptscore/score_gptscore.py runs/run-002.csv   # scores a different file

Output:
    golden-dataset/gptscore/results/run-001-scores.csv
    golden-dataset/gptscore/results/summary.md

How the metric works:
    GPTScore — Claude rates faithfulness (1-5) and relevance (1-5).
               Catches hallucinations and correct paraphrases that BLEU/ROUGE miss.
               Blind spot: costs money, slightly non-deterministic, prompt-sensitive.
"""

import csv
import json
import os
import sys
import time

# --------------------------------------------------------------------------
# Paths — run from the repo root: python3.11 golden-dataset/gptscore/score_gptscore.py
# --------------------------------------------------------------------------
args = sys.argv[1:]
INPUT_FILE = args[0] if args else "golden-dataset/runs/run-001.csv"
OUTPUT_DIR = "golden-dataset/gptscore/results"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "run-001-scores.csv")
OUTPUT_SUMMARY = os.path.join(OUTPUT_DIR, "summary.md")

# --------------------------------------------------------------------------
# Load .env from the repo root (this script lives two levels down, in golden-dataset/gptscore/)
# --------------------------------------------------------------------------
def load_dotenv(path=".env"):
    here = os.path.dirname(os.path.abspath(globals().get("__file__", "")))
    repo_root = os.path.dirname(os.path.dirname(here))
    repo_root_env = os.path.join(repo_root, path)
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

try:
    import anthropic
except ImportError:
    sys.exit("Missing: anthropic\nRun: pip install anthropic")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_KEY or "your-key" in ANTHROPIC_KEY:
    sys.exit(
        "ANTHROPIC_API_KEY not set.\n"
        "Add ANTHROPIC_API_KEY=sk-ant-... to your .env file and re-run."
    )

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

Faithfulness (1-5): Does the answer contain ONLY information supported by the retrieved context?
  5 = every claim in the answer is directly grounded in the retrieved context
  4 = nearly all claims are grounded; one minor detail is vague
  3 = mostly grounded, but one fact appears to come from outside the context
  2 = several claims lack support in the context
  1 = answer contains significant fabricated content not in the context

Relevance (1-5): Does the answer actually address the question that was asked?
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

Faithfulness (1-5): Did the system correctly limit itself to what the document says?
  5 = system clearly stated the topic is not covered in the handbook
  4 = system acknowledged the limitation but was slightly vague
  3 = system hedged without clearly declining
  2 = system partially fabricated an answer while noting uncertainty
  1 = system gave a confident, fabricated answer as if it were fact (critical failure)

Relevance (1-5): Did the system acknowledge the question while explaining the limitation?
  5 = acknowledged the question and clearly explained the scope limitation
  3 = gave a generic "I don't know" without acknowledging the question
  1 = ignored the question entirely or answered a different question

Reply with JSON only:
{{"faithfulness": <integer 1-5>, "relevance": <integer 1-5>, "notes": "<one sentence: did it refuse correctly or hallucinate?>"}}"""


def gpt_score(row: dict, client) -> tuple:
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
        prompt = OUT_OF_SCOPE_PROMPT.format(question=question, actual_answer=actual_answer)
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


def write_summary(rows: list) -> None:
    in_scope = [r for r in rows if r.get("query_type", "").lower() in IN_SCOPE_TYPES]
    out_scope = [r for r in rows if r.get("query_type", "").lower() in OUT_OF_SCOPE_TYPES]

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

    faith_avg = gpt_avg(in_scope, 0)
    relev_avg = gpt_avg(in_scope, 1)

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
        "# GPTScore (Claude as Judge) Scores\n",
        f"Input file: {INPUT_FILE}\n",
        f"Total rows: {len(rows)} ({len(in_scope)} in-scope, {len(out_scope)} out-of-scope/adversarial)\n",
        "\n## Averages (in-scope rows)\n",
        f"GPTScore Faithfulness:   {faith_avg if faith_avg is not None else 'n/a'} / 5",
        f"GPTScore Relevance:      {relev_avg if relev_avg is not None else 'n/a'} / 5",
        "\n## Hallucination Rate (out-of-scope + fictitious-entity + adversarial rows)\n",
        f"Rows where system hallucinated (GPTScore faithfulness <= 2): {hall_rate}",
        "\n## Per-row GPTScore breakdown\n",
        f"{'#':<4} {'Type':<20} {'GPT Score':<12} Notes",
        "-" * 80,
    ]
    for i, r in enumerate(rows, 1):
        qt = r.get("query_type", "")
        score = r.get("gpt_score", "")
        notes = r.get("gpt_notes", "")
        lines.append(f"{i:<4} {qt:<20} {score:<12} {notes[:60]}")

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

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    print(f"Running GPTScore (Claude as judge) on {total} rows...")

    out_rows = []
    for i, row in enumerate(rows, 1):
        q_short = row.get("question", "")[:60]
        print(f"  [{i:02d}/{total}] {row.get('query_type', ''):18s} {q_short}")
        score, notes = gpt_score(row, client)
        print(f"           -> {score}  {notes[:70]}")

        out_row = {
            "question": row.get("question", ""),
            "query_type": row.get("query_type", ""),
            "actual_answer": row.get("actual_answer", ""),
            "gpt_score": score,
            "gpt_notes": notes,
        }
        out_rows.append(out_row)

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["question", "query_type", "actual_answer", "gpt_score", "gpt_notes"])
            writer.writeheader()
            writer.writerows(out_rows)

        if i < total:
            time.sleep(0.5)

    print(f"\nScores saved to {OUTPUT_CSV}")
    write_summary(out_rows)


if __name__ == "__main__":
    main()
