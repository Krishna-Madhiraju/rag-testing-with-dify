# RAG Application Testing with Dify

A hands-on learning project for building and testing **Retrieval-Augmented Generation (RAG)** pipelines using [Dify](https://github.com/langgenius/dify) — an open-source LLM application platform.

The focus is the *testing* side: how RAG systems fail, how to measure quality, and how to build a repeatable test suite against a real pipeline.

---

## Table of Contents

- [What is RAG?](#what-is-rag)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Dify Configuration](#dify-configuration)
- [Testing the Pipeline](#testing-the-pipeline)
- [Stopping and Restarting](#stopping-and-restarting)
- [Troubleshooting](#troubleshooting)
- [Resources](#resources)

---

## What is RAG?

**Retrieval-Augmented Generation** gives an LLM access to your own documents at query time. Instead of relying on training data, it:

1. **Indexes** documents — splits them into chunks and converts each to a vector embedding
2. **Retrieves** the most relevant chunks when a user asks a question
3. **Augments** the LLM prompt with those chunks so the model answers from your data

```
User Question
     │
     ▼
┌─────────────┐     similar chunks     ┌──────────────────┐
│  Embedding  │ ──────────────────────▶│  Vector Store    │
│   Model     │◀──────────────────────│  (Weaviate)      │
└─────────────┘     top-K results      └──────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│  Prompt = System + Retrieved Chunks     │
│           + User Question               │
└─────────────────────────────────────────┘
     │
     ▼
   LLM Response
```

Dify handles this entire pipeline visually and exposes a retrieval inspector that shows exactly which chunks were returned for any query — making it well-suited for RAG testing.

---

## Project Structure

```
rag-demo/
├── dify/                        # Dify platform (cloned repo)
│   └── docker/                  # Docker Compose setup — run all commands from here
├── docs/
│   ├── concepts/
│   │   ├── how-rag-works.md             # START HERE — the RAG pipeline + test implications
│   │   └── glossary.md                  # RAG terminology reference
│   ├── setup/
│   │   └── dify-setup.md                # Step-by-step Dify configuration guide
│   ├── reference/
│   │   ├── llm-api-cost-comparison.md          # Frontier vs. open-source-serving LLM API pricing, free tiers, Dify compatibility
│   │   └── embedding-model-pricing-comparison.md  # Embedding API cost, dimensions, and quality comparison
│   ├── testing/
│   │   ├── test-strategy.md                  # One-page test strategy for the RAG pipeline
│   │   ├── rag-evaluation-playbook.md        # How to execute evaluation — metrics, A/B testing
│   │   ├── functional-test-scenarios.md      # 74 functional test cases
│   │   ├── chunking-strategies.md            # Chunk size, overlap, strategy — failure modes + how to measure
│   │   ├── ragas-intro.md                    # How RAGAS TestsetGenerator works — components, flow
│   │   ├── ragas-evaluation-metrics.md       # Faithfulness, Answer Relevancy, Context Precision, Context Recall
│   │   ├── advanced-evaluation-metrics.md    # BERTScore, MRR, NDCG — completing the metrics stack
│   │   ├── rag-vs-api-testing.md             # Why RAG testing is harder — non-determinism, silent retrieval failure, two surfaces
│   │   ├── comparing-rag-configurations.md   # Controlled experiment design, scorecard, reading results by query type, declaring a winner
│   │   ├── rag-testing-toolkit.md            # Testing levels and tools (manual/scripted/RAGAS)
│   │   └── adversarial-testing.md            # Hallucination, false premise, prompt injection, document injection, conflicting docs
│   ├── going-further/
│   │   ├── resources.md                 # Curated external reading + references
│   │   └── quizzes/
│   │       ├── rag-testing-quiz.md       # Quiz 1 — pipeline, chunking, retrieval basics
│   │       ├── rag-testing-quiz-2.md     # Quiz 2 — evaluation metrics, BLEU/ROUGE/RAGAS
│   │       └── rag-testing-quiz-3.md     # Quiz 3 — retrieval internals, Advanced RAG
│   └── sample-data/
│       ├── orion-technologies-employee-handbook.pdf  # Test document
│       └── generate_handbook.py                      # Script that generated the test document
├── golden-dataset/              # Everything for golden dataset evaluation — end to end
│   ├── golden-dataset.csv               # The dataset — 60 rows (questions, reference answers, expected chunks)
│   ├── guide.md                         # Why golden datasets, how to build one, generation approaches
│   ├── first-evaluation.md              # Step-by-step: run the dataset, score retrieval + generation
│   ├── run_evaluation.py                # Script: sends every question to the Orion HR Assistant
│   ├── score_results.py                 # Script: computes BLEU, ROUGE-L, and GPTScore on results
│   ├── ragas_eval.py                    # Script: runs Faithfulness, Answer Relevancy, Context Precision/Recall via RAGAS
│   └── runs/                            # Output from each evaluation run (run-001.csv is a sample)
└── README.md
```

---

## Quick Start

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (4 GB RAM minimum, 8 GB recommended) and [Git](https://git-scm.com/).

> **Windows only:** Enable WSL 2 first — run `wsl --install` in PowerShell as Administrator, then restart before continuing.

```bash
# 1. Clone and navigate to the Docker directory
git clone https://github.com/langgenius/dify.git
cd dify/docker

# 2. Create the environment file (no edits needed to get started)
cp .env.example .env           # macOS / Linux
# Copy-Item .env.example .env  # Windows PowerShell

# 3. Start all services
#    First run downloads ~3–4 GB of images — allow 5–15 minutes
docker compose up -d

# 4. Confirm everything is healthy
docker compose ps
```

Open **http://localhost** in your browser. The first load may take 30–60 seconds while the API runs database migrations.

---

## Dify Configuration

> **Full walkthrough:** [docs/setup/dify-setup.md](docs/setup/dify-setup.md) — LLM provider setup, Knowledge Base creation, chatbot build, and API key for automated testing.

Summary of the one-time setup:

1. Create your admin account on first login at http://localhost
2. Go to **Settings → Model Provider** and add an LLM API key
3. Set a default embedding model (star icon next to the model)
4. Create a **Knowledge Base**, upload the test document from `docs/sample-data/`, and configure chunking
5. Build a **Chatbot** app, attach the Knowledge Base, and publish it

**Provider recommendation:** OpenAI `gpt-4o-mini` + `text-embedding-3-small` is cheap (~$0.10/session) and well-supported. [Ollama](https://ollama.com) is free and runs entirely locally if you prefer no API costs.

---

## Testing the Pipeline

This is the core focus of the project. The system under test is the **Orion HR Assistant** — a RAG chatbot built on the Orion Technologies Employee Handbook, a realistic test document with policy information, dates, named roles, and edge-case content.

### Test layers

| Layer | What you're checking | How |
|---|---|---|
| **Retrieval quality** | Right chunks returned for a query | Dify retrieval inspector + direct API calls |
| **Faithfulness** | Answer grounded in retrieved chunks — no hallucination | Manual check + RAGAS / LLM-as-judge |
| **Answer relevance** | Response actually addresses the question | Manual check + RAGAS |
| **Out-of-scope handling** | System refuses questions outside the knowledge base | Scripted negative test cases |
| **Adversarial robustness** | Prompt injection, jailbreaks, boundary probes | Red-team test cases |
| **Chunking sensitivity** | Answer quality changes when chunk size / overlap changes | A/B config comparison |

### API test (run from terminal)

```bash
APP_API_KEY="your-api-key-here"   # App → API Access → API Key in Dify UI

curl -X POST http://localhost/v1/chat-messages \
  -H "Authorization: Bearer $APP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the annual leave policy?",
    "response_mode": "blocking",
    "user": "test-user-1",
    "conversation_id": ""
  }'
```

Full reading list, in suggested order: see [Resources](#resources) below.

---

## Stopping and Restarting

```bash
docker compose down           # stop services, data preserved
docker compose down -v        # stop and delete all data (full reset)
docker compose up -d          # start again
```

> `-v` deletes all volumes including your database and uploaded documents. Use only for a clean slate.

---

## Troubleshooting

**http://localhost shows nothing / connection refused**
The API takes 1–2 minutes on first boot to run migrations. Wait, refresh, then check:
```bash
docker compose logs api --tail=50
```

**A container keeps restarting**
```bash
docker compose ps              # identify which container
docker compose logs <name>     # read the error
```
Common causes: insufficient RAM allocated to Docker, or a port conflict on 80/443.

**Port 80 already in use**
In `.env`, set `EXPOSE_NGINX_PORT=8080`, then:
```bash
docker compose down && docker compose up -d
```
Access Dify at **http://localhost:8080**

**Out of disk space**
```bash
docker system prune            # remove unused images and containers
```

---

## Resources

A suggested reading order — concepts first, then set up, then test:

**1 · Learn the concepts**
- [How RAG Works](docs/concepts/how-rag-works.md) — **start here.** The pipeline end to end, with the testing implication at each step
- [RAG Terminology Glossary](docs/concepts/glossary.md) — every RAG term, explained in plain language

**2 · Set up the pipeline**
- [Dify Setup Guide](docs/setup/dify-setup.md) — step-by-step Dify configuration
- [LLM API Cost Comparison](docs/reference/llm-api-cost-comparison.md) — frontier vs. open-source-serving providers, pricing, free tiers, and Dify plugin compatibility (useful if you hit Gemini's free-tier rate limits)
- [Embedding Model API Comparison](docs/reference/embedding-model-pricing-comparison.md) — embedding API cost, dimensions, and quality across providers

**3 · Test it — must-read**
- [Why RAG Testing Is Harder Than Normal API Testing](docs/testing/rag-vs-api-testing.md) — read this first: three properties that break standard test assumptions; the three-layer testing strategy
- [Test Strategy](docs/testing/test-strategy.md) — scope, risk areas, test types, cadence, and release gates
- [Functional Test Scenarios](docs/testing/functional-test-scenarios.md) — 74 test cases across 12 categories (in-scope, paraphrase, adversarial, multi-hop, multi-turn, tone, and more)
- [RAG Evaluation Playbook](docs/testing/rag-evaluation-playbook.md) — how to execute evaluation: retrieval metrics, generation scoring, A/B testing
- [RAGAS Evaluation Metrics](docs/testing/ragas-evaluation-metrics.md) — Faithfulness, Answer Relevancy, Context Precision, Context Recall: how each works, what it catches, when to use it
- [Adversarial Testing](docs/testing/adversarial-testing.md) — five failure modes (hallucination, false premise, prompt injection, document injection, conflicting docs); how to write cases and classify severity

**4 · Test it — go deeper**
- [Chunking Strategies](docs/testing/chunking-strategies.md) — how chunk size, overlap, and strategy affect retrieval; failure modes by query type; how to run a before/after comparison
- [Comparing RAG Configurations](docs/testing/comparing-rag-configurations.md) — controlled experiment design, scorecard by config type, reading results by query type, declaring a winner
- [Advanced Evaluation Metrics](docs/testing/advanced-evaluation-metrics.md) — BERTScore, MRR, and NDCG: the metrics that complete the picture beyond BLEU/ROUGE and Recall@K
- [Introduction to RAGAS](docs/testing/ragas-intro.md) — how RAGAS TestsetGenerator works: components, flow, question types
- [RAG Testing Toolkit](docs/testing/rag-testing-toolkit.md) — manual / scripted / eval tooling levels and RAGAS setup

**5 · Golden dataset evaluation** (end to end in one folder: `golden-dataset/`)
- [Golden Dataset Guide](golden-dataset/guide.md) — why golden datasets, how to build one, generation approaches
- [First RAG Evaluation](golden-dataset/first-evaluation.md) — run the dataset, score retrieval and generation, record a baseline
- Scripts — run in this order:
  1. `run_evaluation.py` — sends every question to the Orion HR Assistant, writes `runs/run-001.csv`
  2. `score_results.py` — computes BLEU, ROUGE-L, and GPTScore on the results
  3. `ragas_eval.py` — runs Faithfulness, Answer Relevancy, Context Precision, Context Recall via RAGAS
- Results land in `golden-dataset/runs/`

**6 · Going further (optional)**
- [Further Resources](docs/going-further/resources.md) — curated external reading: surveys, frameworks, leaderboards, primary sources
- [Quiz 1](docs/going-further/quizzes/rag-testing-quiz.md) · [Quiz 2](docs/going-further/quizzes/rag-testing-quiz-2.md) · [Quiz 3](docs/going-further/quizzes/rag-testing-quiz-3.md) — self-check on pipeline, metrics, and retrieval internals

### External
- [Dify Documentation](https://docs.dify.ai)
- [RAGAS — RAG Evaluation Framework](https://docs.ragas.io)
- [Weaviate Vector Database](https://weaviate.io/developers/weaviate)
- [What is RAG? (AWS)](https://aws.amazon.com/what-is/retrieval-augmented-generation/)

> More curated external links — surveys, the MTEB leaderboard, security references — are in [docs/going-further/resources.md](docs/going-further/resources.md).

---

*Built for learning and sharing. If this helped you, feel free to star the repo or connect on LinkedIn.*
