# RAG Evaluation Playbook

A practical guide for executing RAG system evaluation — what to test, how to test it, which metrics to use, and how to interpret results. Complements the [Test Strategy](test-strategy.md) (scope and sign-off) and the [Golden Dataset Guide](../reference/golden-dataset-guide.md) (building your test data).

The approach here is based on three pillars that must work together:

- **Dataset** — representative, high-quality questions with verified answers and source chunks
- **Metrics** — a balanced scorecard across multiple dimensions, not a single number
- **Methodology** — structured techniques for finding specific failure modes

---

## The Two Layers of RAG Testing

Always evaluate retrieval and generation separately. They fail independently and require different metrics.

```
User query
    │
    ▼
[ Retrieval layer ]  ← test this first, without the LLM
    │  top-K chunks
    ▼
[ Generation layer ] ← test this second, given the retrieved chunks
    │
    ▼
Answer
```

If retrieval is broken, generation cannot save it. Fix retrieval first.

---

## Layer 1 — Retrieval Evaluation

Test retrieval in isolation by sending the question to the vector store and checking whether the expected chunk appears in the results. No LLM involved.

### Metrics

| Metric | What it measures | How to calculate |
|---|---|---|
| **Precision@K** | Of the K chunks returned, what fraction were relevant? | relevant chunks in top-K ÷ K |
| **Recall@K** | Of all relevant chunks in the knowledge base, what fraction appeared in top-K? | relevant chunks in top-K ÷ total relevant chunks |
| **MRR (Mean Reciprocal Rank)** | Was the best chunk ranked first, or buried? | average of 1/rank of first relevant chunk across all queries |
| **NDCG (Normalised Discounted Cumulative Gain)** | Ranking quality weighted by position — a chunk at rank 1 counts more than rank 5 | see formula below |

**NDCG simplified:** a chunk retrieved at rank 1 scores full marks; at rank 2, it scores about 63%; at rank 5, about 43%. It penalises burying the right answer.

### Practical target values

| Metric | Minimum acceptable | Good | Excellent |
|---|---|---|---|
| Recall@5 | 0.70 | 0.85 | 0.95+ |
| Precision@5 | 0.40 | 0.60 | 0.80+ |
| MRR | 0.60 | 0.75 | 0.90+ |

### How to run it

For each row in your golden dataset:
1. Submit the `question` to the retrieval API (Dify or Weaviate directly)
2. Collect the top-K returned chunks
3. Check whether `expected_chunk` appears in the results
4. Record rank position if found; record miss if not found
5. Calculate Precision@K, Recall@K, MRR across all rows

Check the Dify retrieval inspector or query Weaviate directly to see raw retrieval results without the LLM step.

---

## Layer 2 — Generation Evaluation

Once retrieval is verified, evaluate answer quality by comparing the system's generated answer to your `reference_answer`.

### The Balanced Metrics Scorecard

Never rely on a single metric. Run all four and compare — disagreement between them reveals specific failure modes.

| Metric | What it catches | What it misses | Speed / cost |
|---|---|---|---|
| **BLEU** | Exact phrasing regression between runs | Paraphrases, synonyms | Fast, free |
| **ROUGE-L** | Key fact coverage via longest common subsequence | Semantic meaning | Fast, free |
| **GPTScore (LLM-as-judge)** | Hallucination, faithfulness, semantic accuracy | Non-deterministic, prompt-sensitive | Slow, costs tokens |
| **NLI / Entailment** | Whether the answer is logically entailed by the retrieved chunk | Does not assess fluency | Medium speed |

**How to interpret disagreement:**

| BLEU/ROUGE | GPTScore | What it means |
|---|---|---|
| High | High | Answer is correct and well-phrased |
| Low | High | Answer is correct but phrased differently — likely fine |
| High | Low | Answer matches reference wording but adds hallucinated content |
| Low | Low | Answer is wrong |

BLEU/ROUGE are good for CI regression checks (fast, deterministic). GPTScore is the release gate check (catches hallucination). Run both, always.

### NLI entailment — what it adds

An NLI (Natural Language Inference) model checks whether the generated answer is *logically entailed* by the retrieved chunk — meaning everything in the answer can be derived from the chunk, with nothing added from outside it. This is a sharper faithfulness test than GPTScore because it targets the specific claim "the answer came from the context," rather than general quality.

RAGAS uses NLI entailment internally for its faithfulness metric.

---

## Testing Techniques

These techniques surface failure modes that standard metric scoring does not catch on its own.

### Prompt Sensitivity Testing

A robust RAG system should return consistent answers regardless of minor query variations. Test this by submitting the same question in multiple surface forms:

| Variation type | Example |
|---|---|
| Case change | `"vacation policy"` → `"VACATION POLICY"` |
| Typo | `"How many vacation days"` → `"How mny vacation days"` |
| Paraphrase | `"What is the annual leave entitlement?"` → `"How much PTO do I get?"` |
| Word order | `"Notice period for resignation?"` → `"If I resign, what notice do I give?"` |

If answers diverge significantly across variations, the retriever is too sensitive to exact phrasing. Root cause is usually embedding model domain mismatch or chunk boundaries splitting the relevant passage.

**How to run it:** pick 10 high-value questions from your golden dataset, write 3 variations of each, run all 30, compare retrieval results and answer scores.

### Hallucination Detection via Fictitious Entities

Ask about things that do not exist in your knowledge base. The system must acknowledge it cannot answer — not fabricate a plausible-sounding response.

Examples for the Orion Technologies handbook:
- `"What is the Orion Platinum Leave scheme?"` (no such scheme)
- `"Who is the Head of People Operations?"` (if not named in the handbook)
- `"What is the policy for remote work in Singapore?"` (if not covered)

A fabricated answer with confident phrasing is your highest-severity finding. Log every instance.

### Non-Response Measurement

The opposite failure: the system says "I don't know" or hedges on questions where the answer is clearly in the knowledge base.

Track non-responses separately on in-scope rows. Calculate:

```
Non-response rate = refusals on in-scope questions ÷ total in-scope questions
```

A rising non-response rate after a prompt change means the system has overcorrected toward caution. Both hallucination rate and non-response rate must stay within threshold for a release to pass.

### Self-Consistency Sampling

RAG systems are non-deterministic — the same question can yield different answers on different runs due to LLM temperature. For critical questions, submit the same query 3–5 times and check:

- Do the answers agree on the key facts?
- Does the retrieved chunk vary between runs?

High factual variance on a stable question signals a temperature setting that is too high, or a retrieval threshold that is borderline — the system is hovering between two chunks.

---

## Running an Evaluation Cycle

A complete evaluation cycle follows this order. Do not skip steps or run them out of sequence.

```
Step 1 — Retrieval evaluation
  Run all golden dataset questions through retrieval only
  Calculate Precision@K, Recall@K, MRR
  Fix any retrieval failures before proceeding

Step 2 — Generation evaluation
  Run all questions end-to-end
  Score each answer with BLEU + ROUGE + GPTScore
  Flag any answers where GPTScore is low but BLEU/ROUGE are high (hallucination signal)

Step 3 — Technique checks
  Run prompt sensitivity test on 10 high-value questions
  Run fictitious entity queries — log any fabricated answers
  Run non-response check on 10 clearly in-scope questions

Step 4 — Rate calculation
  Calculate hallucination rate (out-of-scope rows)
  Calculate non-response rate (in-scope rows)
  Compare both to your established thresholds

Step 5 — Compare to baseline
  Score delta on retrieval metrics vs previous run
  Score delta on generation metrics vs previous run
  Flag any metric that has dropped by more than your regression threshold
```

---

## A/B Configuration Testing

Use the golden dataset to compare two configurations — for example, chunk size 256 vs 512, or embedding model A vs B.

### Rules

1. **Change one thing at a time.** If you change chunking and embedding model simultaneously, you cannot isolate the cause of any score change.
2. **Use the same golden dataset for both runs.** Do not regenerate the dataset between runs — question distribution changes will contaminate the comparison.
3. **Require statistical significance.** With fewer than ~246 golden entries, a score difference of 2–3% is likely noise. See [Golden Dataset Guide](../reference/golden-dataset-guide.md) for sample size guidance.

### What to compare

| Configuration axis | What it affects | Metric to watch |
|---|---|---|
| Chunk size | Retrieval precision vs context completeness | Precision@K, ROUGE-L |
| Chunk overlap | Multi-hop and boundary-spanning questions | Recall@K, MRR |
| Embedding model | Semantic retrieval quality | Recall@K, NDCG |
| Top-K value | How much context is passed to the LLM | Faithfulness (GPTScore), hallucination rate |
| System prompt | Answer style, refusal behaviour | Non-response rate, BLEU |

### Declaring a winner

A configuration is better only if:
- Retrieval metrics are equal or better
- Generation metrics are equal or better
- Hallucination rate has not increased
- Non-response rate has not increased

A configuration that improves answer quality but raises hallucination rate is not a win.

---

## When to Use Which Technique

| Situation | Technique |
|---|---|
| After any config change | Full retrieval evaluation → generation scoring → baseline comparison |
| Before a release | Full evaluation cycle + hallucination detection + non-response check |
| Investigating a user complaint | Prompt sensitivity testing on the failing query type |
| Comparing chunking strategies | A/B test with same golden dataset, retrieval metrics focus |
| Checking a new embedding model | A/B test, Recall@K and NDCG focus |
| Suspecting the LLM is fabricating | GPTScore + fictitious entity probes + NLI entailment |
| Tuning the system prompt | Non-response rate tracking before and after |
