# How RAG Works — and What That Means for Testing

This is the one doc to read first. It walks the RAG pipeline from end to end, explains the *mechanism* at each step, and — because this is a testing project — calls out **what can go wrong and how a tester catches it** as we go.

If a term is unfamiliar, the [Glossary](glossary.md) has a quick definition for everything here.

---

## What RAG is, in one paragraph

**Retrieval-Augmented Generation (RAG)** gives a language model access to *your* documents at question time. Instead of answering from what it memorised during training, the system searches a database of your content for the most relevant passages, pastes them into the prompt, and asks the model to answer *from that text*. The payoff: when your data changes, you re-index a document in minutes — you never retrain the model. ([What is RAG? — AWS](https://aws.amazon.com/what-is/retrieval-augmented-generation/))

```
User question
     │
     ▼
  Embed the question  ──►  Search the vector store  ──►  Top-K relevant chunks
                                                              │
                                                              ▼
                          Prompt =  system instructions
                                  + retrieved chunks
                                  + user question
                                                              │
                                                              ▼
                                                         LLM answer
```

Everything in RAG is a variation on this loop: **chunk → embed → index → retrieve → assemble → generate.**

---

## The pipeline, step by step

The first three steps (chunk, embed, index) happen once, when a document is added — this is **ingestion**. The last three (retrieve, assemble, generate) happen on every query.

### 1. Chunking — splitting documents into pieces

A document is too big to retrieve whole, so it's split into smaller passages called **chunks**. Two settings control this:

- **Chunk size** — how many tokens (roughly words) per piece.
- **Overlap** — how many tokens repeat between neighbouring chunks, so a fact sitting on a boundary doesn't get cut in half.

Chunk size is a **precision-vs-context trade-off**. Small chunks retrieve precisely but may miss surrounding context; large chunks carry more context but drag in noise.

> **What to test:** run the same questions at different chunk sizes and compare retrieval quality. Watch *boundary questions* — ones whose answer straddles a chunk edge — they're the first to break when overlap is too low.

### 2. Embedding — turning text into meaning-vectors

An **embedding model** converts each chunk into a list of numbers (a **vector**) that captures its meaning. Passages with similar meaning land close together in this number-space — so "refund window" and "return policy" sit near each other even though they share no words. This is what makes *semantic* search possible.

One rule matters above all: **the same embedding model must be used for both indexing and querying.** Each model defines its own coordinate system; index with model A and query with model B, and the vectors are meaningless. Swapping the embedding model is therefore a *breaking change* — you must wipe the index, re-embed everything, and re-baseline.

> **What to test:** paraphrase questions. If the right chunk exists but a reworded question can't find it, the embedding model doesn't understand your domain's language well enough. (Model quality is benchmarked on the [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard).)

### 3. Indexing — storing vectors in a vector database

The vectors go into a **vector store** (this project uses [Weaviate](https://weaviate.io/)). Unlike a normal database that matches exact values, a vector store searches by *closeness of meaning*. To stay fast at scale it uses an **approximate** nearest-neighbour algorithm — Weaviate uses **HNSW** (Hierarchical Navigable Small World), which navigates a layered graph from coarse to fine, like zooming in on a map. "Approximate" means it trades a tiny chance of missing the very best match for a large speed gain.

> **What to test — first, did everything get in?** Ingestion can fail silently: a scanned PDF parses to nothing, an embedding API call times out and skips a chunk, a schema mismatch drops the lot — and *no error is shown*. After any ingestion, verify the chunk count is what you expect. An "ingestion smoke test" (assert chunk count > 0) is the cheapest, highest-value check in RAG.

<details>
<summary><strong>Deeper dive: how the index actually finds chunks — HNSW vs IVF</strong></summary>

The index exists to avoid the slow way. The *exact* answer to "which chunks are closest?" means comparing the query against **every** stored vector — **brute-force** (or "flat") search. Accurate, but it scales linearly: a million vectors = a million comparisons per query. So vector stores use an **approximate** algorithm that avoids looking at most vectors. The two dominant ones:

**HNSW (Hierarchical Navigable Small World)** — *a navigable graph, used by Weaviate.* Vectors are nodes linked to their nearest neighbours across several layers: sparse top layers with long jumps, a dense bottom layer holding everything. A search enters at the top, greedily hops toward the query, and drops a layer at a time — zooming in like a map from country → city → street — then reads the top-K off the bottom layer.

```
Layer 2:   A ─────────────── F          (few nodes, long jumps)
                │
Layer 1:   A ── C ──── F ──── H         (more nodes)
                │
Layer 0:   A-B-C-D-E-F-G-H-I-J-K...      (ALL vectors, dense links)
           └── greedy walk to the query's neighbourhood ──┘
```

The search-time dial is **`ef`** (beam width): higher = more recall, slower. HNSW gives excellent recall and handles incremental inserts/deletes well — which is why it fits RAG's "add a document, re-index" workload.

**IVF (Inverted File Index)** — *cluster, then scan a few buckets.* At build time, k-means splits all vectors into N clusters, each with a **centroid**. At query time it compares the query to the centroids, picks the closest few, and **only scans the vectors in those clusters** — skipping the rest.

```
   ┌────────┬────────┬────────┐
   │ cluster│ cluster│ cluster│   ← query lands near these centroids
   │  #12   │  #47   │  #200  │
   │ [v,v,v]│ [v,v,v]│ [v,v,v]│   ← only these get scanned
   └────────┴────────┴────────┘
        the other clusters are never opened
```

The dial is **`nprobe`** (clusters to open): higher = more recall, slower. IVF is cheaper to build and lighter on memory (especially **IVF-PQ**, which compresses vectors too), so it wins on huge, mostly-static corpora where RAM is the bottleneck.

| | **HNSW** | **IVF** |
|---|---|---|
| Approach | Layered navigable graph | Cluster, scan a few buckets |
| Recall dial | `ef` (beam width) | `nprobe` (clusters probed) |
| Build cost / memory | Higher | Lower (IVF-PQ lower still) |
| Incremental updates | Handles well | Degrade clusters → periodic re-training |
| Best when | Low-latency, high-recall, changing data | Massive static data, memory-constrained |

> **What to test — the index is an approximate layer that can silently drop the right chunk:**
> - **Recall@K is your index-health metric.** If the expected chunk was indexed but isn't in top-K, raise the recall dial (`ef` / `nprobe`) and re-run. If recall jumps, the *index* was starving you — not chunking or embedding.
> - **Treat the recall-vs-latency dial as an A/B axis.** Measure Recall@K *and* p95 latency at a few `ef`/`nprobe` settings and pick the knee of the curve.
> - **"Approximate" allows non-determinism.** Aggressive speed settings can return slightly different chunks for the same query across runs or re-indexes — run a self-consistency check before blaming LLM temperature.
> - **IVF only:** re-test Recall@K after bulk ingestion — adding vectors without re-clustering degrades recall over time.

</details>

### 4. Retrieval — finding the right chunks

When a question arrives, it's embedded and the store returns the most similar chunks. Two knobs shape the result:

- **Top-K** — how many chunks to return. Too low and the correct chunk ranks 4th and gets dropped; too high and junk enters the prompt (and risks overflowing the context window).
- **Similarity threshold** — a minimum score; chunks below it are excluded even if they're in the top K. Too high → nothing comes back for uncommon questions; too low → noise reaches the model.

> **What to test — Recall@K:** across your test questions, how often does the correct source chunk appear in the top K results? This measures the retrieval layer *in isolation, before the LLM is involved* — the single most useful retrieval metric.

### 5. Context assembly — building the prompt

The retrieved chunks are combined with the system prompt and the user's question into one block of text — the **context** — and sent to the model.

> **What to test — context-window overflow:** every model has a token limit. If system prompt + chunks + question exceed it, the tail is *silently truncated* — no error, the answer just quietly degrades. Probe it with a high Top-K and large chunks and watch whether answers fall apart.

### 6. Generation — the LLM writes the answer

The model reads the context and produces an answer. It *should* answer only from the provided chunks — but it has seen most topics in training, so it can produce confident, wrong answers when the context doesn't actually contain the answer. The main controls are the **system prompt** (the instructions) and **temperature** (how random/creative the output is; near 0 = deterministic, good for fact retrieval).

A strong RAG system prompt needs three things:
1. **Grounding** — "Answer only from the context below; do not use outside knowledge."
2. **Out-of-scope handling** — "If the answer isn't in the context, say you don't know."
3. **A role** — "You are an HR assistant for Orion Technologies."

> **What to test — out-of-scope and adversarial questions:** ask things the documents don't cover and confirm the system *refuses* rather than inventing a plausible answer. These cases are highly sensitive to system-prompt wording — re-run them every time the prompt changes.

---

## The knobs you'll tune (and test)

| Knob | What it controls | What to test when you change it |
|---|---|---|
| **Chunk size** | Tokens per indexed piece | Recall@K and answer completeness at 3–4 sizes |
| **Overlap** | Tokens shared between adjacent chunks | Boundary questions (answer sits at a chunk edge) |
| **Top-K** | Chunks retrieved per query | Recall@K at low K; context overflow at high K |
| **Similarity threshold** | Minimum score to include a chunk | Out-of-scope questions — nothing should clear it |
| **Temperature** | Output randomness | At 0: stable/repeatable; higher: re-check faithfulness |
| **System prompt** | How the model behaves | Out-of-scope + adversarial sets after every edit |
| **Embedding model** | The meaning-vector space | Full re-index + full re-baseline (breaking change) |

---

## The two failure modes — the most useful idea in RAG testing

Almost every RAG failure is one of exactly two things. Telling them apart tells you *where to fix it*.

| | **Retrieval failure** | **Generation failure (hallucination)** |
|---|---|---|
| **What happened** | The right chunk never reached the model | The right chunk was retrieved, but the answer isn't supported by it |
| **Where it lives** | Upstream — chunking, embedding, Top-K, threshold, indexing | Downstream — system prompt, temperature, model |
| **How to fix** | Chunking / Top-K / embedding / re-index | Harden the system prompt; lower temperature; change model |

**The diagnostic rule** — open the citation / sources block for the failing question:

```
Test fails → look at the retrieved chunk
   ├── Chunk DOES contain the answer  → GENERATION failure  (fix the prompt)
   └── Chunk does NOT contain it       → RETRIEVAL failure   (fix chunking / Top-K / embedding)
```

This one check turns "the answer is wrong" into "I know which half of the system to fix." In Dify, the retrieval inspector and the citation block on each chat answer give you exactly this.

---

## Single-turn vs. multi-turn (conversational RAG)

Everything above describes a **single-turn** exchange: one question in, one answer out. But most RAG apps are *chatbots*, and real users have **conversations** — they ask a follow-up, say "and the other one?", or refer back with "it". This is **multi-turn** (conversational) RAG, and it adds a failure surface the single-turn pipeline doesn't have.

**The mechanism: query reformulation.** A follow-up like *"how does it vest?"* is meaningless to the retriever on its own — there's no "it" in the vector store. So before retrieval, a conversational RAG system **rewrites the follow-up into a standalone query** using the chat history: *"how does the 401k employer match vest?"*. That rewritten query is what actually gets embedded and searched. If this rewrite step is missing or weak, retrieval fails on every follow-up — even though the same question works fine when asked in full.

In Dify this is the **Memory** setting (and its **Window Size** — how many past messages it keeps; see [Dify Setup](../setup/dify-setup.md)).

**Four failure modes unique to multi-turn:**

| Failure | What happens | How to test |
|---|---|---|
| **Lost context** | App treats each message as standalone; "it"/"the other one" go unresolved | Ask a follow-up that depends on the previous turn; check it's answered without restating the topic |
| **Stale context carry** | User switches topic, but the old topic bleeds into the new answer | Ask about A, then about an unrelated B; confirm B's answer isn't contaminated by A |
| **Bad query rewrite** | Reformulation injects wrong terms and retrieves the wrong chunk | Compare retrieval for the follow-up vs. the full standalone question |
| **Context-window growth** | Long conversation + retrieved chunks eventually overflow the token limit → silent truncation | Run a long multi-turn session and watch for quality decay deep in the conversation |

> **What to test:** follow-ups, pronoun/ellipsis resolution, topic switches, follow-ups that go *out of scope* ("ok, and what's the stock price?"), and long sessions. These live in [Functional Test Scenarios → Conversation Memory](../testing/functional-test-scenarios.md#category-10--conversation-memory-multi-turn). A practical tip: run multi-turn tests by reusing the `conversation_id` the API returns from turn 1.

**Note — multi-turn is not multi-hop.** They sound alike but are different: *multi-hop* is one question whose answer needs **several chunks** (a retrieval challenge); *multi-turn* is several questions across **several messages** (a conversation-state challenge). A single follow-up can even be both.

---

## Three generations of RAG (so you know what you're testing)

You don't need all of this for an intro, but knowing which architecture you're looking at tells you what your test suite has to cover. ([Gao et al., *RAG for LLMs: A Survey*](https://arxiv.org/abs/2312.10997))

- **Naive RAG** — the basic loop above: embed → search → retrieve → generate. Easy to test: every failure is retrieval or generation, and the citation block tells you which. Breaks on paraphrases and multi-fact ("multi-hop") questions.
- **Advanced RAG** — adds steps before retrieval (query rewriting, **HyDE**), during it (**hybrid search** = vector + keyword, **reranking**), and after it (**context compression**). Each addition is a *new test surface* — e.g. a reranker can push the right chunk out of the top slot.
- **Modular RAG** — routing across multiple knowledge bases, fusing sub-queries, or letting the model decide *whether* to retrieve at all (Self-RAG). More powerful, harder to test because the control flow itself varies per run.

For an intro project, you're testing **Naive RAG** — and that's the right place to build your instincts before adding complexity.

---

## How quality gets measured

You'll go deep on this in the [RAG Evaluation Playbook](../testing/rag-evaluation-playbook.md) and [Testing Toolkit](../testing/rag-testing-toolkit.md). The mental model to carry in:

**The RAG Triad** — three checks, one per part of the pipeline ([TruLens](https://www.trulens.org/getting_started/core_concepts/rag_triad/)):

| Check | Question it answers | Targets |
|---|---|---|
| **Context Relevance** | Did retrieval pull the right chunks? | Retrieval |
| **Faithfulness / Groundedness** | Is every claim backed by the chunks? | Generation |
| **Answer Relevance** | Did the answer address the question? | Generation |

**Metric families** — match the tool to the moment:

- **Lexical (BLEU, ROUGE-L)** — fast, free, deterministic; catch wording drift between runs. Blind to paraphrase ("car" ≠ "automobile"). Good for every-commit regression.
- **LLM-as-judge (GPTScore, RAGAS faithfulness)** — semantic; catch hallucination and paraphrase. Slower, costs money, slightly non-deterministic. Good for release gates.
- Run both and look at *disagreements* — that's where the interesting failures hide.

---

## Where to go next

1. **[Glossary](glossary.md)** — quick definitions for every term above.
2. **[Dify Setup](../setup/dify-setup.md)** — get a real pipeline running locally.
3. **[Your First Evaluation](../../golden-dataset/first-evaluation.md)** — build a tiny golden dataset, run it, score it, record a baseline.
4. **[Test Strategy](../testing/test-strategy.md)** and the **[Evaluation Playbook](../testing/rag-evaluation-playbook.md)** — the full testing picture.
5. **[Further Resources](../going-further/resources.md)** — curated external reading: surveys, frameworks, leaderboards, and primary sources.
