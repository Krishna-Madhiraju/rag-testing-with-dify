# Reading `score_bleu_rouge.py` — A Code Walkthrough for Non-Coders

This doc exists for one purpose: to let you read
[`golden-dataset/bleu-rouge/score_bleu_rouge.py`](../../golden-dataset/bleu-rouge/score_bleu_rouge.py)
and understand *every line*, even if you've never written Python before. It teaches the Python
syntax and the libraries (`nltk`, `rouge_score`) as they appear, and ties each piece back to what
it's doing for RAG testing.

This is **not** an explanation of what BLEU and ROUGE-L measure conceptually — that's already
covered in the [glossary](../concepts/glossary.md#evaluation-metrics) (see the BLEU and ROUGE-L
entries under "Evaluation Metrics") and in [Advanced Evaluation Metrics](../testing/advanced-evaluation-metrics.md).
This doc assumes you already know *what* the metrics mean and focuses purely on *how the code
computes them*.

## How to read this doc

Python doesn't run top-to-bottom the way you'd read a page. It runs in two phases:

1. **Definition phase** — Python reads through function definitions (`def bleu(...):`) and just
   remembers them. It doesn't run the code inside yet.
2. **Execution phase** — at the bottom of the file, `main()` is actually *called*, and only then
   does the code inside it run — which in turn calls the functions defined earlier.

So this walkthrough follows **execution order**, not file order: imports and setup, then each
function explained (with a "try it yourself" snippet), then `main()` last, since that's where the
story actually happens.

---

## 1. Imports (lines 35–51)

```python
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
```

**`import`** pulls in a *library* — code someone else already wrote, so you don't reinvent it.
`csv`, `os`, and `sys` ship with Python itself (the "standard library"); `nltk` and `rouge_score`
are third-party libraries this script depends on (installed via `pip`, Python's package manager).

- **`csv`** — reads and writes `.csv` files. Used later to load the run results and write the scores.
- **`os`** — talks to the operating system: check if a file exists, create a folder.
- **`sys`** — access to command-line arguments and the ability to stop the program (`sys.exit`).
- **`nltk`** (Natural Language Toolkit) — a general-purpose NLP library. Here it's used only for
  its **tokenizer** (splitting a sentence into words) and its **BLEU score** implementation.
- **`rouge_score`** — a small, focused library that does one thing: compute ROUGE scores.

**`try` / `except`** is Python's way of saying "attempt this, and if it fails in a specific way,
do something else instead of crashing with a wall of red error text." Here:

```python
try:
    import nltk
except ImportError:
    sys.exit("Missing: nltk\nRun: pip install nltk")
```

reads as: *"Try to import nltk. If that specific kind of failure happens — `ImportError`, meaning
the library isn't installed — stop the program and print a helpful message telling the user what
to install."* Without this, a missing library would produce a much scarier, harder-to-read Python
traceback. This is defensive coding aimed at a human running the script from the terminal, not at
handling something that's expected to happen — which is why it makes sense here but you shouldn't
expect to see `try/except` wrapped around *everything*.

**`nltk.download("punkt", ...)`** — `punkt` is the name of NLTK's pretrained tokenizer model
(a small file, not a huge language model). NLTK doesn't ship it by default to keep the install
small; this line fetches it once. `quiet=True` just suppresses NLTK's own progress-bar chatter.

> **Try it yourself** — open a Python REPL (type `python3` in your terminal) and run:
> ```python
> >>> import nltk
> >>> nltk.word_tokenize("The employee handbook covers PTO policy.")
> ['The', 'employee', 'handbook', 'covers', 'PTO', 'policy', '.']
> ```
> That's the tokenizer this script relies on — it splits a sentence into words *and* punctuation as
> separate tokens (notice the trailing `.` is its own item). This matters for BLEU: if reference
> and candidate tokenize punctuation differently, scores would drift for reasons that have nothing
> to do with meaning.

---

## 2. Paths and config (lines 53–63)

```python
args = sys.argv[1:]
INPUT_FILE = args[0] if args else "golden-dataset/runs/run-001.csv"
OUTPUT_DIR = "golden-dataset/bleu-rouge/results"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "run-001-scores.csv")
OUTPUT_SUMMARY = os.path.join(OUTPUT_DIR, "summary.md")

IN_SCOPE_TYPES = {"factual", "paraphrase", "multi-hop", "comparative"}
OUT_OF_SCOPE_TYPES = {"out-of-scope", "fictitious-entity", "adversarial"}
```

**`sys.argv`** is a *list* of everything typed on the command line. If you run:

```bash
python3.11 golden-dataset/bleu-rouge/score_bleu_rouge.py runs/run-002.csv
```

then `sys.argv` is `["score_bleu_rouge.py", "runs/run-002.csv"]` — item `0` is always the script's
own name, so `sys.argv[1:]` ("everything from index 1 onward") strips that off and leaves just the
arguments the user actually passed.

**`args[0] if args else "..."`** is a *conditional expression* — a compact if/else that produces a
value instead of running a block of code. Read it right-to-left-ish as: *"if `args` is non-empty,
use `args[0]`; otherwise use this default string."* This is why the script works both with no
argument (defaults to `run-001.csv`) and with an explicit filename.

**`os.path.join(a, b)`** glues a folder and filename together correctly for whatever operating
system you're on (`/` on Mac/Linux, `\` on Windows) — safer than typing `OUTPUT_DIR + "/" + "..."`
by hand.

**`{"factual", "paraphrase", ...}`** with curly braces is a **set** — an unordered collection with
no duplicates, optimized for one thing: checking "is X in this collection?" very fast. It's used a
few lines down as `qt in IN_SCOPE_TYPES`. A list (`[...]`) would work too, but a set communicates
"I only care about membership, not order or duplicates" and is the idiomatic choice here.

**What this is really doing, testing-wise:** this is the code's answer to "BLEU/ROUGE only make
sense for questions that have a reference answer to compare against." Adversarial and
out-of-scope rows in the golden dataset are deliberately designed to have *no* clean reference
answer (the correct response is a refusal, not a fact) — so lexical overlap metrics are meaningless
for them. This split is a testing decision encoded directly in data structures.

---

## 3. The `bleu()` function (lines 66–76)

```python
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
```

**`def bleu(reference: str, candidate: str) -> float:`** defines a *function* — a named, reusable
block of code. `reference` and `candidate` are its **parameters** (inputs); `: str` after each one
is a *type hint* — a note to human readers (and some tools) saying "I expect a string here." It's
not enforced by Python at runtime; it's documentation, not a rule. `-> float` says "this function
returns a decimal number." The text in triple quotes right below is a **docstring** — documentation
attached to the function, retrievable in Python via `bleu.__doc__`.

**`if not reference or not candidate:`** — an empty string `""` is treated as "falsy" in Python
(false-like), so `not reference` means "reference is missing or empty." This guards against the
case where a row in the CSV has a blank answer — instead of crashing, it just scores 0.

**`reference.lower()`** — lowercases the text before comparing. This is a *design decision*, not a
Python requirement: without it, `"Employee"` and `"employee"` would count as different words and
be unfairly penalized, since BLEU is purely about exact token matches (see next section).

**`nltk.word_tokenize(...)`** — as shown above, splits the string into a list of word/punctuation
tokens. BLEU doesn't work on raw strings; it works on the *sequences of tokens*.

**`SmoothingFunction().method1`** — this is the trickiest line, and it's a real BLEU quirk worth
understanding. BLEU multiplies together precision scores for 1-gram, 2-gram, 3-gram, and 4-gram
matches (single words, pairs of words, triples, quadruples). If a candidate answer is short — say,
five words — it might have *zero* 4-grams in common with the reference purely because it's short,
not because it's wrong. Multiplying by a hard zero would crash the score to 0.0 regardless of how
good the shorter n-grams matched. "Smoothing" adds a small fudge factor so a missing high-order
n-gram doesn't wipe out the whole score. `method1` is just NLTK's name for one specific smoothing
formula (there are several, numbered by the paper that proposed them) — chosen here because it's a
reasonable default for short, sentence-level text like RAG answers.

**`sentence_bleu([ref_tokens], cand_tokens, smoothing_function=smoother)`** — note `[ref_tokens]` is
wrapped in a list. That's because BLEU was designed for machine translation, where a single sentence
can have *multiple* acceptable reference translations, and the function is built to accept a list of
references. This script only has one reference answer per question, so it's a list containing one item.

**`round(..., 4)`** rounds the result to 4 decimal places — purely for readable output in the CSV.

**The outer `try/except Exception`** here is different from the import one above — this one is
guarding against *any* unexpected failure during scoring (e.g. a malformed row) so that one bad row
doesn't crash the entire run of 60 questions. This is a deliberate robustness choice for a batch
script: better to score that one row as 0.0 and keep going than to lose all 59 other results.

> **Try it yourself:**
> ```python
> >>> from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
> >>> ref = "employees accrue fifteen days of PTO per year".split()
> >>> cand = "employees earn fifteen PTO days annually".split()
> >>> sentence_bleu([ref], cand, smoothing_function=SmoothingFunction().method1)
> 0.041...  # very low score — same *meaning*, almost no shared word sequences
> ```
> This is BLEU's blind spot in action: a paraphrase that a human would call "correct" scores low
> because BLEU only counts exact overlapping word sequences, not meaning.

---

## 4. The `rouge_l()` function and scorer setup (lines 79–90)

```python
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
```

**`_rouge = rouge_lib.RougeScorer(["rougeL"], use_stemmer=True)`** sits *outside* any function, at
module level, so it runs once — the moment the file is loaded — rather than being recreated on
every call to `rouge_l()`. This is an efficiency pattern: building a scorer object has a small
setup cost, so it's built once and reused. The leading underscore in `_rouge` is a Python
convention meaning "this is internal to this file, not meant to be imported/used elsewhere" — it's
a naming signal to readers, not an enforced rule.

**`RougeScorer(["rougeL"], use_stemmer=True)`** — the list tells the library which ROUGE variants to
compute (it also supports `rouge1`, `rouge2`, but this script only asks for `rougeL`). `use_stemmer=True`
means words get reduced to their root form before comparing — e.g. `"accrues"` and `"accrued"` both
stem to `"accru"` — so minor grammatical differences (tense, plurals) don't count against the score.

**`_rouge.score(reference, candidate)`** returns a *dictionary* keyed by metric name. `scores["rougeL"]`
pulls out the ROUGE-L entry, which is itself an object with `.precision`, `.recall`, and `.fmeasure`
attributes. `.fmeasure` is the F1 score — the harmonic mean of precision and recall — which is the
single number this script cares about.

> **Try it yourself:**
> ```python
> >>> from rouge_score import rouge_scorer
> >>> scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
> >>> scorer.score("employees accrue fifteen days of PTO per year",
> ...               "employees earn fifteen PTO days annually")["rougeL"].fmeasure
> 0.428...  # still not high, but noticeably better than BLEU on the same pair
> ```
> Same paraphrase as before. ROUGE-L scores it higher than BLEU did, because ROUGE-L looks for the
> *longest common subsequence* (words that appear in the same relative order, but not necessarily
> consecutively) rather than requiring consecutive n-gram matches. Still lexical, still misses true
> synonyms — but more forgiving of reordering.

---

## 5. `should_score()` (lines 93–96)

```python
def should_score(row: dict) -> bool:
    """BLEU and ROUGE only make sense for in-scope rows with a reference answer."""
    qt = row.get("query_type", "").strip().lower()
    return qt in IN_SCOPE_TYPES and bool(row.get("reference_answer")) and bool(row.get("actual_answer"))
```

**`row: dict`** — a **dict** (dictionary) is Python's key-value lookup structure, like a mini
database record: `{"question": "...", "query_type": "factual", ...}`. Each row read from the CSV
becomes one dict, with the CSV's column headers as keys.

**`row.get("query_type", "")`** — `.get(key, default)` looks up a key in the dict, but instead of
crashing if the key is missing (which `row["query_type"]` would do), it returns the second argument
(`""` here) as a fallback. This is defensive against unexpected/missing CSV columns.

**`.strip().lower()`** — chained method calls: `.strip()` removes leading/trailing whitespace,
`.lower()` lowercases. Chaining just means "do this, then do that to the result" — read left to right.

**`qt in IN_SCOPE_TYPES`** — this is the set membership check mentioned earlier: "is this string one
of the four in-scope query types?"

**`bool(row.get("reference_answer"))`** — `bool()` converts a value to `True`/`False`. An empty
string becomes `False`; any non-empty string becomes `True`. So this checks "does a reference answer
actually exist and have content?"

**`and`** chains all three conditions — all must be true for the function to return `True`. This
function is the single gatekeeping decision in the whole script: *does this row get scored at all?*

---

## 6. `write_summary()` (lines 99–132)

```python
def write_summary(rows: list) -> None:
    in_scope = [r for r in rows if r.get("query_type", "").lower() in IN_SCOPE_TYPES]

    def avg(values):
        vals = [float(v) for v in values if v not in ("", "n/a", None)]
        return round(sum(vals) / len(vals), 3) if vals else None

    bleu_avg = avg(r.get("bleu_score") for r in in_scope)
    rouge_avg = avg(r.get("rouge_score") for r in in_scope)
    ...
```

**`[r for r in rows if r.get(...) in IN_SCOPE_TYPES]`** is a **list comprehension** — Python's
compact way of writing "build a new list by looping over `rows`, keeping only items that pass this
condition." It's equivalent to the longer:

```python
in_scope = []
for r in rows:
    if r.get("query_type", "").lower() in IN_SCOPE_TYPES:
        in_scope.append(r)
```

Both do exactly the same thing; the comprehension is just the idiomatic, more compact Python form
once you're comfortable reading it.

**`def avg(values):` defined *inside* `write_summary`** — a function defined inside another function
is a **nested function**. It only exists while `write_summary` is running, and it's only usable
inside `write_summary`. This is done because `avg` is a small helper that's only meaningful in this
one context — bundling it here rather than at module level signals "this isn't a general-purpose
utility, don't reuse it elsewhere."

**`[float(v) for v in values if v not in ("", "n/a", None)]`** — another list comprehension, this
time also *filtering out* placeholder values (empty string, the literal `"n/a"` written by `main()`
for skipped rows, or `None`) before converting each remaining value to a `float` (a decimal number).
`("", "n/a", None)` here is a **tuple** — like a list, but written with parentheses and conventionally
used for a small fixed group of values rather than a growing collection.

**`round(sum(vals) / len(vals), 3) if vals else None`** — another conditional expression: *"if
`vals` is non-empty, compute average and round to 3 decimals; otherwise return `None`"* (Python's
"no value" placeholder) so the summary doesn't crash trying to divide by zero if somehow every row
lacked a score.

**`avg(r.get("bleu_score") for r in in_scope)`** — note there are no square brackets here, so this
isn't a list comprehension, it's a **generator expression**: it produces values one at a time
on demand rather than building the whole list in memory first. For 60 rows the difference is
invisible, but it's why the parentheses are just `(...)` implied by the function call rather than
explicit `[...]`.

The rest of the function (lines 109–132) builds a list of formatted text lines, joins them into one
string with `"\n".join(lines)` (glue every item together with a newline between them), prints it to
the terminal, and writes it to `summary.md`. **`f"Average BLEU:      {bleu_avg if bleu_avg is not None else 'n/a'}"`**
is an **f-string** (formatted string) — the `f` prefix before the quotes means anything inside `{}`
gets evaluated and inserted into the string. This is how Python builds strings with variables mixed in,
instead of concatenating pieces with `+`.

**What this is really doing, testing-wise:** this function is why a CI run of this script produces
a human-readable regression report, not just a pile of numbers in a CSV — the averages let you spot
"did BLEU drop across the whole run?" at a glance, and the per-row table lets you drill into *which*
question regressed.

---

## 7. `main()` — where it all runs (lines 135–171)

```python
def main():
    if not os.path.exists(INPUT_FILE):
        sys.exit(f"File not found: {INPUT_FILE}\nRun run_evaluation.py first to generate results.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
```

**`os.path.exists(INPUT_FILE)`** checks the input CSV is actually there before doing anything else —
fail fast with a clear message rather than a confusing crash later.

**`os.makedirs(OUTPUT_DIR, exist_ok=True)`** creates the `results/` folder if it doesn't exist yet.
`exist_ok=True` means "don't complain if it's already there" — without that flag, `os.makedirs`
raises an error on a folder that already exists, which would be the wrong behavior here since this
script runs repeatedly.

**`with open(INPUT_FILE, ...) as f:`** — the **`with` statement** is Python's pattern for "open this
resource, do stuff with it, and guarantee it gets closed afterward — even if an error happens inside
the block." Without `with`, you'd have to remember to call `f.close()` yourself, and a crash midway
could leave the file open. This pattern (called a **context manager**) shows up any time a script
opens a file, a network connection, or similar.

**`csv.DictReader(f)`** reads the CSV and turns *each row* into a dict, using the header row as keys
— this is why `row.get("query_type")` works the way it does throughout the script: `DictReader`
already did the work of matching columns to values. **`list(...)`** around it converts the reader
(which yields rows one at a time) into an actual list held in memory, since the script needs to loop
over `rows` more than once (once in `main`, once again inside `write_summary`).

```python
    out_rows = []
    for i, row in enumerate(rows, 1):
        out_row = {
            "question": row.get("question", ""),
            ...
        }
        if should_score(row):
            out_row["bleu_score"] = bleu(row["reference_answer"], row["actual_answer"])
            out_row["rouge_score"] = rouge_l(row["reference_answer"], row["actual_answer"])
            print(f"  [{i:02d}/{total}] BLEU={out_row['bleu_score']:.3f}  ...")
        else:
            out_row["bleu_score"] = "n/a"
            out_row["rouge_score"] = "n/a"
        out_rows.append(out_row)
```

**`enumerate(rows, 1)`** loops over `rows` while also handing back a counter — `i` — starting at 1
instead of Python's default start of 0. This is purely for the human-readable progress print
(`[01/60]`, `[02/60]`, ...); it doesn't affect the scoring logic at all.

**`{i:02d}`** inside an f-string is a **format spec**: `02d` means "format this as a whole number,
padded with a leading zero to at least 2 digits" — so `1` prints as `01`, `12` prints as `12`. Similarly
`{out_row['bleu_score']:.3f}` means "format as a decimal with exactly 3 digits after the point."

**This loop is the heart of the script**: for every row, decide via `should_score()` whether it
qualifies, and either compute real BLEU/ROUGE numbers or write the string `"n/a"` as a placeholder.
Every row — scored or not — gets appended to `out_rows`, which is why the output CSV has the same
row count as the input, just with two new columns added.

```python
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[...])
        writer.writeheader()
        writer.writerows(out_rows)
```

**`csv.DictWriter`** is the mirror image of `DictReader` — given a list of dicts, it writes them out
as CSV rows, using `fieldnames` to fix the column order (dicts themselves don't guarantee order the
way a spreadsheet needs). `writeheader()` writes the column-name row first; `writerows(out_rows)`
writes every data row in one call.

Finally, `main()` calls `write_summary(out_rows)` — reusing the exact same list of results to build
the human-readable report described in section 6.

---

## 8. The entry point (lines 174–175)

```python
if __name__ == "__main__":
    main()
```

This is the single most common idiom in Python scripts, and it looks cryptic the first time you see
it. Every Python file has a hidden variable called `__name__`. When you *run* a file directly
(`python3.11 score_bleu_rouge.py`), Python sets `__name__` to the string `"__main__"`. But if this
file were instead *imported* by some other script (`import score_bleu_rouge`), `__name__` would be
set to `"score_bleu_rouge"` instead.

So this line means: *"only actually call `main()` — and start doing work — if this file was run
directly, not if it was imported as a library by something else."* It's what lets every function in
this file (`bleu`, `rouge_l`, `should_score`) be reused elsewhere without automatically re-running
the whole script the moment it's imported.

---

## Python concepts you picked up in this file

| Concept | What it means | Where it appeared |
|---|---|---|
| `import` / `try...except ImportError` | Load a library; handle it being missing gracefully | Lines 39–48 |
| List `[...]` vs. set `{...}` vs. tuple `(...)` | Ordered/mutable, unordered/unique, fixed-and-small | `IN_SCOPE_TYPES`, tuple in `avg()` |
| Function `def name(param: type) -> type:` | A reusable, named block of code with typed inputs/output (hints only, not enforced) | `bleu()`, `rouge_l()` |
| Docstring `"""..."""` | Documentation attached to a function/module | Every function |
| Conditional expression `x if cond else y` | Compact if/else that produces a value | `INPUT_FILE = args[0] if args else ...` |
| `dict.get(key, default)` | Safe dict lookup that won't crash on a missing key | `should_score()` |
| List comprehension `[x for x in y if cond]` | Compact loop-and-filter that builds a list | `in_scope = [...]` |
| Generator expression `(x for x in y)` | Like a list comprehension, but lazy (no brackets) | `avg(r.get(...) for r in in_scope)` |
| f-string `f"{var:.3f}"` | Build strings with variables/format specs inserted | Progress prints, summary lines |
| `with open(...) as f:` | Context manager — guarantees the file gets closed | Reading/writing CSVs |
| `csv.DictReader` / `DictWriter` | Read/write CSV rows as dicts keyed by column header | `main()` |
| `enumerate(iterable, start)` | Loop with an automatic counter | `main()`'s scoring loop |
| `if __name__ == "__main__":` | Only run this code if the file was executed directly | Bottom of every standalone script |

---

## What to test here

| Risk | How to catch it |
|---|---|
| Lowercasing/tokenization differences silently change scores between runs | Pin the `nltk` version in `requirements`; re-run the same input twice and confirm identical output |
| A malformed CSV row crashes the whole 60-row batch | The inner `try/except Exception` in `bleu()`/`rouge_l()` already guards this — verify with a deliberately blank `actual_answer` row |
| Someone changes `IN_SCOPE_TYPES` without updating the golden dataset's `query_type` values | Cross-check the set literals here against every distinct value in `golden-dataset.csv`'s `query_type` column |
| Averages silently exclude more rows than expected | `avg()` filters out `"", "n/a", None` — log how many rows were excluded, not just the average, to catch a mass of skipped rows going unnoticed |

## See also

- [Evaluation Metrics glossary](../concepts/glossary.md#evaluation-metrics) — what BLEU and ROUGE-L mean conceptually
- [Advanced Evaluation Metrics](../testing/advanced-evaluation-metrics.md) — BERTScore, MRR, NDCG: what completes the picture beyond BLEU/ROUGE
- [golden-dataset/first-evaluation.md](../../golden-dataset/first-evaluation.md) — how this script fits into the end-to-end evaluation run
