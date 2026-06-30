# RAG Testing Knowledge Check — 10 Questions

A self-assessment covering the core concepts a tester needs to confidently test a RAG application. Work through these before your first hands-on session or use them as interview prep.

For each question: read it, write your answer, then check the answer below.

---

## Q1 — The RAG pipeline

**Walk me through what happens — step by step — when a user sends a message to a RAG chatbot. Start from the moment they hit send and end at the answer appearing on screen.**

<details>
<summary>Answer</summary>

1. The user's query is passed through an **embedding model**, which converts it into a vector (a list of numbers representing the meaning of the query)
2. The vector store (**Weaviate** in this project) is searched for chunks whose vectors are closest to the query vector — this is the **similarity search**
3. The top-K most similar chunks are retrieved
4. *(Advanced RAG only)* A **reranker** reorders the top-K results to improve relevance ranking
5. A prompt is assembled from three parts: **system prompt** + **retrieved chunks** + **user question**
6. The full prompt is sent to the **LLM**
7. The LLM generates an answer and it is shown to the user

**Key distinction:** the reranker is an Advanced RAG feature — it is not always present. In Naive RAG, raw top-K results go directly into the prompt. Know which pipeline you're testing before diagnosing retrieval failures.

</details>

---

## Q2 — What makes a test actually pass

**A user asks: "What is the notice period for resigning?" The RAG system retrieves 5 chunks. Chunk 3 contains the exact answer. The final answer the chatbot gives is correct. Is this a passing test? What else would you check before marking it green?**

<details>
<summary>Answer</summary>

A correct final answer is not enough on its own. Check all four of these:

**1. Did the answer come FROM the chunks, or from training data?**
The LLM may have answered from its own training knowledge and ignored the retrieved chunks entirely. That's a faithfulness failure — dangerous because the next question it doesn't know from training will be hallucinated instead. Verify the answer is traceable to the retrieved context.

**2. Where did chunk 3 rank?**
If the correct chunk is ranked #3 out of 5, your retrieval scoring is weak. The most relevant chunk should rank #1. A correct answer with the right chunk buried at position 3 is a retrieval quality warning.

**3. Are the other 4 chunks relevant or noise?**
Irrelevant chunks waste context space and can confuse the LLM. On harder questions, too much noise causes the model to pick the wrong signal.

**4. Does it still work if the question is phrased differently?**
"How much notice do I need to give?" should retrieve the same chunk. One correct answer on one phrasing is not a reliable pipeline.

**Core lesson:** a correct output can hide a broken pipeline. Verify the mechanism, not just the result.

</details>

---

## Q3 — Context relevance vs faithfulness

**What is the difference between context relevance and faithfulness? Give an example where one fails but the other passes.**

<details>
<summary>Answer</summary>

These measure two different failure points in the pipeline.

**Context relevance** — did retrieval do its job?
Are the chunks that were returned actually about what the user asked? This is a judgement on the retrieved chunks, not the answer.

**Faithfulness** — did the LLM use those chunks?
Is the final answer grounded in the retrieved context, or did the LLM make something up or pull from training data?

---

**Example: context relevance passes, faithfulness fails**

The HR handbook says notice period is 30 days.

| Step | What happened |
|---|---|
| Retrieved chunks | Chunk about resignation policy — correct, contains "30 days" ✓ |
| LLM answer | "The notice period is 2 weeks." ✗ |

The right chunk was retrieved. The LLM ignored it and answered from training data. Retrieval worked. Generation failed.

---

**Example: faithfulness passes, context relevance fails**

| Step | What happened |
|---|---|
| Retrieved chunks | Chunks about health insurance and annual leave — wrong topic ✗ |
| LLM answer | "Based on the provided context, I cannot find information about the notice period." ✓ |

The LLM only used what it was given and honestly said it couldn't find the answer. Generation was faithful. Retrieval failed.

---

Together with **answer relevance** (does the response actually address the question?), these three form the **RAG Triad** — the standard quality framework for RAG evaluation. All three are measurable automatically with RAGAS.

</details>

---

## Q4 — Chunking settings and trade-offs

**Your RAG system is returning chunks that contain part of the answer but keep cutting off mid-sentence. What setting would you adjust, and what is the trade-off?**

<details>
<summary>Answer</summary>

Three settings are relevant — in order of importance:

**1. Chunk size (primary fix)**
If chunks cut off mid-sentence, they are too small to hold a complete answer. Increase chunk size so more content fits in each chunk.

**2. Overlap (boundary fix)**
Overlap makes neighbouring chunks share a tail/head of content. If an answer straddles the boundary between chunk 4 and chunk 5, overlap ensures chunk 4 ends with lines that also appear at the start of chunk 5. Fixes boundary problems, not capacity problems.

**3. Top-K (workaround)**
Retrieving more chunks increases the chance of catching the continuation. This is a patch, not a fix — it adds noise, increases token cost, and risks hitting the LLM's context window limit.

| Setting | Benefit | Cost |
|---|---|---|
| Larger chunk size | Complete answers in one chunk | Less precise retrieval — a big chunk matches many queries even when only part of it is relevant |
| Higher overlap | Fewer boundary cut-offs | Index grows; same content stored multiple times; redundant content in prompt |
| Higher Top-K | More chances to catch the answer | More tokens, more noise, higher cost, context window risk |

**Testing implication:** changing chunk size or overlap means re-indexing the entire document. Re-run your full retrieval test suite after — don't assume previously passing tests still pass.

</details>

---

## Q5 — Out-of-scope handling

**A user asks a question that is completely outside the knowledge base. What should the RAG system do, and how would you test that it does it correctly?**

<details>
<summary>Answer</summary>

**Expected behaviour:** the system should acknowledge it cannot answer from the available context. It should not hallucinate a plausible-sounding answer.

This behaviour is enforced by the system prompt — typically: *"Answer only using the provided context. If the answer is not in the context, say you don't know."* Without this instruction, the LLM answers from training data instead.

---

**How to test it:**

**Step 1 — Build a negative test set with three types of question:**

| Type | Example | Why |
|---|---|---|
| Completely unrelated | "What is the capital of France?" | Easy case — nothing should match |
| Plausible but absent | "What is John Smith's salary?" | Tempts the LLM to hallucinate a realistic answer |
| Near-miss | "What is the CEO's bonus?" | Related topic but specific data is not in the handbook |

**Step 2 — Check the retrieval layer**
For true out-of-scope questions, similarity scores should be low. High scores on an out-of-scope question means your threshold is too loose.

**Step 3 — Check the response**
It should acknowledge the missing information — not give a generic "I can't help" but specifically reference the lack of context.

**Step 4 — Remove the system prompt instruction and re-run**
The LLM should now hallucinate. If it doesn't, the model is being cautious on its own — which you cannot rely on. The instruction must be the enforcement mechanism, not the model's discretion.

**Hardest case:** the near-miss. "What is the CEO's bonus?" may retrieve a chunk about pay grades. The LLM now has loosely related chunks and a question it cannot fully answer. Does it stay grounded or extrapolate? This is where most systems break.

</details>

---

## Q6 — Non-determinism and temperature

**You run the same query twice on the same RAG system with the same document. You get two slightly different answers. Retrieval returned the same chunks both times. What caused the different answers, and is this a bug?**

<details>
<summary>Answer</summary>

**Cause: temperature**

LLMs sample from a probability distribution when generating each token. At any temperature above 0, the same input produces slightly different output on each run — different word choices, different sentence structure.

| Temperature | Behaviour |
|---|---|
| `0.0` | Deterministic — same input always produces same output |
| `0.5` | Moderate variation — natural but focused |
| `1.0+` | High variation — creative, more likely to drift |

**Is it a bug?**

It depends on what changed:

| Scenario | Bug? |
|---|---|
| Different wording, same meaning, same facts | No — normal LLM variation |
| Different facts stated (one says 30 days, one says 2 weeks) | Yes — faithfulness failure |
| One refuses, the other answers confidently | Yes — inconsistent behaviour is a reliability defect |

Variation in *phrasing* is expected. Variation in *facts* is a defect.

**Testing implication:** set temperature to `0` during test runs so results are reproducible. At temperature 0, same input must always produce same output — if it doesn't, that is your bug. Use semantic evaluation (RAGAS, LLM-as-judge) rather than exact string matching, because phrasing variation at any temperature above 0 will cause false failures on lexical checks.

</details>

---

## Q7 — What to build before the first test

**You are about to test a RAG system for the first time. You have the HR handbook, the Dify app, and an API key. What is the first thing you build before you run a single test — and why?**

<details>
<summary>Answer</summary>

**A golden dataset.**

The vector database is already built — Dify indexed the document when you uploaded it. The infrastructure is ready. Before you run any tests you need something to compare results against.

A golden dataset is a curated set of questions where you already know the correct answer and which source chunk should have retrieved it.

| Question | Expected answer | Source chunk |
|---|---|---|
| What is the notice period for resigning? | 30 days | Section 7.2, paragraph 1 |
| How many days of annual leave do employees get? | 20 days per year | Section 4.1 |
| Can I carry over unused leave? | Up to 5 days, with manager approval | Section 4.3 |

**Why it must come first:**

Without it, you have no baseline. You can send 50 queries and get 50 responses — but if you don't know what correct looks like, you're just reading outputs. Every other test depends on it:

- **Retrieval test** — did the source chunk appear in the top-K results?
- **Faithfulness test** — is the answer grounded in that chunk?
- **RAGAS scoring** — needs expected answers to calculate recall and relevancy
- **Regression testing** — when you change chunk size or swap models, you re-run the same dataset and compare

Garbage dataset, garbage scores — regardless of the tool.

</details>

---

## Q8 — Chunking trade-off in practice

**You change chunk size from 500 tokens to 200 tokens and re-run your golden dataset. Retrieval recall goes up but answer quality goes down. Explain why both things happened.**

<details>
<summary>Answer</summary>

**Retrieval recall went up** because smaller chunks are more focused. A 200-token chunk about "notice period" produces a tighter embedding — less noise, stronger semantic signal for that specific topic. The similarity search finds it more reliably.

**Answer quality went down** because the LLM now gets fragments instead of complete thoughts. A policy that reads *"employees must give 30 days notice, except during probation where 1 week applies, unless the contract specifies otherwise"* might span 400 tokens. At 200-token chunks, the LLM gets the first half and answers as if the exception doesn't exist — technically correct, materially incomplete.

This is the fundamental chunking tension:

| Chunk size | Retrieval precision | Answer completeness |
|---|---|---|
| Small (200 tokens) | High — tight semantic match | Low — answer may be split across chunks |
| Large (1000 tokens) | Lower — chunk covers many topics | High — full context in one chunk |

The right size depends on your document. Policies with long conditional clauses need larger chunks. FAQs with short discrete answers work well with smaller chunks.

**Testing implication:** never tune chunk size by feel. Run your golden dataset before and after, and compare both recall and answer quality scores together. One going up while the other drops means you haven't found the right value yet.

</details>

---

## Q9 — Embedding model swap

**A developer tells you: "We're switching the embedding model from text-embedding-3-small to a different model next sprint." What do you need to do before that change goes live — and what happens if you skip it?**

<details>
<summary>Answer</summary>

**Why this is high risk:**

Chunk vectors and query vectors must come from the same embedding model. Different models produce vectors in incompatible mathematical spaces — comparing them is meaningless. A vector from `text-embedding-3-small` and a vector from a different model point in completely different directions even for identical text.

If you swap the model without re-indexing, the index still holds old vectors. The new model generates query vectors in a different space. Retrieval breaks — completely unrelated chunks come back for every query. The system appears to work (it still returns chunks, the LLM still answers) but the chunks are wrong. **The failure is silent.**

---

**What to do before the change goes live:**

**1. Re-index the entire document set**
Every chunk must be re-embedded using the new model. Old vectors are invalid the moment you switch.

**2. Run your full golden dataset against the new index**
Retrieval recall, context relevance, faithfulness — all of it. The new model may embed meaning differently enough that queries which worked before no longer retrieve the right chunks.

**3. Compare scores before and after**
A model swap can silently degrade quality even after re-indexing if the new model is a worse fit for your document type.

**4. Pay attention to domain-specific terms**
HR jargon, policy names, and role titles are where embedding models diverge most. A general-purpose model may not embed "probationary period" as semantically close to "notice period" as a domain-tuned model would.

| Skipped step | Consequence |
|---|---|
| Skip re-indexing | Retrieval is silently broken |
| Skip golden dataset re-run | Regression goes undetected |
| Skip domain term testing | Edge cases fail quietly |

</details>

---

## Q10 — Release gates

**A tester on your team says: "I ran 20 queries manually, all the answers looked good, so the RAG system is ready to ship." What is wrong with that sign-off — and what would a proper release gate look like instead?**

<details>
<summary>Answer</summary>

**What is wrong with the manual sign-off:**

- **Too small a sample** — 20 hand-picked queries naturally avoid the edge cases that break systems
- **No metric** — "looked good" is not a threshold; there is nothing to compare against next release
- **Not reproducible** — two testers reading the same answer will judge it differently; the same tester will judge it differently on different days
- **No baseline** — even if all 20 answers look good today, you cannot tell if quality dropped since last sprint
- **Does not scale** — manual review of every query on every release is not sustainable

---

**What a proper release gate looks like:**

Run your full golden dataset through RAGAS and block the release unless all of the following pass:

| Gate | Threshold |
|---|---|
| Faithfulness | ≥ 0.85 |
| Context Relevance | ≥ 0.80 |
| Answer Relevance | ≥ 0.80 |
| Out-of-scope refusal rate | 100% |
| Prompt injection blocked | 100% |
| End-to-end latency at peak | ≤ 3 seconds |
| Open P1 defects | 0 |

Every gate must pass — not a majority. A system that is fast but faithfully returns hallucinations is not ready to ship.

| Manual sign-off | Proper release gate |
|---|---|
| Subjective | Metric-driven |
| Ad hoc queries | Curated golden dataset |
| No threshold | Explicit pass/fail thresholds |
| Not reproducible | Automated, runs every release |
| Cannot detect regression | Scores compared across releases |

</details>

---

## Score guide

| Score | What it means |
|---|---|
| 85–100 | Ready to test a RAG system independently |
| 70–84 | Strong foundations — brush up on evaluation concepts before going live |
| 50–69 | Good pipeline intuition, gaps in metrics and test design — do the hands-on golden dataset exercise |
| Below 50 | Re-read the glossary and toolkit docs, then retake |
