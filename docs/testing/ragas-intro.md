# Introduction to RAGAS

RAGAS (Retrieval-Augmented Generation Assessment) is a Python library with two distinct capabilities:

1. **Synthetic dataset generation** — building a golden dataset from your documents automatically
2. **Evaluation scoring** — measuring faithfulness, answer relevance, context precision, and context recall against an existing dataset

This document covers the generation side. For how each evaluation metric works mechanically — Faithfulness, Answer Relevancy, Context Precision, Context Recall — see **[RAGAS Evaluation Metrics](ragas-evaluation-metrics.md)**.

---

## What RAGAS TestsetGenerator Does

The `TestsetGenerator` is RAGAS's built-in tool for generating a golden dataset from your documents. It combines two LLMs and an embeddings model to produce diverse, quality-filtered question / answer / chunk triples — without you writing filter logic or hand-crafting every question.

This is Approach 3 from the [Golden Dataset Guide](golden-dataset-guide.md): fully automated generation with built-in quality scoring. It is the recommended starting point for knowledge bases with more than five documents.

---

## The Three Components

RAGAS is built around three components that you configure and wire together:

**Generator LLM** — creates the questions and answers. This is typically a faster, cheaper model (e.g. `gpt-4o-mini`). It reads each chunk of your document and produces candidate Q&A pairs.

**Critic LLM** — reviews what the generator produced and scores it for quality. This is a more capable model (e.g. `gpt-4o`). It asks: is this question realistic? Is the answer grounded in the passage? Is it too trivially easy? Pairs that score below threshold are dropped before you ever see them. This is the key advantage over a custom script — automatic quality filtering without writing filter code.

**Embeddings model** — maps semantic relationships between passages across your document. RAGAS needs this to build multi-hop questions: it identifies two passages that are related but not adjacent, then writes a question requiring both. Without it, RAGAS can only generate single-passage questions.

---

## What Happens Internally When You Run It

```
Your documents
      │
      ▼
  Document loader
  (splits into document objects — each one is a page or section)
      │
      ▼
  Knowledge graph construction
  (RAGAS maps relationships between passages using the embeddings model)
      │
      ▼
  Generator LLM
  (for each passage or pair of passages, writes candidate Q&A triples)
      │
      ▼
  Critic LLM
  (scores each triple on: groundedness, question quality, answer faithfulness)
  (drops low-scorers automatically)
      │
      ▼
  TestDataset
  (structured result you inspect or export as CSV)
```

The knowledge graph step is what separates RAGAS from a basic "send each chunk to GPT" loop. By mapping the whole document first, RAGAS knows which passages are thematically linked and can write multi-hop questions without you identifying those pairs manually.

---

## Question Types RAGAS Produces

| Type | What it is | Why it matters for testing |
|---|---|---|
| **Simple** | Single-passage, direct factual question | Tests basic retrieval — right chunk, right answer |
| **Multi-context** | Requires combining two passages | Tests whether chunking preserves cross-passage reasoning |
| **Reasoning** | Requires an inference, not just extraction | Tests whether the LLM can reason from context, not just copy it |

You can control how many of each type you want. If your knowledge base has many related topics, lean toward more multi-context questions — they expose chunk boundary failures that simple questions never catch.

---

## What RAGAS Does NOT Generate

RAGAS only writes questions that are answerable from your documents. These three types must always be written manually and appended to the RAGAS output:

| Type | Why RAGAS cannot generate it |
|---|---|
| Out-of-scope questions | The document must contain the answer for RAGAS to write the question |
| Fictitious entity questions | Same reason — RAGAS cannot invent things that do not exist in the source |
| Adversarial phrasing | RAGAS writes natural questions, not deliberately confusing ones |

Think of RAGAS as generating your in-scope coverage, and manual effort as generating your boundary and stress cases. A complete golden dataset requires both.

---

## Where LangChain Fits In

RAGAS uses LangChain as its plumbing layer — instead of building its own connectors to OpenAI and other providers, it uses LangChain's standardised wrappers. That is why RAGAS setup involves creating a `ChatOpenAI` object and passing it in: RAGAS is asking for a LangChain-compatible LLM object, not a raw OpenAI client.

You do not need to learn LangChain to use RAGAS. Just know that it provides the connectors RAGAS uses internally, and that any LangChain-compatible LLM or embeddings model will work.

---

## Python Concepts You Need to Follow RAGAS Setup

If you are new to Python, these are the only six concepts needed to read and understand RAGAS code:

**Packages and imports** — Python code is organised into packages. `pip install ragas` downloads the package onto your machine. `import` brings specific parts into your script. When you see `from ragas.testset import TestsetGenerator`, read it as: "from the ragas package, inside the testset module, bring in TestsetGenerator."

**Classes and objects** — A class is a blueprint. `TestsetGenerator` is a class — a definition of what a generator can do. When you create one by passing your chosen LLMs into it, you get an object — an actual thing in memory you can use. RAGAS gives you the class; you build your own object by supplying the LLMs and embedding model.

**Keyword arguments** — Arguments with names inside function calls: `testset_size=50` means "the parameter called testset_size gets the value 50." Most RAGAS configuration is done this way — each named argument is a dial you turn.

**Environment variables** — API keys are never written directly into code. They are stored as system-level settings outside your script. When you see `OpenAI()` with no key visible, it reads `OPENAI_API_KEY` from your environment automatically. You set these once in your terminal and every script picks them up.

**Method chaining** — When a method returns an object, you can immediately call another method on it: `testset.to_pandas().to_csv(...)`. Read left to right: `to_pandas()` converts the RAGAS output into a table, then `to_csv()` saves that table to a file. Each step hands its result to the next.

**DataFrames** — A DataFrame (from the `pandas` library) is a table in memory — rows and columns, like a spreadsheet. RAGAS produces its output as a DataFrame so you can inspect, filter, or export it. You do not need to know pandas deeply — `to_pandas()` gives you a table and `to_csv("file.csv")` saves it.

---

## Setting Up RAGAS in Practice

### Step 1 — Choose your LLM and embeddings

You need one LLM (for question generation and quality scoring) and one embeddings model (for knowledge graph construction). OpenAI is the simplest starting point — your API key is already configured if you are using Dify with OpenAI.

Recommended pairing:

| Component | Recommended model | Why |
|---|---|---|
| LLM | `gpt-4o-mini` | Cheap, fast, sufficient quality for generation |
| Embeddings | `text-embedding-3-small` | Matches Dify's default — keeps chunk representations consistent |

If you want zero API cost, Ollama models work but generation quality and speed drop significantly.

### Step 2 — Understand the wrapper layer

The current RAGAS API does not accept raw OpenAI objects directly. It requires you to wrap them first using `LangchainLLMWrapper` and `LangchainEmbeddingsWrapper`. These are adapters that translate between RAGAS's internal interface and LangChain's.

```
Your OpenAI API key
        │
        ▼
  ChatOpenAI          ← LangChain object
        │
        ▼
  LangchainLLMWrapper ← RAGAS adapter
        │
        ▼
  TestsetGenerator
```

You build that chain once, then pass the wrapped object to `TestsetGenerator`. This is a common stumbling point — passing a raw `ChatOpenAI` object without wrapping it will fail.

### Step 3 — Choose your document input path

RAGAS offers two ways to feed documents:

| Method | What you hand RAGAS | When to use |
|---|---|---|
| `generate_with_langchain_docs(docs)` | Raw document objects — RAGAS chunks them internally | Quick start; less control over chunking |
| `generate_with_chunks(chunks)` | Pre-chunked documents you prepared yourself | Recommended when testing against Dify |

**Use `generate_with_chunks` when testing against Dify.** Pre-chunk your documents using the same chunk size and overlap settings as your Dify Knowledge Base. If RAGAS chunks at 1000 characters but Dify chunks at 500, the `expected_chunk` in your golden dataset will not match what Dify actually retrieves — and your retrieval recall scores will be meaningless.

Check your Dify Knowledge Base settings before chunking, then use those exact values.

### Step 4 — Install the required packages

```bash
pip install ragas langchain-openai langchain-community
```

Three packages:
- `ragas` — the core library
- `langchain-openai` — provides `ChatOpenAI` and `OpenAIEmbeddings`
- `langchain-community` — provides document loaders (e.g. `PyPDFLoader`, `DirectoryLoader`)

### Step 5 — Start small, then scale

Run your first generation with `testset_size=10`. This validates that the setup works end to end before you spend tokens on a full 50–100 entry run. RAGAS makes many API calls during knowledge graph construction — a misconfigured API key or rate limit error mid-run wastes the entire generation.

Once a small run completes and the output looks sensible, scale to your target size.

---

## The Output Structure

RAGAS returns a `TestDataset` object. Convert it to a DataFrame to inspect or export it. The columns you get:

| Column | What it contains | Maps to golden dataset field |
|---|---|---|
| `user_input` | The generated question | `question` |
| `reference` | The expected answer | `reference_answer` |
| `reference_contexts` | The source chunk(s) used | `expected_chunk` |
| `synthesizer_name` | Question type: `single_hop`, `multi_hop`, `reasoning` | `query_type` |

Rename these columns to match the `question / reference_answer / expected_chunk / source_doc` structure from the [Golden Dataset Guide](golden-dataset-guide.md) so all your tooling works consistently across manual and synthetic rows.

After exporting to CSV, add your manual out-of-scope, fictitious entity, and adversarial rows. Those are not in the RAGAS output and must be appended by hand.

---

## Common Gotcha — Rate Limiting

RAGAS makes many parallel embedding calls during knowledge graph construction. If you hit an OpenAI rate limit mid-run, the generation fails and you lose the work done so far.

Two ways to reduce the risk:
- Start with a small `testset_size` (10–20) to validate setup before scaling
- Use a project API key with a higher rate limit tier if you plan to generate 100+ entries

---

## Setup Checklist

Before running RAGAS for the first time:

- [ ] Check your Dify Knowledge Base chunk size and overlap settings
- [ ] Pre-chunk your documents using those exact values
- [ ] Set `OPENAI_API_KEY` in your terminal environment
- [ ] Install `ragas`, `langchain-openai`, `langchain-community`
- [ ] Wrap your LLM and embeddings in `LangchainLLMWrapper` / `LangchainEmbeddingsWrapper`
- [ ] Run with `testset_size=10` first to confirm the setup works
- [ ] Inspect the output — check question quality before scaling up
- [ ] Export to CSV, rename columns to match the golden dataset structure
- [ ] Append manual out-of-scope, fictitious entity, and adversarial rows

---

## How the Output Fits Into Your Golden Dataset

The RAGAS output covers in-scope questions only. A complete golden dataset adds manual rows on top:

| Row source | What it covers |
|---|---|
| RAGAS TestsetGenerator | Factual, multi-hop, reasoning — all in-scope |
| Manual additions | Out-of-scope, fictitious entity, adversarial |

Merge both into a single CSV. The manual rows are small in number but critical for release gate testing — they are the only rows that measure hallucination rate and refusal behaviour.

See [Golden Dataset Guide](golden-dataset-guide.md) for the full dataset structure, quality checklist, and how to use the dataset for regression testing.
