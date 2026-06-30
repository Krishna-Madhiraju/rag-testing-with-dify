# Advanced Evaluation Metrics: BERTScore, MRR, and NDCG

BLEU, ROUGE-L, GPTScore, and Recall@K cover the basics. But each has a blind spot. BERTScore fills the gap between lexical and LLM-based generation scoring. MRR and NDCG fill the gap between binary retrieval checking and rank quality measurement. This document explains how each works, what it catches, and when to use it.

---

## BERTScore

### The gap it fills

BLEU and ROUGE are purely lexical — they count word overlap. They give zero credit for paraphrases, synonyms, or reordered sentences. GPTScore captures semantics and hallucination but costs an LLM call per row. BERTScore sits between the two: semantic similarity, no LLM required.

### How it works mechanically

BERTScore uses a pre-trained language model (BERT or similar) to convert every token in both the reference answer and the candidate answer into a **contextual embedding** — a vector that represents that word in its surrounding context.

It then computes **pairwise cosine similarity** between tokens across the two texts:

```
Reference: "Full-time employees receive 10 days of paid sick leave per year."
Candidate: "Orion staff are entitled to 80 hours of annual illness leave."

For each candidate token, find the most similar reference token:
  "staff"    → "employees"   → similarity 0.91
  "entitled" → "receive"     → similarity 0.87
  "illness"  → "sick"        → similarity 0.95
  "annual"   → "year"        → similarity 0.89
```

**BERTScore Precision** — for each candidate token, its maximum similarity to any reference token, averaged across all candidate tokens.

**BERTScore Recall** — for each reference token, its maximum similarity to any candidate token, averaged across all reference tokens.

**BERTScore F1** — harmonic mean of Precision and Recall. This is the number you use in practice.

The reason "staff" and "employees" score ~0.91 is that BERT was trained on billions of sentences where both words appear in identical grammatical and semantic contexts. The model learned they are interchangeable. BLEU would score them as zero overlap.

### What it catches that BLEU and ROUGE miss

LLMs never repeat the exact wording of a chunk. They paraphrase. BLEU and ROUGE penalise every paraphrase. BERTScore does not.

```
Reference:  "Employees are entitled to 10 days of paid sick leave annually."
Candidate:  "Staff members can take up to 10 sick days each year at full pay."

BLEU:       ~0.12  (almost no n-gram overlap)
ROUGE-L:    ~0.35  (LCS captures "10", "sick", "days", "year")
BERTScore:  ~0.91  (semantically equivalent — same facts, different wording)
```

BERTScore correctly identifies that these two sentences say the same thing. BLEU treats them as almost unrelated.

### What BERTScore misses

BERTScore measures **semantic similarity to the reference answer**, not factual grounding. It cannot detect hallucination. It cannot tell you whether the answer is based on the retrieved chunk or on training data.

```
Reference:  "Employees are entitled to 10 days of paid sick leave annually."
Candidate:  "Orion provides generous sick leave benefits for all permanent employees."

BERTScore:  ~0.82  (right domain, right vocabulary — scores well)
Problem:    The key fact — 10 days — is missing. The answer is vague, not wrong.
            BERTScore rewards vocabulary similarity without checking for the number.

GPTScore:   Low faithfulness — the answer claims "generous" benefits without
            grounding that in the specific figure from the chunk.
```

A high BERTScore tells you the answer sounds like it is about the right topic. It does not tell you whether the answer is accurate. GPTScore remains the tool for catching hallucination and vagueness.

### Where BERTScore sits in the generation metrics stack

| Metric | Catches paraphrases? | Catches hallucination? | Cost |
|---|---|---|---|
| BLEU | No | No | Near zero |
| ROUGE-L | No | No | Near zero |
| **BERTScore** | **Yes** | **No** | **Low** |
| GPTScore | Yes | Yes | High |

BERTScore is most useful when your LLM regularly paraphrases the source content — which is always true. It replaces ROUGE-L as the generation coverage check when you want semantic rather than lexical matching. It does not replace GPTScore for faithfulness audits.

---

## MRR — Mean Reciprocal Rank

### The gap it fills

Recall@K is binary: did the right chunk appear anywhere in the top-K results? It treats rank 1 and rank 5 identically — both count as "found." But rank matters. The LLM reads retrieved chunks in order. A relevant chunk buried at position 5 under four irrelevant chunks is far less likely to influence the answer than the same chunk at position 1. Recall@K cannot see this. MRR can.

### How it works mechanically

For each query, find the position of the first relevant chunk. Take the reciprocal of that position. Average across all queries.

```
Query 1: right chunk at rank 1 → 1/1 = 1.00
Query 2: right chunk at rank 3 → 1/3 = 0.33
Query 3: right chunk at rank 5 → 1/5 = 0.20

MRR = (1.00 + 0.33 + 0.20) / 3 = 0.51
```

MRR of 1.0 means the right chunk always ranks first. MRR of 0.33 means the right chunk averages position 3. MRR of 0.20 means it averages position 5 — technically retrieved, but barely.

### What MRR tells you

A configuration change that keeps Recall@K stable but drops MRR is a real quality regression. The right chunks are still being found, but they now rank lower — buried beneath noisier results. The LLM receives the relevant content, but only after processing irrelevant context first.

```
Config A: chunk found at rank 1 → MRR contribution 1.00
Config B: chunk found at rank 4 → MRR contribution 0.25

Recall@K: both pass (chunk found in top-5)
MRR:      Config A is four times better than Config B
```

### What MRR misses

MRR only cares about the *first* relevant chunk. For multi-hop questions that need two chunks, MRR scores only whether the highest-ranked relevant chunk was near the top. It ignores whether the second relevant chunk was also retrieved and ranked well. For multi-hop coverage, NDCG is the right tool.

---

## NDCG — Normalized Discounted Cumulative Gain

### The gap it fills

MRR handles one relevant chunk. NDCG handles three things MRR cannot:

- **Multiple relevant chunks** — both chunks needed for a multi-hop question each contribute to the score
- **Rank discounting** — a logarithmic penalty that rewards getting relevant chunks to the top positions rather than just anywhere in top-K
- **Graded relevance** — if one chunk is more relevant than another, you can weight it higher

### How the discounting works

Relevance at position k is divided by log₂(k + 1). This logarithmic curve means the reward drops steeply from position 1 to 2, then more gradually from 2 to 5:

| Position | Discount factor |
|---|---|
| 1 | 1/log₂(2) = 1.00 |
| 2 | 1/log₂(3) = 0.63 |
| 3 | 1/log₂(4) = 0.50 |
| 4 | 1/log₂(5) = 0.43 |
| 5 | 1/log₂(6) = 0.39 |

The raw score (DCG) sums each relevant chunk's discounted contribution. You then normalise it against the ideal score — what DCG would be if all relevant chunks ranked first (IDCG). The result is always 0 to 1.

**NDCG = DCG / IDCG**

### Concrete Orion example: a multi-hop question

Query: "Can a new employee on probation take parental leave?"
Requires two chunks — the probation policy and the parental leave policy.

**Config A** — both relevant chunks found, one near the top:

| Rank | Chunk | Relevant? | Discount | Contribution |
|---|---|---|---|---|
| 1 | Parental leave policy | Yes | 1.00 | 1.00 |
| 2 | Irrelevant | No | — | 0 |
| 3 | Probation policy | Yes | 0.50 | 0.50 |
| 4 | Irrelevant | No | — | 0 |
| 5 | Irrelevant | No | — | 0 |

DCG = 1.50 · IDCG (ideal: both at positions 1 and 2) = 1.63 · **NDCG = 0.92**

**Config B** — both found, but buried:

| Rank | Chunk | Relevant? | Discount | Contribution |
|---|---|---|---|---|
| 1 | Irrelevant | No | — | 0 |
| 2 | Irrelevant | No | — | 0 |
| 3 | Parental leave policy | Yes | 0.50 | 0.50 |
| 4 | Irrelevant | No | — | 0 |
| 5 | Probation policy | Yes | 0.39 | 0.39 |

DCG = 0.89 · IDCG = 1.63 · **NDCG = 0.55**

Both configurations pass Recall@K — both relevant chunks appear in the top 5. But NDCG exposes that Config B is substantially worse. The LLM in Config B receives both relevant chunks only after processing two irrelevant ones first, and they rank so far down that the LLM is less likely to combine them correctly.

---

## MRR vs NDCG — When to Use Which

| Metric | Use when |
|---|---|
| MRR | One correct chunk per question; you want to know if it consistently ranks first |
| NDCG | Multi-hop questions needing multiple chunks; you want rank quality across the full list |

For the Orion HR Assistant:
- Factual and paraphrase rows → MRR (one relevant chunk, rank quality matters)
- Multi-hop rows → NDCG (two chunks required, both must rank well)

---

## The Complete Metrics Stack

With BERTScore, MRR, and NDCG added, the picture is complete. Every failure mode now has a metric that can surface it.

**Generation metrics:**

| Metric | What it measures | Catches paraphrases | Catches hallucination | Cost |
|---|---|---|---|---|
| BLEU | Lexical n-gram precision | No | No | Near zero |
| ROUGE-L | Lexical LCS coverage | No | No | Near zero |
| BERTScore | Semantic similarity to reference | Yes | No | Low |
| GPTScore | Semantic quality + faithfulness | Yes | Yes | High |

**Retrieval metrics:**

| Metric | What it measures | Handles multiple chunks | Rank-sensitive | Cost |
|---|---|---|---|---|
| Recall@K | Was the chunk found at all? | No | No | Near zero |
| MRR | Did it rank near the top? | No (first hit only) | Yes | Near zero |
| NDCG | Rank quality across all relevant chunks | Yes | Yes | Near zero |

**How to read disagreements between metrics:**

- BLEU/ROUGE low, BERTScore high → LLM paraphrased correctly; lexical metrics penalised it unfairly
- BERTScore high, GPTScore faithfulness low → answer sounds right but adds facts not in the chunk
- Recall@K passes, MRR low → right chunk found but buried; retrieval ranking degraded
- MRR stable, NDCG drops → single-chunk retrieval is fine; multi-hop is broken (second chunk now ranks poorly)

Disagreements between metrics are the most informative signal in evaluation. When two metrics point in opposite directions, that is where the interesting failure is.

---

## See Also

- [RAGAS Evaluation Metrics](ragas-evaluation-metrics.md) — Faithfulness, Answer Relevancy, Context Precision, Context Recall
- [RAG Evaluation Playbook](rag-evaluation-playbook.md) — when to run which metrics, how to interpret results across a full run
- [Comparing RAG Configurations](comparing-rag-configurations.md) — how to use these metrics together to decide between two configurations
- [Why RAG Testing Is Harder Than Normal API Testing](rag-vs-api-testing.md) — why multiple metrics across two surfaces are necessary
