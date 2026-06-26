  # RAG Application Testing with Dify

A hands-on learning project for exploring and testing **Retrieval-Augmented Generation (RAG)** pipelines using [Dify](https://github.com/langgenius/dify) — an open-source platform for building LLM applications.

> This project documents my journey in learning how to test RAG systems: evaluating retrieval quality, chunking strategies, embedding models, and end-to-end pipeline behaviour.

---

## Table of Contents

- [What is RAG?](#what-is-rag)
- [Why Dify?](#why-dify)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup on macOS](#setup-on-macos)
- [Setup on Windows](#setup-on-windows)
- [First-Time Dify Configuration](#first-time-dify-configuration)
- [Building Your First RAG Pipeline](#building-your-first-rag-pipeline)
- [Testing RAG Applications](#testing-rag-applications)
- [Stopping and Restarting](#stopping-and-restarting)
- [Troubleshooting](#troubleshooting)

---

## What is RAG?

**Retrieval-Augmented Generation (RAG)** is a technique that gives a Large Language Model (LLM) access to your own data at query time. Instead of relying solely on what the model learned during training, RAG:

1. **Indexes** your documents by splitting them into chunks and converting each chunk into a vector embedding
2. **Retrieves** the most relevant chunks when a user asks a question
3. **Augments** the LLM prompt with those chunks so the model can answer using your data

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

---

## Why Dify?

| Feature | Benefit for RAG Testing |
|---|---|
| Visual workflow builder | See every step of your RAG pipeline, no code required |
| Built-in knowledge base | Upload documents and test chunking/embedding strategies instantly |
| Multiple vector stores | Switch between Weaviate, pgvector, Qdrant, Chroma, and more |
| Retrieval inspection | View which chunks were retrieved for any given query |
| API-first design | Automate test cases via REST API |
| Open source | Full visibility into how RAG is implemented under the hood |

---

## Project Structure

```
rag-demo/
├── dify/                   # Dify platform (submodule / cloned repo)
│   └── docker/             # Docker Compose setup — this is where you run commands
│       ├── .env            # Your local environment config (gitignored)
│       ├── .env.example    # Template with all available settings
│       └── docker-compose.yaml
├── docs/
│   ├── dify-setup.md       # Step-by-step Dify configuration guide
│   ├── glossary.md         # RAG terminology reference
│   └── sample-data/
│       └── orion-technologies-employee-handbook.pdf  # Test document
└── README.md               # This file
```

---

## Prerequisites

You need the following tools installed before starting.

### Docker Desktop

Docker runs all Dify services in containers so you do not need to install Python, Node.js, or any database manually.

| Platform | Download |
|---|---|
| macOS | https://www.docker.com/products/docker-desktop/ |
| Windows | https://www.docker.com/products/docker-desktop/ |

**Minimum resources to allocate to Docker:**
- CPU: 2 cores
- RAM: **4 GB** (8 GB recommended)
- Disk: 20 GB free

> On Windows, Docker Desktop requires **WSL 2** (Windows Subsystem for Linux). The Docker installer will guide you through enabling it.

### Git

| Platform | Download |
|---|---|
| macOS | Comes pre-installed. Verify with `git --version` in Terminal |
| Windows | https://git-scm.com/download/win |

---

## Setup on macOS

Open **Terminal** and follow these steps.

### 1. Clone the repository

```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
```

### 2. Create the environment file

```bash
cp .env.example .env
```

This copies the default configuration. No edits are needed to get started — all passwords and keys are pre-filled with development defaults.

### 3. Start Docker Desktop

Launch **Docker Desktop** from your Applications folder and wait for the whale icon in the menu bar to stop animating (it is ready when it shows "Docker Desktop is running").

### 4. Start all Dify services

```bash
docker compose up -d
```

The first run downloads all container images (~3–4 GB total). This takes **5–15 minutes** depending on your internet speed. Subsequent starts take under 30 seconds.

**What `-d` means:** Detached mode — containers run in the background so you keep your terminal free.

### 5. Verify all containers are running

```bash
docker compose ps
```

You should see all services with status `Up` or `healthy`:

```
docker-api-1           Up (healthy)
docker-web-1           Up
docker-db_postgres-1   Up (healthy)
docker-redis-1         Up (healthy)
docker-weaviate-1      Up
docker-nginx-1         Up
...
```

### 6. Open Dify

Navigate to **http://localhost** in your browser. The first load may take 30–60 seconds while the API completes database migrations.

---

## Setup on Windows

Open **PowerShell** (or Windows Terminal) and follow these steps.

### 1. Enable WSL 2 (if not already done)

Open PowerShell **as Administrator** and run:

```powershell
wsl --install
```

Restart your computer when prompted.

### 2. Install Docker Desktop

Download and install Docker Desktop from https://www.docker.com/products/docker-desktop/

During installation, ensure **"Use WSL 2 instead of Hyper-V"** is checked. After installation, start Docker Desktop and wait for it to show "Docker Desktop is running" in the system tray.

### 3. Clone the repository

```powershell
git clone https://github.com/langgenius/dify.git
cd dify\docker
```

### 4. Create the environment file

**PowerShell:**
```powershell
Copy-Item .env.example .env
```

**Or using Git Bash / Command Prompt:**
```bash
copy .env.example .env
```

### 5. Start all Dify services

```powershell
docker compose up -d
```

The first run downloads all container images (~3–4 GB). This takes **5–15 minutes** on first run.

### 6. Verify all containers are running

```powershell
docker compose ps
```

All services should show `Up` or `healthy` status.

### 7. Open Dify

Navigate to **http://localhost** in your browser.

> **Windows Firewall note:** If prompted by Windows Defender Firewall, click "Allow access" for Docker.

---

## First-Time Dify Configuration

> **Detailed walkthrough:** [docs/dify-setup.md](docs/dify-setup.md) covers adding an LLM provider, creating a Knowledge Base, building a chatbot, and getting the API key for automated testing.

### Step 1 — Create your admin account

On your first visit to http://localhost, you will see the setup screen. Enter:
- Your email address
- A username
- A password

This becomes your administrator account.

### Step 2 — Add an LLM provider

Dify needs access to an LLM to generate answers and (optionally) to create embeddings.

1. Click your avatar (top right) → **Settings**
2. Go to **Model Provider**
3. Choose a provider and enter your API key:

| Provider | Free tier? | Good for |
|---|---|---|
| OpenAI | No (pay per use) | Best quality, `gpt-4o` + `text-embedding-3-small` |
| Anthropic | No (pay per use) | Excellent reasoning, `claude-sonnet-4-6` |
| Ollama | **Yes — fully local** | No API cost, runs models on your machine |

> **Recommended for beginners:** Use OpenAI with `gpt-4o-mini` (very cheap) and `text-embedding-3-small` for embeddings. A typical RAG test session costs under $0.10.

### Step 3 — Set a default embedding model

1. In **Settings → Model Provider**, find your provider
2. Click the **star icon** next to an embedding model (e.g. `text-embedding-3-small`) to set it as the system default
3. This model will be used automatically when you create a Knowledge Base

---

## Building Your First RAG Pipeline

### Create a Knowledge Base

1. Click **Knowledge** in the left sidebar
2. Click **Create Knowledge**
3. Upload a PDF, TXT, or Markdown file (try a document you want to query)
4. Configure chunking:
   - **Chunk size:** 500–1000 tokens is a good starting point
   - **Overlap:** 50–100 tokens helps preserve context across chunk boundaries
5. Click **Save and Process** — Dify will embed all chunks into Weaviate

### Test retrieval directly

Before building a full app, test raw retrieval:

1. Open your Knowledge Base
2. Click the **Test** tab
3. Type a question and see which chunks are retrieved
4. Adjust Top-K (number of chunks returned) and the similarity threshold

### Build a RAG chatbot

1. Click **Studio** → **Create App** → **Chatbot**
2. In the **Context** section, attach your Knowledge Base
3. Set a system prompt, e.g.:
   ```
   You are a helpful assistant. Answer questions using only the provided context.
   If the answer is not in the context, say "I don't know."
   ```
4. Click **Publish** and test in the preview panel

---

## Testing RAG Applications

This is the core focus of this project. Below are the key dimensions to test.

### 1. Retrieval Quality

Check whether the right chunks are returned for a given query.

| Test | What to check |
|---|---|
| Relevant query | Top chunks should clearly contain the answer |
| Irrelevant query | Should return low similarity scores or nothing |
| Paraphrased query | Different wording of the same question should still retrieve the right chunks |

### 2. Chunking Strategy

Compare how different settings affect answer quality.

| Setting | Effect |
|---|---|
| Small chunks (200 tokens) | More precise retrieval, but may miss context |
| Large chunks (1000 tokens) | More context per chunk, but less precise |
| Overlap (100 tokens) | Reduces boundary artifacts at chunk edges |

### 3. Answer Quality

Evaluate the final LLM response.

- **Faithfulness** — Is the answer grounded in the retrieved chunks? (No hallucination)
- **Relevance** — Does the answer actually address the question?
- **Completeness** — Is any important information missing?

### 4. API-based automated testing

Dify exposes a REST API you can use to run automated test suites.

```bash
# Get your app's API key from: App → API Access → API Key
APP_API_KEY="your-api-key-here"

curl -X POST http://localhost/v1/chat-messages \
  -H "Authorization: Bearer $APP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the return policy?",
    "response_mode": "blocking",
    "user": "test-user-1",
    "conversation_id": ""
  }'
```

---

## Stopping and Restarting

### Stop all services (keeps data)

```bash
docker compose down
```

### Stop and delete all data (full reset)

```bash
docker compose down -v
```

> **Warning:** The `-v` flag deletes all volumes including your database and uploaded documents. Only use this for a clean slate.

### Restart after stopping

```bash
docker compose up -d
```

---

## Troubleshooting

### http://localhost shows nothing / connection refused

The API takes 1–2 minutes on first boot to run database migrations. Wait and refresh. Check logs with:

```bash
docker compose logs api --tail=50
```

### A container keeps restarting

```bash
docker compose ps          # identify which container
docker compose logs <name> # read the error
```

Common causes: not enough RAM allocated to Docker, or a port conflict on 80 or 443.

### Port 80 is already in use (Windows/Mac)

Edit `.env` and change:
```
EXPOSE_NGINX_PORT=8080
```
Then restart: `docker compose down && docker compose up -d`
Access Dify at **http://localhost:8080**

### Out of disk space

```bash
docker system prune        # remove unused images and containers
```

### Reset everything and start fresh

```bash
docker compose down -v     # stop containers and delete volumes
docker compose up -d       # start again from scratch
```

---

## Resources

- [RAG Terminology Glossary](docs/glossary.md) — every term you will encounter, explained in plain language
- [Dify Setup Guide](docs/dify-setup.md) — step-by-step configuration for Knowledge Base and Chatbot
- [Functional Test Scenarios](docs/functional-test-scenarios.md) — 54 test cases covering in-scope, out-of-scope, paraphrase, adversarial, and ambiguous queries
- [Dify Documentation](https://docs.dify.ai)
- [Dify GitHub Repository](https://github.com/langgenius/dify)
- [What is RAG? (AWS explainer)](https://aws.amazon.com/what-is/retrieval-augmented-generation/)
- [Weaviate Vector Database](https://weaviate.io/developers/weaviate)

---

*Built for learning and sharing. If this helped you, feel free to star the repo or connect on LinkedIn.*
