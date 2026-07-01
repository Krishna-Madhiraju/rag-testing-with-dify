# Setting Up Dify for RAG — Knowledge Base & Chatbot

This guide walks you through configuring Dify after the Docker containers are running.
If you haven't started the containers yet, follow the [main setup guide](../../README.md) first.

---

## Overview

There are 4 phases to get a working RAG chatbot:

1. [Add an LLM Provider](#phase-1--add-an-llm-provider)
2. [Create a Knowledge Base and upload your files](#phase-2--create-a-knowledge-base)
3. [Build a Chatbot app and connect the Knowledge Base](#phase-3--build-the-chatbot-app)
4. [Test it](#phase-4--test-the-chatbot)

---

## Phase 1 — Add an LLM Provider

Dify needs an LLM to generate answers and an embedding model to convert your documents into vectors.

1. Go to **http://localhost** and log in
2. Click your **avatar** (top-right corner) → **Settings** → **Model Provider**
3. Choose a provider from the table below and click **Set Up**

| Provider | Cost | Models to use |
|---|---|---|
| **OpenAI** | Pay per use (~$0.01 per test session) | LLM: `gpt-4o-mini` · Embeddings: `text-embedding-3-small` |
| **Anthropic** | Pay per use | LLM: `claude-haiku-4-5` |
| **Ollama** | Free / runs locally | LLM: `llama3.2` · Embeddings: `nomic-embed-text` |

4. Paste your API key → **Save**

### Set default models

Still in **Settings → Model Provider**:

- Find your LLM model → click the **star icon** to set it as default
- Find your embedding model → click the **star icon** to set it as default

> The embedding model is used automatically every time you create a Knowledge Base. Setting it as default means you won't need to pick it each time.

---

## Phase 2 — Create a Knowledge Base

The Knowledge Base is where you upload your documents. Dify splits them into chunks, embeds each chunk using your embedding model, and stores the vectors in Weaviate.

> **Sample document:** This repo includes a ready-to-use test document at `docs/sample-data/orion-technologies-employee-handbook.pdf` -- a realistic 25-page fictional company handbook with specific facts, numbers, and policies ideal for writing RAG test cases.

### Step 1 -- Navigate to Knowledge

Click **Knowledge** in the left sidebar. You will see three options:

| Option | What it does | Pick this? |
|---|---|---|
| **Create a ready-to-use knowledge base** *(Recommended)* | Upload documents and let Dify handle chunking and indexing automatically | Yes -- use this |
| Build a custom knowledge base | Custom processing workflow with manual nodes | No -- advanced use only |
| Connect to an External Knowledge Base | Connect an existing external vector store via API | No -- not needed here |

Click **"Create a ready-to-use knowledge base"**.

### Step 2 -- Upload your document

On the upload screen, drag and drop your file or click to browse.

**Supported formats:** PDF, TXT, Markdown (.md), DOCX, CSV, HTML (max 15 MB per file)

### Step 3 -- Choose a chunk mode

You will be asked to pick a chunking mode before configuring settings.

| Mode | What it does | Use when |
|---|---|---|
| **General** | Standard chunking, flexible indexing options | Starting out -- use this |
| **Parent-child** | Retrieves small child chunks for matching, returns larger parent chunk for context | You want more context in answers |
| **Q&A** | Extracts question-answer pairs from the document | Your document is already FAQ-style |

**Pick General mode.**

> **Important:** Chunk mode cannot be changed after saving. Choose carefully.

### Step 4 -- Configure indexing and chunk settings

On the Document Processing screen you will see three sections: Chunk Settings, Index Method, and Embedding Model.

#### Chunk Settings

| Setting | Value to use | What it controls |
|---|---|---|
| **Chunk mode** | `General` | Standard chunking -- retrieved and recalled chunks are the same |
| **Delimiter** | `\n\n` | Splits on paragraph breaks -- leave as default |
| **Maximum chunk length** | `1,500` characters | Max size of each chunk. Default is 1,024 -- increase to 1,500 for dense policy/handbook text so paragraphs are not cut mid-sentence |
| **Chunk overlap** | `50` characters | Text shared between adjacent chunks -- preserves context at boundaries |

**Text Pre-processing Rules:**
- `Replace consecutive spaces, newlines and tabs` -- leave **checked** (cleans up PDF extraction noise)
- `Delete all URLs and email addresses` -- leave **unchecked** (contact details in the document are valid test targets)
- `Summary Auto-Gen` -- leave **off**
- `Chunk using Q&A format` -- leave **unchecked**

> **Before saving, click "Preview Chunk"** to see how the document is split. Check that no chunk is a broken sentence or half a table row. If chunks look clean, proceed.

#### Index Method

| Option | Pick this? | Why |
|---|---|---|
| **High Quality** *(Recommended)* | Yes | Uses the embedding model for semantic vector search -- required for RAG |
| Economical | No | Uses 10 keywords per chunk only, no embeddings, poor retrieval accuracy |

> **Important:** Once embedded in High Quality mode, switching to Economical is not available. Choose High Quality from the start.

#### Embedding Model

Dify will automatically use your default embedding model. Confirm it shows **`gemini-embedding-001`** before proceeding.

#### Retrieval Setting

Scroll down past the Embedding Model section to find the Retrieval Setting. Three options are available:

| Option | How it works | Pick this? |
|---|---|---|
| **Vector Search** | Embeds the question and finds the most semantically similar chunks | Yes -- start here |
| Full-Text Search | Keyword matching, like a traditional search engine | No -- no semantic understanding |
| Hybrid Search *(Recommended by Dify)* | Runs vector + full-text simultaneously and re-ranks results | Later -- once you understand vector search first |

**Select Vector Search** and configure:

| Setting | Value | Why |
|---|---|---|
| **Top K** | `5` | Number of chunks retrieved per query. Default 3 is low for a 25-page document -- 5 gives better coverage |
| **Score Threshold** | Off (disabled) | Leave the toggle off while learning -- enabling it silently drops low-scoring chunks, hiding retrieval behaviour you need to observe |
| **Rerank Model** | Off | Leave off for now -- adds complexity without benefit at this stage |

> **Why not Hybrid Search from the start?** Hybrid search is more accurate but combines two retrieval methods. Starting with pure Vector Search lets you learn how embedding-based retrieval works first. You can switch to Hybrid later and compare scores -- that comparison is itself a valuable RAG test.

> **Good news:** Retrieval settings can be changed at any time in Knowledge settings without re-indexing your document.

### Step 5 -- Save and process

Click **Save and Process**.

Dify will now split your document into chunks, embed each one using `gemini-embedding-001`, and store all vectors in Weaviate. Watch the progress indicator -- when it shows **Completed** in green, your Knowledge Base is ready.

### Step 6 -- Verify retrieval is working

1. Open your Knowledge Base -> click the **Test** tab
2. Type a question your document should answer
3. Matching chunks appear with similarity scores (0 to 1)

If chunks come back with scores above `0.5`, retrieval is working correctly.

---

## Phase 3 — Build the Chatbot App

### Step 1 — Create the app from a template

1. Click **Studio** in the left sidebar
2. Click **Create App**
3. In the template gallery, find and select **"Knowledge Retrieval: A Smart Chatbot"**

> This template creates a **Chatflow** -- a visual workflow with two pre-wired nodes: a Knowledge Retrieval node (handles retrieval) and an LLM node (handles generation). This is better than a blank chatbot because you can see exactly how retrieval feeds into generation.

A dialog appears:

| Field | What to enter |
|---|---|
| **App Name** | `Orion HR Assistant` |
| **Description** | `An AI assistant that answers questions about Orion Technologies employee policies, benefits, and HR procedures using the official employee handbook.` |

Click **Create**.

### Step 2 — Connect your Knowledge Base to the Knowledge Retrieval node

You will see the Chatflow canvas with nodes: **START → Knowledge Retrieval → LLM → ANSWER**.

The Knowledge Retrieval node is not connected to any Knowledge Base yet. To connect it:

1. Click the **Knowledge Retrieval** node in the canvas
2. In the right panel, scroll to the **KNOWLEDGE** section and click the **+** button
3. Select your Knowledge Base (`orion-technologies-employee-handbook`)

After adding the Knowledge Base, click **Retrieval Setting** to configure how retrieval works.

You will see two re-ranking options:

**Weighted Score** — re-ranks retrieved chunks using the similarity scores that already come out of vector search. No extra model needed. Fast and works out of the box.

**Rerank Model** — uses a cross-encoder model that reads the query and each chunk together in one pass, producing more accurate relevance scores. Requires a separate rerank model to be installed (e.g. Cohere Rerank, BGE Reranker). If no rerank model is installed, Dify shows "Incompatible".

| | Weighted Score | Rerank Model |
|---|---|---|
| Extra model needed | No | Yes |
| Accuracy | Good | Better |
| Speed | Fast | Slower |
| Use when | Starting out / single KB | High-precision / production |

Configure as follows:

| Setting | Value | Why |
|---|---|---|
| **Rerank Setting** | `Weighted Score` | No rerank model installed -- Weighted Score is the correct choice for learning |
| **Top K** | `5` | Default is 4 -- increase to 5 for better coverage on longer documents |
| **Score Threshold** | Off (toggle disabled) | Leave off while learning so all retrieval results are visible |

Close the Retrieval Setting popup when done.

### Step 3 — Update the system prompt in the LLM node

1. Click the **LLM** node in the canvas
2. The right panel opens showing model settings and the system prompt
3. In the **SYSTEM** section you will see a pre-filled default prompt. It contains a blue **Context** pill -- **do not remove it**, this is how retrieved chunks get injected into the LLM prompt
4. Below the Context pill, replace the default guidelines text with:

```
You are an HR assistant for Orion Technologies. Answer questions using only the provided context from the employee handbook.
If the answer is not in the context, say: "I don't know based on the provided documents."
Do not add information that is not in the context. Do not make assumptions.
```

> **Why this prompt matters for RAG testing:** It forces the LLM to stay grounded in retrieved chunks only. If the answer contains information not in the handbook, the model broke the instruction -- that is a hallucination. This is exactly what the Faithfulness metric measures.

### Step 4 — Verify the LLM node settings

With the LLM node selected, confirm the right panel shows:

| Setting | Expected value | Notes |
|---|---|---|
| **Model** | `Gemini 2.5 Flash` | CHAT mode |
| **Context** | `Knowledge Retrieval [x] result Array[Object]` | Confirms retrieval output is wired into the LLM |
| **SYSTEM prompt** | Contains the blue Context pill + your custom guidelines | Both must be present |
| **MEMORIES** | `BUILT-IN` | Handles conversation history automatically |
| **Memory toggle** | On (blue) | Enables conversation memory |
| **Window Size** | `50` | Remembers last 50 messages of conversation history |

### Step 5 — Fix the Rerank Model warning before publishing

Before publishing, Dify runs a checklist. If you see a warning: **"A configured Rerank Model is required"**, fix it:

1. Click the **Knowledge Retrieval** node
2. Click **Retrieval Setting**
3. Switch from the **Rerank Model** tab to the **Weighted Score** tab
4. Close the popup

This warning appears because the Rerank Model option was active but no rerank model is installed. Weighted Score achieves the same re-ranking using similarity weights -- no extra model needed.

### Step 6 — Publish

Click **Publish** (top-right corner). A dropdown appears with these options:

| Option | What it does |
|---|---|
| **Run App** | Opens the chatbot in a full-page tab -- the public-facing interface |
| **Embed Into Site** | Generates an iframe snippet to embed the chatbot in a website |
| **Open in Explore** | Opens the app in Dify's internal app explorer |
| **Access API Reference** | Shows the API key and REST API docs for automated testing |
| **Publish to Marketplace** | Share the app template publicly in Dify Marketplace |

For Phase 4 testing, either:
- Click **Preview** (top-right of the builder) to test inline with citation blocks visible, or
- Click **Run App** to test in the full chatbot interface

> **Note the API key location:** Click **Access API Reference** from this dropdown to find your app API key (`app-xxxxxxxxxxxxxxxx`). You will need this later for automated evaluation scripts (BLEU, ROUGE-L, GPTScore).

---

## Phase 4 — Test the Chatbot

Click **Preview** (top-right of the app builder) to open the chat panel. This runs the full RAG pipeline -- retrieval + generation -- exactly as a real user would experience it.

### What to look for in every response

Every response has two parts:
- **The answer** -- generated by Gemini 2.5 Flash using the retrieved chunks as context
- **Citation block** -- shown below the answer. Click it to expand and see exactly which chunk was retrieved, which document it came from, and its similarity score. This is your window into the retrieval layer.

### Run these 4 test types in order

**Test 1 — In-scope (does it retrieve and answer correctly?)**

Ask something the handbook clearly answers with a specific fact:

- *"What is the company's 401k employer match?"*
- *"How many days of parental leave does the primary caregiver get?"*
- *"What is the gift value limit in the code of conduct?"*

Expected: A factual answer with a citation showing the correct handbook section. Check that the citation chunk actually contains the answer.

**Test 2 — Out-of-scope (does it know when to say I don't know?)**

Ask something the handbook does not cover:

- *"What is Orion's stock price today?"*
- *"Who are Orion's biggest competitors?"*

Expected: "I don't know based on the provided documents." If the chatbot makes up an answer instead -- that is a hallucination. This is what the Faithfulness metric catches.

**Test 3 — Paraphrased (does semantic search work?)**

Ask the same question from Test 1 using completely different words:

- Instead of "401k match" → *"How much does the company contribute to my retirement savings?"*
- Instead of "parental leave" → *"How long can I take off after having a baby?"*

Expected: The same correct answer. If retrieval fails here, it means the embedding model is not capturing semantic meaning well -- a chunking or embedding model issue.

**Test 4 — Ambiguous (does it degrade gracefully?)**

Ask a vague or very short query:

- *"Leave"*
- *"Benefits"*
- *"What are the rules?"*

Expected: Either a reasonable answer covering the most relevant section, or a polite request for clarification. Watch the citation -- which chunk did it retrieve for a vague query?

### How to read the citation block

The citation block tells you everything about what the retrieval layer did:

| What you see | What it means |
|---|---|
| Document name | Which file the chunk came from |
| Chunk text | The exact passage retrieved and passed to the LLM |
| Similarity score | How close the query vector was to this chunk (0–1). Above 0.7 is strong, 0.5–0.7 is acceptable, below 0.5 is weak |

If the citation chunk clearly contains the answer but the LLM gave a wrong response -- that is a **generation failure** (LLM problem).
If the citation chunk does not contain the answer -- that is a **retrieval failure** (embedding or chunking problem).
This distinction is critical for diagnosing RAG issues.

---

## Get the API Key (for automated testing)

Once the chatbot is working in the preview panel:

1. Click **API Access** (top-right in the app builder, or in the published app view)
2. Copy the **API Key** — it looks like `app-xxxxxxxxxxxxxxxx`

You will use this key to run automated evaluation scripts (BLEU, ROUGE-L, GPTScore) against the app via the REST API.

---

## What's next

With a working chatbot and an API key, you can:

- Build a **golden dataset** (question + expected answer pairs) and run it through the API
- Measure answer quality with **BLEU, ROUGE-L, and GPTScore**
- Experiment with different chunking settings and compare scores

See the [main README](../../README.md#testing-the-pipeline) for the testing guide.
