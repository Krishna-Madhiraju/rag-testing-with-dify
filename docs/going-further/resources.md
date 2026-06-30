# Further Resources — Curated RAG & RAG-Testing Reading

A hand-picked reading list for going deeper than this project's intro material. Each entry says *why* it's worth your time. Grouped by purpose so you can jump to what you need.

> Links verified June 2026. The RAG field moves fast — version numbers, pricing, and tool UIs change often, so check the date on anything you read and prefer the official docs for current details.

---

## Start here — foundations

| Resource | Why read it |
|---|---|
| [What is RAG? — AWS](https://aws.amazon.com/what-is/retrieval-augmented-generation/) | The clearest short, vendor-neutral explainer of the concept. |
| [Retrieval-Augmented Generation for LLMs: A Survey (Gao et al., 2023, updated)](https://arxiv.org/abs/2312.10997) | The reference survey for the **Naive → Advanced → Modular** RAG framing used throughout this repo. |
| [RAG: Knowledge-Intensive NLP Tasks (Lewis et al., 2020)](https://arxiv.org/abs/2005.11401) | The original RAG paper — where the idea and the name come from. |
| [A Systematic Review of Key RAG Systems (2025)](https://arxiv.org/pdf/2507.18910) | Current map of where RAG works, where it still fails, and open problems. |

---

## RAG evaluation — the core of this project

| Resource | Why read it |
|---|---|
| [RAGAS documentation](https://docs.ragas.io/) | The framework you'll actually run. Its four metrics — faithfulness, answer relevancy, context precision, context recall — are the practical backbone of RAG evaluation. ([project site](https://www.ragas.io/)) |
| [The RAG Triad — TruLens](https://www.trulens.org/getting_started/core_concepts/rag_triad/) | The canonical Context Relevance / Faithfulness / Answer Relevance framing, from the team that coined it. |
| [RAG Evaluation Metrics — Confident AI (DeepEval)](https://www.confident-ai.com/blog/rag-evaluation-metrics-answer-relevancy-faithfulness-and-more) | Clear walkthrough of each metric with worked examples; DeepEval is the pytest-native alternative to RAGAS. |
| [RAG Evaluation Metrics — Patronus AI](https://www.patronus.ai/llm-testing/rag-evaluation-metrics) | Practitioner view on choosing and combining metrics. |
| [RAG Evaluation in the Era of LLMs: A Comprehensive Survey (2025)](https://arxiv.org/pdf/2504.14891) | Academic survey of evaluation methods, datasets, and judge reliability — the deep end. |

### Recent practical guides (2025–2026)

These are blog-grade but current and practical — good for seeing how teams actually wire evaluation into CI/CD.

- [RAG Evaluation 101: from Recall@K to Faithfulness — LangCopilot](https://langcopilot.com/posts/2025-09-17-rag-evaluation-101-from-recall-k-to-answer-faithfulness)
- [Complete Guide to RAG Evaluation (2025) — Maxim AI](https://www.getmaxim.ai/articles/complete-guide-to-rag-evaluation-metrics-methods-and-best-practices-for-2025/)
- [RAG Evaluation: Metrics, Frameworks & Testing (2026) — Prem AI](https://blog.premai.io/rag-evaluation-metrics-frameworks-testing-2026/)
- [RAG Evaluation: Methods, Metrics, Frameworks (2026) — DataVLab](https://datavlab.ai/post/rag-evaluation-methods-metrics-2026-guide)

---

## Retrieval internals — vectors, indexes, embeddings

| Resource | Why read it |
|---|---|
| [HNSW: Efficient and Robust ANN Search (Malkov & Yashunin)](https://arxiv.org/abs/1603.09320) | The algorithm behind Weaviate's "approximate" search. Explains *why* fast retrieval is approximate — and what that means for recall testing. |
| [Weaviate documentation](https://weaviate.io/developers/weaviate) | The vector store this project uses. Schema design, querying, and how to inspect what was indexed. |
| [MTEB — Massive Text Embedding Benchmark leaderboard](https://huggingface.co/spaces/mteb/leaderboard) | The standard ranking of embedding models across retrieval tasks. Use it when choosing or comparing embedding models. |
| [Introducing Contextual Retrieval — Anthropic](https://www.anthropic.com/news/contextual-retrieval) | A practical technique that cuts retrieval failures by adding context to chunks before embedding — a concrete "Advanced RAG" upgrade you can test before/after. |

---

## Tools you'll meet in this repo

| Tool | Use | Link |
|---|---|---|
| **Dify** | Visual RAG pipeline + retrieval inspector | [docs.dify.ai](https://docs.dify.ai) |
| **RAGAS** | Automated RAG metrics (Python) | [docs.ragas.io](https://docs.ragas.io) |
| **DeepEval** | pytest-native eval; can gate CI on quality | [confident-ai.com](https://www.confident-ai.com) |
| **TruLens** | RAG Triad + production tracing | [trulens.org](https://www.trulens.org) |
| **Promptfoo** | Prompt regression + adversarial red-teaming | [promptfoo.dev](https://www.promptfoo.dev) |
| **Weaviate** | Vector store | [weaviate.io](https://weaviate.io) |

---

## Security & adversarial testing

| Resource | Why read it |
|---|---|
| [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) | The reference list of LLM/RAG risks — prompt injection, data leakage, insecure output handling. The basis for adversarial test design. |
| [Promptfoo red-teaming](https://www.promptfoo.dev/docs/red-team/) | Auto-generates prompt-injection and jailbreak inputs so you don't have to write them all by hand. |

---

## How to use this list

- **Learning the concepts?** Foundations → Retrieval internals → then come back to this repo's [How RAG Works](../concepts/how-rag-works.md).
- **Building the test suite?** RAG evaluation section → RAGAS docs → this repo's [Evaluation Playbook](../testing/rag-evaluation-playbook.md) and [Testing Toolkit](../testing/rag-testing-toolkit.md).
- **Hardening against attacks?** Security section → this repo's [Functional Test Scenarios](../testing/functional-test-scenarios.md) (adversarial category).
