# Reading `ragas_eval.py` — A Code Walkthrough for Non-Coders

This doc exists for one purpose: to let you read
[`golden-dataset/ragas/ragas_eval.py`](../../golden-dataset/ragas/ragas_eval.py)
and understand *every line*, even the ones that look like black magic on first glance. It teaches
the Python syntax as it appears and ties each piece back to what it's doing for RAG testing.

This is the **most syntax-dense of the four scoring scripts** in this repo (`run_evaluation.py`,
`score_bleu_rouge.py`, `score_gptscore.py`, and this one). Make sure you've already read
[`bleu-rouge-code-walkthrough.md`](bleu-rouge-code-walkthrough.md) first — this doc assumes you're
already comfortable with `import`/`try...except`, f-strings, `csv.DictReader`/`DictWriter`,
`dict.get`, list/dict comprehensions, `enumerate`, `if __name__ == "__main__":`, `with open(...)`,
`sys.argv` file selection, `os.makedirs`, and the `load_dotenv` pattern — all covered there. Where
this file repeats one of those patterns, you'll see a short **(covered in earlier walkthroughs)**
note with a link, not a re-explanation.

This is also **not** an explanation of what Faithfulness, Answer Relevancy, Context Precision, and
Context Recall mean conceptually — that's covered in
[RAGAS Evaluation Metrics](../testing/ragas-evaluation-metrics.md) and
[Intro to RAGAS](../testing/ragas-intro.md). This doc focuses purely on *how the code computes
them* — including some genuinely unusual code that exists only because of real dependency
conflicts encountered while building this script.

## How to read this doc

Same rule as the bleu-rouge walkthrough: Python has a **definition phase** (reading `def`s and
remembering them) and an **execution phase** (`main()` actually being called at the bottom of the
file). So this walkthrough mostly follows execution order.

But there's a wrinkle in *this* file worth flagging up front: several lines near the top of the
file — before any function is even defined — run *immediately* the moment the file is loaded, not
inside `main()`. That includes command-line flag parsing, loading the `.env` file, and (most
unusually) a block that patches Python's own import system to work around a missing library
submodule. If you've only read scripts where "nothing happens until `main()` runs," this file will
feel different, and that's deliberate — it's doing setup work that has to happen before the `ragas`
library can even be safely imported.

---

## 1. Imports (lines 54–57)

```python
import csv
import math
import os
import sys
```

`csv`, `os`, and `sys` are the same standard-library modules from the bleu-rouge script (covered in
[bleu-rouge-code-walkthrough.md](bleu-rouge-code-walkthrough.md#1-imports-lines-3551)). New here:
**`math`** — a standard-library module of mathematical functions and constants. This script only
uses one thing from it, `math.isnan()`, covered in section 8 below.

---

## 2. Manual CLI flag parsing (lines 59–69)

```python
args = sys.argv[1:]
METRIC_FILTER = None
INPUT_FILE_ARG = None
for a in args:
    if a.startswith("--metrics="):
        METRIC_FILTER = a.split("=", 1)[1].split(",")
    elif not a.startswith("--"):
        INPUT_FILE_ARG = a

INPUT_FILE = INPUT_FILE_ARG or "golden-dataset/runs/run-001.csv"
```

`sys.argv[1:]` (everything typed after the script name) is the same pattern from bleu-rouge
(covered in [bleu-rouge-code-walkthrough.md](bleu-rouge-code-walkthrough.md#2-paths-and-config-lines-5363)).
What's new is that this script accepts **two different kinds of command-line argument** — a
filename (`run-002.csv`) and a flag (`--metrics=faith,rel`) — and has to tell them apart itself,
because Python doesn't do this for you automatically. That's what this `for` loop does, one
argument at a time:

- **`a.startswith("--metrics=")`** — checks whether this particular argument is the metrics flag,
  by checking whether the string starts with that literal prefix. If you ran the script with
  `python3.11 golden-dataset/ragas/ragas_eval.py --metrics=faith,rel`, then `a` would be the string
  `"--metrics=faith,rel"`, and this check would be `True`.
- **`elif not a.startswith("--"):`** — otherwise, if the argument does *not* start with `--` at
  all, it's treated as a positional filename argument instead (e.g. `runs/run-002.csv`). Anything
  that starts with `--` but *isn't* `--metrics=...` is silently ignored by this loop — there's no
  `else` branch, so an unrecognized flag like `--foo` just does nothing rather than erroring.

Now the actual splitting, worked through with the real example `"--metrics=faith,rel"`:

```python
a.split("=", 1)[1].split(",")
```

Step by step:

1. **`a.split("=", 1)`** — `.split(sep, maxsplit)` breaks a string into a list wherever `sep`
   occurs. The `1` means "split at most once" — stop after the first `=`. Verified in a real
   Python shell:
   ```python
   >>> "--metrics=faith,rel".split("=", 1)
   ['--metrics', 'faith,rel']
   ```
   Without the `1` limit, this particular string would still split the same way (there's only one
   `=`), but the `maxsplit` argument matters in general: it guards against a filename or value that
   happens to contain an `=` character somewhere later in the string, which would otherwise produce
   more than two pieces and make `[1]` (below) grab the wrong thing.
2. **`[1]`** — indexing into the resulting list, grabbing the *second* item (index `1`, since
   indexing starts at `0`) — the part *after* the `=`, which is `"faith,rel"`.
3. **`.split(",")`** — splits that string on every comma, with no limit this time, producing:
   ```python
   >>> "faith,rel".split(",")
   ['faith', 'rel']
   ```

So the full expression turns the raw string `"--metrics=faith,rel"` into the Python list
`['faith', 'rel']` — one string per metric shortcode the user asked for. This becomes
`METRIC_FILTER`, used later in `select_metrics()` (section 9).

**`INPUT_FILE = INPUT_FILE_ARG or "golden-dataset/runs/run-001.csv"`** — `or` here is Python's
short-circuit fallback: if `INPUT_FILE_ARG` is anything "truthy" (a non-empty string), use it;
otherwise (it's still `None`, because the loop never found a plain filename argument) fall back to
the default path. This is the same idea as bleu-rouge's `args[0] if args else "..."` conditional
expression, just written with `or` instead because there are now two variables involved, not one.

> **What this is really doing, testing-wise:** parsing your own CLI flags by hand (instead of using
> a library like `argparse`) is a reasonable choice for a small internal script with only one flag,
> but it's also a place bugs hide quietly — an unrecognized flag is silently swallowed rather than
> rejected. If you ever add a second flag, test what happens when a typo'd flag name is passed; this
> code won't tell you.

---

## 3. Loading `.env` (lines 76–95)

```python
def load_dotenv(path=".env"):
    here = os.path.dirname(os.path.abspath(globals().get("__file__", "")))
    repo_root = os.path.dirname(os.path.dirname(here))
    ...
```

This is the same `.env`-loading pattern used by `score_gptscore.py` (covered in that walkthrough) —
read the file line by line, skip comments and blanks, and set each `KEY=value` pair into
`os.environ` if it isn't already set. The one detail worth calling out here is *why* it walks up
two directory levels (`os.path.dirname` twice) to find `repo_root`: this script lives two folders
down from the repo root (`golden-dataset/ragas/ragas_eval.py`), so it needs to climb back up
(`ragas/` → `golden-dataset/` → repo root) to find the `.env` file sitting at the top level,
regardless of what directory you happen to run the script from.

---

## 4. The compatibility shim (lines 97–110)

This is the strangest-looking block in the whole file, and it's worth slowing down for, because
it's real, hard-won engineering, not a syntax trick for its own sake. Read the comment already
above it in the file first:

```python
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
```

**The problem this solves:** the `ragas` library (version 0.4.x, which this script targets) has
some internal code that, when it starts up, tries to `import langchain_community.chat_models.vertexai`
— the module for Google's VertexAI chat models — purely so it can add `ChatVertexAI` to a list of
"known LLM types" it checks against internally. It never actually *uses* VertexAI unless you ask it
to. But newer releases of `langchain-community` removed that submodule entirely (Google's VertexAI
integration moved to its own separate package). So on a fresh install, `ragas` crashes on import —
not because of anything this project does, but because two libraries it depends on have drifted out
of sync with each other. This project never uses VertexAI or Google's SDK at all, so the fix doesn't
need to install anything real — it just needs to make Python *believe* the import succeeded.

**`import sys as _sys`** — `as` renames an import; this creates a variable called `_sys` that
refers to the `sys` module, instead of the usual name `sys`. Why bother renaming it, when `sys` is
already imported at the top of the file (line 57)? Because both names point to the exact same
module object — the rename here is purely a *readability* signal: the leading underscore marks
`_sys` and `_types` (below) as "internal plumbing used only by this one shim block," visually
distinct from the `sys` used everywhere else in the file for normal argument parsing and
`sys.exit()`. It's the same underscore convention as `_rouge` in the bleu-rouge script.

**`_types.ModuleType(name)`** — this is the key trick. `types.ModuleType` is the class that
*every* Python module is secretly an instance of. When you write `import os`, Python builds an
object of this exact type behind the scenes and hands it to you as `os`. Calling `ModuleType(name)`
directly does the same construction manually — it manufactures a brand new, empty module object out
of thin air, with the given name, containing nothing yet. `_stub` is now a real module object; it
just doesn't have any of the real VertexAI code inside it (because there isn't any real code — the
submodule doesn't exist anymore).

**`_stub.ChatVertexAI = type("ChatVertexAI", (), {})`** — this is the three-argument form of
Python's built-in `type()` function, and it's genuinely one of the more mind-bending things in the
language the first time you see it: **`type()` can create a new class, at runtime, as an
expression**, instead of you writing a `class` statement. The three arguments are:

1. `"ChatVertexAI"` — the name of the new class.
2. `()` — an empty tuple of base classes (nothing it inherits from).
3. `{}` — an empty dict of attributes/methods to put on it.

This line is *exactly* equivalent to writing, elsewhere in the file:

```python
class ChatVertexAI:
    pass
```

The reason this matters conceptually: in Python, **classes are themselves just objects** — the same
way `5` is an `int` object and `"hi"` is a `str` object, `ChatVertexAI` (whether written with `class`
or built with `type()`) is an object of type `type`. Normally you build class-objects with the
`class` keyword because you know what you want up front. But when you need to build one
*programmatically* — here, because the real class doesn't exist and you just need *something* that
satisfies "there is a class called `ChatVertexAI`" — `type(name, bases, namespace)` is how you do it
without a `class` statement. Verified directly in a Python shell:

```python
>>> Foo = type("Foo", (), {})
>>> Foo
<class '__main__.Foo'>
>>> f = Foo()
>>> f
<__main__.Foo object at 0x103b19410>
>>> isinstance(f, Foo)
True
```

It behaves exactly like a normal empty class — it can be instantiated, checked with `isinstance`,
and so on. `ragas`'s internal type-check list never actually instantiates it or calls any methods on
it (remember: it only ever checks "is this in the list of known types," it never calls VertexAI for
real), so an empty, do-nothing class is a perfectly sufficient stand-in.

**`_sys.modules[name] = _stub`** — this is the last piece, and it's what makes the whole trick
work. Python keeps a dictionary, `sys.modules`, of every module it has ever successfully imported in
this process, keyed by name (`sys.modules["os"]`, `sys.modules["csv"]`, etc.). Whenever *any* code,
anywhere, writes `import langchain_community.chat_models.vertexai`, Python's very first move is to
check `sys.modules` for that name — and if it's already there, Python just hands back the existing
object instead of going to disk to find and load the real file. By manually inserting the fake
`_stub` module under that exact name, this line pre-empts the real import: the next time `ragas`
(or anything else) tries to import that submodule, Python finds the fake entry already sitting in
`sys.modules` and is satisfied — it never tries to load the real (now-missing) file at all.

**Why the `try/except ModuleNotFoundError` around all of this** — the shim only *installs* the fake
module if the real one genuinely can't be found. On an older `langchain-community` version where
the real submodule still exists, the `import` on line 106 succeeds outright, the `except` block
never runs, and `ragas` gets the real thing. This makes the whole file work correctly across both
old and new `langchain-community` versions, not just the broken one.

> **Why this exists, in one sentence:** a downstream library (`ragas`) imports a submodule that an
> upstream library (`langchain-community`) quietly deleted, purely to populate a list it never
> actually needs for this project's usage — and since this project never touches Google's VertexAI,
> a harmless three-line fake module satisfies the import without installing Google's SDK just to
> throw it away. This was one of three upstream bugs found and fixed while porting this script from
> the old pinned `ragas<0.2` API to current RAGAS 0.4.x (see `golden-dataset/findings.md` for the
> others). This is what real-world dependency archaeology looks like — reading a traceback back to
> its root cause instead of just pinning an older version and moving on.

---

## 5. The ragas/langchain import block (lines 112–135)

```python
try:
    from ragas import evaluate
    from ragas.dataset_schema import EvaluationDataset
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.llms import llm_factory
    from langchain_community.embeddings import HuggingFaceEmbeddings as LCHuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
except ImportError as e:
    sys.exit(f"Missing dependency: {e}\nRun: pip install ragas sentence-transformers anthropic")
```

The `try/except ImportError` wrapper is the same defensive pattern from bleu-rouge (covered in
[bleu-rouge-code-walkthrough.md](bleu-rouge-code-walkthrough.md#1-imports-lines-3551)) — fail with a
helpful message instead of a raw traceback. This block only runs *after* the shim above has already
run, which is exactly why the shim has to come first in the file: if `ragas` were imported before
the shim installed the fake `vertexai` module, `ragas`'s own internal import would crash here with
`ModuleNotFoundError` before this `try` even gets a chance to catch anything useful.

Two things new here worth naming explicitly:

**`from langchain_community.embeddings import HuggingFaceEmbeddings as LCHuggingFaceEmbeddings`** —
another `as`-rename, this time for a real reason (not just readability): the local variable name
`LCHuggingFaceEmbeddings` ("LC" for LangChain) distinguishes this specific class from RAGAS's *own*
class of a similar name, referenced in the comment above this block:

```python
# ragas.embeddings.HuggingfaceEmbeddings (the legacy, sync-only wrapper that would
# otherwise match the answer_relevancy/faithfulness metrics used below) ships
# incomplete in ragas 0.4.3 — it never implements the required aembed_query/
# aembed_documents methods, so it can't even be instantiated. Instead we use
# LangChain's own local HuggingFace embeddings class (which gets working async
# methods for free via LangChain's base Embeddings executor default) and adapt it
# with ragas's LangchainEmbeddingsWrapper.
```

This is the second of the three upstream bugs mentioned above: RAGAS ships its *own*
`HuggingfaceEmbeddings` class meant for exactly this use case, but in the version this script
targets, that class is missing methods it needs (`aembed_query`/`aembed_documents` — the `a`
prefix means "async version") and simply can't be used. The fix swaps in LangChain's own
well-maintained local-embeddings class instead.

**`LangchainEmbeddingsWrapper`** — this is an **adapter** (also called a *wrapper*), a very common
pattern any time two libraries need to talk to each other but weren't built with each other in
mind. In plain terms: RAGAS's `evaluate()` function expects to be handed an object that speaks
"RAGAS's embeddings interface" — a specific set of method names and signatures it knows how to call.
LangChain's `HuggingFaceEmbeddings` object speaks "LangChain's embeddings interface" instead — a
*different* set of method names that happen to do the same underlying job (turn text into vectors).
`LangchainEmbeddingsWrapper` is a small class, provided by RAGAS itself, whose entire job is to take
a LangChain-shaped embeddings object and dress it up so it *looks like* a RAGAS-shaped one from the
outside — every call RAGAS makes to it gets internally forwarded to the real LangChain object. You
don't need to understand either library's actual interface to get the idea: an adapter is a
translator standing between two objects that don't speak the same "shape" of API, so each side only
ever has to know its own language. You'll see this instantiated in section 12 below.

---

## 6. API key check (lines 137–143)

```python
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_KEY or "your-key" in ANTHROPIC_KEY:
    sys.exit(...)
```

Same pattern as `score_gptscore.py` — read the key from the environment (populated by
`load_dotenv()` above), and refuse to continue with a clear message if it's missing or still the
placeholder text from a template `.env` file. Nothing new syntactically here.

---

## 7. Row filters and `parse_chunks()` (lines 145–161)

```python
OUT_OF_SCOPE_TYPES = {"out-of-scope", "fictitious-entity", "adversarial"}
IN_SCOPE_TYPES = {"factual", "paraphrase", "multi-hop", "comparative"}


def parse_chunks(pipe_separated: str) -> list:
    if not pipe_separated:
        return []
    return [c.strip() for c in pipe_separated.split("|") if c.strip()]
```

The two sets and the "empty-string guard, then list comprehension" shape are the same patterns from
bleu-rouge (covered there). `parse_chunks()` reverses whatever `run_evaluation.py` did to store
multiple retrieved chunks in a single CSV cell — the chunks were joined with `|` characters to fit
in one column, so this splits them back apart into a Python list of strings, trimming whitespace
and dropping any empty pieces. RAGAS needs `retrieved_contexts` as an actual list, not a
pipe-joined string, which is exactly what this function produces for use in the next section.

---

## 8. Building the RAGAS dataset (lines 164–198)

```python
def build_ragas_dataset(rows: list) -> tuple:
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
```

The loop itself is ordinary — `enumerate`, `.get()` with defaults, `continue` to skip a row that
fails a check (a `continue` jumps straight to the next loop iteration, skipping everything below it
for that row) — all covered in earlier walkthroughs. Two things are new:

**`original_indices.append(i)`** alongside building `samples` — this script keeps a *second* list,
in lockstep with `samples`, recording which row number in the *original* CSV each sample came from.
This matters because RAGAS is only given the *filtered* subset (in-scope rows with a non-empty
answer and at least one retrieved chunk) — out-of-scope and empty rows never make it into `samples`
at all. Once RAGAS scores that filtered subset, the code needs a way to map "RAGAS's 3rd result"
back to "row 47 in the original 60-row CSV" — that's exactly what `original_indices` is for, and
you'll see it used for that purpose in section 12.

**`EvaluationDataset.from_list(samples)`** — this is the same *adapter* idea as
`LangchainEmbeddingsWrapper`, just in data form rather than object form: `samples` is a plain
Python list of plain Python dicts — nothing RAGAS-specific about it. `EvaluationDataset.from_list()`
is RAGAS's front door for "convert my own data into the shape I expect for evaluation." Each dict in
the list must use RAGAS's exact expected key names — `user_input`, `response`, `retrieved_contexts`,
`reference` — because that's the contract `EvaluationDataset.from_list()` documents; get a key name
wrong and RAGAS either errors or silently treats a field as missing. This is a very common pattern
when working with any external library: you build your data in your own natural shape (here, CSV
rows read by `csv.DictReader`), then convert it, at the boundary, into whatever shape the library's
constructor demands — rather than trying to make your own data structures match the library's
shape from the start.

---

## 9. The dict-of-functions metric registry (lines 201–228)

```python
ALL_METRICS = {
    "faith": faithfulness,
    "rel": answer_relevancy,
    "prec": context_precision,
    "rec": context_recall,
}
```

This looks like an ordinary dict of strings mapping to... other things. The important thing to
notice is *what kind of thing* the values are: `faithfulness`, `answer_relevancy`,
`context_precision`, and `context_recall` are the exact same names imported from `ragas.metrics` on
line 118 — they are RAGAS **metric objects** (pre-built instances RAGAS ships, each one knowing how
to score one dimension of a RAG answer). They are *not* being called here (there's no `()` after
any of them) — they're being stored, as-is, as dict values, the same way you could store a string or
a number as a dict value. In Python, functions and objects are "first-class values" — anything you
can do with a number (assign it to a variable, put it in a list, put it in a dict) you can also do
with a function or an object, including one imported from a library. This dict is simply a lookup
table from a short human-typed string (`"faith"`) to the actual heavyweight object RAGAS needs
(`faithfulness`).

```python
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
```

This function is the payoff of the whole flag-parsing exercise in section 2. If the user passed
`--metrics=faith,rel`, `METRIC_FILTER` is `['faith', 'rel']` (from section 2's walkthrough); this
loop looks up each shortcode in `ALL_METRICS` and collects the *actual metric objects* (not the
strings) into `selected`. If the user typed a shortcode that doesn't exist (e.g. `--metrics=faitH` —
a typo), `key not in ALL_METRICS` catches it and exits with a helpful list of valid options rather
than silently skipping it or crashing deep inside RAGAS later. If no `--metrics=` flag was given at
all, `METRIC_FILTER` is still `None` (falsy), so the function falls through to
`list(ALL_METRICS.values())` — every metric object in the dict, i.e. "run all four by default."

---

## 10. `write_summary()` and `math.isnan()` (lines 234–284)

Most of `write_summary()` — building a list of formatted lines, list comprehensions, `.join()`,
`with open(...) as f:` — mirrors the bleu-rouge summary function (covered in that walkthrough,
[section 6](bleu-rouge-code-walkthrough.md#6-write_summary-lines-99132)). Two new patterns appear
here.

**Set comprehension (line 261):**

```python
types = sorted({r.get("query_type", "") for r in rows_with_scores if r.get("query_type")})
```

The `{...}` here — curly braces, same as a list comprehension's square brackets but with braces
instead — builds a **set**: every distinct, non-empty `query_type` value found across all the
scored rows, with duplicates automatically collapsed (a set can't contain the same value twice).
This is the same underlying idea as the list comprehension `[r for r in rows if ...]` from
bleu-rouge, just producing a set instead of a list — you'd choose a set here specifically because
you don't want 60 rows' worth of repeated `"factual"`, `"factual"`, `"factual"` in your result, you
want each query type to appear exactly once.

**`sorted(...)` wrapping it:** a set has no guaranteed order — asking Python for its contents twice
in a row isn't promised to give you the same order both times. Since this list drives the order the
"By Query Type" sections get printed in the summary report, wrapping the set in `sorted()` converts
it back into an ordered list (alphabetical, since these are strings) so the report prints
`"comparative"`, then `"factual"`, then `"multi-hop"`, then `"paraphrase"` in the same order every
single time the script runs — a small but real detail for a regression report you're diffing
between runs.

**`math.isnan(fv)` (lines 251 and 272):**

```python
v = r.get(col, "")
try:
    fv = float(v)
    if not math.isnan(fv):
        vals.append(fv)
except (ValueError, TypeError):
    pass
```

RAGAS can fail to score a particular row for a particular metric — say, the judge LLM's response
couldn't be parsed for that one row — and rather than leaving the cell blank, it can write the
special floating-point value **NaN** ("Not a Number") into the result. NaN is a real, valid `float`
value in Python (and in almost every programming language) that specifically means "the result of
this calculation is undefined," not "this cell is empty." That distinction is exactly why this code
can't just check for blank strings and call it a day — verified directly:

```python
>>> float("nan")
nan
>>> float("nan") == float("nan")
False
>>> import math
>>> math.isnan(float("nan"))
True
```

`float("nan")` parses *successfully* — it doesn't raise an error the way `float("abc")` would — so a
naive filter like `if v not in ("", "n/a")` (the bleu-rouge script's filter, which never needs to
worry about NaN because BLEU/ROUGE never produce it) would let a NaN value straight through into the
list being averaged. And NaN has a genuinely strange property baked into the IEEE floating-point
standard: **`nan == nan` is `False`**. NaN isn't even equal to itself. That means you can't reliably
filter it out with an equality check (`if v != v` technically *would* detect it, using that very
quirk, but it reads as a bug to anyone unfamiliar with it) — you need the dedicated
`math.isnan()` function, which is built specifically to answer "is this float NaN?" correctly. This
script does exactly that: computes `fv = float(v)`, then only appends it to `vals` if
`not math.isnan(fv)` — silently NaN-poisoned rows are excluded from the average rather than
corrupting it (averaging in a NaN would make the *entire* average print as `nan`, silently, since
any arithmetic involving NaN produces NaN). A naive string filter that only excludes `""` and `"n/a"`
would let the string `"nan"` parse straight through and quietly poison an average — which is
precisely the footgun `math.isnan()` avoids here.

---

## 11. Loading the input CSV in `main()` (lines 290–304)

```python
def main():
    if not os.path.exists(INPUT_FILE):
        sys.exit(...)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        base_fieldnames = reader.fieldnames or []
```

All of this — the existence check, `os.makedirs(..., exist_ok=True)`, `with open(...)`,
`csv.DictReader` — is the same pattern from bleu-rouge (covered in that walkthrough,
[section 7](bleu-rouge-code-walkthrough.md#7-main--where-it-all-runs-lines-135171)). The one new
detail is **`reader.fieldnames`** — after a `csv.DictReader` is created, it exposes the column
headers it read from the CSV's first row as a list, e.g. `["question", "query_type", ...]`. This
script saves that list as `base_fieldnames` because it needs it later, when writing the output CSV,
to know which columns already existed *before* this script adds its own four new `ragas_*` columns
(see section 13).

---

## 12. Setting up the judge LLM and embeddings (lines 306–332)

```python
metrics = select_metrics()
metric_names = [m.name for m in metrics]
```

`[m.name for m in metrics]` — a list comprehension pulling the `.name` attribute off each metric
*object* (recall from section 9 these are real RAGAS objects, not strings) — this is purely so the
`print()` right after it can show something readable like `Metrics: faithfulness, answer_relevancy`
instead of printing the raw Python objects.

```python
ragas_dataset, original_indices = build_ragas_dataset(rows)
```

This is Python's **tuple unpacking** — `build_ragas_dataset()` (section 8) returns a tuple of two
values, `(dataset, original_indices)`, and this single line assigns the first item to
`ragas_dataset` and the second to `original_indices` in one step.

```python
judge_llm = llm_factory("claude-haiku-4-5-20251001", provider="anthropic", client=Anthropic(api_key=ANTHROPIC_KEY))
judge_llm.model_args.pop("top_p", None)
local_embeddings = LangchainEmbeddingsWrapper(
    LCHuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
)
```

**`llm_factory(...)`** is RAGAS's own helper for building an LLM object it knows how to drive as a
judge, here configured to use Claude (via the `Anthropic(...)` client, the same SDK object used in
`score_gptscore.py`) instead of RAGAS's OpenAI default.

**`judge_llm.model_args.pop("top_p", None)`** — the comment directly above this line explains the
*why*: "Anthropic's API rejects requests that set both `temperature` and `top_p`, but ragas's
`InstructorModelArgs` defaults both." RAGAS's `llm_factory` builds `judge_llm` with a dict of
default generation settings attached at `judge_llm.model_args` — and that dict, by default, includes
both `temperature` and `top_p`. Anthropic's Claude API, unlike some other providers, refuses a
request that specifies both at once (it wants you to pick one knob, not two). **`dict.pop(key,
default)`** removes `key` from a dict and returns its value — but *if the key isn't there at all*,
instead of crashing (which plain `del some_dict[key]` or `some_dict[key]` would do on a missing
key), it just returns the `default` you supplied (`None` here) and moves on quietly. So this line
reads as: *"remove `top_p` from the judge's settings if it's there; if it's somehow already absent,
don't crash, just continue."* It's a one-line surgical fix for a mismatch between what RAGAS
configures by default and what Anthropic's API will actually accept.

**`LangchainEmbeddingsWrapper(LCHuggingFaceEmbeddings(...))`** — this is the adapter from section 5
actually being *used*: a `LCHuggingFaceEmbeddings` object (LangChain's local
`sentence-transformers`-backed embedding model, downloaded once and run entirely on your own
machine — no OpenAI key, no per-call API cost) gets wrapped so that RAGAS's `evaluate()` call below
can use it as if it were a native RAGAS embeddings object.

```python
result = evaluate(ragas_dataset, metrics=metrics, llm=judge_llm, embeddings=local_embeddings)
result_df = result.to_pandas()
```

**`evaluate(...)`** is the actual RAGAS entry point — it runs every selected metric against every
sample in `ragas_dataset`, calling the judge LLM and the embedding model as needed, and returns a
`result` object holding all the scores.

**`result.to_pandas()`** — this is this script's first use of **pandas**, a very widely used Python
library for working with tabular data (think: a spreadsheet you can manipulate in code). RAGAS's
native result object isn't a plain list or dict — it's its own type — but it offers this one
convenience method to convert itself into a pandas **DataFrame**: a table-shaped object, with rows
and named columns, that's easy to slice, filter, and pull individual cells out of. That's exactly
what the next section needs to do.

---

## 13. Mapping RAGAS scores back onto the original rows (lines 334–348)

```python
for col in result_df.columns:
    if col not in ("user_input", "response", "retrieved_contexts", "reference"):
        canonical = METRIC_COL_NAMES.get(col, f"ragas_{col}")
        for df_idx, row_idx in enumerate(original_indices):
            val = result_df.at[df_idx, col]
            rows[row_idx][canonical] = round(float(val), 4) if val is not None else ""
```

**`result_df.columns`** — every DataFrame carries a list of its column names (here, the four
metric names like `"faithfulness"`, plus the original input columns `user_input`/`response`/etc.
that RAGAS keeps around for reference). The `if col not in (...)` skips those input columns — this
script only wants to copy across the *score* columns, not duplicate the question/answer/context data
that's already in the original CSV.

**`result_df.at[df_idx, col]`** — this is the pandas idiom for pulling exactly **one single cell**
out of a table: "give me the value at row `df_idx`, column `col`." `.at[]` is deliberately narrow —
it only ever gets or sets one cell at a time, by an exact row/column pair, which makes it fast and
unambiguous compared to pandas' more general (and more complex) slicing syntax. Read it as: "look up
this one cell, the way you'd click a single cell in a spreadsheet by its row number and column
header."

**Why the nested loop with `enumerate(original_indices)`:** this is where `original_indices` (built
back in section 8) earns its keep. `result_df` only has rows for the *filtered* subset RAGAS
actually scored — `df_idx` (0, 1, 2, ...) is that subset's own internal row numbering, which has
nothing to do with row numbers in the original 60-row CSV. `original_indices[df_idx]` translates
"RAGAS's row 3" back into "row 47 of the original CSV" (`row_idx`), and `rows[row_idx][canonical] =
...` writes the score directly onto that original row's dict, under a human-readable column name
like `ragas_faithfulness` (looked up via `METRIC_COL_NAMES`, or built on the fly with the f-string
`f"ragas_{col}"` if it's a metric name not in that lookup table).

The remaining lines (342–348) fill in `"n/a"` for every row that was *never* sent to RAGAS at all
(out-of-scope rows, or in-scope rows missing an answer or chunks) — the same "every row gets a
value, scored or not" discipline the bleu-rouge script uses, so the output CSV always has the same
row count as the input.

---

## 14. Writing the output and calling `write_summary()` (lines 350–358)

```python
new_fieldnames = list(base_fieldnames) + [c for c in ragas_new_cols if c not in base_fieldnames]
with open(OUTPUT_SCORES, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=new_fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
```

`csv.DictWriter` is the same pattern as bleu-rouge — the only new detail is
**`extrasaction="ignore"`**: by default, `DictWriter` raises an error if a row-dict contains a key
that *isn't* in `fieldnames`. Since `rows` still carries every original CSV column plus whatever the
script added, `extrasaction="ignore"` tells it to simply skip writing any dict key that isn't listed
in `new_fieldnames`, rather than crashing over columns this script doesn't care about writing back
out.

`main()` finishes by calling `write_summary(rows, scored_indices)` — reusing the exact same list of
scored rows to build the human-readable report described in section 10.

---

## 15. The entry point (lines 361–362)

```python
if __name__ == "__main__":
    main()
```

Same idiom as every other script in this repo (covered in
[bleu-rouge-code-walkthrough.md](bleu-rouge-code-walkthrough.md#8-the-entry-point-lines-174175)) —
only run `main()` if this file was executed directly, not if it's imported elsewhere.

---

## Python concepts you picked up in this file

*(Concepts already covered in the bleu-rouge walkthrough — `import`/`try...except`, f-strings,
`csv.DictReader`/`DictWriter`, `dict.get`, list comprehensions, `enumerate`, `if __name__ ==
"__main__":`, `with open(...)`, `sys.argv`, `os.makedirs`, `load_dotenv` — are not repeated below.)*

| Concept | What it means | Where it appeared |
|---|---|---|
| `str.split(sep, maxsplit)` | Break a string into a list at each occurrence of `sep`, stopping after `maxsplit` splits if given | `a.split("=", 1)[1].split(",")` |
| `import x as y` (aliasing) | Give an imported module a different local name | `import sys as _sys`, `import types as _types` |
| `types.ModuleType(name)` | Manufacture a real, empty Python module object programmatically | The compatibility shim |
| `type(name, bases, namespace)` | The 3-argument form of `type()` — dynamically builds a new class at runtime, equivalent to a `class` statement | `type("ChatVertexAI", (), {})` |
| `sys.modules` dict manipulation | Python's cache of every imported module; inserting a fake entry pre-empts a real import | `_sys.modules[name] = _stub` |
| Adapter / wrapper classes | Dressing up one library's object so it satisfies another library's expected interface | `LangchainEmbeddingsWrapper`, `EvaluationDataset.from_list()` |
| Dict of functions/objects as values | Functions and objects are first-class values — a dict can map names to callables/objects, not just to strings/numbers | `ALL_METRICS = {"faith": faithfulness, ...}` |
| `dict.pop(key, default)` | Remove a key if present and return its value; return `default` instead of crashing if the key is missing | `judge_llm.model_args.pop("top_p", None)` |
| Tuple unpacking | Assign multiple return values from a function in one line | `dataset, original_indices = build_ragas_dataset(rows)` |
| Set comprehension `{x for x in y}` | Like a list comprehension, but builds a set (unique, unordered) | `{r.get("query_type", "") for r in rows_with_scores ...}` |
| `sorted(some_set)` | Convert an unordered set into a deterministic, ordered list | `sorted({...})` in `write_summary()` |
| `math.isnan(x)` | Correctly detect the special float value NaN, which is not equal to itself (`nan == nan` is `False`) | Score-averaging loops in `write_summary()` |
| pandas `DataFrame` / `.to_pandas()` | Convert a library's custom result object into a table-shaped structure for easy access | `result.to_pandas()` |
| pandas `.at[row, col]` | Get/set exactly one cell in a DataFrame by row index and column name | `result_df.at[df_idx, col]` |

---

## What to test here

| Risk | How to catch it |
|---|---|
| The compatibility shim only patches the *one* missing submodule (`chat_models.vertexai`) it knows about today — a future `ragas` or `langchain-community` release could drop or rename a *different* submodule and this script would crash again with a fresh `ModuleNotFoundError` the shim doesn't cover | Pin `ragas` and `langchain-community` versions in requirements; when bumping either, re-run this script once in a clean environment before trusting it in CI |
| NaN scores are silently excluded from averages (`math.isnan` filter) rather than surfaced as a scoring failure worth investigating — a row that RAGAS couldn't judge at all looks identical, in the summary, to a row that was never in scope | Log a count of excluded/NaN rows per metric alongside the average, not just the average itself, so a spike in unscoreable rows doesn't go unnoticed |
| The local embedding model (`sentence-transformers/all-MiniLM-L6-v2`) can be updated by its maintainers between runs, silently changing Answer Relevancy scores without any code in this repo changing | Pin the `sentence-transformers` package version; if Answer Relevancy shifts between runs with no other change, check whether the embedding model itself was re-downloaded or updated |
| `judge_llm.model_args.pop("top_p", None)` assumes `top_p` is the only conflicting default — if RAGAS's `InstructorModelArgs` defaults change to add another Anthropic-incompatible setting, this one-line fix won't catch it | Run this script once after any `ragas` version bump and confirm it completes without an Anthropic 400-error about incompatible parameters |
| An unrecognized `--` flag (a typo, e.g. `--metric=faith` missing the `s`) is silently ignored rather than rejected, so the script quietly falls back to scoring all four metrics instead of erroring | Manually test a deliberately misspelled flag and confirm the behavior is what you expect, since there's no test coverage forcing this today |

## See also

- [RAGAS Evaluation Metrics](../testing/ragas-evaluation-metrics.md) — what Faithfulness, Answer
  Relevancy, Context Precision, and Context Recall mean conceptually
- [Intro to RAGAS](../testing/ragas-intro.md) — the RAGAS framework overview and how it fits this
  project's testing strategy
- [golden-dataset/findings.md](../../golden-dataset/findings.md) — the actual evaluation results
  this script produced, including the three upstream bugs fixed while porting to RAGAS 0.4.x
- [bleu-rouge-code-walkthrough.md](bleu-rouge-code-walkthrough.md) — the companion walkthrough for
  `score_bleu_rouge.py`, covering the foundational Python syntax this doc builds on

