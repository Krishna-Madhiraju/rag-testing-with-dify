# Why RAG Testing Is Harder Than Normal API Testing

Testing a RAG system looks similar to testing any other API on the surface: send a request, check the response. But three fundamental properties of RAG break the assumptions that normal API testing relies on. Understanding these properties changes how you design your tests, what you assert on, and how you decide whether a release is safe.

---

## Property 1 — The Output Is Non-Deterministic

A normal API function is deterministic. The same input produces the same output, every time. That guarantee is the foundation of automated testing: if your assertion passed last Tuesday, it will pass again today unless something changed.

An LLM does not make that guarantee. Even with temperature set to zero, the exact wording of an answer can vary between runs. The model may phrase the same fact differently, reorder sentences, or use a synonym. Two runs that both retrieve the correct chunk and correctly state "10 days of sick leave" may produce answers that share no exact string in common:

```
Run 1: "Full-time employees are entitled to 10 days of paid sick leave per year."
Run 2: "Orion provides 80 hours of sick leave annually for full-time staff."
```

Both answers are correct. Neither would pass a strict equality assertion against the other.

**What this means for testing:**
You cannot assert `response.answer == expected_answer`. You need a different assertion strategy — either flexible keyword checks (does the answer contain the key fact?), or score-based thresholds (is the ROUGE-L score above 0.40?). Exact string matching only works for out-of-scope refusals, where any affirmative answer is a failure regardless of wording.

---

## Property 2 — Retrieval Quality Degrades Silently

When a normal API breaks, it usually signals the failure: an error code, an exception, an empty response. The system tells you something went wrong.

RAG retrieval fails silently. If a configuration change causes the wrong chunk to rank above the right one, the system still returns HTTP 200. The answer still looks coherent. The user gets a response. But the response is now grounded in the wrong chunk — or no relevant chunk at all. The LLM fills the gap with plausible-sounding training data, and the failure is invisible until someone checks the answer against the source.

Retrieval degradation is the hardest RAG failure to catch without explicit testing because:

- The API never errors
- The answer usually sounds reasonable
- The wrong chunk retrieved is often on a related topic, making the hallucination plausible

**What this means for testing:**
You must assert on retrieval separately from generation. After every configuration change — chunk size, overlap, top-K, embedding model, re-indexing — run a retrieval check: did the expected chunk appear in the top-K results? This check is independent of whether the final answer is correct, and it localises the failure: you know whether the problem is in retrieval or in generation.

---

## Property 3 — Two Independent Failure Surfaces

A RAG pipeline has two components that can each fail independently, and the failures do not look the same.

**The retrieval surface:** the wrong chunk is returned, or no relevant chunk is returned. The LLM receives bad context. Whatever it generates from bad context is not the LLM's fault — it was given the wrong material.

**The generation surface:** the correct chunk is returned, but the LLM ignores it, misreads it, or embellishes it with information not in the chunk. This is a faithfulness failure. The retrieval worked; the generation did not.

In a normal API, there is one place to look when something fails: the code. In RAG, you must first determine which surface failed before you know what to investigate or fix.

```
Scenario A: Correct chunk not retrieved → LLM hallucinates
  → Fix: retrieval configuration (chunk size, top-K, embedding model)

Scenario B: Correct chunk retrieved → LLM ignores it and halluccinates
  → Fix: system prompt, temperature, LLM choice, or context assembly

A test that only checks the final answer cannot distinguish A from B.
```

**What this means for testing:**
Every test result needs two data points: chunk_found (was the right chunk retrieved?) and the answer quality score. When a test fails, you need to know which surface broke. A suite that only checks final answers will tell you something is wrong but cannot tell you where.

---

## The Layered Response

These three properties lead directly to a three-layer test strategy. Each layer addresses a different property.

### Layer 1 — Retrieval assertions

Test the retrieval surface directly. Call the API, look at which chunks came back, check whether the expected chunk is in the top-K. Do not look at the answer at all.

**Why this layer works:** retrieval is near-deterministic. The same query against the same index returns the same chunks on almost every run. This makes retrieval assertions reliable enough for CI — they will not produce false failures from LLM phrasing variation.

**What it catches:** indexing regressions, chunk size changes that split answers, top-K changes that push the right chunk out of the result set, embedding model changes.

**Cost:** fast. One API call per question. No LLM scoring involved.

### Layer 2 — Keyword assertions on answers

Check the answer for required facts or for required refusals. Do not assert exact phrasing — assert that a key value is present, or that a refusal phrase is present.

**Why this layer works:** while exact phrasing varies, the key facts in a correct answer are usually stable. "10 days", "20 weeks", "5%" — these values should appear in any correct answer regardless of how the sentence is structured. Similarly, an out-of-scope refusal should always contain one of a known set of decline phrases.

**What it catches:** wrong values stated, out-of-scope answers that should have been refused, prompt injection that caused the system to leave its role.

**What it misses:** paraphrased correct answers where the key term was expressed differently ("ten days" vs "10 days"), semantic hallucinations that use the right number in the wrong context.

**Cost:** fast. Same API call as Layer 1. String matching only.

### Layer 3 — Scored quality gates

Run BLEU, ROUGE-L, GPTScore, or RAGAS against the answers. Assert that scores are above a threshold. Mark these tests as slow — exclude them from CI, run them before a release or after a significant configuration change.

**Why this layer works:** scoring captures what keyword checks miss. RAGAS Faithfulness detects when the LLM added facts not in the retrieved context. ROUGE-L catches answer drift across runs. GPTScore catches semantic errors that are lexically invisible.

**What it catches:** systematic quality regressions across the whole dataset, faithfulness degradation after a model or prompt change, subtle hallucinations that pass keyword checks.

**Cost:** expensive. Requires LLM calls for GPTScore and RAGAS. Run selectively.

---

## What Each Layer Is Responsible For

| Layer | Surface tested | Assertion type | When to run | Cost |
|---|---|---|---|---|
| Retrieval | Retrieval | Binary (chunk found / not found) | Every commit, after any config change | Low |
| Keyword | Generation | Substring match | After config changes, before release | Low |
| Scored | Generation | Score threshold | Pre-release, after model/prompt changes | High |

No layer replaces the others. Retrieval passes and keyword fails tells you the chunk came back but the LLM misread it. Retrieval fails and keyword passes tells you the correct chunk was not retrieved but the LLM guessed correctly from training data — which is a hidden reliability risk even though the test passed. You need both signals.

---

## How This Changes Your Mindset

Normal API testing asks: **"Does the system return the right answer?"**

RAG testing asks three questions:
1. **Did the right chunk get retrieved?** (retrieval surface)
2. **Does the answer contain the right facts?** (generation surface, keyword check)
3. **Is the answer grounded in what was retrieved, not in training data?** (faithfulness, scored check)

Only when all three questions have satisfactory answers can you say the test passed for the right reasons. A test that passes questions 2 and 3 but fails question 1 is a system that got lucky — the LLM knew the answer from training even though retrieval failed. That is a reliability gap, not a passing test.

---

## See Also

- [Test Strategy](test-strategy.md) — how the three layers map to release gates and test cadence
- [RAG Evaluation Playbook](rag-evaluation-playbook.md) — how to score answers and interpret metrics across a run
- [RAGAS Evaluation Metrics](ragas-evaluation-metrics.md) — Layer 3 scoring in detail: Faithfulness, Answer Relevancy, Context Precision, Context Recall
- [Adversarial Testing](adversarial-testing.md) — the additional failure surfaces Layer 2 keyword checks must cover
- [Golden Dataset Guide](../../golden-dataset/guide.md) — the dataset that drives all three layers
