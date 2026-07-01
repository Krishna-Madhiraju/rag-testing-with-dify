# RAGAS Evaluation Metrics

RAGAS provides four standardised metrics for evaluating RAG systems. They are the industry-converged way to measure RAG quality — your scores are comparable across teams, tools, and benchmarks.

**What makes RAGAS different from BLEU/ROUGE/GPTScore:**

- BLEU and ROUGE compare words. RAGAS compares meaning.
- Your custom GPTScore judges the answer. RAGAS also judges the retriever.
- RAGAS metrics have published definitions — "faithfulness 0.82" means the same thing to everyone who uses RAGAS.

---

## The Four Metrics

### Faithfulness — did the answer stay inside the retrieved context?

**How it works:**

RAGAS breaks the generated answer into individual factual statements. For each statement, it asks an LLM: "can this be inferred from the retrieved chunks?" Faithfulness is the fraction of statements that are supported.

```
Faithfulness = statements supported by context ÷ total statements in answer
```

**Concrete example:**

```
Answer: "Orion matches 100% of contributions up to 5% of salary.
         This benefit started in 2019."

Statement 1: "Orion matches 100% up to 5% of salary" → in the chunk → ✓
Statement 2: "This benefit started in 2019"           → not in the chunk → ✗

Faithfulness = 1 / 2 = 0.50
```

**What it catches that BLEU misses:** BLEU compares the whole answer to a reference text. Faithfulness hunts for specific unsupported claims regardless of what the reference says. A hallucinated date buried in an otherwise-accurate answer is invisible to BLEU but drops faithfulness immediately.

**What it misses:** It does not tell you whether the answer is complete — only whether what it says is grounded.

---

### Answer Relevancy — does the answer actually address the question?

**How it works:**

RAGAS generates N artificial questions from the answer itself using an LLM. It then embeds those questions and measures their cosine similarity to the original question. If the answer is relevant, questions derived from it should semantically resemble the question that was asked.

```
Answer Relevancy = mean cosine similarity(generated questions, original question)
```

**Concrete example:**

```
Original question: "How many sick days do full-time employees get?"

Questions generated from the answer:
  → "How much paid sick leave do employees receive annually?"
  → "When does sick leave reset at Orion?"

High cosine similarity to original → high Answer Relevancy
```

If the answer wanders off-topic — correct facts, wrong question — the generated questions will point in a different direction, dropping cosine similarity.

**Key advantage:** This metric needs no reference answer. You can run it on live traffic without a golden dataset.

**What it misses:** It does not check factual accuracy — an irrelevant but factually correct answer still scores low.

---

### Context Precision — were the retrieved chunks actually useful?

**How it works:**

For each chunk your retriever returned (top-K), RAGAS asks: "given the question and the correct answer, was this chunk needed to produce the answer?" It then computes a rank-weighted precision — relevant chunks at rank 1 contribute more than relevant chunks at rank 4.

```
Context Precision = rank-weighted fraction of retrieved chunks that were relevant
```

**Concrete example:**

```
Top-3 retrieved chunks for "What is the 401k match?":
  Rank 1: "Orion matches 100% up to 5% of base salary. Vests over 3 years." → relevant ✓
  Rank 2: "Orion is publicly traded on NASDAQ under ticker ORNX."           → irrelevant ✗
  Rank 3: "Employer match vests 33% year 1, 67% year 2, 100% year 3."      → relevant ✓

Context Precision is penalised because the irrelevant chunk sits at rank 2,
pushing the relevant rank-3 chunk further down.
```

**What low precision means:** The retriever is pulling noisy chunks. That dilutes the LLM's context window and pushes it toward using training data instead of the document — which causes hallucinations.

**What it misses:** It does not tell you whether the retriever found *all* the relevant chunks — only whether what it did find was useful.

---

### Context Recall — did the retriever find everything needed?

**How it works:**

RAGAS breaks the reference answer into individual statements, then checks whether each statement can be attributed to something in the retrieved context. Context Recall is the fraction of reference answer statements that the retrieved chunks can support.

```
Context Recall = reference statements attributable to retrieved context ÷ total reference statements
```

**Concrete example:**

```
Reference answer has 3 statements:
  "match is 100% up to 5%"         → found in retrieved chunk → ✓
  "match vests over 3 years"       → found in retrieved chunk → ✓
  "33% vests after year one"       → NOT in any retrieved chunk → ✗

Context Recall = 2 / 3 = 0.67
```

**What low recall means:** The retriever missed chunks. Even a perfect LLM cannot produce a complete answer from incomplete context.

**What it misses:** It does not tell you whether what was retrieved was relevant — only whether what was needed was present.

---

## What Each Metric Needs

Different metrics require different inputs — this matters when you run them:

| Metric | Question | Actual answer | Retrieved chunks | Reference answer |
|---|:---:|:---:|:---:|:---:|
| Faithfulness | ✓ | ✓ | ✓ | — |
| Answer Relevancy | ✓ | ✓ | ✓ | — |
| Context Precision | ✓ | — | ✓ | ✓ |
| Context Recall | ✓ | — | ✓ | ✓ |

Faithfulness and Answer Relevancy need no reference answer — run them on any live traffic.
Context Precision and Context Recall require a reference answer — run them against your golden dataset.

---

## How the Four Metrics Work Together

No single metric tells the full story. Read them as a system:

| Pattern | What it means |
|---|---|
| High Faithfulness, low Context Recall | LLM stayed loyal to the chunks it got, but the retriever missed key passages — fix retrieval |
| High Context Recall, low Faithfulness | Retriever found the right chunks, but the LLM added things not in them — fix generation or system prompt |
| Low Context Precision, low Faithfulness | Noisy retrieval is leading the LLM to hallucinate — fix retrieval first |
| High Precision, high Recall, low Answer Relevancy | Right chunks retrieved, answer is grounded, but it doesn't address the question — fix the prompt |
| All four high | Healthy pipeline |

---

## How RAGAS Differs from What You Already Have

| What you have | What it measures | RAGAS equivalent |
|---|---|---|
| `chunk_found` in CSV | Did the expected chunk come back? | Context Recall (more precise — checks every statement) |
| BLEU / ROUGE | Answer wording matches reference | — (RAGAS measures meaning, not wording) |
| GPTScore faithfulness | LLM judge: is answer grounded? | Faithfulness (same idea, standardised definition) |
| GPTScore relevance | LLM judge: does it answer the question? | Answer Relevancy (RAGAS uses embedding similarity, not LLM opinion) |

RAGAS does not replace what you built — it standardises it. Your GPTScore is bespoke to your prompt; RAGAS faithfulness is a published metric others use, so your scores are comparable across systems.

---

## Running RAGAS

The script is at `golden-dataset/ragas/ragas_eval.py` — self-contained: it only reads `golden-dataset/runs/run-001.csv` and never modifies it, writing its own scored CSV and summary into `golden-dataset/ragas/results/`.

```bash
# Install (current RAGAS, 0.4.x — the API changed significantly since 0.1/0.2)
python3.11 -m pip install ragas sentence-transformers anthropic

# Add to your .env file:
# ANTHROPIC_API_KEY=sk-ant-...   ← same key used by gptscore/score_gptscore.py.
# RAGAS's judge is Claude, and embeddings run locally (sentence-transformers) — no OpenAI key needed.

# Run all four metrics against run-001.csv
python3.11 golden-dataset/ragas/ragas_eval.py

# Run only the two that need no reference answer (works on any live traffic)
python3.11 golden-dataset/ragas/ragas_eval.py --metrics=faith,rel
```

Results land in `golden-dataset/ragas/results/run-001-scores.csv` with a summary in `golden-dataset/ragas/results/summary.md`.

---

## Cost Note

RAGAS makes one or more LLM API calls per sample per metric. With 21 rows and four metrics, expect roughly $0.02–$0.05 on `gpt-5.4-nano`. Context Precision and Context Recall skip out-of-scope and fictitious-entity rows (no reference answer to compare against).

---

## See Also

- [Introduction to RAGAS](ragas-intro.md) — the dataset generation side: how RAGAS builds a golden dataset automatically from your documents
- [Golden Dataset Guide](../../golden-dataset/guide.md) — how to build and validate a golden dataset manually or synthetically
- [RAG Evaluation Playbook](rag-evaluation-playbook.md) — how to run a full evaluation end to end and interpret the results
