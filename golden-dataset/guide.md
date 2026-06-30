# Golden Dataset Guide

A **golden dataset** is a curated set of question / answer / source-chunk triples where you have manually verified what the correct answer is and which chunk should have been retrieved to produce it.

Without one, RAG testing is impressionistic — you run a query, read the answer, and think "that seems right." A golden dataset turns that into a repeatable measurement: you can detect regressions, compare configurations, and automate scoring.

---

## Dataset Quality Checklist — The 5 D's

Before treating any dataset as your baseline, verify it passes all five checks. (Framework from Google's *A Practical Guide for Evaluating LLMs and LLM-Reliant Systems*, 2025.)

| D | Check | What failure looks like |
|---|---|---|
| **Defined scope** | Questions match what real users actually ask | You tested "what is the PTO policy?" but users actually ask "how do I book time off?" |
| **Demonstrative of production** | Query style mirrors real usage — vague, misspelled, colloquial where appropriate | Every question is perfectly phrased; real users never write that way |
| **Diverse** | All query types represented: factual, multi-hop, comparative, out-of-scope, adversarial | 90% of questions are simple factual lookups |
| **Decontaminated** | Questions not generated from the exact text the model was trained on | Synthetic questions copy phrases verbatim from the source, making retrieval trivially easy |
| **Dynamic** | Dataset is updated when the knowledge base changes | Baseline was built six months ago; three documents have since been replaced |

---

## Structure of a Golden Dataset Row

Each record has four required fields and several optional ones.

**Required**

| Field | What it is | Example |
|---|---|---|
| `question` | The user query | `"How many vacation days do new employees get?"` |
| `reference_answer` | The ideal answer, written by you | `"New employees receive 10 days of paid vacation in their first year."` |
| `expected_chunk` | The exact passage that should be retrieved | `"Full-time employees accrue 10 days of PTO in year one..."` |
| `source_doc` | Document name and page | `orion-handbook.pdf, p.12` |

**Optional but useful**

| Field | Purpose |
|---|---|
| `query_type` | `factual`, `comparative`, `multi-hop`, `out-of-scope` |
| `difficulty` | `easy`, `medium`, `hard` |
| `notes` | Why this case is interesting or tricky |

---

## Approach 1 — Manual (up to ~5 documents)

Best when you need high-quality, hand-verified baselines. Does not scale beyond a small knowledge base.

### Step-by-step

**Step 1 — Coverage mapping.** Read through your knowledge base and list the key facts, policies, and procedures it contains. These become your test surface. Do not write questions yet — just inventory what is there.

**Step 2 — Write diverse questions.** For each topic, write at least one of each query type:

| Query type | Description | Example |
|---|---|---|
| Factual | Single-hop, one correct answer | `"What is the notice period for resignation?"` |
| Comparative | Requires contrasting two things | `"How does leave differ for part-time vs full-time staff?"` |
| Multi-hop | Answer requires combining two passages | `"Can a probationary employee take parental leave?"` |
| Out-of-scope | Answer is NOT in the document — system should say so | `"What is the CEO's salary?"` |
| Adversarial | Phrased to confuse the retriever | `"Is there any flexibility around the vacation policy?"` when the doc says it is fixed |
| Fictitious entity | Asks about something that does not exist — system must not fabricate | `"What is the Orion Technologies Platinum Leave scheme?"` (no such scheme exists) |

**Step 3 — Find the ground truth chunk.** For each question, locate the exact sentence(s) in the source document that contain the answer. Paste them in as `expected_chunk`. This is what you use to measure retrieval recall.

**Step 4 — Write the reference answer.** Write the ideal answer in 1–3 sentences, based only on what the chunk says. Do not add information the chunk does not contain.

**Step 5 — Tag and validate.** Label query type and difficulty. Then read each Q&A cold — does the reference answer actually follow from the expected chunk? Fix anything ambiguous.

---

## Approach 2 — LLM-generated + human spot-check (5–200 documents)

Feed each chunk to an LLM and ask it to generate question / answer / chunk triples. A human reviews a sample (10–20%) to catch bad generations before they corrupt your baseline. This is the most common real-world approach.

### Generation prompt template

```
Given this passage:
"{chunk_text}"

Generate 2 questions that:
- Are answerable purely from this passage
- Would be realistic user queries
- Are not too similar to each other

Return JSON:
[
  {"question": "...", "answer": "...", "chunk": "..."}
]
```

Run this across all chunks, collect output, and you have a synthetic golden dataset in minutes.

---

## Approach 3 — Fully automated with quality filters (200+ documents)

Generate synthetically, then apply automated quality filters instead of human review. Human spot-check drops to ~5%. Used at scale in production RAG teams.

RAGAS has a built-in `TestsetGenerator` that combines a generator LLM and a critic LLM: the generator produces questions, the critic scores their quality before you ever see them. It classifies each question as simple, multi-hop, or reasoning — giving you a diversified, quality-filtered dataset without writing filter code.

For a full explanation of how RAGAS works internally, the three components, question types, what it cannot generate, and the Python concepts needed to follow the setup, see **[Introduction to RAGAS](../docs/testing/ragas-intro.md)**.

---

## Choosing Between Approach 2 and Approach 3

Use Approach 3 (RAGAS) as your base, then fill the gaps with Approach 2.

| | Approach 2 (custom code + LLM) | Approach 3 (RAGAS) |
|---|---|---|
| Control over prompt | Full — you write it | Limited — RAGAS controls generation |
| Question diversity | You must engineer it | Built-in: simple, multi-hop, reasoning |
| Quality filtering | You write the filters | Critic LLM does it automatically |
| Cost | Cheaper — one LLM call per chunk | More expensive — generator + critic per question |
| Adversarial / fictitious entity questions | You add them manually | RAGAS will not generate these |
| Setup effort | More code | Less code |

**Recommended combination:** use RAGAS to generate the bulk of your factual, multi-hop, and reasoning questions, then manually write the out-of-scope and fictitious entity rows and append them to the RAGAS output. RAGAS only generates questions that are answerable from the document — it cannot produce the adversarial and refusal-testing rows you need for a complete golden dataset.

---

## When the Source is Not a Document

The generation process is the same regardless of where your knowledge lives. The generator only needs text — how you get that text is your extraction layer.

```
Source → extract text → chunk → generate Q&A → golden dataset
```

The extraction step is the only thing that changes:

| Source type | Extraction approach |
|---|---|
| PDF / Word / Markdown | Parse file to plain text, then chunk |
| Relational database | Query rows, concatenate relevant columns into a text string per record |
| REST API | Call the endpoint, extract the content fields from the JSON response |
| Structured data (tables, catalogues) | Convert each record to a readable prose sentence before chunking |

**Structured data needs a prose conversion step.** An LLM generates better questions from readable text than from raw JSON or CSV. Before passing a structured record to the generator, convert it to a sentence:

```
Instead of: {"leave_type": "annual", "days": 15, "eligibility": "full-time"}

Send:       "Full-time employees are entitled to 15 days of annual leave per year."
```

Write a small conversion function that maps your record format to plain English, then feed the result into the same generation pipeline.

**Multi-record questions are the hard case.** When an answer requires joining multiple records — for example, "what leave policy applies to a part-time employee on probation?" — pre-join the relevant records into a single text block before chunking, or write those questions manually and mark them as `multi-hop`. Do not expect the generator to infer cross-record relationships automatically.

---

## Practical Workflow for Large Knowledge Bases

```
1. Chunk your documents (same chunking config as your RAG pipeline)
2. Sample chunks — not every chunk needs a question; aim for coverage, not exhaustion
3. Run LLM generation over sampled chunks → raw synthetic dataset
4. Apply automated filters (remove generic, unanswerable, duplicate questions)
5. Human spot-check 10–20% of what remains
6. Lock the validated set as your golden baseline
7. Re-generate only when documents change significantly
```

> The golden dataset does not need to cover every chunk. It needs to cover your **risk surface**: the topics users actually query, the edge cases that could fail, and a representative sample of everything else. 50–100 high-quality questions often beat 500 low-quality synthetic ones.

---

## How Many Entries Do You Need?

The minimum depends on what you want to do with the dataset.

| Use case | Minimum entries | Why |
|---|---|---|
| Sanity check after a config change | 20–50 | Directional signal only — not statistically reliable |
| Detect regressions in CI | 50–100 | Catches obvious degradation; misses subtle shifts |
| Statistically valid A/B comparison | ~246 | 95% confidence, 5% margin of error at 80% expected accuracy |
| Release gate with compliance risk | 300+ | Tighter margin of error; covers tail failure modes |

The ~246 figure comes from a standard sample size formula at 95% confidence with a 5% margin of error. Below 50 entries, differences between two configurations are likely noise, not signal — do not make configuration decisions from a small set.

---

## Known Failure Modes in Synthetic Generation

| Failure mode | What it looks like | How to catch it |
|---|---|---|
| Lexical overlap | Question uses the same rare words as the chunk — trivially easy to retrieve | Filter questions that copy >3 consecutive words from the chunk |
| Unanswerable answers | LLM writes an answer that goes beyond what the chunk says | Check: can every sentence of the answer be found in the chunk? |
| Generic questions | `"What is discussed in this passage?"` — useless as a test | Filter questions that contain "this passage" or are shorter than 6 words |
| Clustering bias | Most questions come from the same few topics | Check distribution across documents |

---

## How the Golden Dataset Powers Regression Testing

Once you have the dataset, every test run does this:

```
For each row:
  1. Send question to RAG system
  2. Check: did expected_chunk appear in the retrieved top-K?  → retrieval recall
  3. Compare generated answer to reference_answer via BLEU / ROUGE / GPTScore → answer quality
  4. Log scores

Compare scores to previous run → any drop = regression
```

| What it catches | How |
|---|---|
| Wrong chunk retrieved | `expected_chunk` not in top-K results |
| Correct chunk retrieved but answer hallucinated | BLEU / ROUGE / GPTScore drop vs reference |
| Regression after config change | Score delta between runs |
| Out-of-scope handled correctly | System says "I don't know" instead of fabricating |
| Hard queries that always fail | Consistently low scores on multi-hop or adversarial rows |

### Track two failure rates separately

Making the system more cautious to reduce hallucinations often causes a new problem: it starts refusing to answer questions it actually knows. Track both rates on every run:

| Rate | Definition | Rows that measure it |
|---|---|---|
| **Hallucination rate** | System answers confidently when it should not know | Out-of-scope and fictitious-entity rows |
| **Non-response rate** | System refuses or hedges on questions clearly in the knowledge base | In-scope factual and comparative rows |

If hallucination rate drops but non-response rate climbs after a prompt change, the change overcorrected. A good release gate requires both rates to be within acceptable thresholds.

