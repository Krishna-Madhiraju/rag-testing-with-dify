# RAG Testing Knowledge Check — Quiz 2: Evaluation & Metrics

Covers your weakest areas from Quiz 1 plus the evaluation concepts not yet tested: golden datasets, BLEU, ROUGE-L, GPTScore, RAGAS metrics, and test suite design.

Attempt each answer before opening the details block.

---

## Q11 — Golden dataset question quality

**You are building a golden dataset for the Orion HR handbook. Below are four candidate questions. Which ones belong in the dataset and which don't — and why?**

- A: "What is the annual leave entitlement?"
- B: "Is the HR policy fair?"
- C: "What happens if an employee is absent for more than 5 consecutive days without notice?"
- D: "What is the capital of France?"

<details>
<summary>Answer</summary>

| Question | In / Out | Reason |
|---|---|---|
| A — Annual leave entitlement | **In** | Factual, answerable from the handbook, clear expected answer |
| B — Is the HR policy fair? | **Out** | Subjective — no single correct answer exists; the RAG system should not attempt this |
| C — 5 consecutive absent days | **In** | Specific, verifiable against the source, tests a real edge case users will ask |
| D — Capital of France | **Out** | Out-of-scope — this belongs in your *negative* test set to verify refusal behaviour, not in your golden dataset |

**What makes a good golden dataset question:**
- Has a single correct, verifiable answer in the document
- Represents a question a real user would ask
- Covers a specific policy, date, number, or named role — not vague topics
- You can point to the exact sentence in the source that answers it

**What makes a bad question:**
- Subjective or opinion-based
- Requires reasoning across many documents (unless testing multi-hop)
- So obvious it could be answered from general knowledge — the LLM doesn't need to retrieve anything
- Duplicate of another question already in the set

**Dataset composition to aim for:**

| Question type | Purpose | Target % |
|---|---|---|
| Straightforward in-scope | Core coverage | ~40% |
| Paraphrased (same answer, different wording) | Tests retrieval robustness | ~20% |
| Multi-hop (answer requires two chunks) | Tests complex reasoning | ~15% |
| Near-miss (related but not in handbook) | Tests boundary handling | ~15% |
| Out-of-scope | Negative testing | ~10% |

</details>

---

## Q12 — How BLEU works

**Reference answer:** "Employees are entitled to 20 days of annual leave per year."
**Generated answer:** "Staff receive twenty days of yearly vacation."

Would BLEU score this as high or low? Explain why — and what that tells you about when not to use BLEU.

<details>
<summary>Answer</summary>

**BLEU would score this very low — close to zero.**

**How BLEU works mechanically:**

BLEU counts n-gram overlap between the generated answer and the reference answer. An n-gram is a sequence of N consecutive words.

For this pair:
- "Employees" vs "Staff" — no match
- "entitled to" vs "receive" — no match
- "20 days" vs "twenty days" — no match (different tokens)
- "annual leave" vs "yearly vacation" — no match
- "per year" vs (absent) — no match

There is almost zero word overlap even though both sentences mean exactly the same thing. BLEU sees them as almost completely different.

**Why this is a problem for RAG evaluation:**

Users rarely phrase answers the same way the document does. An LLM will naturally paraphrase, use synonyms, and reorder sentences. BLEU penalises all of this even when the answer is semantically correct.

**When BLEU is still useful:**

- Regression testing between two versions of the same system — you're not checking absolute quality, you're checking whether scores *changed*
- Catching cases where the answer drifted significantly in phrasing between runs
- As a cheap first pass before running more expensive metrics

**When not to use BLEU as your primary metric:**

- Any time the generated answer might be a correct paraphrase of the reference
- Faithfulness evaluation — BLEU cannot detect hallucinations
- Any question with a long, complex answer where word order naturally varies

</details>

---

## Q13 — How ROUGE-L works

**Reference answer:** "The probationary period is 3 months."
**Generated answer:** "During the first 3 months of employment, the employee is considered to be on probation."

What does ROUGE-L measure here? What does it capture that BLEU misses — and what does it still miss?

<details>
<summary>Answer</summary>

**What ROUGE-L measures:**

ROUGE-L finds the **Longest Common Subsequence (LCS)** between the reference and generated answer — the longest sequence of words that appear in both, in the same order, but not necessarily consecutively.

In this example:
- Reference: "The probationary period is **3 months**."
- Generated: "During the first **3 months** of employment, the employee is considered to be on probation."

The LCS includes "3 months" and fragments around "probation" — ROUGE-L would give a moderate score because key terms appear in order even though the sentences are structured differently.

**What ROUGE-L captures that BLEU misses:**

BLEU requires words to appear as consecutive n-grams. ROUGE-L only requires them to appear in order — so it handles reordering and inserted words better. It is better at measuring whether key facts were *covered*, even if phrased differently.

**What ROUGE-L still misses:**

It is still lexical. It matches words, not meaning. Consider:
- Reference: "The probationary period is 3 months."
- Generated: "New employees serve a 90-day trial period."

90 days = 3 months, and "trial period" = "probationary period" — but ROUGE-L scores this near zero because no words overlap.

**The rule of thumb:**

| Metric | Good for | Blind to |
|---|---|---|
| BLEU | Exact phrasing regression | Synonyms, paraphrases, reordering |
| ROUGE-L | Coverage of key facts, flexible ordering | Synonyms, semantic equivalence |
| GPTScore | Semantic correctness, hallucination | Cost, non-determinism |

Use BLEU and ROUGE-L together for fast CI checks. Use GPTScore when you need to catch semantic failures they both miss.

</details>

---

## Q14 — When BLEU and ROUGE both pass but the answer is wrong

**A developer asks: "Why do we need LLM-as-judge if BLEU and ROUGE are cheaper and deterministic?"**

Give them one concrete scenario where BLEU and ROUGE both score well but the answer is actually a defect.

<details>
<summary>Answer</summary>

**The scenario: hallucination that parrots the reference**

Reference answer: "Employees must give 30 days notice before resigning."

Generated answer: "Employees must give 30 days notice before resigning. They are also entitled to a severance package of 3 months' salary."

The second sentence was not in the handbook. The LLM added a true-sounding fact from its training data.

- BLEU score: **high** — the generated answer contains the entire reference verbatim
- ROUGE-L score: **high** — the LCS covers all key reference terms in order
- Actual quality: **defect** — the system hallucinated a severance policy that does not exist in the knowledge base

BLEU and ROUGE only check whether reference content appears in the generated answer. They have no concept of whether the generated answer *adds* false information. An answer that reproduces the reference perfectly and then hallucinates will score full marks on both.

**GPTScore / LLM-as-judge catches this** because the judge reads the full generated answer against the retrieved chunks and asks: "Is every claim in this answer supported by the provided context?" The hallucinated sentence is not in the chunks, so faithfulness drops.

**The principle:** BLEU and ROUGE measure overlap with the reference. They cannot detect what the reference does not contain. LLM-as-judge measures grounding in the *context* — a fundamentally different check.

</details>

---

## Q15 — RAGAS context precision vs context recall

**What is the difference between context precision and context recall in RAGAS? Give a concrete example where one is high and the other is low.**

<details>
<summary>Answer</summary>

Both metrics evaluate the retrieved chunks — but they ask opposite questions.

**Context recall** — did we retrieve everything we needed?
Of all the information required to answer the question, how much of it appeared somewhere in the retrieved chunks?

**Context precision** — was what we retrieved actually useful?
Of all the chunks that were retrieved, how many of them were actually relevant to the question?

---

**Example: high recall, low precision**

Question: "What is the notice period for resigning?"

Retrieved chunks:
1. Chunk about resignation notice — relevant ✓
2. Chunk about annual leave — not relevant ✗
3. Chunk about health insurance — not relevant ✗
4. Chunk about resignation notice (duplicate) — marginally relevant
5. Chunk about disciplinary process — not relevant ✗

- **Recall: high** — the chunk containing the answer was retrieved (chunk 1)
- **Precision: low** — only 1 of 5 chunks was actually useful; 4 were noise

**Example: high precision, low recall**

Question: "What is the notice period, and does it change during probation?"

Retrieved chunks:
1. Chunk about standard notice period — relevant ✓
2. Chunk about maternity leave — not relevant ✗

- **Precision: moderate** — 1 of 2 chunks is relevant
- **Recall: low** — the chunk about probationary notice period was never retrieved; the answer is incomplete

---

**Testing implication:**

| Problem | Symptom | Fix |
|---|---|---|
| Low precision | LLM confused by noise, inconsistent answers | Raise similarity threshold, reduce Top-K |
| Low recall | Answer is incomplete or missing key facts | Lower similarity threshold, increase Top-K, check chunking |

Low recall means your system cannot find what it needs. Low precision means it finds too much it doesn't need. Both hurt answer quality but for different reasons — and they point to different fixes.

</details>

---

## Q16 — Diagnosing a faithfulness score drop

**Your RAGAS faithfulness score drops from 0.88 to 0.71 after a system prompt change. Retrieval results are identical — the same chunks come back for every query. What happened and how would you diagnose it?**

<details>
<summary>Answer</summary>

Faithfulness measures whether the LLM's answer is grounded in the retrieved chunks. Retrieval is unchanged, so the chunks are the same. The only thing that changed is how the LLM is being instructed to use them.

**What most likely happened:**

The new system prompt changed how the LLM behaves in one of these ways:

| Cause | Effect on faithfulness |
|---|---|
| Instruction to "be helpful and thorough" added | LLM supplements chunks with training knowledge — hallucination increases |
| Instruction to "use your expertise" added | LLM trusts itself over the context |
| Grounding instruction weakened or removed | e.g. removed "answer only from the provided context" |
| Persona added ("you are an HR expert") | LLM answers as an expert, not from the document |

**How to diagnose it:**

1. **Diff the two system prompts** — find every sentence that changed, was added, or removed
2. **Run the same 5–10 questions manually** against both versions — read the answers side by side and identify which answers changed and whether they added content not in the chunks
3. **Look at the low-scoring questions specifically** — RAGAS tells you per-question scores; the questions that dropped most will reveal the pattern
4. **Test the grounding instruction in isolation** — restore just the "answer only from context" line and re-run. If faithfulness recovers, that was the culprit

**The lesson:** system prompt changes are a release risk even when the data and retrieval pipeline are untouched. They must trigger a full evaluation run, not just a smoke test.

</details>

---

## Q17 — BLEU vs ROUGE vs GPTScore — when they disagree

**You run all three metrics on 50 answers. BLEU averages 0.31, ROUGE-L averages 0.58, GPTScore averages 0.89. The scores strongly disagree. What does this pattern tell you?**

<details>
<summary>Answer</summary>

This is actually a healthy and informative divergence — not a sign something is broken.

**What the pattern says:**

- **BLEU is low (0.31)** — the generated answers don't use the same words as the reference answers. The phrasing is different.
- **ROUGE-L is moderate (0.58)** — key facts and terms are present in the generated answers, just not in the same order or with the same surrounding words as the reference.
- **GPTScore is high (0.89)** — a judge model reading the answers finds them semantically correct, grounded in context, and relevant.

**Interpretation:** the LLM is paraphrasing well. The answers are correct in meaning but not in wording. This is normal and desirable — you don't want a system that copies the reference verbatim, you want one that synthesises an answer naturally.

**When this pattern is a concern:**

If GPTScore were also low (e.g. 0.41), you'd have a real quality problem — the system is wrong *and* phrasing it badly. When GPTScore is high and BLEU is low, the system is right but sounds different. Trust GPTScore for quality; treat BLEU as a phrasing-consistency signal.

**When to be suspicious of high GPTScore:**

LLM-as-judge is prompt-sensitive and can be fooled by confident, fluent answers. A hallucinated answer written with conviction can score well. Pair GPTScore with faithfulness checks that verify claims against the source chunks, not just the reference answer.

**Which to trust for the release gate:**

GPTScore / RAGAS faithfulness for go/no-go decisions. BLEU/ROUGE-L for regression — track them over time to catch drift, not to judge absolute quality.

</details>

---

## Q18 — Component testing vs end-to-end testing

**What is the difference between component testing and end-to-end testing in a RAG pipeline? Give a concrete example of a bug that end-to-end testing would miss but component testing would catch.**

<details>
<summary>Answer</summary>

**Component testing** isolates a single stage of the pipeline and tests it independently.

**End-to-end testing** sends a question through the full pipeline and evaluates the final answer.

---

**Concrete example of a bug component testing catches that E2E misses:**

**Scenario:** retrieval is silently broken — the wrong chunks are being returned for a set of queries.

In **end-to-end testing**, you ask the question and read the answer. If the LLM happens to know the answer from training data, it might give a correct response *despite* retrieving the wrong chunks. The test passes. The retrieval bug is invisible.

In **component testing**, you test retrieval in isolation:
- Send the query to the retrieval API directly
- Check which chunks came back
- Verify the correct source chunk appears in the top-K results
- Check the similarity scores

The bug is immediately visible — the wrong chunks appear, or scores are unexpectedly low — even though the final answer looked fine.

---

**The full component test map:**

| Component | What to test in isolation |
|---|---|
| **Ingestion** | Were all chunks indexed? Are chunk counts correct? |
| **Embedding** | Does the same text produce the same vector each run? |
| **Retrieval** | Does the correct chunk appear in top-K? Is it ranked appropriately? |
| **Prompt assembly** | Is the full prompt structured correctly? Are chunks truncated? |
| **LLM generation** | Given the right context, does the LLM use it faithfully? |

**The rule:** use component tests to find *where* the failure is. Use end-to-end tests to confirm the full pipeline works together. You need both — E2E alone will miss silent retrieval failures; component tests alone won't catch integration issues.

</details>

---

## Q19 — A/B configuration testing

**You want to compare two chunking strategies: Strategy A (500 tokens, 50 overlap) vs Strategy B (200 tokens, 20 overlap). What is your test plan? What must stay constant, what changes, and how do you decide which wins?**

<details>
<summary>Answer</summary>

**What must stay constant (control variables):**

| Variable | Why it must not change |
|---|---|
| Document set | Different documents = different results regardless of chunking |
| Embedding model | Changing this changes the vector space entirely |
| LLM and system prompt | Different generation behaviour confounds the comparison |
| Top-K | Changing this affects how many chunks reach the LLM |
| Similarity threshold | Changing this affects which chunks are included |
| Golden dataset | Different questions = incomparable results |
| Temperature | Set to 0 for both runs for reproducibility |

**What changes:** chunk size and overlap only.

**The test plan:**

1. Index the document with Strategy A → run the full golden dataset → record scores
2. Delete the index, re-index with Strategy B → run the identical golden dataset → record scores
3. Compare on all metrics, not just one

**Metrics to compare:**

| Metric | What it tells you |
|---|---|
| Retrieval recall | Did the correct chunk appear in top-K? |
| Context precision | Were the retrieved chunks relevant? |
| Faithfulness | Did the LLM use the chunks correctly? |
| Answer relevance | Did the answer address the question? |
| Latency | Did chunk size affect response time? |

**How to decide which wins:**

No single metric decides. Look at the full picture:
- If recall goes up but faithfulness goes down → smaller chunks help retrieval but hurt generation
- If both recall and faithfulness improve → clear winner
- If results are mixed → the decision depends on which failure mode is worse for your users

**Never decide on one query or one metric.** A configuration that looks better on 3 queries may perform worse across the full 50-question dataset.

</details>

---

## Q20 — CI test suite vs release gate design

**Design a two-tier test strategy: what runs automatically on every commit (CI), and what runs as a release gate before shipping? Explain why each check belongs in its tier.**

<details>
<summary>Answer</summary>

**The principle behind two tiers:**

CI checks must be fast, cheap, and deterministic — they run dozens of times a day. Release gate checks can be slower and more expensive — they run once before shipping.

---

**Tier 1 — CI (runs on every commit)**

| Check | Tool | Why here |
|---|---|---|
| Ingestion smoke test — did all chunks get indexed? | Direct Weaviate query | Fast, binary, catches broken indexing immediately |
| Out-of-scope refusal on 5 negative questions | Dify API + assertion | Fast, deterministic at temperature 0 |
| BLEU / ROUGE-L on golden dataset | pytest + evaluate library | Cheap, deterministic, catches phrasing regression |
| Retrieval recall on golden dataset | Retrieval API + assertion | Fast check that correct chunks still appear in top-K |
| Unit tests on prompt assembly | pytest | Validates context structure before LLM call |

**Tier 2 — Release gate (runs before shipping)**

| Check | Tool | Why here |
|---|---|---|
| RAGAS faithfulness ≥ 0.85 | RAGAS | LLM-based, expensive, slow — not for every commit |
| RAGAS context relevance ≥ 0.80 | RAGAS | Same reason |
| RAGAS answer relevance ≥ 0.80 | RAGAS | Same reason |
| Prompt injection blocked — 100% | Promptfoo | Adversarial, needs curated attack set |
| Latency at peak load (p95 ≤ 3s) | Locust / k6 | Load testing is expensive and environment-sensitive |
| 0 open P1 defects | Manual triage | Human judgement required |

**The key rule:** release gates are not a superset of CI — they test *different things*. CI catches regressions fast. Release gates measure absolute quality. Both are necessary.

</details>

---

## Score guide

| Score | What it means |
|---|---|
| 85–100 | Strong on evaluation — ready to design a real test suite |
| 70–84 | Good foundations — revisit BLEU/ROUGE mechanics and RAGAS precision vs recall |
| 50–69 | Re-read the testing toolkit doc, then retake |
| Below 50 | Work through the glossary evaluation section before this quiz |
