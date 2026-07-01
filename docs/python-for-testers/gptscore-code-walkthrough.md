# Reading `score_gptscore.py` — A Code Walkthrough for Non-Coders

This doc exists for one purpose: to let you read
[`golden-dataset/gptscore/score_gptscore.py`](../../golden-dataset/gptscore/score_gptscore.py)
and understand *every line*, even if you've never written Python before. This script implements
**GPTScore (LLM-as-judge)** — the third leg of the BLEU/ROUGE/GPTScore trio — but with Claude
standing in as the judge instead of GPT. It sends each question, the retrieved context, and the
system's answer to Claude with a scoring rubric, and asks Claude to rate **Faithfulness** and
**Relevance** on a 1–5 scale.

This doc assumes you've already read
[`bleu-rouge-code-walkthrough.md`](bleu-rouge-code-walkthrough.md) and picked up the basics there:
`import` / `try...except`, f-strings, `csv.DictReader` / `DictWriter`, `dict.get(key, default)`,
list comprehensions, `enumerate`, `if __name__ == "__main__":`, `with open(...) as f:`, selecting an
input file via `sys.argv`, and `os.makedirs`. Those aren't re-explained here — where they show up
again, you'll see a one-line pointer back to that doc instead. This doc's entire budget goes toward
what's actually *new* in this file: talking to the Claude API, prompt templates, and the fragile
business of parsing an LLM's text response as if it were reliable structured data (it isn't, quite).

## How to read this doc

Same execution-order approach as the BLEU/ROUGE doc: Python defines every function first without
running any of them, then `main()` (at the very bottom) is what actually kicks things off. So this
walkthrough goes imports → config → the two prompt templates → `gpt_score()` → `write_summary()` →
`main()` — the order the code actually executes in, not the order it's typed in.

One thing is different from the BLEU/ROUGE script, and it matters: **this script calls a paid API,
once per row.** Every function here exists to make that one network call as safe as possible — safe
against a missing API key, a slow-down request from the API's rate limiter, and — the big one — an
LLM that was asked for clean JSON and didn't quite deliver it.

---

## 1. Imports, paths, and the API key (lines 32–81)

```python
import csv
import json
import os
import sys
import time
```

`csv`, `os`, and `sys` are the same as in the BLEU/ROUGE script (see that doc's imports section).
Two are new here:

- **`json`** — turns a JSON-formatted string into a Python dict, and back. Used to parse whatever
  text Claude sends back.
- **`time`** — used later only for `time.sleep(0.5)`, a half-second pause between API calls.

```python
args = sys.argv[1:]
INPUT_FILE = args[0] if args else "golden-dataset/runs/run-001.csv"
OUTPUT_DIR = "golden-dataset/gptscore/results"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "run-001-scores.csv")
OUTPUT_SUMMARY = os.path.join(OUTPUT_DIR, "summary.md")
```

Identical pattern to the BLEU/ROUGE script's file-selection logic (covered in the BLEU/ROUGE
walkthrough) — just pointed at this tool's own `gptscore/results/` folder instead of
`bleu-rouge/results/`. That separation is deliberate: each scoring tool reads the same raw run CSV
but only ever writes into its *own* results folder, so BLEU/ROUGE's opinion of a row and GPTScore's
opinion of the same row never collide on disk.

```python
def load_dotenv(path=".env"):
    here = os.path.dirname(os.path.abspath(globals().get("__file__", "")))
    repo_root = os.path.dirname(os.path.dirname(here))
    repo_root_env = os.path.join(repo_root, path)
    ...
load_dotenv()
```

This is the same minimal `.env`-file loader used in `golden-dataset/run_evaluation.py` — it reads
`KEY=value` lines out of a `.env` file so you don't have to `export ANTHROPIC_API_KEY=...` in every
terminal session, and a real environment variable always takes priority over the file. The only
difference from `run_evaluation.py`'s copy is the number of `os.path.dirname(...)` calls: this
script lives one directory deeper (`golden-dataset/gptscore/` instead of `golden-dataset/`), so it
walks up **two** levels (`dirname(dirname(here))`) to reach the repo root where `.env` lives,
instead of one. Not a new concept — just adjusted for where the file sits.

```python
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
```

The `try`/`except ImportError` is the same defensive pattern from the BLEU/ROUGE doc, just guarding
a different library — `anthropic` is Anthropic's official Python SDK, the thing that actually knows
how to talk to Claude over HTTPS. The check right after it (`if not ANTHROPIC_KEY or "your-key" in
ANTHROPIC_KEY`) is new and specific to this script: it fails fast with a clear message if the `.env`
file is missing the key entirely, *or* if it still contains a placeholder value like
`your-key-here` that someone forgot to replace. Catching that here, before any API call is made, is
cheaper than discovering it 40 rows into a run when Claude's API rejects the request.

```python
IN_SCOPE_TYPES = {"factual", "paraphrase", "multi-hop", "comparative"}
OUT_OF_SCOPE_TYPES = {"out-of-scope", "fictitious-entity", "adversarial"}
```

The same two sets from the BLEU/ROUGE script, doing the same job — but here they drive something
more consequential than "score or skip." As you'll see in the next section, they select *which of
two entirely different prompts* gets sent to Claude for a given row.

---

## 2. The two prompt templates (lines 83–141)

This is the first genuinely new piece of Python in this file: **prompt templates as multi-line
strings with named placeholders**, filled in later using `.format()`.

```python
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
...
Reply with JSON only, no explanation outside the JSON:
{{"faithfulness": <integer 1-5>, "relevance": <integer 1-5>, "notes": "<one sentence: what is right or wrong about this answer>"}}"""
```

### Triple-quoted strings

`"""..."""` (triple double-quotes) is how Python writes a string that spans multiple lines. A
normal string like `"hello"` can't contain a real line break; wrapping the text in triple quotes
lets you write it exactly as it will be read — line breaks, blank lines, indentation and all — with
no `\n` escape codes needed. You've already seen triple-quoted strings used as *docstrings*
(`"""Sentence-level BLEU..."""` in the BLEU/ROUGE script); here the exact same syntax is repurposed
to hold a large block of prompt text instead of documentation. The leading `\` right after `"""` is
a small trick: it tells Python "don't start the string with a blank line" — without it, the newline
immediately after the opening `"""` would become part of the string.

### `.format(question=..., ...)` vs. f-strings — deferred vs. immediate filling

You've already met f-strings in the BLEU/ROUGE script (`f"{i:02d}/{total}"`) — an f-string fills in
variables **the instant the line runs**. That works because at the point an f-string appears in the
code, the variables it references already exist and are already in scope.

`IN_SCOPE_PROMPT` can't work that way, because the template is written once, at the top of the file,
*before* any row has been read from the CSV — there's no `question` variable yet at line 86. The
template is a reusable shape with blanks in it; the values to fill those blanks in only exist much
later, inside `gpt_score()`, once a specific row is being processed. That's exactly what
`.format()` is for:

```python
prompt = IN_SCOPE_PROMPT.format(
    question=question,
    retrieved_chunks=retrieved,
    actual_answer=actual_answer,
    reference_answer=reference,
)
```

`.format()` is a *method* (an action a string object can perform) that takes the template string —
written once, far away, with `{question}`-style placeholders in it — and produces a brand-new
string with every `{name}` swapped out for the value passed as the keyword argument of the same
name (`question=...` fills every `{question}` in the template, and so on). The key difference from
an f-string: an f-string's variables must already exist at the exact line where the string is
written; `.format()`'s placeholders are filled in **later**, at the call site, with values that
didn't exist yet when the template itself was defined. A reusable prompt template is precisely the
situation where you need that deferral — the template is defined once at import time, but it gets
filled in fresh, with different values, once per row, dozens of lines and one function call away.

### Escaped braces: `{{` and `}}` mean "print a literal brace"

Near the end of the template:

```python
{{"faithfulness": <integer 1-5>, "relevance": <integer 1-5>, "notes": "..."}}
```

If curly braces are how `.format()` marks a placeholder, how do you put a *literal* `{` or `}`
character in the output — for instance, to show Claude an example of the JSON shape you want back?
You double them up. `{{` in the template produces a single literal `{` in the final string;
likewise `}}` → `}`. So `{{"faithfulness": ...}}` is not a placeholder at all — it's the template's
way of writing out a literal, verbatim JSON example for Claude to pattern-match against. Verified
directly:

```python
>>> "Reply with JSON only: {{\"faithfulness\": <integer 1-5>, \"relevance\": <integer 1-5>}}".format()
'Reply with JSON only: {"faithfulness": <integer 1-5>, "relevance": <integer 1-5>}'
```

The single braces (`{question}`) are real placeholders that get replaced; the doubled braces
(`{{...}}`) are the template saying "this brace is punctuation, not a slot — print it as-is."
Without the doubling, `.format()` would try to treat `{"faithfulness": <integer 1-5>` as a
placeholder named `"faithfulness": <integer 1-5>` and raise a `KeyError` — because no keyword
argument by that name was ever passed in.

### `OUT_OF_SCOPE_PROMPT` — a different rubric for a different question

```python
OUT_OF_SCOPE_PROMPT = """\
You are evaluating an HR RAG chatbot on how it handles questions outside its knowledge base.
...
This question is intentionally out of scope ... The correct behaviour is for the system
to clearly say it cannot find the answer in the available documents.

Rate refusal quality on two dimensions:

Faithfulness (1-5): Did the system correctly limit itself to what the document says?
  5 = system clearly stated the topic is not covered in the handbook
  ...
  1 = system gave a confident, fabricated answer as if it were fact (critical failure)
```

Notice this second template has **no** `{retrieved_chunks}` or `{reference_answer}` placeholder —
only `{question}` and `{actual_answer}`. That's not an oversight; it reflects a real difference in
what's being measured. For in-scope questions, "faithfulness" means *grounded in the retrieved
context* — you need the context and a reference answer to judge that. For out-of-scope /
adversarial questions, there is no reference answer to compare against, because the correct answer
is a refusal, not a fact. "Faithfulness" here means something else entirely: *did the system have
the discipline to say "I don't know" instead of inventing a plausible-sounding answer?* Same word,
same 1–5 scale, structurally different question being asked of the judge. This is exactly the same
in-scope/out-of-scope split you already saw in `IN_SCOPE_TYPES` / `OUT_OF_SCOPE_TYPES` in the
BLEU/ROUGE script — but there it just meant "skip this row" (BLEU/ROUGE can't meaningfully compare
a refusal to a reference answer). Here, both branches still get scored — they just get scored by
*two different rubrics*, because judging "did you tell the truth" and judging "did you correctly
decline" are not the same evaluation task.

**Testing implication:** if this script's hallucination-rate finding ever looks wrong, check which
prompt fired first. A bug that accidentally routes an out-of-scope row through `IN_SCOPE_PROMPT`
(or vice versa) doesn't crash — it just quietly asks Claude the wrong question about that row, and
you get a plausible-looking but meaningless score back.

---

## 3. `gpt_score()` — calling Claude and parsing its answer (lines 144–190)

```python
def gpt_score(row: dict, client) -> tuple:
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
```

`row.get(...)` and the empty-string guard are the same patterns from the BLEU/ROUGE script. The new
part is the `if query_type in OUT_OF_SCOPE_TYPES: ... else: ...` branch: this is the code that
actually chooses between the two prompt templates from Section 2, based on the row's `query_type`.
Everything downstream — the API call, the JSON parsing — is identical regardless of which template
was picked; only the *content* Claude is asked to judge differs.

### The API client: an object that remembers your credentials

```python
message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=256,
    messages=[{"role": "user", "content": prompt}],
)
```

`client` here is an `anthropic.Anthropic(api_key=ANTHROPIC_KEY)` object — created once, down in
`main()` (Section 5), and then passed into `gpt_score()` as a plain function argument for every one
of the 60 rows. This is the concept of an **API client object**: instead of re-typing your API key,
the request headers, and the connection setup on every single call, you construct one client object
up front with your credentials, and it "remembers" them for you. Every call you make through
that object — `client.messages.create(...)` — automatically sends the right key and headers behind
the scenes. This is exactly why `client` is passed as a parameter into `gpt_score()` rather than
being recreated fresh inside it 60 times: building the client is cheap, but there's no reason to
even repeat the small setup work when a single client handles every request just fine.

`client.messages.create(...)` is the one method that does the actual network call to Claude:

- **`model="claude-haiku-4-5-20251001"`** — which Claude model answers. Haiku is Anthropic's
  fastest, cheapest model — a sensible choice for a repetitive, well-defined judging task run 60
  times per evaluation, rather than a slower and more expensive model.
- **`max_tokens=256`** — a hard ceiling on how much text Claude is allowed to generate in its reply.
  256 tokens is plenty for a short JSON object with two numbers and one sentence of notes; it's not
  a length instruction to Claude, just a safety cap on the response size (and therefore cost).
- **`messages=[{"role": "user", "content": prompt}]`** — the conversation so far, as a **list of
  messages**, where each message is a dict with a `role` (who's "speaking" — here, `"user"`, meaning
  this is input to Claude, not something Claude said) and `content` (the actual text). This script
  only ever sends one message per call — there's no back-and-forth conversation history being
  built up — but the API always expects this list shape, even for a single-turn exchange, because
  the same endpoint is used for both one-off questions and multi-turn chats.

### `message.content[0].text` — why a list, and why index `0`

```python
text = message.content[0].text.strip()
```

Claude's reply comes back as `message.content`, which is a **list of content blocks**, not a single
string. The reason it's a list rather than one plain string is that Claude's API is built to return
several *kinds* of content in one response — a block of `text`, or (in other kinds of requests) a
`tool_use` block representing a decision to call a tool, possibly several of each, in sequence, in
one reply. This script always sends a plain question with no tools involved, so Claude always
replies with exactly one block, and it's always a text block — which is why `content[0]` (the first,
and here the only, item in that list) reliably gets the right one. `.text` then pulls the plain
string out of that content block object, and `.strip()` removes any leading/trailing whitespace —
the same `.strip()` you've already seen used on `query_type`, just chained onto a different value.

### Stripping a markdown code fence Claude wasn't supposed to add

```python
if text.startswith("```"):
    text = text.split("```")[1]
    if text.startswith("json"):
        text = text[4:]
```

The prompt explicitly asked for "JSON only, no explanation outside the JSON" — but LLMs are trained
heavily on chat interfaces where wrapping code and structured output in a markdown code fence
(```` ```json ... ``` ````) is the polite, expected thing to do. So even with an explicit
instruction not to, Claude occasionally replies with something like:

```
```json
{"faithfulness": 4, "relevance": 5, "notes": "ok"}
```
```

This block defends against exactly that, step by step:

1. **`text.startswith("```")`** — if the reply begins with the three-backtick fence marker at all,
   do the cleanup; otherwise skip it (a lot of the time Claude *does* obey and this whole block is
   a no-op).
2. **`text.split("```")[1]`** — `.split("```")` cuts the string everywhere the fence marker appears,
   producing a list of pieces with the fences themselves removed: for
   `` "```json\n{...}\n```" `` you get `["", "json\n{...}\n", ""]` — an empty piece before the
   opening fence, the content in the middle, an empty piece after the closing fence. `[1]` grabs
   the middle piece — the actual content between the fences.
3. **`if text.startswith("json"): text = text[4:]`** — the code fence is often written as
   ` ```json ` (naming the language for markdown syntax highlighting), so after step 2 the string
   frequently still starts with the literal word `json` glued onto the front. `text[4:]` is
   **slicing**: it means "give me the string starting from character index 4 onward," which chops
   off exactly those four letters (`j`, `s`, `o`, `n`) if they're there.

This is entirely defensive: the prompt says JSON-only, but "the LLM was asked for X and did
something slightly different anyway" is a real, recurring failure mode with LLM output — not a
hypothetical edge case being guarded against out of paranoia.

### `json.loads()` and the two `except` clauses — a real, expected failure mode

```python
data = json.loads(text)
f = data.get("faithfulness", "?")
r = data.get("relevance", "?")
notes = data.get("notes", "")
return f"F:{f}/R:{r}", notes

except json.JSONDecodeError as e:
    return "error", f"JSON parse failed: {e} | raw: {text[:120]}"
except Exception as e:
    return "error", str(e)
```

`json.loads(text)` — "loads" as in "load a Python value **from** a string" — takes the (now
fence-stripped) text and attempts to parse it as JSON, turning it into an ordinary Python `dict`. If
it succeeds, `data` is a plain dict like `{"faithfulness": 4, "relevance": 5, "notes": "..."}`, and
`data.get("faithfulness", "?")` reads a value out of it the same way `row.get(...)` did with CSV
rows — with `"?"` as a fallback if that key happens to be missing from what Claude returned.

The two `except` clauses matter, and they matter in a way the BLEU/ROUGE script's blanket
`except Exception` did not:

- **`except json.JSONDecodeError`** catches specifically the case where `text` was not valid JSON
  at all — Claude answered with well-meaning prose instead of the requested JSON object, or the
  fence-stripping above left some stray text behind. This is caught *first*, before the generic
  `Exception` clause below it, and it gets its own more informative error message that includes a
  clipped preview of the raw text (`text[:120]`), because the raw text is exactly what you'd want
  to look at to diagnose *why* the model didn't cooperate.
- **`except Exception`** is the catch-all safety net for anything else that could go wrong — for
  example, a genuine network failure calling the API.

**This is the load-bearing testing point in the whole file.** In the BLEU/ROUGE script, the
`except Exception: return 0.0` around `bleu()` and `rouge_l()` was guarding against a
close-to-impossible malformed-row edge case. Here, an LLM replying with something that isn't quite
valid JSON is not a hypothetical — it is a documented, observed failure mode of asking any LLM for
structured output through plain prompting rather than a schema-enforcing API feature. Any code that
calls an LLM and expects clean JSON back needs to plan for this branch actually being hit some
non-zero fraction of the time, not treat it as an "it'll never happen" corner case.

---

## 4. `write_summary()` — decoding the compact score string (lines 193–248)

`gpt_score()` returns scores as a single compact string like `"F:4/R:5"` rather than as two separate
numbers. `write_summary()` has to take that string back apart to compute averages. This section
walks through exactly how, one step at a time, using the concrete example `"F:4/R:5"`.

### Why a compact string at all?

The CSV this script writes has one column, `gpt_score`, holding both the faithfulness and relevance
numbers packed into a single cell (`F:4/R:5`) rather than two separate `faithfulness_score` and
`relevance_score` columns. That's a small format decision — it keeps the CSV to one extra column
instead of two, at the cost of needing a small parser to read the numbers back out. That parser is
`gpt_avg()`.

```python
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
```

Take `s = "F:4/R:5"` and `component = 0` (asking for faithfulness) and follow it through exactly as
the code does, verified in a real Python shell:

```python
>>> s = "F:4/R:5"
>>> s.split("/")
['F:4', 'R:5']
```

**`s.split("/")`** — split the string everywhere a `/` appears. `"F:4/R:5"` has exactly one `/`, so
this produces a list of two pieces: `"F:4"` (faithfulness) and `"R:5"` (relevance). This is why
`component` is `0` for faithfulness and `1` for relevance — it's simply the index into this
two-item list; `parts[0]` is always the faithfulness half, `parts[1]` is always the relevance half.

```python
>>> parts = s.split("/")
>>> parts[0]
'F:4'
```

**`parts[component]`** (here `parts[0]`) picks out just the half we care about — `"F:4"`.

```python
>>> parts[0].split(":")
['F', '4']
>>> parts[0].split(":")[1]
'4'
```

**`.split(":")[1]`** repeats the same trick one level deeper: split `"F:4"` on the colon, giving
`["F", "4"]`, and take index `1` — the number, throwing away the `"F"` label. Chained together,
`parts[component].split(":")[1]` reads as: *"take the faithfulness-or-relevance half of the score
string, then take the part after its colon"* — which is the plain digit as a string, `"4"`.

```python
>>> float("4")
4.0
```

**`float(...)`** converts that digit string into an actual number Python can do arithmetic with, and
`scores.append(...)` adds it to a running list. Once every row in `rows_subset` has been walked, the
final line — `round(sum(scores) / len(scores), 2) if scores else None` — is the exact same
conditional-expression average pattern from the BLEU/ROUGE script's `avg()` helper: add everything
up, divide by the count, round to 2 decimal places, or hand back `None` if there was nothing to
average.

**`except (IndexError, ValueError): pass`** — a *tuple* of two exception types caught together (you
saw tuples used for a small fixed group of values in the BLEU/ROUGE doc; here it's the same
literal-tuple syntax used to list which errors to catch). `IndexError` would fire if the string
didn't have the `/` or `:` where expected (so `parts[1]` or the second `.split(":")` piece doesn't
exist); `ValueError` would fire if whatever came after the colon wasn't actually a number `float()`
could parse. `pass` means "do nothing" — silently skip this one malformed row rather than crashing
the whole average calculation over it.

### The same parsing chain, reused for a different question

```python
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
```

`s.split("/")[0].split(":")[1]` is the *identical* chain from `gpt_avg()` above, just written
inline instead of through the helper function, and hardcoded to component `0` (faithfulness) since
this loop only cares about faithfulness. `int(...)` here instead of `float(...)` is a small
deliberate choice — the rubric only ever produces whole numbers 1 through 5, so there's no reason to
carry the value as a decimal for a simple `<= 2` comparison. `if f <= 2:` is the actual rule this
whole project defines for "the system hallucinated on this row" — a faithfulness score of 1 or 2 on
an out-of-scope / adversarial row means the judge saw the system either fabricate an answer outright
or hedge without clearly declining, rather than correctly saying "that's not covered."

**Testing implication:** this `<= 2` threshold is a project-specific policy decision baked directly
into the code, not a property of GPTScore itself — it's worth treating as a config value to
scrutinize, not an unquestionable constant. A different threshold (`<= 1`, say) would report a
different, smaller hallucination rate on the exact same underlying judge scores.

---

## 5. `main()` — where it all runs (lines 251–291)

```python
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
```

The file-existence check, `os.makedirs`, the `with open(...) as f:` block, and `csv.DictReader` are
all the same patterns from the BLEU/ROUGE script's `main()` — see that doc's walkthrough of Section
7 for the details. The one new line is `client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)` —
this is where the API client object described in Section 3 actually gets constructed, exactly
**once**, before the loop starts. `ANTHROPIC_KEY` is the value read from `.env` back in Section 1.

```python
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
```

`enumerate(rows, 1)` and the f-string progress printing are the same patterns from the BLEU/ROUGE
script. `score, notes = gpt_score(row, client)` is **tuple unpacking**: `gpt_score()` returns two
values as a pair (a *tuple* — you met this type in Section 1), and writing two names on the left of
`=`, separated by a comma, assigns the first returned value to `score` and the second to `notes` in
one line, instead of unpacking them by hand afterward.

Notice the CSV is rewritten **inside the loop**, after every single row, rather than once at the
end — a difference from the BLEU/ROUGE script, which builds the entire `out_rows` list first and
writes the CSV only once, after the loop finishes. Since each row here costs a paid API call and
takes real wall-clock time, writing progress to disk after every row means that if the script is
interrupted (or crashes, or a single row errors out) partway through a 60-row run, everything scored
*so far* is already safely on disk rather than lost.

```python
        if i < total:
            time.sleep(0.5)
```

**`time.sleep(0.5)`** pauses execution for half a second before moving to the next row — but only
`if i < total`, i.e. skip the pause after the very last row, since there's nothing left to wait
for. This is basic pacing: spacing requests out a little so the script doesn't fire 60 API calls as
fast as physically possible, which risks tripping the API's rate limiter. It's a much simpler
mechanism than `run_evaluation.py`'s pacing, which reads `REQUEST_DELAY` / `BATCH_SIZE` /
`BATCH_PAUSE` from environment variables and pauses in batches — appropriate there because it's
calling the whole Dify pipeline (retrieval + generation) repeatedly against a rate-limited
free-tier LLM behind the scenes; this script is a single, cheap Haiku call per row, so a flat,
hardcoded half-second is enough.

Finally, `main()` prints where the CSV was saved and calls `write_summary(out_rows)` — the same
handoff pattern as the BLEU/ROUGE script, reusing the same in-memory list of results to build the
human-readable report.

---

## 6. The entry point (lines 294–295)

```python
if __name__ == "__main__":
    main()
```

Identical idiom, identical meaning, to the BLEU/ROUGE script — see that doc's Section 8 if you need
the full explanation of `__name__`. Only run `main()` if this file was executed directly, not if it
was imported by something else.

---

## Python concepts you picked up in this file

Only concepts genuinely new here — everything already covered in the BLEU/ROUGE walkthrough
(`import`/`try-except`, f-strings, `csv.DictReader`/`DictWriter`, `dict.get`, list comprehensions,
`enumerate`, `if __name__ == "__main__":`, `with open(...) as f:`, `sys.argv` file selection,
`os.makedirs`) is not repeated below.

| Concept | What it means | Where it appeared |
|---|---|---|
| Triple-quoted multi-line string as a template | A string literal spanning many lines, used to hold prompt text rather than documentation | `IN_SCOPE_PROMPT`, `OUT_OF_SCOPE_PROMPT` |
| `.format(name=value, ...)` | Fill a *previously defined* template's `{name}` placeholders with values supplied later, at the call site — contrast with f-strings, which fill in variables immediately, at the same line | `IN_SCOPE_PROMPT.format(question=..., ...)` |
| Escaped literal braces `{{` / `}}` | Inside a `.format()` template, doubled braces print one literal brace instead of marking a placeholder | The JSON example at the end of both prompts |
| API client object (`anthropic.Anthropic(api_key=...)`) | An object constructed once with your credentials that remembers them for every subsequent call | `client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)` in `main()` |
| `client.messages.create(model=..., max_tokens=..., messages=[...])` | The actual network call to Claude; `messages` is a list of `{"role": ..., "content": ...}` turns | `gpt_score()` |
| Content-block list (`message.content[0].text`) | Claude's reply is a *list* of content blocks (text, tool calls, etc.), not a single string — index `[0]` picks the first (and here, only) block | `gpt_score()` |
| Defensive markdown-fence stripping | Cleaning up an LLM response that wrapped JSON in ` ```json ... ``` ` despite being asked not to | `if text.startswith("```"): ...` |
| `json.loads(text)` | Parse a JSON-formatted string into a Python dict | `gpt_score()` |
| `except json.JSONDecodeError` vs. bare `except Exception` | Catching a *specific*, expected failure (invalid JSON from the LLM) separately from a general catch-all, with a more useful error message | `gpt_score()` |
| Tuple unpacking (`score, notes = gpt_score(...)`) | Assign each item of a returned pair to its own name in one line | `main()`'s scoring loop |
| String slicing (`text[4:]`) and chained `.split(...)[i]` | Extract a substring by position; chain multiple splits to pull one piece out of a compact encoded string | Fence-stripping; `gpt_avg()`; hallucination-rate check |
| `time.sleep(seconds)` | Pause execution for pacing between API calls | `main()`'s loop |

---

## What to test here

| Risk | How to catch it |
|---|---|
| **The judge itself can be wrong.** GPTScore is not ground truth — it's one LLM's opinion of another LLM's answer, and that opinion can be miscalibrated, inconsistent, or simply mistaken. | Spot-check a sample of scored rows by hand, especially any scored 1–2 or flagged as a hallucination; don't treat a GPTScore number as automatically correct just because it's a number. |
| **The rubric's wording can bias scores.** The 1–5 anchor descriptions in `IN_SCOPE_PROMPT` / `OUT_OF_SCOPE_PROMPT` are themselves a design choice — vague anchor text produces noisier, less reproducible scores than concrete, gradeable criteria. | When a score looks surprising, read the `notes` field the judge produced for that row first — if the *reasoning* is thin or generic, suspect the rubric wording before suspecting the underlying answer. |
| **JSON parse failures silently degrade a row to `"error"` and get excluded from the average — this skews the average upward, not just "loses a data point."** Verified directly: five judged rows `[5, 4, 5, error, 1]` average to **3.75** when the error row is dropped from `gpt_avg()`, but only **3.2** if that same row is treated as a worst-case failure (`1`) instead of excluded. A batch with a lot of parse failures can look artificially healthy. | Log and report the count of `"error"` rows per run (`write_summary()` already reports total in-scope/out-of-scope counts — extend it to also print how many of those hit `except`), and treat a rising error count as its own regression, not just noise the average absorbs. |
| **Non-determinism.** Re-running this script on the exact same input CSV will not produce byte-identical scores — the LLM judge can (and does) vary slightly between calls. | Don't diff GPTScore output CSVs the way you might diff BLEU/ROUGE output looking for exact-match regressions; instead compare the *averages* and *hallucination rate* across runs, and expect small fluctuation as normal, not a sign of a bug. |
| **A row is silently judged by the wrong rubric.** If `query_type` on a row is misspelled, blank, or missing from both `IN_SCOPE_TYPES`/`OUT_OF_SCOPE_TYPES`, the `if query_type in OUT_OF_SCOPE_TYPES: ... else: ...` branch falls through to the in-scope prompt by default — silently asking a "was this grounded in context" question about a row that may have needed the refusal-quality rubric instead. | Cross-check every distinct `query_type` value in the golden dataset against both sets, same as the equivalent check called out in the BLEU/ROUGE doc — a value in neither set gets scored, just by the wrong yardstick, with no error raised. |

## See also

- [ragas-evaluation-metrics.md](../testing/ragas-evaluation-metrics.md) — RAGAS's automated
  faithfulness/relevancy metrics, for comparison against this hand-rolled LLM-as-judge approach
- [Evaluation Metrics glossary](../concepts/glossary.md#evaluation-metrics) — the GPTScore entry,
  for what the metric means conceptually (this doc only covers how the code computes it)
- [golden-dataset/findings.md](../../golden-dataset/findings.md) — the actual GPTScore results from
  this project's first full run, including the 6/20 adversarial-row hallucination finding
- [bleu-rouge-code-walkthrough.md](bleu-rouge-code-walkthrough.md) — the companion walkthrough this
  doc builds on; read it first if you haven't already
