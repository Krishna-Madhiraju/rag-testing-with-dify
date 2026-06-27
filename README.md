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
│   ├── setup/
│   │   └── dify-setup.md               # Step-by-step Dify configuration guide
│   ├── reference/
│   │   ├── glossary.md                 # RAG terminology reference
│   │   ├── rag-interview-prep.md       # Key terms + 12 interview Q&As for RAG testing roles
│   │   ├── rag-tester-faq.md           # Tester FAQ — considerations and interview guide
│   │   └── rag-testing-toolkit.md      # Testing levels and tools (manual/scripted/RAGAS)
│   ├── testing/
│   │   ├── test-strategy.md            # One-page test strategy for the RAG pipeline
│   │   └── functional-test-scenarios.md # 67 functional test cases
│   └── sample-data/
│       └── orion-technologies-employee-handbook.pdf  # Test document
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

This is the core focus of the project. The system under test is an **HR Assistant chatbot** built on top of the Orion Technologies Employee Handbook — a realistic test document with policy information, dates, named roles, and edge-case content.

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

### Test documents

| Document | What's in it |
|---|---|
| [test-strategy.md](docs/testing/test-strategy.md) | Scope, risk areas, metrics, release gates, test cadence |
| [functional-test-scenarios.md](docs/testing/functional-test-scenarios.md) | 67 test cases — in-scope, paraphrase, ambiguous, adversarial, multi-hop, out-of-scope |
| [rag-testing-toolkit.md](docs/reference/rag-testing-toolkit.md) | Manual / scripted / eval tooling levels, RAGAS setup, which tool to use when |
| [rag-tester-faq.md](docs/reference/rag-tester-faq.md) | Scenario-based considerations — what to check when documents, models, or config change |

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

### This project
- [Test Strategy](docs/testing/test-strategy.md) — scope, risk areas, test types, cadence, and release gates
- [Functional Test Scenarios](docs/testing/functional-test-scenarios.md) — 67 test cases
- [RAG Testing Toolkit](docs/reference/rag-testing-toolkit.md) — manual / scripted / eval tooling levels and RAGAS setup
- [RAG Tester FAQ](docs/reference/rag-tester-faq.md) — scenario-based considerations and interview prep
- [RAG Interview Prep](docs/reference/rag-interview-prep.md) — key terms + 12 interview Q&As
- [RAG Terminology Glossary](docs/reference/glossary.md) — every RAG term, explained in plain language
- [Dify Setup Guide](docs/setup/dify-setup.md) — step-by-step Dify configuration

### External
- [Dify Documentation](https://docs.dify.ai)
- [RAGAS — RAG Evaluation Framework](https://docs.ragas.io)
- [Weaviate Vector Database](https://weaviate.io/developers/weaviate)
- [What is RAG? (AWS)](https://aws.amazon.com/what-is/retrieval-augmented-generation/)

---

*Built for learning and sharing. If this helped you, feel free to star the repo or connect on LinkedIn.*
