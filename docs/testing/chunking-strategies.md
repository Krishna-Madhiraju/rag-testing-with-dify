# Chunking Strategies and Their Effect on Test Outcomes

Chunking is the step where a document is split into smaller pieces before embedding and indexing. It happens once at ingestion time. The choices you make here — how big each piece is, how much pieces overlap, and where boundaries are drawn — have a direct, measurable effect on retrieval quality. This document explains the mechanism behind each setting, the failure modes each creates, and how to measure the impact using your golden dataset.

---

## Why Chunking Matters for Testing

The chunk is the unit of retrieval. When a question arrives, the vector store returns whole chunks — never sentences extracted from inside a chunk, never a merge of partial chunks. This single fact has three important consequences for testers:

1. **If the answer is inside a chunk, that chunk must be retrieved** — or the answer is lost
2. **If the answer spans two chunks, both chunks must be retrieved** — or the answer is incomplete
3. **If a chunk contains the answer plus a lot of unrelated text, the LLM has to filter noise** — and sometimes it fails

Every chunking decision is a trade-off between these three risks. There is no setting that eliminates all of them.

---

## The Three Settings That Control Chunking

### Chunk Size

How many characters (or tokens) each chunk contains.

**Too small:** answers that span more than one sentence get split across multiple chunks. The retriever fetches one chunk, misses the other half, and the LLM produces an incomplete answer.

```
Example — chunk size 200 characters:
  Chunk A: "Full-time employees receive 10 days (80 hours) of paid sick"
  Chunk B: "leave per calendar year. Sick leave does not carry over."

Question: "Does sick leave carry over?"
Retriever returns Chunk A (highest similarity to "sick leave")
Chunk B is not retrieved → LLM cannot answer the carryover question
```

**Too large:** each chunk covers many topics. When retrieved, most of the text is irrelevant to the specific question. The LLM must work harder to locate the relevant sentence among noise — which increases the chance it hallucinates or ignores the document and falls back on training data.

```
Example — chunk size 2000 characters:
  Chunk covers PTO, sick leave, bereavement leave, and parental leave
  Question: "How many sick days do full-time employees get?"
  Chunk is retrieved — but 75% of it is about other leave types
  Context Precision drops; LLM may mix up the figures between leave types
```

**Common starting points by document type:**

| Document type | Recommended chunk size |
|---|---|
| Dense policy / HR handbook | 300–500 characters |
| Technical documentation | 500–800 characters |
| Long narrative / reports | 800–1200 characters |
| Structured tables or short records | 200–300 characters |

These are starting points, not rules. Measure with your golden dataset and adjust.

---

### Chunk Overlap

How many characters from the end of one chunk are copied into the beginning of the next.

Without overlap, a sentence that straddles a chunk boundary is split in two. Whichever side the retriever fetches, it gets half a sentence — which the LLM may misread or ignore.

With overlap, that boundary sentence appears in both chunks. Either chunk retrieved gives the LLM the complete sentence.

```
No overlap — chunk boundary falls mid-policy:
  Chunk A: "...PTO must be scheduled with manager approval."
  Chunk B: "Taking into account business needs and team coverage, employees..."

  Question: "Does manager approval for PTO consider business needs?"
  Chunk A: has "manager approval" but not the business needs context
  Chunk B: has "business needs" but not "manager approval"
  Neither chunk alone answers the question fully

50-character overlap:
  Chunk A: "...PTO must be scheduled with manager approval."
  Chunk B: "manager approval. Taking into account business needs and team coverage..."

  Now Chunk B contains both "manager approval" AND "business needs"
  Either chunk can answer the question
```

**Typical overlap:** 10–15% of chunk size. For a 500-character chunk, that means 50–75 characters of overlap. Going above 20% adds redundancy without meaningfully improving boundary coverage, and wastes context window space.

---

### Chunking Strategy

How the boundaries are decided — where in the text the splits happen.

#### Fixed-size (character-based)
Split every N characters, regardless of content. Simple and fast, but can cut sentences mid-thought.

```
Text: "The employer match vests over 3 years: 33% after year 1, 67% after year 2,
       100% after year 3."
Chunk size: 50 characters
Split: "The employer match vests over 3 years: 33% af" / "ter year 1, 67% after year 2..."
```
The word "after" is split across chunks. The vector representation of the first chunk is semantically broken.

#### Fixed-size (token-based)
Split every N tokens (words + punctuation) instead of characters. More predictable for the embedding model since embeddings are trained on tokens, not characters. Still doesn't respect sentence structure.

#### Sentence-aware
Split at sentence endings (`.`, `!`, `?`). Never cuts mid-sentence. Produces variable chunk sizes — a paragraph with long sentences produces a larger chunk than one with short sentences — but every chunk contains complete, coherent units of meaning.

This is usually a better starting point than fixed-size for policy documents, where sentences contain the unit of fact.

#### Recursive character splitting (Dify's default)
Try to split at progressively smaller units: paragraph breaks → sentence endings → words → individual characters. Whichever produces a chunk closest to the target size without exceeding it is used.

This produces chunks that almost always end at a natural boundary (usually a paragraph or sentence), while still hitting close to the target size. It is the best general-purpose strategy for mixed documents.

#### Semantic chunking
Use an embedding model during ingestion to detect where the topic changes — split when the cosine similarity between adjacent sentences drops below a threshold.

The advantage: every chunk is about one topic. A question about 401k matching will not retrieve a chunk that mixes 401k and health insurance.

The trade-off: requires an extra embedding call per sentence during ingestion (slower and more expensive), and the chunk sizes are unpredictable. A long discussion of one topic produces a very large chunk; a rapid topic shift produces many small ones.

**Summary of strategies:**

| Strategy | Boundary respect | Size consistency | Ingestion cost | Best for |
|---|---|---|---|---|
| Fixed-size (char) | Poor | High | Low | Quick prototypes |
| Fixed-size (token) | Poor | High | Low | Token-budgeted pipelines |
| Sentence-aware | Good | Medium | Low | Policy / HR documents |
| Recursive (Dify default) | Good | Medium | Low | General-purpose |
| Semantic | Excellent | Low | High | Topic-dense, multi-subject docs |

---

## How Each Setting Creates Specific Test Failures

Different chunking problems show up in different query types. This is why your golden dataset has multiple query types — they are designed to surface different failure modes.

### Multi-hop questions are the canary for chunk size

Multi-hop questions require combining two passages. If chunk size is too small, the two relevant passages may each be split across multiple chunks — and retrieving any single chunk gives an incomplete picture.

```
Question: "Can a new employee on probation take parental leave?"
Requires:
  Chunk about probation period: "...access to all standard benefits but
    may not participate in tuition reimbursement or the promotion cycle."
  Chunk about parental leave:   "Primary Caregiver Leave: 20 weeks,
    100% of base salary. All full-time employees."

If chunk size is 200 chars, the probation policy might be split across:
  Chunk A: "...access to all standard benefits but may not"
  Chunk B: "participate in tuition reimbursement or the promotion cycle."
  Chunk C: "Primary Caregiver Leave: 20 weeks, 100% of base"
  Chunk D: "salary. All full-time employees."

The retriever returns Chunks A and C — incomplete on both sides.
```

**Signal:** if multi-hop Recall@K drops after reducing chunk size, the chunks are too small for your document's sentence length.

### Paraphrase questions expose boundary and overlap failures

Paraphrase questions ask the same thing as a factual question but with different wording. They surface embedding sensitivity — but they also surface boundary problems, because a paraphrased question may match a different part of the relevant chunk.

```
Factual: "How many sick days do full-time employees get?"
→ matches "10 days (80 hours) of paid sick leave" directly

Paraphrase: "If I'm not feeling well, how much paid time off can I take?"
→ must match semantically to the sick leave chunk
→ if the sick leave chunk has "not feeling well" split at its boundary,
  the retriever may fetch the chunk that lacks the "10 days" answer
```

**Signal:** if paraphrase Recall@K is noticeably lower than factual Recall@K, check chunk boundaries around the most-asked topics. Increasing overlap usually closes this gap.

### Factual questions are your precision baseline

Simple factual questions — single answer, single chunk — should always be retrievable. If factual recall drops, something fundamental broke: the chunk containing the answer is either not indexed, is too large and ranks below the top-K, or the chunk size change moved the answer to a different position within a chunk.

**Signal:** factual recall should be the most stable number across chunk size experiments. Any drop here warrants investigation before reading multi-hop or paraphrase results.

### Out-of-scope and fictitious entity questions should not change

Chunking doesn't affect whether the system hallucinates about things that aren't in the document. If hallucination rate changes after a chunking change, the cause is elsewhere (probably top-K or system prompt, not chunking).

**Signal:** if out-of-scope and fictitious entity results change after a chunking change, you changed something else at the same time. Re-check what was modified.

---

## The Failure Mode Map

| Chunking setting | What breaks | Metric that drops | Query type that shows it first |
|---|---|---|---|
| Chunk size too small | Answers split across chunk boundaries | Context Recall, Recall@K | Multi-hop |
| Chunk size too large | Noisy chunks with irrelevant text | Context Precision, Faithfulness | Factual (dense sections) |
| No overlap | Boundary sentences lost | Recall@K, MRR | Paraphrase, boundary factual |
| Too much overlap | Redundant context fills context window | Faithfulness (LLM confuses repeated text) | Adversarial |
| Fixed-size cutting sentences | Broken semantic units in chunks | Recall@K on paraphrase | Paraphrase |
| Semantic chunking with poor threshold | Very large chunks on verbose topics | Context Precision | Factual |

---

## How to Run a Before/After Comparison

### The one rule

**Change one thing at a time.** If you change chunk size and overlap simultaneously, you cannot tell which one caused any score change. Change chunk size. Measure. Then change overlap. Measure again.

### In Dify

1. Note your current settings: **Knowledge Base → Settings → Chunking & Indexing**. Write down chunk size, overlap, and strategy before making any change.
2. Run `run_evaluation.py` against the current configuration and save as `runs/run-001.csv`. This is your baseline.
3. Change exactly one setting in Dify Knowledge Base settings.
4. Click **Save and Re-process**. Dify deletes all existing vectors and rebuilds the index with the new chunks. Wait for re-indexing to complete before running the evaluation again.
5. Run `run_evaluation.py` again and save as `runs/run-002.csv`.
6. Compare the two files using the metrics below.

### What to compare

Read the metrics together, not in isolation:

| Metric | What a change tells you |
|---|---|
| Context Recall | Did the new chunks improve how much needed content was retrieved? |
| Context Precision | Did the new chunks reduce noise in what was retrieved? |
| Recall@K (multi-hop rows only) | Did boundary improvements help cross-passage questions? |
| Recall@K (factual rows only) | Did simple questions stay stable or degrade? |
| Faithfulness | Did the LLM stay grounded, or did noise push it toward hallucination? |

### Declaring a winner

A chunk configuration is better only if:
- No metric you care about got meaningfully worse
- At least one metric improved
- The change is consistent across query types, not just on one category

A chunk size that improves multi-hop recall but tanks factual precision is a trade-off, not a win. Document what you found and decide whether the trade-off suits your use case.

---

## Parent-Child Chunking (Advanced)

One way to escape the precision-vs-context trade-off entirely is **parent-child chunking** (also called small-to-big retrieval):

- Each passage is indexed at **two granularities**: a small child chunk (~100–200 chars) and a large parent chunk (~500–1000 chars) that contains the child
- At retrieval time, the **small chunk** is used for vector matching — high precision, the vector captures a tight semantic unit
- When a small chunk matches, the **parent chunk** is what gets returned to the LLM — full context, less noise risk

```
Document passage about 401k:
  Parent chunk (800 chars): full policy explanation including match, vesting, limits
  Child chunks (~150 chars each):
    "Orion matches 100% of employee contributions up to 5% of base salary."
    "Employer match vests over 3 years: 33% year 1, 67% year 2, 100% year 3."
    "Maximum annual employee contribution: $23,000 (2024 IRS limit)."

Query: "What is the vesting schedule?"
→ Child chunk 2 matches with high precision
→ Parent chunk (full 401k policy) is returned to the LLM
→ LLM has complete context without the chunk being diluted by unrelated topics
```

**Trade-off:** doubles storage (every passage is indexed twice) and adds complexity to the ingestion pipeline. Worth it for knowledge bases where answers frequently require the surrounding context to be fully understood. Dify supports this under **Retrieval Settings → Parent-Child Chunking**.

---

## See Also

- [Golden Dataset Guide](../../golden-dataset/guide.md) — how to build the dataset you use to measure chunking impact
- [First RAG Evaluation](../../golden-dataset/first-evaluation.md) — how to run the evaluation and capture results
- [RAG Evaluation Playbook](rag-evaluation-playbook.md) — A/B testing rules, statistical significance, and declaring a winner
- [RAG Terminology Glossary](../concepts/glossary.md) — definitions for chunk size, overlap, separator, and chunking strategies
