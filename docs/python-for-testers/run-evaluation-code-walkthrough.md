# Reading `run_evaluation.py` — A Code Walkthrough for Non-Coders

This doc exists for one purpose: to let you read
[`golden-dataset/run_evaluation.py`](../../golden-dataset/run_evaluation.py) and understand *every
line*, even if you've never written Python before. This is the script that sends all 60
golden-dataset questions to the Dify API and produces `golden-dataset/runs/run-001.csv` — the raw
file every scoring tool (BLEU/ROUGE, GPTScore, RAGAS) reads but never writes to.

This doc assumes you've already read
[Reading `score_bleu_rouge.py`](bleu-rouge-code-walkthrough.md), and it will **not** re-explain
syntax covered there: `import` / `try...except`, f-strings, `csv.DictReader`/`DictWriter`,
`dict.get(key, default)`, list comprehensions, `enumerate()`, `if __name__ == "__main__":`, or
`with open(...) as f:`. Where one of those reappears here, you'll see a short
"(covered in the BLEU/ROUGE walkthrough)" note instead of a re-explanation. Everything else —
raw HTTP requests, the rate-limit retry loop, the hand-rolled `.env` loader, set-based word
overlap, tuple returns, incremental writes, and batch pacing — is new, and gets the full
explanation here.

## How to read this doc

Same two-phase idea as before, but this file has one extra wrinkle: a chunk of code runs
**at import time**, before `main()` is ever called.

1. **Definition phase** — Python reads through the `def` blocks and remembers them, without
   running the code inside.
2. **A line that actually executes immediately** — `load_dotenv()` (line 68) is called at module
   level, not inside any function, and not guarded by `if __name__ == "__main__":`. That means it
   runs the instant this file is loaded — whether it's run directly *or* imported by something
   else. Everything that depends on `os.environ` (like `API_KEY` on line 71) runs right after it,
   also at import time.
3. **Execution phase** — at the very bottom, `if __name__ == "__main__": main()` calls `main()`,
   which drives the actual work: read the golden dataset, loop over every row, call the API, write
   results.

So this walkthrough follows **execution order**: imports/config, `load_dotenv()`, then each
function in the order `main()` actually calls it, then `main()` itself last.

---

## 1. Imports and config (lines 37–88)

```python
import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error
```

`csv`, `os`, `sys` are the same standard-library modules from the BLEU/ROUGE script (covered in
the BLEU/ROUGE walkthrough). Three are new:

- **`json`** — converts between Python dicts/lists and JSON text. Dify's API speaks JSON: this
  script builds a JSON *request* body and parses a JSON *response* body.
- **`time`** — here it's used for exactly one thing, `time.sleep(seconds)`, which pauses the
  script for a given number of seconds. That's how the rate-limit pacing (section 8) is built.
- **`urllib.request` / `urllib.error`** — Python's **built-in** HTTP client. Most Python code you
  see online reaches for the third-party `requests` library instead, because its API is friendlier.
  This script deliberately avoids that dependency — see the explanation under `query_assistant()`
  below for why that trade-off makes sense here.

```python
API_KEY = os.environ.get("DIFY_API_KEY", "")
API_URL = "http://localhost/v1/chat-messages"
GOLDEN_DATASET = "golden-dataset/golden-dataset.csv"
OUTPUT_FILE = "golden-dataset/runs/run-001.csv"

REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "4"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))
BATCH_PAUSE = float(os.environ.get("BATCH_PAUSE", "60"))

GOLDEN_COLS = ["question", "reference_answer", "expected_chunk", "source_doc", "query_type", "difficulty", "notes"]
RESULT_COLS = ["actual_answer", "retrieved_chunks", "chunk_found", "chunk_rank",
               "retrieval_score_rank1", "flags"]
```

`os.environ.get(key, default)` — same `.get()`-with-fallback pattern you already know from dicts
(covered in the BLEU/ROUGE walkthrough), except `os.environ` isn't a dict you built — it's a
dict-*like* object Python maintains automatically, populated from your shell's environment
variables (whatever you'd see if you ran `env` in the terminal). `os.environ.get("REQUEST_DELAY",
"4")` reads an environment variable if one was set, otherwise falls back to the string `"4"` —
note it's wrapped in `float(...)` right after, because everything from `os.environ` comes back as
a plain string, even if it looks like a number.

`GOLDEN_COLS` and `RESULT_COLS` are two plain lists of column names. They exist so the rest of the
script never hard-codes column order in more than one place — `GOLDEN_COLS` are the columns
carried straight through from the input dataset unchanged; `RESULT_COLS` are the new columns this
script adds (the answer, the retrieved chunks, whether retrieval succeeded, and so on).

**What this is really doing, testing-wise:** every tunable number that affects how fast this script
hits the API (`REQUEST_DELAY`, `BATCH_SIZE`, `BATCH_PAUSE`) is read from the environment with a
sane default, rather than buried as a magic number inside a function. That means you can tune
pacing for a stricter or looser rate limit (`REQUEST_DELAY=6 BATCH_SIZE=8 BATCH_PAUSE=70 python3.11
golden-dataset/run_evaluation.py`) without touching the code at all — a config-via-environment
pattern you'll see in most real-world scripts that call external APIs.

---

## 2. `load_dotenv()` (lines 45–68)

```python
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
```

**Why a hand-rolled `.env` reader instead of `pip install python-dotenv`?** This script already
avoids one third-party dependency (`requests`, see section 3) in favor of the standard library.
`.env` file parsing is genuinely simple — read lines, split on the first `=`, skip blanks and
comments — so writing ~15 lines here means one less package for a learner to install just to run a
demo script. That's a deliberate "keep the dependency list at zero" choice for this project, not a
universal rule (a bigger production codebase would likely just use `python-dotenv`).

**`os.path.dirname(os.path.abspath(globals().get("__file__", "")))`** — read inside-out:
`globals()` returns a dict of everything defined at module level in this file, and `.get("__file__",
"")` looks up the special variable Python sets to "the path of the file currently running,"
falling back to `""` if it's missing for some reason (e.g. running in certain interactive
consoles). `os.path.abspath(...)` turns that into a full path regardless of what directory you
launched the script from, and `os.path.dirname(...)` chops off the filename, leaving just the
folder the script lives in (`golden-dataset/`).

**`repo_root_env = os.path.join(os.path.dirname(here), path)`** — one more `os.path.dirname` climbs
up one more folder (from `golden-dataset/` to the repo root), then joins that with `path`
(`.env`) — so this builds the path to a `.env` file sitting at the repo root, one level above
`golden-dataset/`.

**`for candidate in (path, repo_root_env):`** — loops over exactly two candidate locations: `.env`
in the current working directory first, then `.env` at the repo root. `if not os.path.exists(candidate):
continue` skips a candidate that doesn't exist. The **`break`** at the very end of the loop body
(indented to align with the `with` block, so it runs once a candidate file is *found and read*)
means: stop after the first `.env` file that actually exists — don't also load a second one and
risk conflicting values.

**`key, _, value = line.partition("=")`** — `str.partition(sep)` splits a string into exactly
three pieces: the part before the separator, the separator itself, and the part after — always
three items, even if the separator doesn't appear (then the last two are empty strings). Unpacking
it into `key, _, value` grabs the first and third pieces and throws away the middle one; the
underscore `_` is a Python convention for "a value I'm required to catch but don't care about."
This is subtly different from `line.split("=")`: if a value itself contains an `=` (unlikely for
an API key, but possible), `split("=")` would break it into more than two pieces, while
`partition("=")` always cuts at only the *first* `=` and leaves the rest of the value intact.

**`os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))`** — this is the one
line in this function worth slowing down on. `os.environ.setdefault(k, v)` is *not* the same as
`os.environ[k] = v`. A normal assignment always overwrites; `setdefault` only sets the value **if
that key isn't already present** — if it's already set, `setdefault` leaves it alone and does
nothing. Since real environment variables (anything already exported in your shell, or passed
inline like `DIFY_API_KEY=app-... python3.11 run_evaluation.py`) are already in `os.environ`
*before* `load_dotenv()` runs, `setdefault` guarantees they win over whatever the `.env` file says.
This is exactly the promise made in the docstring above the function: "a real environment variable
always wins." The `.strip('"').strip("'")` at the end strips a leading/trailing quote character if
the `.env` file wrote `DIFY_API_KEY="app-123"` instead of `DIFY_API_KEY=app-123`, so both styles
work.

> **Try it yourself** — the override behavior, without needing a real `.env` file:
> ```python
> >>> import os
> >>> os.environ["DIFY_API_KEY"] = "from-shell"
> >>> os.environ.setdefault("DIFY_API_KEY", "from-dotenv-file")
> 'from-shell'
> >>> os.environ["DIFY_API_KEY"]
> 'from-shell'
> ```
> `setdefault` returns the value that ends up stored — here, the shell-set value, because the key
> already existed. If you delete the first line (`os.environ["DIFY_API_KEY"] = "from-shell"`) and
> re-run just the `setdefault` call, it *would* store `"from-dotenv-file"`, because the key wasn't
> present yet.

**Why this matters for testing:** because `load_dotenv()` runs at import time (line 68, at module
level, no `if __name__` guard), simply importing this file — say, from a test — has the side
effect of mutating `os.environ`. A test suite that imports `run_evaluation` and also sets its own
`DIFY_API_KEY` for a mock server needs to set it *before* the import happens, not after, or
`setdefault` will silently ignore the test's value.

---

## 3. `query_assistant()` (lines 91–130)

```python
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
```

This is the first raw-HTTP code in this project's scripts, so it's worth walking through what an
HTTP request actually needs, mechanically:

- **`json.dumps({...})`** — converts a Python dict into a JSON-formatted *string*. Dify's API (like
  almost every modern web API) expects the request body to be JSON text, not a Python object —
  `json.dumps` is the translator.
- **`.encode("utf-8")`** — HTTP request bodies are sent as raw *bytes*, not text. `.encode("utf-8")`
  converts the JSON string into the byte representation the network layer actually transmits. You'll
  see the mirror-image operation, `.decode("utf-8")`, when reading the response back into text.
- **`urllib.request.Request(url, data=..., headers=..., method="POST")`** — builds a request
  *object* describing everything to send, without actually sending it yet:
  - `data=payload` — the JSON bytes to POST as the request body.
  - `headers={...}` — a dict of HTTP headers, sent alongside the body. Two matter here:
    `"Content-Type": "application/json"` tells the server "the body you're about to read is JSON,"
    and `"Authorization": f"Bearer {API_KEY}"` is how the request proves who's calling — `Bearer` is
    a naming convention (a "bearer token" scheme) meaning "whoever holds this token is authorized";
    the server checks it against the app's API key configured in Dify.
  - `method="POST"` — one of the HTTP verbs. `GET` asks a server for data; `POST` sends data *to* a
    server to be processed (here: "run this query through the RAG pipeline and give me an answer").

Contrast this with the third-party `requests` library, where the same request would be one line:
`requests.post(url, json={...}, headers={...})`. `urllib` needs three separate steps
(JSON-encode → build a `Request` object → open it) because it's a lower-level, standard-library
tool — nothing to install, at the cost of more ceremony. For a project intentionally keeping
dependencies minimal, that trade favors `urllib`.

```python
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")

            if e.code == 400 and "429" in error_body and "retryDelay" in error_body:
                import re
                match = re.search(r"retryDelay.*?(\d+)s", error_body)
                wait = int(match.group(1)) + 5 if match else 65
                print(f"  Rate limited. Waiting {wait}s before retry (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue

            raise

    raise Exception(f"Failed after {max_retries} retries (rate limit not resolved)")
```

**`urllib.request.urlopen(req, timeout=60)`** actually sends the request and gets back a response
object (`resp`), used here as a context manager — the same `with ... as` pattern from the
BLEU/ROUGE walkthrough, just applied to a network connection instead of a file: it guarantees the
connection is closed afterward. `resp.read()` gets the raw response bytes, `.decode("utf-8")`
turns them back into text, and `json.loads(...)` parses that text back into a Python dict — the
exact mirror of `json.dumps` above.

**`except urllib.error.HTTPError as e:`** — `HTTPError` is raised specifically when the server
responds with an error status code (anything 4xx or 5xx), as opposed to a connection failure or
timeout. `e.code` is the numeric status (e.g. `400`), and `e.read()` gets the error response
*body* — servers usually explain *why* a request failed in the body text, so this line reads that
explanation instead of discarding it.

**The retry condition and the regex** — this is the trickiest logic in the whole file, so here's
what's actually happening. Dify is a proxy in front of Google's Gemini API in this project's setup.
When Gemini's own free-tier rate limit is hit, Gemini returns its own error (HTTP 429, "Too Many
Requests," including a suggested `retryDelay`) — but Dify wraps that in *its own* HTTP 400 response
and passes Gemini's error message through as text inside the body. So the code checks three things
together: the outer status is `400`, and the string `"429"` appears somewhere inside the body text,
and the string `"retryDelay"` appears too — all three together are the fingerprint of "this 400 is
actually a disguised rate-limit error, not a real bad request."

Once that's confirmed, it needs to pull the actual wait time out of a blob of error text that looks
roughly like `..."retryDelay": "59s"...`. That's what the regex does:

```python
match = re.search(r"retryDelay.*?(\d+)s", error_body)
```

Think of this pattern as a description of a shape to search for inside the text, piece by piece:

- `retryDelay` — match those literal characters, wherever they occur.
- `.*?` — then skip forward through *any* characters (`.`), as *few* as possible (`?` after `*`
  makes it "non-greedy" — stop skipping as soon as the rest of the pattern can match, rather than
  skipping all the way to the end of the string and backtracking). In practice this hops over the
  `": "` and the opening quote between `retryDelay` and the number.
- `(\d+)` — then match one or more digits (`\d` means "any digit," `+` means "one or more"). The
  **parentheses are a capture group** — they don't change what's matched, they just mark "remember
  this specific piece separately so I can pull it out afterward."
- `s` — then match a literal `s` right after the digits (from `"59s"`).

`re.search(...)` scans the string looking for the first place this whole shape occurs, and returns
a `Match` object if found (or `None` if not). `match.group(1)` retrieves whatever the *first*
capture group (`(\d+)`) actually matched — in this example, the digits before the `s`.

Verified with the actual error-body shape Gemini/Dify produces:

```python
>>> import re
>>> error_body = '...\'retryDelay\': \'59s\'...'
>>> match = re.search(r"retryDelay.*?(\d+)s", error_body)
>>> match.group(1)
'59'
>>> wait = int(match.group(1)) + 5 if match else 65
>>> wait
64
```

That's real output from running it. `int(match.group(1))` converts the captured text `"59"` (still
a string — regex always returns strings) into the number `59`, then `+ 5` adds a small safety
margin on top of what the server asked for, and `if match else 65` (a conditional expression,
covered in the BLEU/ROUGE walkthrough) falls back to a flat 65-second wait if the regex somehow
didn't match — better to wait too long than to hammer a rate-limited API with a crash.

**`continue`** — skips the rest of the current loop iteration and jumps back to `for attempt in
range(max_retries):`, i.e. tries the same question again after sleeping. **`raise`** with nothing
after it (bare `raise`, inside the `except` block) means "re-raise whatever exception I just
caught, unchanged" — used for any HTTP error that *isn't* the rate-limit pattern, so a genuine bad
request or server error isn't silently retried forever; it propagates up to whoever called
`query_assistant()`.

If the loop runs `max_retries` times without ever successfully returning, the final line raises a
plain `Exception` with a message explaining the retries were exhausted — so a caller always either
gets a real response or a clear exception, never silence.

**What this is really doing, testing-wise:** this whole function is a hand-built retry-with-backoff
policy for one very specific, brittle situation — a rate-limit error identified by *matching
substrings in free-text error messages*, not a structured error code. If the upstream provider
changes its error message wording (a different phrase than `"retryDelay"`, or restructures the
JSON), this detection silently stops matching, and every rate-limited call falls through to the
bare `raise` instead of retrying — turning a recoverable, transient condition into a hard failure
partway through a 60-row run.

---

## 4. `extract_chunks()` (lines 133–139)

```python
def extract_chunks(retriever_resources: list) -> tuple[str, float]:
    """Return pipe-separated chunk texts and the top-1 similarity score."""
    if not retriever_resources:
        return "", 0.0
    texts = [r.get("content", "").replace("\n", " ").strip() for r in retriever_resources]
    top_score = retriever_resources[0].get("score", 0.0)
    return " | ".join(texts), top_score
```

**`-> tuple[str, float]`** is a type hint (the `-> type` syntax is covered in the BLEU/ROUGE
walkthrough) describing a **tuple** — an ordered, fixed-size group of values, written with commas
(parentheses are often used too, but aren't required to *create* one — the comma is what actually
makes it a tuple). `tuple[str, float]` means "this function returns exactly two values: a string
first, then a float." Look at the `return` line: `return " | ".join(texts), top_score` — the
comma between `" | ".join(texts)` and `top_score` is what packs both values into a single tuple
that gets handed back to the caller in one go.

Whoever calls this function (see section 8, inside `evaluate_row()`) unpacks it right back into two
separate names:

```python
retrieved_text, top_score = extract_chunks(resources)
```

This is Python's **multiple-return-value** pattern: a function can only technically return one
thing, but that "one thing" can be a tuple bundling several values, and the caller can unpack a
tuple into several names in one line — cleaner than returning a dict or defining two separate
functions when the two values are always produced and used together.

The list comprehension `[r.get("content", "").replace("\n", " ").strip() for r in
retriever_resources]` (comprehension syntax itself is covered in the BLEU/ROUGE walkthrough) pulls
the text out of each retrieved chunk, replaces internal newlines with spaces, and trims whitespace
— so a multi-line chunk becomes one clean single-line string. `" | ".join(texts)` then glues all
the chunk texts into one string separated by ` | `, so multiple retrieved chunks fit into a single
CSV cell without breaking the CSV's row structure.

**What this is really doing, testing-wise:** `retriever_resources[0]` assumes Dify always returns
chunks pre-sorted with the best match first — if that ordering assumption were ever wrong (or the
list were empty, which the `if not retriever_resources:` guard at the top handles), `top_score`
would silently record the wrong chunk's score instead of erroring loudly.

---

## 5. `check_chunk_match()` (lines 142–165)

```python
def check_chunk_match(expected: str, retrieved_chunks: list) -> tuple[str, str]:
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
```

This function is the mechanical heart of the whole golden-dataset methodology: it's the code that
decides whether retrieval "worked" for a given question, which is what every Recall@K number in
this project ultimately traces back to.

**`set(expected.lower().split())`** — `.split()` with no arguments (already familiar from
`.split()`-style calls, though this is the first time it's wrapped in `set(...)`) breaks a string
into a list of words on whitespace. Wrapping that in `set(...)` converts the list into a **set**
— an unordered collection with no duplicates (sets were introduced in the BLEU/ROUGE walkthrough
for `IN_SCOPE_TYPES`; this is the same data structure, used for a different purpose: word overlap
instead of category membership).

**`expected_words & content_words`** — the `&` operator between two sets computes their
**intersection**: the set of words present in *both*. This is the actual overlap check. Worked
example, run for real:

```python
>>> expected = "Employees accrue fifteen days of PTO per year"
>>> expected_words = set(expected.lower().split())
>>> expected_words
{'of', 'fifteen', 'days', 'pto', 'year', 'per', 'accrue', 'employees'}

>>> retrieved_ok = "The handbook states that employees accrue fifteen days of paid time off per year for full time staff"
>>> content_words = set(retrieved_ok.lower().split())
>>> expected_words & content_words
{'of', 'fifteen', 'days', 'year', 'employees', 'accrue', 'per'}
>>> len(expected_words & content_words) / len(expected_words)
0.875   # 7 of 8 expected words found ("pto" is missing — retrieved chunk said "paid time off" instead) -> HIT (>= 0.60)

>>> retrieved_bad = "Overtime is paid at 1.5x the regular hourly rate for hours worked beyond 40"
>>> content_words = set(retrieved_bad.lower().split())
>>> expected_words & content_words
set()
>>> len(expected_words & content_words) / len(expected_words)
0.0     # completely unrelated chunk -> MISS
```

That's real output from running exactly this code. Notice the first example is a *near-miss on
purpose*: the expected chunk says "PTO," the retrieved chunk paraphrases it as "paid time off," so
one word (`pto`) fails to overlap — yet 7 of the other 8 words still match, clearing the 60%
threshold. That's the design intent: this is a *fuzzy* recall check tolerant of minor paraphrasing
in how a chunk happens to be worded, not an exact-string match.

`overlap = len(expected_words & content_words) / len(expected_words)` turns that intersection into
a fraction: "what percentage of the expected chunk's words showed up somewhere in this retrieved
chunk?" `>= 0.60` is a fixed, hand-picked threshold — 60% of expected words must appear for this
to count as a hit. If a hit is found, the function returns `"yes"` plus `str(resource.get("position",
""))` — `position` is whatever rank Dify assigned that chunk in its retrieved list (1st, 2nd,
3rd, ...), converted to a string since it's going into a CSV cell alongside text columns. If no
retrieved chunk clears the threshold, the loop finishes and falls through to `return "no", ""`.

**`-> tuple[str, str]`** — same two-value-return pattern as `extract_chunks()` above, just both
values are strings this time: `("yes", "2")` or `("no", "")`.

**What this is really doing, testing-wise:** the entire Recall@K metric this project reports rests
on this one arbitrary number, `0.60`. It was picked as "seems reasonable," not derived from
measurement. Two failure modes to watch for: (1) too *low* a threshold inflates recall by counting
loosely-related chunks as hits, and (2) too *high* a threshold undercounts real hits whenever a
chunk is correct but phrased differently (exactly like the `"pto"` vs `"paid time off"` example
above, pushed just a little further). Any change to this threshold changes every historical
Recall@K number and makes runs before/after the change incomparable.

---

## 6. `write_results()` (lines 168–174)

```python
def write_results(results: list) -> None:
    """Write all collected results to OUTPUT_FILE (called after every question)."""
    fieldnames = GOLDEN_COLS + RESULT_COLS
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
```

Mechanically this is identical to the CSV-writing code in the BLEU/ROUGE walkthrough — `with open`,
`csv.DictWriter`, `writeheader()`, `writerows()` are all covered there. What's different, and
worth calling out explicitly, is **when** this function gets called.

Look ahead to `main()` (section 8): `write_results(results)` is called **inside the loop, after
every single row** — not once, after all 60 rows finish. Each call opens `OUTPUT_FILE` in `"w"`
mode (which *overwrites* the whole file) and rewrites the *entire* `results` list collected so far,
from scratch, every time. That sounds wasteful — for 60 rows it's fast enough not to matter — but
it buys something important: if the script crashes or gets killed partway through row 37 (a network
timeout, a rate limit that exhausts all retries, someone hitting Ctrl-C), rows 1–36 are already
safely written to disk, because `write_results()` already ran 36 times by that point. Without this
pattern, a crash on row 37 would lose *all* 37 rows of completed work, not just the one that failed.

**What this is really doing, testing-wise:** this incremental-write pattern is a deliberate
reliability trade-off (a little redundant disk I/O, in exchange for crash resilience) — but it has
a sharp edge: a `run-001.csv` on disk gives you **no signal about whether the run actually
finished**. A file with 37 rows and a file with all 60 rows look identical in shape — same columns,
well-formed CSV — so a scoring tool run against a partial file would silently compute BLEU/ROUGE/
RAGAS metrics over 37 questions and report them as if they represented the full 60-row golden
dataset.

---

## 7. `evaluate_row()` (lines 177–221)

```python
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
```

**`response.get("metadata", {}).get("retriever_resources", [])`** — chained `.get()` calls
(`.get()` itself covered in the BLEU/ROUGE walkthrough) with a twist: the default for the *first*
`.get()` is `{}` (an empty dict), not a string. That matters because the *second* `.get()` is
called immediately on whatever the first one returned — if `"metadata"` were simply missing from
the response and the default had been `None` instead, calling `.get(...)` on `None` would crash
with an `AttributeError`. Defaulting to `{}` guarantees there's always something dict-shaped to
call `.get("retriever_resources", [])` on next, so a response missing metadata just yields an empty
list of chunks instead of crashing.

**`{col: row[col] for col in GOLDEN_COLS}`** — this is a **dict comprehension**, the dict version
of the list comprehensions from the BLEU/ROUGE walkthrough. The shape difference: a list
comprehension is `[value for item in iterable]`; a dict comprehension is `{key: value for item in
iterable}` — the `key: value` pair before `for` is what makes it build a dict instead of a list.
Read this one as: "for every column name in `GOLDEN_COLS`, build a dict entry mapping that column
name to `row`'s value for that column." Since `GOLDEN_COLS` is `["question", "reference_answer",
...]`, this single line copies exactly those seven fields from the input row into a fresh result
dict — equivalent to writing `result = {"question": row["question"], "reference_answer":
row["reference_answer"], ...}` by hand, but immune to a typo dropping one of the columns, since it
always derives the keys from the same `GOLDEN_COLS` list used everywhere else in the file.

**Two `except` clauses, most specific first** — this is the same `try/except` idea from the
BLEU/ROUGE walkthrough, taken one level deeper: instead of one `except`, there are two, stacked in
order:

```python
except urllib.error.HTTPError as e:
    ...
except Exception as e:
    ...
```

Python checks `except` clauses top to bottom and runs the *first* one that matches the exception
that was actually raised. `HTTPError` is a more specific *subtype* of the general `Exception` —
every `HTTPError` is also an `Exception`, but not every `Exception` is an `HTTPError` (a timeout,
a malformed response, a missing dict key would all be plain `Exception`s, not `HTTPError`s). If the
order were flipped — `except Exception` first, `except urllib.error.HTTPError` second — the
broader `Exception` clause would catch *everything*, including HTTP errors, and the more specific
`HTTPError` clause below it would be unreachable dead code. This is why **order matters**: Python
requires (and this script correctly follows) putting narrower, more specific exception types before
broader ones.

The two branches also differ in what they log: the `HTTPError` branch prints the HTTP status code
and reads the response body for a specific error message (`e.read().decode()`); the general
`Exception` branch just prints whatever generic error message Python attached (`e`) — because at
that point, it could be almost anything (a network timeout, a `KeyError` from a malformed CSV row,
a bug elsewhere in the function). Both branches still return a same-shaped `result` dict (all
`RESULT_COLS` set to `""`, with `flags` recording what went wrong) so that one failed row doesn't
crash the whole 60-row run or produce a differently-shaped CSV row that would break
`csv.DictWriter`.

**What this is really doing, testing-wise:** the `flags` column is the audit trail for exactly
which rows failed and why (`API_ERROR_429`, `API_ERROR_500`, or a generic `ERROR: ...` message) —
without it, a row with an empty `actual_answer` would look identical whether the assistant gave a
genuinely empty response or the API call blew up entirely.

---

## 8. `main()` (lines 224–277)

```python
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
```

`sys.exit(...)` with a helpful message, `with open(...)`, `csv.DictReader`, `list(...)` around the
reader — all covered in the BLEU/ROUGE walkthrough.

**`n_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE`** — this computes a **ceiling division**
(round *up* to the next whole number) using only integer arithmetic, without importing
`math.ceil`. Plain `//` (floor division, already familiar from integer arithmetic) always rounds
*down* — `60 // 10` is `6`, but `61 // 10` is also `6`, which would undercount batches by one
whenever there's a partial leftover batch. Adding `BATCH_SIZE - 1` to the numerator before dividing
pushes any nonzero remainder up over the next multiple, so it rounds up instead — without changing
the result when the division was already exact. Verified for real:

```python
>>> for total, batch in [(60, 10), (61, 10), (59, 10), (1, 10), (0, 10)]:
...     print(total, batch, "->", (total + batch - 1) // batch)
60 10 -> 6
61 10 -> 7
59 10 -> 6
1 10 -> 1
0 10 -> 0
```

60 rows in batches of 10 divides exactly, giving 6 batches. Add one more row (61) and the formula
correctly bumps to 7 batches, since that 61st row needs its own (mostly-empty) batch. 59 rows still
needs 6 batches (5 full + 1 partial of 4). Even 1 row still needs 1 batch, and 0 rows correctly
needs 0.

```python
    results = []
    for i, row in enumerate(rows, start=1):
        query_type = row.get("query_type", "")
        batch_no = (i - 1) // BATCH_SIZE + 1
        print(f"[{i:02d}/{total}] (batch {batch_no}/{n_batches}) "
              f"{query_type:20s}  {row['question'][:70]}")

        results.append(evaluate_row(row))

        write_results(results)

        if i == total:
            break

        if i % BATCH_SIZE == 0:
            print(f"  --- Batch {batch_no}/{n_batches} done. "
                  f"Pausing {BATCH_PAUSE}s to respect the rate limit ---")
            time.sleep(BATCH_PAUSE)
        else:
            time.sleep(REQUEST_DELAY)
```

`enumerate(rows, start=1)` is covered in the BLEU/ROUGE walkthrough (there it was `enumerate(rows,
1)` — `start=1` here is the same thing written with the keyword name spelled out). `batch_no = (i
- 1) // BATCH_SIZE + 1` uses the same floor-division idea as the ceiling formula above, just for a
different purpose: converting a 1-based row counter into a 1-based batch number (row 1–10 → batch
1, row 11–20 → batch 2, and so on).

**`if i % BATCH_SIZE == 0:`** — `%` is the *modulo* operator: the remainder after division. `i %
BATCH_SIZE == 0` is `True` exactly on rows 10, 20, 30, ... (whenever `i` is an exact multiple of
`BATCH_SIZE`) — i.e., "this row was the *last* row of its batch." That's the trigger for the long
`BATCH_PAUSE` (default 60s) instead of the short per-question `REQUEST_DELAY` (default 4s) —
pacing designed to stay under a requests-per-minute limit from the underlying LLM/embedding
provider (see the module docstring at the top of the file) while not making every single question
wait the full batch-length pause.

**`if i == total: break`** — placed *before* the pacing check, this exits the loop right after the
very last row is processed, skipping the sleep entirely — there's no reason to pause for a batch
boundary (or wait `REQUEST_DELAY` seconds) after the final question, since there's nothing left to
send.

**Persisting after every row, revisited**: `write_results(results)` is called on *every* iteration
of this loop, immediately after `evaluate_row(row)` — this is the same call from section 6, now
seen in its actual context: it runs 60 times over the course of a full run, once per row, which is
exactly why a mid-run crash still leaves completed rows safely on disk.

```python
    print(f"\nResults written to {OUTPUT_FILE}")

    scoreable = [r for r in results if r["chunk_found"] not in ("n/a", "", "no")]
    total_scoreable = [r for r in results if r["chunk_found"] not in ("n/a", "")]
    found = len(scoreable)
    total = len(total_scoreable)
    recall = found / total if total else 0

    print(f"\n--- Quick Retrieval Summary ---")
    ...
```

Two list comprehensions (covered in the BLEU/ROUGE walkthrough) build: `scoreable` — rows where a
chunk was actually found (`chunk_found` is `"yes"`, i.e. not one of `"n/a"`, `""`, or `"no"`); and
`total_scoreable` — every row that *could* have had a chunk match attempted at all (excludes only
`"n/a"` rows — the out-of-scope/adversarial/fictitious-entity categories that never had an
`expected_chunk` to check against, and any row with an outright empty result from a failed API
call). `recall = found / total if total else 0` is the conditional-expression divide-by-zero guard
pattern from the BLEU/ROUGE walkthrough's `avg()` function, reused here for the same reason: don't
crash if, for some reason, zero rows were scoreable.

---

## 9. The entry point (lines 280–281)

```python
if __name__ == "__main__":
    main()
```

Same idiom, same meaning, as the BLEU/ROUGE walkthrough: only run `main()` — and start actually
calling the API 60 times — if this file is executed directly, not if some other script imports it.
Note this is *not* the same line as `load_dotenv()` back in section 2: that call sits outside this
guard entirely and runs unconditionally at import time, while `main()` only runs when the file is
the one actually being executed.

---

## Python concepts you picked up in this file

*(Only concepts not already in the BLEU/ROUGE walkthrough's table.)*

| Concept | What it means | Where it appeared |
|---|---|---|
| `os.environ.get(...)` / `os.environ.setdefault(...)` | Read/conditionally-set environment variables; `setdefault` only writes if the key is absent, so real env vars can override a `.env` file | `load_dotenv()`, config section |
| `str.partition(sep)` | Split a string into exactly 3 pieces (before, separator, after) around the *first* occurrence | `load_dotenv()` |
| `json.dumps(...)` / `json.loads(...)` | Convert Python dict ↔ JSON text, for talking to a web API | `query_assistant()` |
| `.encode("utf-8")` / `.decode("utf-8")` | Convert text ↔ raw bytes, needed for network I/O | `query_assistant()` |
| `urllib.request.Request(...)` / `urlopen(...)` | Build and send a raw HTTP request without a third-party library | `query_assistant()` |
| `except SpecificError:` before `except Exception:` | Python tries `except` clauses top to bottom; put narrower exception types first or they become unreachable | `evaluate_row()` |
| Regex `re.search(pattern, text)` + capture group `(...)` | Search text for a shape; parentheses mark a piece to extract via `match.group(n)` | `query_assistant()`'s retry logic |
| Tuple return `return a, b` / `-> tuple[str, float]` | A function can hand back multiple values at once, unpacked by the caller into separate names | `extract_chunks()`, `check_chunk_match()` |
| Set intersection `set_a & set_b` | The elements present in both sets — the basis of the word-overlap recall check | `check_chunk_match()` |
| Dict comprehension `{k: v for x in y}` | Like a list comprehension, but builds a dict — note the `key: value` pair before `for` | `evaluate_row()` |
| Ceiling division `(n + d - 1) // d` | Round a division up to the next whole number using only integer math (no `math.ceil` needed) | `main()`, batch-count calculation |
| `%` (modulo) for "every Nth iteration" | `i % N == 0` is true exactly on multiples of `N` — used to detect batch boundaries | `main()`'s pacing logic |
| Calling a function at module level (no `if __name__` guard) | Runs immediately at import time, before `main()` — as opposed to code only reachable via `main()` | `load_dotenv()` on line 68 |

---

## What to test here

| Risk | How to catch it |
|---|---|
| The rate-limit retry logic depends on matching substrings (`"429"`, `"retryDelay"`) in free-text error messages; if the upstream provider (Dify/Gemini) changes its error wording or JSON shape, detection silently stops matching and every rate-limited call falls straight to a hard failure instead of retrying | Write a unit test that feeds `query_assistant`'s retry branch a captured real 429 error body as a fixture, so a wording change in that fixture (updated whenever the real API's error format is observed to change) is a visible, deliberate test update — not a silent runtime failure discovered mid-evaluation-run |
| The 60% word-overlap threshold in `check_chunk_match()` is a hand-picked, untuned constant that directly determines every Recall@K number this project reports | Treat `0.60` as a documented, versioned config value, not a magic number; if it's ever changed, re-run the golden dataset and note in the results that pre/post-change Recall@K numbers aren't comparable |
| Incremental writes (`write_results()` after every row) mean a crash mid-run leaves a syntactically valid but incomplete `run-001.csv` — indistinguishable in shape from a completed 60-row run | Have `main()` (or a wrapper) write a row-count or a completion marker on success, and have scoring tools assert the row count equals the golden dataset's row count before trusting the file |
| `query_assistant()`'s bare `raise` (non-rate-limit HTTP errors) and the outer `except Exception` in `evaluate_row()` both swallow errors into a `flags` column rather than stopping the run — a systemic failure (e.g. Dify down, wrong API key) still "completes" 60 rows, each flagged with the same error, and could be mistaken for a low-quality answer run rather than an infrastructure outage | After a run, check for `flags` values concentrated in `API_ERROR_*`/`ERROR:` across many/most rows before treating scores from that run as meaningful |
| `extract_chunks()` assumes `retriever_resources[0]` is always the top-ranked chunk; if Dify's ordering assumption ever changed, `retrieval_score_rank1` would silently record the wrong chunk's score | Spot-check a raw Dify API response's `retriever_resources` ordering against the `score` field to confirm it's sorted descending before trusting `retrieval_score_rank1` |

## See also

- [Reading `score_bleu_rouge.py`](bleu-rouge-code-walkthrough.md) — the companion walkthrough this doc builds on; covers Python basics not repeated here
- [golden-dataset/first-evaluation.md](../../golden-dataset/first-evaluation.md) — how this script fits into the end-to-end evaluation run
- [golden-dataset/guide.md](../../golden-dataset/guide.md) — the golden dataset methodology this script's retrieval-match logic implements
