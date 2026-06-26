<div align="center">

# RAG Application Testing with Dify

**A hands-on project for learning how to test Retrieval-Augmented Generation (RAG) pipelines**

[![Docker](https://img.shields.io/badge/Docker-required-2496ED?logo=docker&logoColor=white)](https://www.docker.com/products/docker-desktop/)
[![Dify](https://img.shields.io/badge/Powered%20by-Dify%201.15-6366f1?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEyIDJMMiA3bDEwIDUgMTAtNS0xMC01ek0yIDE3bDEwIDUgMTAtNS0xMC01TDIgMTd6TTIgMTJsMTAgNSAxMC01LTEwLTVMMiAxMnoiLz48L3N2Zz4=)](https://github.com/langgenius/dify)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey?logo=apple)](https://github.com/Krishna-Madhiraju/rag-testing-with-dify)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/Krishna-Madhiraju/rag-testing-with-dify/pulls)

<br/>

> *Documenting my journey in understanding and testing RAG systems — from setup to evaluating retrieval quality, chunking strategies, embedding models, and full pipeline behaviour.*

<br/>

[What is RAG?](#what-is-rag) · [Why Dify?](#why-dify) · [macOS Setup](#setup-on-macos) · [Windows Setup](#setup-on-windows) · [First Config](#first-time-dify-configuration) · [Testing Guide](#testing-rag-applications) · [Troubleshooting](#troubleshooting)

</div>

---

## What is RAG?

**Retrieval-Augmented Generation (RAG)** gives a Large Language Model access to *your own data* at query time — rather than relying solely on what it learned during training.

**How it works in three steps:**

| Step | What happens |
|:---:|---|
| **1. Index** | Documents are split into chunks and converted into vector embeddings stored in a vector database |
| **2. Retrieve** | When a user asks a question, the most semantically similar chunks are fetched |
| **3. Generate** | The LLM receives those chunks as context and answers using your data |

```
User Question
     │
     ▼
┌─────────────┐    top-K similar chunks    ┌──────────────────┐
│  Embedding  │ ─────────────────────────▶ │  Vector Store    │
│   Model     │ ◀─────────────────────────│  (Weaviate)      │
└─────────────┘                            └──────────────────┘
     │
     ▼
┌──────────────────────────────────────────────┐
│  Prompt = System Prompt                      │
│          + Retrieved Chunks (context)        │
│          + User Question                     │
└──────────────────────────────────────────────┘
     │
     ▼
   LLM Response  ✓
```

---

## Why Dify?

[Dify](https://github.com/langgenius/dify) is an open-source LLM application platform that makes RAG pipelines easy to build, inspect, and test — without writing boilerplate code.

| Feature | Why it matters for testing |
|---|---|
| Visual workflow builder | See and debug every node in your RAG pipeline |
| Built-in Knowledge Base | Upload documents and test chunking/embedding settings instantly |
| Retrieval inspector | See exactly which chunks were returned for any query |
| Multiple vector stores | Swap between Weaviate, pgvector, Qdrant, Chroma, and more |
| REST API | Automate test cases and integrate with test frameworks |
| Open source | Full transparency into how RAG is implemented |

---

## Project Structure

```
rag-testing-with-dify/
├── dify/                   # Dify platform clone (gitignored — not pushed)
│   └── docker/             # All Docker Compose files live here
│       ├── .env            # Your local config (gitignored, never committed)
│       ├── .env.example    # Template — copy this to .env to get started
│       └── docker-compose.yaml
└── README.md               # You are here
```

---

## Prerequisites

Before you start, install these two tools.

### 1. Docker Desktop

Docker runs all Dify services in isolated containers — no need to install Python, Node.js, PostgreSQL, or Redis manually.

**[Download Docker Desktop](https://www.docker.com/products/docker-desktop/)** — available for both macOS and Windows.

Minimum resources to configure in Docker Desktop settings:

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB free | 30 GB free |

> **Windows users:** Docker Desktop requires **WSL 2** (Windows Subsystem for Linux). The installer handles this — see the [Windows setup](#setup-on-windows) section below.

### 2. Git

| Platform | How to get it |
|---|---|
| macOS | Pre-installed. Verify: `git --version` in Terminal |
| Windows | [Download Git for Windows](https://git-scm.com/download/win) |

---

## Setup on macOS

Open **Terminal** and run the following commands in order.

### Step 1 — Clone the Dify repository

```bash
git clone https://github.com/langgenius/dify.git
cd dify/docker
```

### Step 2 — Create your environment file

```bash
cp .env.example .env
```

This copies the default config file. All passwords and connection strings are pre-filled with safe development defaults — no editing required to get started.

### Step 3 — Start Docker Desktop

Open **Docker Desktop** from your Applications folder. Wait for the whale icon in the menu bar to stop animating — it is ready when the tooltip says **"Docker Desktop is running"**.

### Step 4 — Start all Dify services

```bash
docker compose up -d
```

> **First run:** Docker downloads all container images (~3–4 GB). This takes **5–15 minutes** depending on your internet speed. Subsequent starts take under 30 seconds.
>
> The `-d` flag runs containers in the background (detached mode), keeping your terminal free.

### Step 5 — Verify everything is running

```bash
docker compose ps
```

Expected output — all services should show `Up` or `healthy`:

```
NAME                     STATUS
docker-api-1             Up (healthy)
docker-web-1             Up
docker-db_postgres-1     Up (healthy)
docker-redis-1           Up (healthy)
docker-weaviate-1        Up
docker-nginx-1           Up
docker-sandbox-1         Up (healthy)
docker-worker-1          Up
```

### Step 6 — Open Dify

Go to **[http://localhost](http://localhost)** in your browser.

> The first load may take **30–60 seconds** while the API runs database migrations. If you see a loading spinner, just wait and refresh.

---

## Setup on Windows

Open **PowerShell** or **Windows Terminal** and follow these steps.

### Step 1 — Enable WSL 2

Open PowerShell **as Administrator** and run:

```powershell
wsl --install
```

Restart your computer when prompted. WSL 2 is required by Docker Desktop on Windows.

### Step 2 — Install Docker Desktop

[Download Docker Desktop](https://www.docker.com/products/docker-desktop/) and run the installer.

During setup, make sure **"Use WSL 2 instead of Hyper-V"** is checked. After installation, start Docker Desktop and wait until the system tray icon shows **"Docker Desktop is running"**.

### Step 3 — Clone the Dify repository

```powershell
git clone https://github.com/langgenius/dify.git
cd dify\docker
```

### Step 4 — Create your environment file

**PowerShell:**
```powershell
Copy-Item .env.example .env
```

**Command Prompt or Git Bash:**
```bash
copy .env.example .env
```

### Step 5 — Start all Dify services

```powershell
docker compose up -d
```

> **First run:** Downloads ~3–4 GB of container images. Allow **5–15 minutes** on first run.

### Step 6 — Verify everything is running

```powershell
docker compose ps
```

All services should show `Up` or `healthy` status.

### Step 7 — Open Dify

Go to **[http://localhost](http://localhost)** in your browser.

> **Windows Firewall:** If prompted by Windows Defender Firewall, click **"Allow access"** for Docker.

---

## First-Time Dify Configuration

### 1. Create your admin account

On your first visit to http://localhost you will see a setup screen. Fill in your email, username, and a password — this becomes your administrator account.

### 2. Add an LLM provider

Dify needs an LLM to generate answers and (optionally) create embeddings.

1. Click your **avatar** (top right) → **Settings** → **Model Provider**
2. Choose a provider and paste your API key:

| Provider | Cost | Best for |
|---|---|---|
| **OpenAI** | Pay per use | `gpt-4o-mini` + `text-embedding-3-small` — best value |
| **Anthropic** | Pay per use | Excellent reasoning with `claude-haiku-4-5` |
| **Ollama** | **Free / local** | Run models on your own machine, no API cost |

> **Tip for beginners:** OpenAI's `gpt-4o-mini` with `text-embedding-3-small` is the most cost-effective starting point. A full RAG test session typically costs **less than $0.10**.

### 3. Set a default embedding model

1. In **Settings → Model Provider**, find your provider
2. Click the **star icon** next to an embedding model (e.g. `text-embedding-3-small`)
3. This model is used automatically whenever you create a Knowledge Base

---

## Building Your First RAG Pipeline

### Create a Knowledge Base

1. Click **Knowledge** in the left sidebar → **Create Knowledge**
2. Upload a **PDF, TXT, or Markdown** file
3. Configure chunking settings:

| Setting | What it controls | Starting value |
|---|---|---|
| Chunk size | Max tokens per chunk | 500–1000 |
| Chunk overlap | Tokens shared between adjacent chunks | 50–100 |

4. Click **Save and Process** — Dify embeds all chunks into Weaviate

### Test retrieval before building an app

1. Open your Knowledge Base → click the **Test** tab
2. Type a question and inspect which chunks are returned
3. Tune **Top-K** (number of chunks) and the **similarity threshold** to see how results change

### Build a RAG chatbot

1. **Studio** → **Create App** → **Chatbot**
2. In the **Context** section, attach your Knowledge Base
3. Add a system prompt:
   ```
   You are a helpful assistant. Answer only using the provided context.
   If the answer is not in the context, say "I don't know."
   ```
4. Click **Publish** → test in the preview panel on the right

---

## Testing RAG Applications

This is the core focus of the project. Here are the key dimensions to evaluate.

### Retrieval Quality

Verify the right chunks come back for a given query.

| Test scenario | What to check |
|---|---|
| Relevant query | Top-K chunks should clearly contain the answer |
| Irrelevant query | Should return low similarity scores or nothing at all |
| Paraphrased query | Different wording of the same question should return the same chunks |
| Edge case query | Very short, very long, or ambiguous queries — does retrieval degrade gracefully? |

### Chunking Strategy

Compare how splitting settings affect end-to-end quality.

| Setting | Trade-off |
|---|---|
| Small chunks (200 tokens) | More precise retrieval, but may cut off necessary context |
| Large chunks (1000 tokens) | More context per chunk, but lower retrieval precision |
| Higher overlap (100+ tokens) | Reduces context loss at chunk boundaries; uses more storage |

### Answer Quality (the "RAG Triad")

| Dimension | Question to ask |
|---|---|
| **Faithfulness** | Is the answer grounded in the retrieved chunks? (No hallucination) |
| **Answer relevance** | Does the response actually address what was asked? |
| **Context relevance** | Were the retrieved chunks actually relevant to the question? |

### Automated testing via API

Dify exposes a full REST API — use it to build repeatable test suites.

```bash
# Find your API key: App → API Access → API Key
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

You can wrap this in a script to run a full set of question–expected-answer pairs and compare results across different chunking or model configurations.

---

## Stopping and Restarting

| Command | Effect |
|---|---|
| `docker compose down` | Stop all containers, **keep all data** |
| `docker compose up -d` | Start containers again (fast after first run) |
| `docker compose down -v` | Stop containers and **delete all data** (full reset) |

> **Warning:** `docker compose down -v` deletes your database, uploaded documents, and all Weaviate vectors. Use it only for a clean slate.

---

## Troubleshooting

<details>
<summary><strong>http://localhost shows nothing / connection refused</strong></summary>

The API takes 1–2 minutes on first boot to run database migrations. Wait and refresh. To watch progress:

```bash
docker compose logs api --tail=50 -f
```
</details>

<details>
<summary><strong>A container keeps restarting</strong></summary>

```bash
docker compose ps                  # see which container is unhealthy
docker compose logs <service-name> # read the error message
```

Most common cause: Docker does not have enough RAM. Open Docker Desktop → Settings → Resources and increase memory to at least 4 GB.
</details>

<details>
<summary><strong>Port 80 is already in use</strong></summary>

Another application (e.g. MAMP, Apache, IIS) is using port 80. Edit `dify/docker/.env` and change:

```
EXPOSE_NGINX_PORT=8080
```

Then restart:
```bash
docker compose down && docker compose up -d
```

Access Dify at **http://localhost:8080**
</details>

<details>
<summary><strong>Running out of disk space</strong></summary>

```bash
docker system prune        # remove unused images, containers, and networks
docker volume prune        # remove unused volumes (careful — check first)
```
</details>

<details>
<summary><strong>Reset everything and start completely fresh</strong></summary>

```bash
docker compose down -v
docker compose up -d
```
</details>

---

## Resources

- [Dify Documentation](https://docs.dify.ai)
- [Dify GitHub](https://github.com/langgenius/dify)
- [What is RAG? — AWS](https://aws.amazon.com/what-is/retrieval-augmented-generation/)
- [Weaviate Vector Database Docs](https://weaviate.io/developers/weaviate)
- [The RAG Triad — Explained](https://www.trulens.org/trulens/getting_started/core_concepts/rag_triad/)

---

<div align="center">

*If this helped you, consider starring the repo or connecting on [LinkedIn](https://www.linkedin.com/in/krishna-madhiraju/)*

</div>
