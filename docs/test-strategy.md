# Test Strategy — RAG Application (Dify + Weaviate)

**Project:** RAG pipeline built on Dify, Weaviate vector store, local Docker deployment  
**Stack:** Dify · Weaviate · OpenAI / Anthropic LLM · Python pytest  
**Version:** 1.0 | June 2026

---

Testing a Retrieval-Augmented Generation (RAG) application requires a specialized framework because traditional software testing cannot evaluate the unpredictable, non-deterministic nature of Large Language Models (LLMs). A robust RAG test strategy must independently validate two core phases: the **Retrieval component** (finding the right context from Weaviate) and the **Generation component** (producing an accurate response using that context). [1, 2, 3]

---

## 1. Test Levels & The RAG Triad Framework

A standard RAG strategy evaluates performance using three primary axes — the **RAG Triad** — each targeting a different part of the pipeline: [4, 5]

- **Context Relevance:** Evaluates the *Retrieval* step. Out of all the chunks indexed in Weaviate, did the system pull content that actually relates to the user's query? Measured by RAGAS `context_precision` and `context_recall`. [6]
- **Groundedness (Faithfulness):** Evaluates the *Generation* step. Does the LLM's response stay strictly within the retrieved context, or does it hallucinate facts not present in any chunk? [7, 8]
- **Answer Relevance:** Evaluates the *end-to-end* experience. Does the final output directly address what the user actually asked? Measured by RAGAS `answer_relevancy`. [9]

Each of the three axes maps to specific test types and metrics covered in the sections below.

---

## 2. Specialized RAG Test Architecture

Unlike standard applications, a RAG test strategy relies heavily on specialized data pipelines and evaluation frameworks rather than traditional assertion-based testing. [10, 11]

```
[ User Query ]
      │
      ▼
┌─────────────────┐
│  1. Retrieval   │ ──► Context Relevance
│  (Weaviate)     │     Did we retrieve the right chunks?
└─────────────────┘     (context_precision, context_recall, recall@K)
      │
      │ (Retrieved Chunks)
      ▼
┌─────────────────┐
│  2. Generation  │ ──► Groundedness / Faithfulness
│  (LLM via Dify) │     Is the answer backed by the retrieved context?
└─────────────────┘     (RAGAS faithfulness, LLM-as-judge)
      │
      │ (Final Response)
      ▼
┌─────────────────┐
│  3. Response    │ ──► Answer Relevance
│  (End-to-end)   │     Did it answer the original question?
└─────────────────┘     (RAGAS answer_relevancy, BLEU, ROUGE-L)
```

### Test Data & Golden Datasets

- **Golden Dataset:** Build a human-curated evaluation set of 30–50+ representative `(query, expected answer, source chunk)` triplets covering all major topics, query types (single-hop, multi-hop, out-of-scope, paraphrase), and document formats in the corpus. See [rag-testing-toolkit.md](rag-testing-toolkit.md) for the full build and maintenance guide.
- **Synthetic augmentation:** Use RAGAS's built-in test set generation to automatically produce diverse query variations from raw source documents — particularly useful for multi-hop and paraphrase coverage. [12]
- **Volatile vs stable split:** For live-data systems, partition the dataset into stable facts (safe for regression) and volatile facts (freshness checks only, not regression targets).

### Evaluation Methodology: LLM-as-a-Judge

Manual regression testing is impossible at scale and cannot objectively measure hallucination or semantic faithfulness. This project deploys a **fixed judge model** (GPT-4o or GPT-4o-mini) as an automated evaluator to score the production RAG pipeline on a 0–1 scale across all three Triad metrics. [13, 14]

The judge model must remain fixed across all runs — swapping it mid-project invalidates score comparisons. Scores are produced by RAGAS and DeepEval; raw answer text regression uses BLEU and ROUGE-L for deterministic, zero-cost checks on every commit. See [rag-testing-toolkit.md](rag-testing-toolkit.md) for setup and the metric-by-metric breakdown.

---

## 3. Non-Functional RAG Testing

The strategy explicitly covers non-functional risks unique to RAG systems: [15]

- **Latency & Throughput:** Weaviate vector search adds latency at scale. LLM Time-to-First-Token (TTFT) can degrade user experience significantly under load. Benchmark p50/p95/p99 query latency as the corpus grows and set a ceiling (target: end-to-end response ≤ 3 seconds at expected peak load).
- **Token Budgeting & Cost:** Monitor token consumption per query — system prompt + retrieved chunks + question + response. A Top-K setting that's too high combined with large chunks can cause context window overflow (silent truncation) and runaway API costs.
- **Security & Guardrails:** Stress-test against prompt injection via document content, data leakage (retrieving chunks the user shouldn't see), and toxic or off-policy outputs. Promptfoo's red-team mode auto-generates adversarial inputs. [16, 17]

---

## 4. Risk Areas & Priority

| Risk | Likelihood | Impact | Priority |
|---|---|---|---|
| Stale chunks after document update | High | High | **P1** |
| Silent ingestion failure (scanned PDFs, bad parsers) | High | High | **P1** |
| Hallucination — LLM invents facts not in context | Medium | High | **P1** |
| Out-of-scope queries answered instead of refused | Medium | High | **P1** |
| Context window overflow at high Top-K | Medium | Medium | **P2** |
| Contradictory documents producing blended answers | Medium | Medium | **P2** |
| Embedding model mismatch after upgrade | Low | High | **P2** |
| Prompt injection through document content | Low | High | **P2** |
| Multi-hop retrieval gaps | Medium | Medium | **P3** |
| Configuration drift (chunk size, overlap, threshold) | Low | Medium | **P3** |

---

## 5. Tooling Stack Matrix

| Test Type | Purpose | Tools [18, 19, 20] |
|---|---|---|
| **Manual retrieval inspection** | Chunk-level spot checks, format parsing, adversarial probing | [Dify Retrieval Testing panel](https://docs.dify.ai/en/use-dify/knowledge/test-retrieval) |
| **Scripted regression** | Ingestion audits, coverage sets, freshness probes, consistency checks | Python + pytest + Dify API + Weaviate client |
| **RAG Triad evaluation** | Faithfulness, answer relevancy, context precision/recall | [RAGAS](https://docs.ragas.io) (primary) |
| **CI/CD quality gating** | Block deploys on quality regression; pytest-native | [DeepEval](https://deepeval.com) |
| **Answer-text regression** | Cheap deterministic drift detection on every commit | BLEU (`sacrebleu`), ROUGE-L (`rouge-score`) |
| **Adversarial & injection** | Red-team; auto-generated adversarial inputs | [Promptfoo](https://www.promptfoo.dev) |
| **LLM Ops tracing** | Debugging retrieval and prompt failures in production | LangSmith, Phoenix (Arize) |
| **Load testing** | Concurrent LLM generation speeds, latency at scale | [Locust](https://locust.io), [k6](https://k6.io) |

---

## 6. Test Cadence

| Test | Cadence | Owner |
|---|---|---|
| Ingestion smoke test (chunk count > 0) | Every deploy | Scripted |
| Out-of-scope refusal set | Every deploy | Manual + scripted |
| BLEU / ROUGE-L regression on golden dataset | Every commit | Scripted |
| Golden dataset recall@K | Every deploy | Scripted |
| RAGAS faithfulness + answer relevancy | Pre-release gate | Eval tooling |
| Format-specific retrieval (per format) | On new format added | Manual |
| Adversarial + injection suite | Weekly / pre-release | Manual + Promptfoo |
| Configuration comparison (chunk size, overlap) | On config change | Scripted + RAGAS |
| Freshness probe (live data) | Daily | Scripted |
| Latency & cost benchmarks | Weekly | Scripted |

---

## 7. Entry & Exit Criteria

### Entry Criteria

- Weaviate is fully indexed with the baseline document corpus.
- LLM API access is stable and a judge model is pinned for evaluation runs.
- The Golden Dataset has been peer-reviewed for factual accuracy and source-chunk correctness.
- The Dify application is published with a confirmed system prompt and API key available for automated testing.

### Exit Criteria

- Average **Groundedness (Faithfulness)** score ≥ 0.85 across the golden dataset.
- Average **Context Relevance** (context_precision) score ≥ 0.80.
- Average **Answer Relevance** score ≥ 0.80.
- Out-of-scope refusal rate = **100%** on the dedicated out-of-scope query set.
- System blocks **100%** of standard prompt injection test cases.
- End-to-end response latency ≤ **3 seconds** at expected peak load.
- No P1 defects open.

---

## Key Test Assets

| Asset | Location |
|---|---|
| Golden dataset (query + expected answer + source chunk) | `tests/` |
| RAG tester FAQ and considerations guide | [docs/rag-tester-faq.md](rag-tester-faq.md) |
| Testing toolkit — tools, RAGAS setup, metric guide | [docs/rag-testing-toolkit.md](rag-testing-toolkit.md) |
| 54 functional test cases | [docs/functional-test-scenarios.md](functional-test-scenarios.md) |
| RAG terminology reference | [docs/glossary.md](glossary.md) |

---

## References

[1] [RAGAS — Evaluating RAG Pipelines](https://docs.ragas.io/en/stable/)  
[2] [Dify — Test Knowledge Retrieval](https://docs.dify.ai/en/use-dify/knowledge/test-retrieval)  
[3] [RAG Evaluation Methods and Metrics 2026](https://datavlab.ai/post/rag-evaluation-methods-metrics-2026-guide)  
[4] [What is the RAG Triad? — TruEra](https://truera.com/ai-quality-education/generative-ai-rags/what-is-the-rag-triad/)  
[5] [RAG Evaluation — Comet ML](https://www.comet.com/site/blog/rag-evaluation/)  
[6] [RAGAS Available Metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)  
[7] [Detecting Hallucination in RAG — Towards Data Science](https://towardsdatascience.com/detecting-hallucination-in-rag-ecaf251a6633/)  
[8] [Measuring RAG Groundedness — Openlayer](https://www.openlayer.com/blog/post/measuring-rag-groundedness-complete-evaluation-guide)  
[9] [RAG Evaluation Metrics — qaskills.sh](https://qaskills.sh/blog/rag-evaluation-metrics-complete-2026)  
[10] [Testing RAG Systems — Testfort](https://testfort.com/blog/testing-rag-systems)  
[11] [RAG Evaluation 2026 — Benchmarking Agents](https://benchmarkingagents.com/rag-eval/)  
[12] [RAGAS Quickstart — Test Set Generation](https://docs.ragas.io/en/stable/getstarted/)  
[13] [LLM-as-a-Judge — Automated Scoring](https://dev.to/lamhot/llm-as-a-judge-automated-scoring-and-reliability-vs-human-evaluation-128n)  
[14] [Evaluate RAG with LLM-as-Judge — W&B](https://wandb.ai/ai-team-articles/evals/reports/Evaluate-your-RAG-pipeline-using-LLM-as-a-Judge-with-custom-dataset-creation-Part-2---VmlldzoxNTIwNjI2MQ)  
[15] [RAG in Production — Kairntech](https://kairntech.com/blog/articles/rag-production-the-complete-guide-to-building-and-deploying-retrieval-augmented-generation-applications/)  
[16] [NeMo Guardrails — NVIDIA](https://github.com/NVIDIA/NeMo-Guardrails)  
[17] [Promptfoo — LLM Red Teaming](https://www.promptfoo.dev)  
[18] [DeepEval vs RAGAS 2026](https://qaskills.sh/blog/deepeval-vs-ragas-rag-evaluation-2026)  
[19] [Promptfoo vs DeepEval vs RAGAS](https://genai.qa/blog/promptfoo-vs-deepeval-vs-ragas/)  
[20] [Top RAG Evaluation Tools 2026 — Maxim AI](https://www.getmaxim.ai/articles/top-5-tools-to-evaluate-rag-performance-in-2026/)
