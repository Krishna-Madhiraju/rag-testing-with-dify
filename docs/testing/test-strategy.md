# Test Strategy — RAG Application (Dify + Weaviate)

**Project:** RAG assistant built on Dify with a Weaviate vector store, deployed via Docker
**Version:** 1.0 · June 2026
**Audience:** Engineering and QA leadership — for sign-off on scope, risk, and release gates

---

## Why this needs its own strategy

A RAG system answers questions from our own documents. Unlike traditional software, it is **non-deterministic** — the same question can yield different wording each time — and it can state a wrong answer with complete confidence. We cannot test it with simple pass/fail assertions. [1, 2, 3]

So the strategy splits testing into the two things that can independently go wrong, and scores each on a 0–1 scale rather than true/false:

| Phase | The question it answers | What goes wrong if we skip it |
|---|---|---|
| **Retrieval** (Weaviate) | Did we find the right source material for the question? | The system answers from the wrong documents, or finds nothing |
| **Generation** (LLM) | Did the model answer using only what it found? | The model invents facts — a confident, wrong answer reaches the user |

---

## What we measure — the RAG Triad

Three checks, each targeting a different failure point. This is the industry-standard framework for RAG quality. [4, 5]

| Check | Plain-English question | Why it matters to the business |
|---|---|---|
| **Context Relevance** | Did retrieval pull the right chunks? | Wrong source = wrong answer, no matter how good the model is [6] |
| **Groundedness / Faithfulness** | Is the answer backed by those chunks? | This is our hallucination guard — the top reputational and compliance risk [7, 8] |
| **Answer Relevance** | Did it actually answer what was asked? | A true-but-unrelated answer still fails the user [9] |

```
[ User Question ]
        │
        ▼
  1. Retrieval  ──►  Context Relevance   ("Did we find the right material?")
   (Weaviate)
        │
        ▼
  2. Generation ──►  Groundedness        ("Is the answer backed by it?")
   (LLM via Dify)
        │
        ▼
  3. Response   ──►  Answer Relevance    ("Did it answer the question?")
```

---

## Risk areas & priority

Where we focus effort. Priority = likelihood × business impact.

| Risk | Likelihood | Impact | Priority |
|---|---|---|---|
| Stale answers after a document is updated | High | High | **P1** |
| Document silently fails to load (e.g. scanned PDF) | High | High | **P1** |
| Hallucination — model invents facts not in the source | Medium | High | **P1** |
| Out-of-scope questions answered instead of refused | Medium | High | **P1** |
| Retrieved content overflows the model's limit (gets cut) | Medium | Medium | **P2** |
| Conflicting documents produce a blended, wrong answer | Medium | Medium | **P2** |
| Model or embedding upgrade changes behaviour | Low | High | **P2** |
| Prompt injection hidden inside a document | Low | High | **P2** |
| Multi-step questions miss part of the answer | Medium | Medium | **P3** |
| Config drift (chunk size, overlap, threshold) | Low | Medium | **P3** |

---

## How we test it

We use the cheapest method that catches each problem. Most checks need no specialist tooling; only deep quality scoring needs an evaluation framework.

| Level | What it covers | Who owns it | Tooling |
|---|---|---|---|
| **Manual inspection** | Spot-checking retrieved chunks, format parsing, adversarial probing | Functional tester | [Dify Retrieval panel](https://docs.dify.ai/en/use-dify/knowledge/test-retrieval) |
| **Scripted regression** | Ingestion audits, coverage sets, freshness and consistency checks | Tester with light Python | Dify API + Weaviate client + pytest |
| **Cheap text regression** | Deterministic drift detection on every commit (free, instant) | Automated | BLEU, ROUGE-L |
| **Quality scoring** | Faithfulness, relevance, retrieval precision/recall | Automated, gated runs | [RAGAS](https://docs.ragas.io), [DeepEval](https://deepeval.com) |
| **Adversarial & injection** | Red-team, auto-generated attack inputs | Tester + tool | [Promptfoo](https://www.promptfoo.dev) |
| **Performance** | Latency and concurrent-load benchmarks | Automated | [Locust](https://locust.io), [k6](https://k6.io) |

**Evaluation method — LLM-as-a-judge:** quality scoring is done by a fixed "judge" model that rates each answer 0–1 on the three Triad checks. The judge stays pinned across runs — swapping it would invalidate score comparisons. Full setup is in the [testing toolkit](../reference/rag-testing-toolkit.md). [13, 14]

**Test data — the golden dataset:** a human-curated set of 30–50+ `(question, expected answer, source)` examples covering every topic, question type, and document format. It is the backbone of every automated check; without it there is nothing to score against. [12]

---

## Non-functional checks

| Area | What we watch | Why |
|---|---|---|
| **Speed** | End-to-end response time at peak load (p50/p95/p99) | Slow answers lose users; latency grows as the document set grows [15] |
| **Cost** | Tokens per query (prompt + retrieved chunks + answer) | Retrieving too much inflates cost and can silently truncate context |
| **Security** | Prompt injection, data leakage, off-policy output | Documents can carry hidden instructions; users must not see restricted content [16, 17] |

---

## Test cadence

| Check | When |
|---|---|
| Ingestion smoke test (documents loaded) | Every deploy |
| Out-of-scope refusal set | Every deploy |
| BLEU / ROUGE-L text regression | Every commit |
| Retrieval recall on golden dataset | Every deploy |
| RAGAS faithfulness + answer relevance | Pre-release gate |
| Adversarial + injection suite | Weekly / pre-release |
| Freshness probe (live data) | Daily |
| Latency & cost benchmarks | Weekly |

---

## Release gates (go / no-go)

A release proceeds only when **all** of the following hold:

| Gate | Threshold |
|---|---|
| Groundedness / Faithfulness | ≥ 0.85 |
| Context Relevance | ≥ 0.80 |
| Answer Relevance | ≥ 0.80 |
| Out-of-scope refusal rate | 100% |
| Prompt injection blocked | 100% |
| End-to-end latency at peak | ≤ 3 seconds |
| Open P1 defects | 0 |

**Entry criteria** (before testing starts): Weaviate fully indexed, LLM and judge model pinned, golden dataset peer-reviewed for accuracy, Dify app published with an API key for automation.

---

## Supporting assets

| Asset | Location |
|---|---|
| Golden dataset (question + expected answer + source) | `tests/` |
| Testing toolkit — tools, RAGAS setup, metric guide | [docs/reference/rag-testing-toolkit.md](../reference/rag-testing-toolkit.md) |
| 67 functional test cases | [docs/testing/functional-test-scenarios.md](functional-test-scenarios.md) |
| RAG tester FAQ & considerations | [docs/reference/rag-tester-faq.md](../reference/rag-tester-faq.md) |
| RAG terminology reference | [docs/reference/glossary.md](../reference/glossary.md) |

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
[12] [RAGAS Quickstart — Test Set Generation](https://docs.ragas.io/en/stable/getstarted/)
[13] [LLM-as-a-Judge — Automated Scoring](https://dev.to/lamhot/llm-as-a-judge-automated-scoring-and-reliability-vs-human-evaluation-128n)
[14] [Evaluate RAG with LLM-as-Judge — W&B](https://wandb.ai/ai-team-articles/evals/reports/Evaluate-your-RAG-pipeline-using-LLM-as-a-Judge-with-custom-dataset-creation-Part-2---VmlldzoxNTIwNjI2MQ)
[15] [RAG in Production — Kairntech](https://kairntech.com/blog/articles/rag-production-the-complete-guide-to-building-and-deploying-retrieval-augmented-generation-applications/)
[16] [NeMo Guardrails — NVIDIA](https://github.com/NVIDIA/NeMo-Guardrails)
[17] [Promptfoo — LLM Red Teaming](https://www.promptfoo.dev)
