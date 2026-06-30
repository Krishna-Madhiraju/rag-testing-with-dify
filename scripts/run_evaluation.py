"""
Run all golden dataset questions through the Orion HR Assistant and capture results.

Setup (one time):
    cp .env.example .env            # then put your real key in .env (it is gitignored)
    # .env contains:  DIFY_API_KEY=app-...   (App → API Access → API Key in the Dify UI)

Usage:
    python scripts/run_evaluation.py
    # or, without a .env file:  DIFY_API_KEY=app-... python scripts/run_evaluation.py

Rate limits (Google Gemini free tier, etc.):
    The underlying LLM/embedding provider caps requests per minute (RPM). To stay
    under it, this script paces requests and runs the dataset in batches with a
    pause between each batch. Tune via environment variables (or edit the defaults):

        REQUEST_DELAY   seconds to wait between questions          (default 4)
        BATCH_SIZE      questions per batch before a long pause     (default 10)
        BATCH_PAUSE     seconds to pause between batches            (default 60)

    Example — slower pacing for a tight free-tier limit:
        REQUEST_DELAY=6 BATCH_SIZE=8 BATCH_PAUSE=70 python scripts/run_evaluation.py

Output:
    results/run-001.csv  — one row per question, actual answers + retrieved chunks
    captured. Written incrementally after every question, so a rate-limit crash
    mid-run does not lose completed work.

What this script does NOT do:
    - Calculate BLEU/ROUGE scores (Step 3)
    - Run GPTScore (Step 4)
    Those steps happen after you have the raw results.
"""

import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error

def load_dotenv(path=".env"):
    """Minimal .env loader (no external dependency).

    Reads KEY=value lines from a .env file in the working directory (or the repo
    root) into os.environ. A real environment variable always wins, so you can
    still override with `DIFY_API_KEY=... python scripts/run_evaluation.py`.
    """
    # Look in the current dir first, then the repo root (parent of scripts/).
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

# Read the API key from the environment — never hard-code secrets in the script.
API_KEY = os.environ.get("DIFY_API_KEY", "")
API_URL = "http://localhost/v1/chat-messages"
GOLDEN_DATASET = "results/golden-dataset.csv"
OUTPUT_FILE = "results/run-001.csv"

# --- Rate-limit pacing (override via environment variables) ----------------
# The LLM/embedding provider behind Dify (e.g. Google Gemini free tier) caps
# requests per minute. These three knobs keep us under that cap.
REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "4"))   # seconds between questions
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))          # questions per batch
BATCH_PAUSE = float(os.environ.get("BATCH_PAUSE", "60"))      # seconds to pause between batches

# Columns carried forward from the golden dataset
GOLDEN_COLS = ["question", "reference_answer", "expected_chunk", "source_doc", "query_type", "difficulty", "notes"]

# Columns you fill in from the API response
RESULT_COLS = ["actual_answer", "retrieved_chunks", "chunk_found", "chunk_rank",
               "retrieval_score_rank1", "bleu_score", "rouge_score",
               "gpt_score", "gpt_notes", "flags"]


def query_assistant(question: str, max_retries: int = 5) -> dict:
    payload = json.dumps({
        "query": question,
        "inputs": {},
        "response_mode": "blocking",
        "user": "eval-user",
        "conversation_id": ""
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST"
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")

            # On rate limit (429 inside a 400), extract the retry delay and wait
            if e.code == 400 and "429" in error_body and "retryDelay" in error_body:
                # Error message contains e.g. 'retryDelay': '59s' — extract the seconds
                import re
                match = re.search(r"retryDelay.*?(\d+)s", error_body)
                wait = int(match.group(1)) + 5 if match else 65
                print(f"  Rate limited. Waiting {wait}s before retry (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue  # retry the same question

            # Any other HTTP error — re-raise so the caller logs it
            raise

    raise Exception(f"Failed after {max_retries} retries (rate limit not resolved)")


def extract_chunks(retriever_resources: list) -> tuple[str, float]:
    """Return pipe-separated chunk texts and the top-1 similarity score."""
    if not retriever_resources:
        return "", 0.0
    texts = [r.get("content", "").replace("\n", " ").strip() for r in retriever_resources]
    top_score = retriever_resources[0].get("score", 0.0)
    return " | ".join(texts), top_score


def check_chunk_match(expected: str, retrieved_chunks: list) -> tuple[str, str]:
    """
    Compare expected_chunk against each retrieved chunk.
    Returns (chunk_found, chunk_rank).

    Match logic: checks if a meaningful portion of the expected chunk text
    appears in any retrieved chunk. Uses a sliding-window word overlap —
    if 60% of the expected chunk's words appear in the retrieved chunk, it's a hit.
    """
    if not expected or not retrieved_chunks:
        return "no", ""

    expected_words = set(expected.lower().split())
    if not expected_words:
        return "no", ""

    for resource in retrieved_chunks:
        content = resource.get("content", "").lower()
        content_words = set(content.split())
        overlap = len(expected_words & content_words) / len(expected_words)
        if overlap >= 0.60:
            return "yes", str(resource.get("position", ""))

    return "no", ""


def write_results(results: list) -> None:
    """Write all collected results to OUTPUT_FILE (called after every question)."""
    fieldnames = GOLDEN_COLS + RESULT_COLS
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def evaluate_row(row: dict) -> dict:
    """Query the assistant for one golden-dataset row and return a result dict."""
    question = row["question"]
    expected_chunk = row.get("expected_chunk", "")
    query_type = row.get("query_type", "")

    try:
        response = query_assistant(question)
        actual_answer = response.get("answer", "")
        resources = response.get("metadata", {}).get("retriever_resources", [])

        retrieved_text, top_score = extract_chunks(resources)

        # Out-of-scope, fictitious-entity, adversarial rows have no expected chunk —
        # mark retrieval fields as n/a so they are not counted in Recall@K
        if query_type in ("out-of-scope", "fictitious-entity", "adversarial"):
            chunk_found = "n/a"
            chunk_rank = "n/a"
        else:
            chunk_found, chunk_rank = check_chunk_match(expected_chunk, resources)

        result = {col: row[col] for col in GOLDEN_COLS}
        result["actual_answer"] = actual_answer
        result["retrieved_chunks"] = retrieved_text
        result["chunk_found"] = chunk_found
        result["chunk_rank"] = chunk_rank
        result["retrieval_score_rank1"] = round(top_score, 4)
        result["bleu_score"] = ""
        result["rouge_score"] = ""
        result["gpt_score"] = ""
        result["gpt_notes"] = ""
        result["flags"] = ""
        return result

    except urllib.error.HTTPError as e:
        print(f"  ERROR HTTP {e.code}: {e.read().decode()}")
        result = {col: row[col] for col in GOLDEN_COLS}
        for col in RESULT_COLS:
            result[col] = ""
        result["flags"] = f"API_ERROR_{e.code}"
        return result

    except Exception as e:
        print(f"  ERROR: {e}")
        result = {col: row[col] for col in GOLDEN_COLS}
        for col in RESULT_COLS:
            result[col] = ""
        result["flags"] = f"ERROR: {e}"
        return result


def main():
    if not API_KEY:
        sys.exit("Error: set the DIFY_API_KEY environment variable before running "
                 "(export DIFY_API_KEY=\"app-...\").")

    print(f"Reading golden dataset from {GOLDEN_DATASET}")
    with open(GOLDEN_DATASET, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    n_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Loaded {total} rows. Running in {n_batches} batch(es) of up to "
          f"{BATCH_SIZE}, with {REQUEST_DELAY}s between questions and "
          f"{BATCH_PAUSE}s between batches.\n")

    results = []
    for i, row in enumerate(rows, start=1):
        query_type = row.get("query_type", "")
        batch_no = (i - 1) // BATCH_SIZE + 1
        print(f"[{i:02d}/{total}] (batch {batch_no}/{n_batches}) "
              f"{query_type:20s}  {row['question'][:70]}")

        results.append(evaluate_row(row))

        # Persist after every question so a rate-limit crash keeps completed work
        write_results(results)

        if i == total:
            break

        # Pause between batches; otherwise just pace individual requests
        if i % BATCH_SIZE == 0:
            print(f"  --- Batch {batch_no}/{n_batches} done. "
                  f"Pausing {BATCH_PAUSE}s to respect the rate limit ---")
            time.sleep(BATCH_PAUSE)
        else:
            time.sleep(REQUEST_DELAY)

    print(f"\nResults written to {OUTPUT_FILE}")

    # Quick summary
    scoreable = [r for r in results if r["chunk_found"] not in ("n/a", "", "no")]
    total_scoreable = [r for r in results if r["chunk_found"] not in ("n/a", "")]
    found = len(scoreable)
    total = len(total_scoreable)
    recall = found / total if total else 0

    print(f"\n--- Quick Retrieval Summary ---")
    print(f"Total rows:          {len(results)}")
    print(f"Rows with expected chunk (scoreable): {total}")
    print(f"Chunks found:        {found}")
    print(f"Recall@5 (rough):    {recall:.2f}")
    print(f"\nDone. Open results/run-001.csv to review.")


if __name__ == "__main__":
    main()
