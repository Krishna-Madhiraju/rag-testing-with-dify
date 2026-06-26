# RAG Testing Toolkit — the three levels and the tools behind them

The companion to [RAG Testing Scenarios](rag-testing-scenarios.md). Every scenario in that doc is tagged with how you'd realistically test it — **Manual**, **Scripted**, or **Eval tooling**. This doc explains what those levels mean, what tools sit under each, how to set them up, and — the question everyone actually asks — *which tool should I use when?*

The short version: a functional tester can own far more of RAG testing than people expect. You only reach for the heavier tooling when you need to *measure quality across many answers*, which is the one thing human eyeballing can't do reliably.

---

## The three levels at a glance

| Level | What it is | Who owns it | Tools |
|---|---|---|---|
| **Manual** | Testing by hand through a UI. Ask, look, judge. | Functional tester, no coding | Dify Retrieval Testing panel, chat preview |
| **Scripted** | Light Python automation against an API or the vector store | Technical tester | Dify API + `requests`/`pytest`, Weaviate client |
| **Eval tooling** | Frameworks that *score* answer quality at scale | Tester + framework | RAGAS (primary), DeepEval, Promptfoo, TruLens |

The levels build on each other. You usually start manual to understand a failure, script it to make it repeatable, then add eval tooling when you need numbers instead of opinions.

---

## Level 1 — Manual (functional tester, no code)

This is where most exploring happens, and it needs nothing but Dify in a browser.

### Dify's Retrieval Testing panel

The single most useful manual tool. It tests **retrieval on its own**, without the LLM in the way — so you can see exactly what the vector search returns before generation muddies the picture.

How to open it:
1. Go to **Knowledge** in the left sidebar and open a Knowledge Base.
2. Click the **Retrieval Testing** icon.
3. Type a query into the source-text box and click **Test**.
4. Read the **retrieved chunks** on the right. Each chunk shows a **match score** — how closely it matched your query.

You can also click the settings icon to change the retrieval method and parameters (Top-K, similarity threshold, hybrid vs semantic) *for that test session only*, which is perfect for "what happens if I bump Top-K?" experiments without rebuilding anything.

**What you can catch here with no code:**
- Garbled chunks from a bad parser (you're reading the raw chunk text — Q5).
- The wrong chunks coming back, or nothing at all (Q3, Q11).
- Old content still retrievable after an update (Q1).
- Weak match scores on out-of-scope queries (Q13).

### The chat preview

The full pipeline — retrieval **plus** the LLM's answer. Use it to check end-to-end behaviour: does the model refuse when it should (Q13), stay grounded (Q2), keep its format (Q2), resist a planted instruction (Q15)?

**Manual testing's ceiling:** it's perfect for *finding* problems and judging a handful of answers. It can't tell you "faithfulness dropped 12% across 50 questions" — for that you need to count, which means going up a level.

---

## Level 2 — Scripted (technical tester, light Python)

When manual checking won't scale — hundreds of documents, a 50-question regression set, a daily freshness probe — you automate it. No evaluation framework yet; just Python talking to Dify or Weaviate.

### Talking to the Dify API

Dify exposes a REST API. Run a list of questions in a loop and inspect what comes back:

```python
import requests

DIFY_API = "http://localhost/v1"
APP_KEY  = "app-xxxxxxxx"   # App → API Access → API Key

def ask(query: str) -> dict:
    resp = requests.post(
        f"{DIFY_API}/chat-messages",
        headers={"Authorization": f"Bearer {APP_KEY}"},
        json={
            "query": query,
            "response_mode": "blocking",
            "user": "test-runner",
            "inputs": {},
            "conversation_id": "",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()

# Run a whole question set
questions = ["What is the refund window?", "How many days of notice are required?"]
for q in questions:
    answer = ask(q)["answer"]
    print(f"Q: {q}\nA: {answer}\n")
```

This is the backbone of the **coverage set** (Q3), the **freshness probe** (Q4), and the **consistency check** (Q10 — ask the same question five times, compare answers).

### Querying Weaviate directly

For anything about *the index itself* — did chunks get created, how many, what's their metadata — go straight to the vector store. This is how you run the **ingestion audit** (Q3), the **chunk-count check** after an update (Q1), and **duplicate detection** for overlap (Q8).

```python
import weaviate   # pip install weaviate-client

client = weaviate.connect_to_local()   # Dify's default Weaviate

# Count chunks for a given source document
collection = client.collections.get("Vector_index_xxxxx")   # Dify names it per knowledge base
count = 0
for obj in collection.iterator():
    if obj.properties.get("document_id") == "the-doc-id":
        count += 1
print(f"Chunks for document: {count}")

client.close()
```

> The exact collection name and property keys depend on your Dify version — open the Weaviate schema once to see what's there, then script against it.

### pytest as the harness

Since you prefer pytest, wrap these checks as test functions so they pass/fail cleanly and slot into CI later (Q17):

```python
def test_document_indexed():
    assert chunk_count("the-doc-id") > 0, "Document produced no chunks"

def test_out_of_scope_refuses():
    answer = ask("Who won the 2026 World Cup?")["answer"].lower()
    assert any(p in answer for p in ["don't know", "no information", "not in"]), \
        "System answered an out-of-scope question instead of refusing"
```

**Scripted testing's ceiling:** it can check *facts* (chunk exists, answer contains a string, response is deterministic). It can't judge *quality* — "is this answer faithful to the context?" is a judgement call a string match can't make. That's the next level.

---

## Level 3 — Eval tooling (scoring quality at scale)

When you need to measure things like faithfulness or relevance across a whole dataset, you need a scoring model, not a human and not a string match. This is what RAGAS and friends do.

### RAGAS — your primary RAG metric engine

[RAGAS](https://docs.ragas.io) is the most widely used open-source RAG-evaluation library, and it's the right default here: it's lightweight, RAG-specific, and some of its metrics need no "correct answer" to compare against.

**The four core metrics:**

| Metric | Plain-language question it answers | Needs a reference answer? |
|---|---|---|
| **Faithfulness** | Is the answer backed by the retrieved chunks, or did the model make it up? | No — just needs the answer + chunks |
| **Answer relevancy** | Does the answer actually address the question that was asked? | No |
| **Context precision** | Of the chunks we retrieved, how many were actually useful? | Yes (or reference chunks) |
| **Context recall** | Of the chunks we *needed*, how many did retrieval actually find? | Yes |

Because **faithfulness** and **answer relevancy** don't need a labelled "right answer," you can run them on live production logs (question + chunks + answer). **Context precision/recall** need a golden dataset (Q16) with reference answers or known-good chunks.

**Install (verified current as of early 2026):**

```bash
pip install ragas
# RAGAS calls an LLM to do the judging — set the judge model's key
export OPENAI_API_KEY=sk-...
```

**A minimal first score** — does this answer stay faithful to its context?

```python
import asyncio
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import Faithfulness
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI

# The judge model that does the scoring
judge = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))

sample = SingleTurnSample(
    user_input="What is the refund window?",
    response="You can return items within 30 days of purchase.",
    retrieved_contexts=[
        "Our refund policy allows returns within 30 days of purchase.",
    ],
)

faithfulness = Faithfulness(llm=judge)
score = asyncio.run(faithfulness.single_turn_ascore(sample))
print(f"Faithfulness: {score:.2f}")   # ~1.0 = fully grounded; near 0 = invented
```

To score a whole golden dataset at once, collect samples into an `EvaluationDataset` and call `evaluate()` with the metrics you want — that's the version you wire into the CI faithfulness gate (Q17).

**Reasonable starting thresholds** (commonly cited RAGAS benchmarks — but measure your own baseline and gate relative to it):

| Metric | Starting threshold |
|---|---|
| Faithfulness | ≥ 0.75 |
| Answer relevancy | ≥ 0.80 |
| Context precision | ≥ 0.70 |
| Context recall | ≥ 0.80 |

> RAGAS scores are produced by an LLM judge, so they cost money per run and vary slightly between runs. Pin the judge model and run faithfulness as a pre-release gate, not on every commit.

### Is RAGAS the best tool? When to reach for something else

RAGAS is the best *starting* and *primary* tool for RAG-specific metrics, but it isn't the only one, and it isn't built for every job. Teams shipping real RAG usually run **two** tools — RAGAS for the metrics, plus a test-runner. Here's the honest map:

| Tool | Best at | Reach for it when… |
|---|---|---|
| **RAGAS** | Deep RAG-specific metrics, fast to start, lightweight | You want faithfulness / relevancy / context scores — the default |
| **DeepEval** | pytest-native, designed to **block deploys**; broader metrics (hallucination, bias, toxicity) | You're building the CI/CD quality gate (Q17) and want eval-as-pytest |
| **Promptfoo** | CLI-first, **red-team mode** auto-generates adversarial inputs | You're doing injection / adversarial testing (Q15) |
| **TruLens** | Feedback functions + tracing | You want to **monitor** faithfulness on live traffic, not just gate releases |

A sensible progression for this project:
1. **Start with RAGAS** — learn the four metrics, score your golden dataset.
2. **Add DeepEval** if/when you want eval baked into pytest and CI as a hard gate.
3. **Add Promptfoo** specifically for the prompt-injection and adversarial work in Q15.
4. **Consider TruLens** only once you have something running in production worth monitoring.

You don't need all four. RAGAS plus pytest (Level 2) covers most of this learning project. The others are there for when a specific scenario outgrows RAGAS.

---

## Which level does each scenario need?

Pulled from the scenarios doc so you can see the pattern — notice how much is manual- or script-owned, and how narrowly eval tooling is actually required:

| Scenario | Manual | Scripted | Eval tooling |
|---|---|---|---|
| Q1 Document updated | Smoke test | Chunk/metadata audit | Optional |
| Q2 LLM swapped | Catches the obvious | Log cost/latency | **Yes** — faithfulness before/after |
| Q3 1000s of documents | Diagnosis only | **Yes** — audit + coverage | Optional |
| Q4 Daily-changing data | Spot checks | **Yes** — freshness probe | Stable half only |
| Q5 Mixed formats | **Yes** — read the chunks | Parse validation | Optional |
| Q6 Temperature | **Yes** — feel it out | Determinism check | **Yes** — faithfulness vs temp |
| Q7 Chunk size | **Yes** — intuition | Re-index + run sets | **Yes** — recall + completeness |
| Q8 Overlap | **Yes** — boundary check | Duplicate detection | Optional |
| Q9 Best overlap | Author Set A | **Yes** — the experiment | **Yes** |
| Q10 Contradictions | **Yes** — strong fit | Consistency check | Limited |
| Q11 Multi-hop | **Yes** — find examples | Track recall | **Yes** — context recall |
| Q12 Context overflow | Symptom only | **Yes** — token counter | Confirms it |
| Q13 Out-of-scope | **Yes** — owns it fully | Threshold check | Optional |
| Q14 Embedding swap | Quick spot check | **Yes** — recall + schema | **Yes** |
| Q15 Prompt injection | **Yes** — owns it | Regression suite | Optional (Promptfoo) |
| Q16 Golden dataset | **Yes** — tester builds it | Runs it | Scores it |
| Q17 CI/CD | Defines it | Cheap tiers | Faithfulness tier only |

**Takeaway for a functional tester:** Q5, Q10, Q13, Q15, and Q16 are yours to own with manual judgement and a browser. Most of the rest you can carry a long way with light Python (Level 2). Eval tooling is the smaller, specialised top of the pyramid — reach for it specifically when you're scoring answer *quality* across many cases, and start that journey with RAGAS.

---

*Sources: [RAGAS docs](https://docs.ragas.io/en/stable/), [RAGAS metrics list](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/), [Dify Test Knowledge Retrieval](https://docs.dify.ai/en/use-dify/knowledge/test-retrieval), and 2026 framework comparisons from [genai.qa](https://genai.qa/blog/promptfoo-vs-deepeval-vs-ragas/) and [atlan.com](https://atlan.com/know/llm-evaluation-frameworks-compared/).*
