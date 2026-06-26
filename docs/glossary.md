# RAG Terminology Glossary

A reference guide to every term you will encounter when building, running, and testing RAG applications. Terms are grouped by topic, not alphabetical order, so related concepts sit together.

---

## Core RAG Concepts

**RAG (Retrieval-Augmented Generation)**
A technique that gives a Large Language Model access to external documents at query time. Instead of relying solely on what the model learned during training, RAG retrieves relevant chunks of your own data and passes them to the LLM as context before generating an answer. The three steps are: Index → Retrieve → Generate.

**LLM (Large Language Model)**
The AI model responsible for generating the final answer (e.g. Gemini 2.5 Flash, GPT-4o, Claude). In a RAG pipeline, the LLM receives the user's question plus the retrieved chunks and produces a response. The LLM does not search — that is the retrieval layer's job.

**Context Window**
The maximum amount of text (measured in tokens) an LLM can process in a single request. Retrieved chunks must fit within the context window alongside the system prompt and the user's question. If too many chunks are retrieved, the context window overflows and some content is dropped.

**Prompt**
The full input sent to the LLM. In a RAG system the prompt has three parts: the system prompt (instructions), the retrieved chunks (context), and the user's question. How these are assembled significantly affects answer quality.

**System Prompt**
Instructions given to the LLM that define its behaviour. In RAG testing, a well-written system prompt typically includes: "Answer only using the provided context. If the answer is not in the context, say I don't know." This instruction is what makes hallucinations detectable.

**Hallucination**
When the LLM generates information that is not present in the retrieved context or that contradicts it. There are two types:
- **Intrinsic hallucination** — the answer directly contradicts the retrieved chunks.
- **Extrinsic hallucination** — the answer adds true-sounding information that is simply not in the chunks (the model draws on its training data instead).

---

## Document Processing

**Ingestion Pipeline**
The full process of preparing documents for RAG: parsing the raw file → splitting into chunks → embedding each chunk → storing vectors in the vector database. This happens once, at setup time.

**Chunking**
Splitting a document into smaller pieces (chunks) before embedding. Chunks are what get stored in the vector database and retrieved at query time. The quality of chunking directly affects retrieval quality.

**Chunk Size**
The maximum length of a single chunk, measured in tokens or characters depending on the tool. Smaller chunks give more precise retrieval but may lack enough context for the LLM to answer well. Larger chunks contain more context but reduce retrieval precision. A common starting point is 500 tokens / 1,500 characters.

**Chunk Overlap**
The number of tokens or characters shared between two adjacent chunks. Overlap prevents important information from being lost at chunk boundaries. For example, with 50-character overlap, the end of chunk 1 is repeated at the start of chunk 2. Typical overlap is 10–15% of chunk size.

**Delimiter**
The character or sequence used to decide where to split text into chunks. `\n\n` (double newline / paragraph break) is a common default — it splits at paragraph boundaries, keeping paragraphs intact rather than cutting mid-sentence.

**Chunking Strategies**
Different approaches to splitting documents:
- **Fixed-size** — split at every N tokens regardless of sentence or paragraph boundaries. Simple but can cut sentences in half.
- **Sentence-aware** — split at sentence endings. Produces coherent chunks but variable sizes.
- **Semantic** — group sentences with similar meaning into the same chunk. Requires an embedding model during ingestion.
- **Recursive** — try progressively smaller delimiters (paragraph → sentence → word) until chunk fits the target size.
- **Parent-child** — see below.

**Parent-child Chunking**
A chunking strategy that stores two sizes of chunk for every passage. The small "child" chunk is used for retrieval (more precise vector matching). When a child chunk is matched, the larger "parent" chunk that contains it is returned to the LLM as context (more complete information). This gives you the precision of small chunks and the context of large chunks at the same time. Trade-off: doubles storage and adds indexing complexity.

**Text Pre-processing**
Cleaning steps applied to raw text before chunking. Common steps include: removing duplicate whitespace, stripping headers/footers from PDFs, normalising encoding. Noisy text produces noisy chunks and degrades retrieval quality.

---

## Embeddings & Vector Databases

**Embedding**
A numerical representation of text as a list of floating-point numbers (a vector). Embeddings capture semantic meaning — similar sentences end up close together in vector space even if they share no words. For example, "dog" and "canine" will have similar embeddings.

**Embedding Model**
The model that converts text into embeddings (e.g. `gemini-embedding-001`, `text-embedding-3-small`). The same embedding model must be used for both indexing documents and embedding queries — mixing models produces incompatible vectors and breaks retrieval entirely.

**Dimensionality**
The number of values in an embedding vector. `gemini-embedding-001` produces 768-dimensional vectors. Higher dimensionality can capture more nuance but requires more storage and compute.

**Vector Database (Vector Store)**
A database optimised for storing and searching embedding vectors. Instead of exact keyword matching, it finds the most similar vectors using approximate nearest neighbour (ANN) search. Examples: Weaviate (used in this project), Pinecone, Qdrant, pgvector, Chroma.

**Weaviate**
The vector database used by Dify in this project. Weaviate stores your document chunks as vector embeddings and handles similarity search when a query comes in.

**Index**
The data structure inside the vector database that makes similarity search fast. Without an index, searching would require comparing the query vector to every stored vector one by one (too slow at scale).

**HNSW (Hierarchical Navigable Small World)**
The most widely used indexing algorithm for vector search. It builds a multi-layer graph where similar vectors are connected. At query time it navigates the graph efficiently to find approximate nearest neighbours. Much faster than exhaustive search with only a small accuracy trade-off.

**ANN (Approximate Nearest Neighbour) Search**
Finding vectors that are approximately (not exactly) closest to a query vector. The approximation is a deliberate trade-off: exact search is too slow at scale, and for RAG the top-5 approximate results are almost always as useful as the exact top-5.

---

## Retrieval

**Similarity Score**
A number between 0 and 1 that measures how similar a retrieved chunk is to the query. A score of 1.0 means identical; 0.0 means completely unrelated. Dify shows these scores in the Knowledge Base Test tab and in citation blocks.

**Cosine Similarity**
The most common similarity metric for text retrieval. Measures the angle between two vectors — independent of their magnitude (length). Two semantically similar sentences will have a small angle between their vectors and therefore a high cosine similarity score.

**Dot Product**
An alternative similarity metric. Measures both angle and magnitude. When vectors are normalised (length = 1), dot product gives the same result as cosine similarity. Slightly faster to compute.

**L2 Distance (Euclidean Distance)**
Measures the straight-line distance between two vectors. Lower distance = higher similarity. Less commonly used for text retrieval than cosine similarity.

**Top-K**
The number of chunks retrieved for each query. If Top-K = 5, the 5 most similar chunks are returned and passed to the LLM. Higher K gives more context but also more noise and higher token cost. Typical values: 3–10. Default in Dify is 3; 5 is a better starting point for longer documents.

**Score Threshold**
A minimum similarity score a chunk must reach to be included in retrieval results. If set to 0.5, any chunk with a similarity score below 0.5 is dropped. Useful in production to prevent low-quality matches, but disable it while learning so you can see all retrieval behaviour.

**Vector Search**
The most common name for embedding-based retrieval in RAG tools and UIs. Also called dense retrieval. The query is converted into a vector using the embedding model, and the vector database finds the stored chunk vectors that are closest to it. Finds semantically similar chunks even when the query uses different words than the document.

**Dense Retrieval**
The technical name for vector search. "Dense" refers to the fact that every dimension of the vector carries meaning (as opposed to sparse vectors where most values are zero). Dense retrieval and vector search are the same thing -- tools use the names interchangeably.

**Sparse Retrieval (BM25)**
Keyword-based retrieval using an inverted index (similar to how traditional search engines work). Fast and precise for exact term matching but cannot understand synonyms or paraphrases.

**Hybrid Search**
Combines dense (vector) and sparse (keyword) retrieval simultaneously, then re-ranks results to select the best matches. Generally more accurate than either method alone, especially for queries that mix specific terms with semantic intent.

**Reranker / Rerank Model**
A model applied after initial retrieval that re-scores and re-orders the retrieved chunks based on how well they match the query. Rerankers use a cross-encoder architecture (see below) which is more accurate than the similarity scores from the embedding model alone. Applied as a post-retrieval step. Requires a separate model to be installed (e.g. Cohere Rerank, BGE Reranker). Slower and more expensive than vector search alone, but significantly more precise.

**Cross-Encoder**
The architecture used by rerank models. Unlike an embedding model (bi-encoder) which encodes the query and each chunk separately and then compares the resulting vectors, a cross-encoder reads the query and a chunk together in a single pass. This means it can attend to how individual words in the query relate to individual words in the chunk -- producing a much more accurate relevance score. The trade-off: you cannot pre-compute cross-encoder scores the way you pre-compute embeddings, so it must run at query time for every retrieved chunk.

**Bi-Encoder**
The architecture used by embedding models (e.g. gemini-embedding-001). Encodes the query and each document chunk independently into separate vectors, then compares them using cosine similarity. Fast because document embeddings are pre-computed at indexing time -- only the query needs to be embedded at search time. Less accurate than a cross-encoder for relevance scoring because query and chunk never interact during encoding.

**Weighted Score**
A re-ranking approach that combines the similarity scores already produced by vector search using configurable weights. No extra model is required -- it works entirely from the scores that come out of the embedding-based retrieval step. In tools like Dify, Weighted Score is used when retrieving from multiple knowledge bases: results from each base are scored and combined using weights before being returned to the LLM. Use this when you want fast, cost-free re-ranking without installing a separate rerank model.

**When to use Weighted Score vs Rerank Model:**

| Situation | Use |
|---|---|
| Single knowledge base, starting out | Weighted Score |
| Need fast, low-cost retrieval | Weighted Score |
| No rerank model installed | Weighted Score |
| Multiple knowledge bases, precision matters | Rerank Model |
| Building a production RAG system | Rerank Model |
| Willing to accept extra latency and cost for accuracy | Rerank Model |

**Full-Text Search**
Index all terms in the document and search by keyword. Retrieves any chunk containing the exact search terms. No semantic understanding — "car" will not retrieve chunks about "automobile".

---

## RAG Patterns

**Naive RAG**
The simplest RAG architecture: query → embed → search vector DB → retrieve top-K chunks → pass to LLM → generate answer. Easy to implement but has clear failure modes: poor retrieval on paraphrased queries, context window limits, and no mechanism for multi-step reasoning.

**Advanced RAG**
Enhancements added before, during, or after retrieval to improve quality:
- **Pre-retrieval**: query expansion, HyDE
- **During retrieval**: hybrid search, re-ranking
- **Post-retrieval**: context compression, chunk re-ordering

**Modular RAG**
A flexible architecture where retrieval is broken into composable modules: routers (which knowledge base?), fusion (combine results from multiple queries), self-RAG (the model decides whether to retrieve at all). Most powerful but most complex to test.

**Query Expansion**
Generating multiple reformulations of the user's question before retrieval, then retrieving for all versions and merging results. Improves recall for queries where the user's phrasing doesn't match the document's phrasing.

**HyDE (Hypothetical Document Embeddings)**
A query expansion technique where the LLM is asked to generate a hypothetical answer to the question. That hypothetical answer is then embedded and used as the search query instead of the original question. Works because a hypothetical answer is semantically closer to the actual document chunk than the question alone.

---

## Evaluation Metrics

**Golden Dataset**
A curated set of question + expected answer + source chunk triples used for regression testing. The "ground truth" against which actual RAG outputs are measured. A good golden dataset has: clear factual questions, unambiguous answers, and deliberate out-of-scope questions to test "I don't know" responses.

**BLEU (Bilingual Evaluation Understudy)**
A metric that measures n-gram precision: what fraction of word sequences (n-grams) in the generated answer also appear in the reference answer. Originally designed for machine translation. Range: 0.0 (no overlap) to 1.0 (perfect match). Limitation: purely lexical — "car" and "automobile" score zero overlap even though they mean the same thing.

**ROUGE-L (Recall-Oriented Understudy for Gisting Evaluation — Longest Common Subsequence)**
A metric that measures the longest common subsequence (LCS) between the reference and generated answer, expressed as an F1 score. More flexible than BLEU about word order. Better at capturing whether key information was covered. Still lexical — misses paraphrases and synonyms.

**GPTScore (LLM-as-Judge)**
Uses an LLM to evaluate RAG output quality on semantic dimensions. The evaluator LLM reads the question, the retrieved context, and the generated answer, then scores each dimension 1–5. Captures meaning, paraphrases, and hallucination that BLEU/ROUGE cannot detect. Limitation: expensive, non-deterministic, and sensitive to the evaluation prompt.

**The RAG Triad**
Three dimensions for evaluating end-to-end RAG quality, popularised by the TruLens framework:
- **Faithfulness** — Is every claim in the answer supported by the retrieved chunks? Measures hallucination. Score of 1.0 = no hallucination.
- **Answer Relevance** — Does the answer actually address what was asked? A faithful answer can still be irrelevant if it focuses on the wrong part of the context.
- **Context Relevance** — Were the retrieved chunks actually relevant to the question? Low context relevance means retrieval failed even if the answer looks good.

**RAGAS**
An open-source Python framework for automated RAG evaluation. Provides metrics including faithfulness, answer relevancy, context precision, and context recall. Can generate synthetic test datasets from your documents. See: [ragas.io](https://ragas.io)

**BERTScore**
A semantic similarity metric that uses a BERT-based model to compare generated and reference answers at the token level. Unlike BLEU/ROUGE, it captures semantic similarity rather than just word overlap. "Car" and "automobile" would score highly similar.

**Context Precision**
Of the chunks retrieved, what fraction were actually relevant? High context precision means the retrieval layer is not returning noise. A RAGAS metric.

**Context Recall**
Of all the chunks that should have been retrieved (based on the expected answer), what fraction were actually retrieved? High context recall means the retrieval layer is not missing relevant chunks. A RAGAS metric.

**MRR (Mean Reciprocal Rank)**
A retrieval quality metric. For each query, find the rank of the first relevant chunk. MRR is the average of 1/rank across all queries. If the correct chunk is always retrieved first, MRR = 1.0. Used to measure ranking quality, not just whether the chunk was retrieved.

---

## Dify-Specific Terms

**Knowledge Base**
In Dify, a named collection of indexed documents. You upload files, configure chunking and indexing settings, and Dify processes them into chunks stored in Weaviate. One Knowledge Base can hold multiple documents.

**High Quality Mode**
Dify's indexing mode that uses the embedding model to convert chunks into vectors. Required for semantic/vector search. Once a Knowledge Base is indexed in High Quality mode, it cannot be switched to Economy mode.

**Economy Mode**
Dify's indexing mode that extracts 10 keywords per chunk and uses keyword matching for retrieval. No embedding model is used and no tokens are consumed. Retrieval accuracy is significantly lower than High Quality mode.

**Studio**
The Dify interface for building applications (chatbots, text generators, agents, workflows). You create and configure your RAG chatbot app here.

**Orchestrate Tab**
Inside a Dify app, the Orchestrate tab is where you connect a Knowledge Base to the app, write the system prompt, and configure the LLM model and parameters.

**Citation Block**
In a Dify chatbot response, the citation block shows which document chunk was retrieved, the similarity score, and the source document. Clicking it reveals the exact chunk text. Essential for debugging retrieval and verifying faithfulness.

**Integrations**
The Dify sidebar section (replacing the older "Settings" location) where you install and configure model providers (Gemini, OpenAI, Anthropic, Ollama etc.) and set default models.

---

## Testing Concepts

**Component Testing (Retrieval Testing)**
Testing the retrieval layer in isolation, without involving the LLM. You query the Knowledge Base directly (via the Test tab or API) and check: did the right chunks come back? What similarity scores did they get? This separates retrieval failures from generation failures.

**End-to-End Testing**
Testing the full RAG pipeline: question in → answer out. Evaluates the combined quality of retrieval + generation. Use BLEU, ROUGE-L, GPTScore, or human review to assess the answer.

**Regression Testing**
Running a fixed set of questions (the golden dataset) against the RAG system after any change (new document, different chunking settings, different model) to check that quality has not degraded.

**A/B Configuration Testing**
Running the same golden dataset against two different RAG configurations (e.g. chunk size 500 vs 1,500, or Vector Search vs Hybrid Search) and comparing the evaluation scores to decide which configuration is better.

**Adversarial Testing**
Deliberately crafting queries designed to expose failures: out-of-scope questions (should trigger "I don't know"), very short or ambiguous queries (should degrade gracefully), leading questions (should not cause the LLM to agree with false premises), and prompt injection attempts.

**Latency Testing**
Measuring how long the full RAG pipeline takes from question to answer. Components to measure separately: embedding time (query → vector), retrieval time (vector search), and generation time (LLM response).
