# Your First RAG Evaluation — Step by Step

This guide walks you through your first end-to-end evaluation of the **Orion HR Assistant** — a RAG-powered chatbot built on the Orion Technologies Employee Handbook. Follow the steps in order. Do not skip ahead — each step builds on the last, and the results from one step inform whether it makes sense to proceed to the next.

**What you will have at the end:** a documented baseline — a record of how the Orion HR Assistant performs today, that you can compare against every future change.

**Time needed:** 2–3 hours for a first run (most of that is writing the golden dataset carefully).

**Prerequisites:**
- The Orion HR Assistant is running (Dify is the platform powering it, running locally at http://localhost)
- The Orion Technologies handbook is uploaded to a Dify Knowledge Base
- A chatbot app is built and published in Dify

---

## Overview — What You Are Doing and Why

Evaluating a RAG system means checking two things separately:

1. **Did retrieval work?** — When you asked a question, did the system pull back the right chunk from the document?
2. **Did generation work?** — Given whatever chunks it retrieved, did the LLM produce a good answer?

These fail independently. A great LLM cannot save a bad retriever. A great retriever cannot save a hallucinating LLM. You test them separately so you know which one broke when something goes wrong.

The four steps below follow that logic:

```
Step 1 — Build golden dataset              ← what "correct" looks like
Step 2 — Query the Orion HR Assistant      ← what the system actually produces
Step 3 — Score retrieval                   ← did the right chunk come back?
Step 4 — Score generation                  ← was the answer correct?
```

---

## How to Document Results

Before you run a single query, set up your result file. This is where you record everything.

Create a spreadsheet or CSV file called `results/run-001.csv`. The `results/` folder already exists — it contains your golden dataset at `results/golden-dataset.csv`.

The result file has two parts: what you expected (from your golden dataset) and what you actually got (from the Orion HR Assistant). Here are all the columns:

| Column | Where it comes from | What you fill in |
|---|---|---|
| `question` | Golden dataset | The question you sent |
| `reference_answer` | Golden dataset | Your ideal answer |
| `expected_chunk` | Golden dataset | The passage that should have been retrieved |
| `source_doc` | Golden dataset | Document and page |
| `actual_answer` | Orion HR Assistant response | What the assistant actually said |
| `retrieved_chunks` | Orion HR Assistant response | The chunks the assistant retrieved (top-K) |
| `chunk_found` | You assess | `yes` or `no` — did `expected_chunk` appear in `retrieved_chunks`? |
| `chunk_rank` | You assess | If found: was it rank 1, 2, 3...? If not found: leave blank |
| `bleu_score` | Calculated in Step 3 | 0.0–1.0 |
| `rouge_score` | Calculated in Step 3 | 0.0–1.0 |
| `gpt_score` | Calculated in Step 4 | 1–5 rating |
| `gpt_notes` | Step 4 | What the LLM judge said about this answer |
| `flags` | You | Any manual note: "hallucinated", "refused", "partially correct", "wrong chunk" |

> **Why document before you test?** Setting up the columns first forces you to think about what you are measuring before you are influenced by the results. It also means every run has the same structure — so you can compare run-001.csv to run-002.csv by column, not by memory.

---

## Step 1 — Build Your Golden Dataset

**Goal:** create a CSV file where you have manually verified the correct answer and the correct source chunk for each question.

**The golden dataset for the Orion HR Assistant is already built** at `results/golden-dataset.csv` — 60 rows covering all query types. If you are setting up a golden dataset for a new system in future, follow the steps below to build one from scratch.

### Column structure

The golden dataset CSV uses these columns:

```
question, reference_answer, expected_chunk, source_doc, query_type, difficulty, notes
```

The `notes` column explains the reasoning behind each row — what failure mode it tests and what a wrong answer looks like. Read it when interpreting results.

### Distribution to aim for

Use this distribution. It mirrors what real users ask while also covering your test surfaces:

| Query type | How many | What they test |
|---|---|---|
| Factual | 20 | Basic retrieval — one answer, one chunk |
| Paraphrase of a factual question | 10 | Retrieval robustness — same answer, different phrasing |
| Multi-hop | 10 | Cross-passage reasoning — answer requires two chunks |
| Out-of-scope | 8 | Refusal behaviour — system must say it does not know |
| Fictitious entity | 6 | Hallucination resistance — system must not fabricate |
| Adversarial phrasing | 6 | Boundary probes — questions designed to expose gaps or mislead |

**How to write each row:**

1. Open the Orion Technologies handbook PDF
2. Pick a topic (leave policy, onboarding process, notice periods, etc.)
3. Write a realistic user question about that topic
4. Find the exact sentence(s) in the PDF that answer it — paste those as `expected_chunk`
5. Write the `reference_answer` in 1–3 sentences using only what the chunk says — do not add anything the chunk does not contain
6. Tag `query_type` and `difficulty` (easy / medium / hard)

**What a completed row looks like:**

```
question:          "How many vacation days do new employees receive in their first year?"
reference_answer:  "New full-time employees receive 10 days of paid vacation during their first year of employment."
expected_chunk:    "Full-time employees accrue 10 days of PTO in year one, increasing to 15 days after two years of continuous service."
source_doc:        "orion-technologies-employee-handbook.pdf, p.12"
query_type:        "factual"
difficulty:        "easy"
```

### Quality check before moving on

Before going to Step 2, read every row cold — as if you did not write it. Ask yourself:

- Can the `reference_answer` be derived entirely from `expected_chunk`? If you added anything extra, trim it.
- Is the `question` something a real HR user would actually type? If it reads like a textbook question, rewrite it.
- Do you have at least one question where the answer genuinely is not in the document (out-of-scope)?

Fix anything that fails these checks. A bad golden dataset produces meaningless scores — garbage in, garbage out.

---

## Step 2 — Send Questions to the Orion HR Assistant

**Goal:** send each question from your golden dataset to the Orion HR Assistant and record what it returns.

**What to capture:** the actual answer the assistant gives, and the chunks it retrieved to produce that answer. Both matter — you are evaluating retrieval and generation separately.

### First — does the assistant have an API?

This is the key question before you start. How you collect responses depends on whether the system exposes an API endpoint you can call programmatically.

| Situation | What it means | Which path to follow |
|---|---|---|
| API available (API key exists) | You can send all questions automatically and capture structured responses | Path A — curl |
| No API, but a chat UI exists | You interact through the browser manually | Path B — manual UI |
| No API, chat UI only, need to scale | Browser automation simulates the UI | Path C — Playwright (advanced) |

**For the Orion HR Assistant running in Dify:** an API is available. Go to your Dify app → API Access to get your key. Path A applies.

**For other RAG systems:** check whether the vendor or team exposes an API. If they do not, start with Path B. Do not let the absence of an API block you from testing — manual testing with 20–30 rows is entirely practical.

---

### Path A — API available (curl)

Confirm the API is reachable with a test question before running all rows:

```bash
APP_API_KEY="your-api-key-here"

curl -s -X POST http://localhost/v1/chat-messages \
  -H "Authorization: Bearer $APP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the annual leave policy?",
    "response_mode": "blocking",
    "user": "eval-user",
    "conversation_id": ""
  }'
```

You should get a JSON response containing `answer` and metadata. If you get a connection error, the platform is not running — check with `docker compose ps` from inside `dify/docker/`.

**What the response contains:**
- `answer` — the full text answer the assistant generated
- `metadata.retriever_resources` — the list of chunks retrieved, with their content and similarity scores

The `retriever_resources` field is what tells you whether retrieval worked. Each item is one chunk, ranked by similarity score.

**For each question in your golden dataset:**
1. Send the query via the API
2. Copy the `answer` field into the `actual_answer` column of your result file
3. Copy the retrieved chunk texts into the `retrieved_chunks` column (separated by `|`)
4. Assess: does any retrieved chunk match your `expected_chunk`?
   - If yes: mark `chunk_found = yes` and record the rank position
   - If no: mark `chunk_found = no`

---

### Path B — No API, manual UI testing

If no API is available, you test through the chat interface in your browser. This takes longer per question but produces exactly the same result file.

**How to capture what you need from the UI:**

Most RAG platforms show you two things in the chat interface: the answer the assistant gave, and (often in a sidebar or expandable panel) the source chunks it retrieved. In Dify, click the citation or source icon next to any response to see the retrieved chunks and their scores.

For each question:
1. Open the chat interface in your browser
2. Type the question and submit it
3. Copy the answer text into the `actual_answer` column
4. Open the sources/citations panel and copy the retrieved chunk text into `retrieved_chunks`
5. Assess chunk_found and chunk_rank as above
6. Move to the next question

**What if the UI does not show retrieved chunks?**

Some deployed systems hide the retrieval layer from the user-facing interface. In that case you can only assess generation quality — you cannot fill in `retrieved_chunks`, `chunk_found`, or `chunk_rank`. Skip Steps 3 and go straight to Step 4. Note in your scores file that retrieval data was not available.

This is a real limitation worth flagging: if you cannot see which chunks were retrieved, you cannot distinguish a retrieval failure from a generation failure. It is worth asking the team to expose retrieval visibility in the UI or provide an API for testing purposes.

---

### Path C — Browser automation with Playwright (advanced)

If you have no API but need to run more than 30 questions without doing it by hand, Playwright can automate the browser interaction. It opens the chat UI, types each question, waits for the response, and scrapes the answer and source chunks.

This is out of scope for a first evaluation run. Return to it once you have a working manual baseline.

---

### What to look for while filling in results

Read every response before moving to the next question. The patterns you notice now will explain the scores later.

| Signal | What it means |
|---|---|
| Assistant says "I don't know" on an in-scope question | Retrieval missed the chunk, or system prompt is too cautious |
| Assistant answers an out-of-scope question confidently | Hallucination — high priority flag |
| Retrieved chunks look correct but the answer is wrong | Generation failure — retrieval worked, LLM did not |
| Retrieved chunks are irrelevant but answer sounds plausible | LLM fabricated from training data, not from the document |

Mark anything unusual in the `flags` column as you go. Do not wait until scoring — these observations are your most valuable finding notes.

---

## Step 3 — Score Retrieval

**Goal:** turn your `chunk_found` and `chunk_rank` observations into two numbers: Recall@5 and MRR.

**Why calculate these instead of just reading the table?** Because a number lets you track change. If you run the same test after changing chunk size, you need a number to compare — "most chunks came back" is not comparable.

### Calculate Recall@5

Count how many of your rows have `chunk_found = yes`. Divide by total rows.

```
Recall@5 = rows where chunk_found = yes ÷ total rows
```

Example: 16 out of 20 found → Recall@5 = 0.80

Do this separately for each query type. Only score the rows where retrieval is meaningful — skip out-of-scope, fictitious entity, and adversarial rows here (those have no `expected_chunk` to compare against):

| Query type | Found | Total | Recall@5 |
|---|---|---|---|
| Factual | ? | 20 | ? |
| Paraphrase | ? | 10 | ? |
| Multi-hop | ? | 10 | ? |

Multi-hop questions almost always have lower recall than factual ones. If they do not, your multi-hop questions may not actually require two passages.

### Calculate MRR (Mean Reciprocal Rank)

For each row where `chunk_found = yes`, calculate 1 ÷ rank. Average those across all rows.

```
MRR = average of (1 ÷ chunk_rank) across all found rows
     (rows where chunk was not found count as 0)
```

| Rank | Score |
|---|---|
| Found at rank 1 | 1.00 |
| Found at rank 2 | 0.50 |
| Found at rank 3 | 0.33 |
| Found at rank 4 | 0.25 |
| Found at rank 5 | 0.20 |
| Not found | 0.00 |

Example: chunks found at ranks 1, 1, 2, 1, not found → (1.0 + 1.0 + 0.5 + 1.0 + 0.0) ÷ 5 = 0.70

### Record your retrieval scores

Add a summary row or a separate `results/scores.md` file:

```
Run: 001
Date: YYYY-MM-DD
Configuration: chunk size 500, overlap 50, top-K 3, model: text-embedding-3-small

Retrieval
---------
Recall@5 (all):         0.80
Recall@5 (factual):     0.88
Recall@5 (multi-hop):   0.67
Recall@5 (paraphrase):  0.67
MRR:                    0.72

Flagged misses:
- Q4: "What is the parental leave duration?" — chunk not retrieved; expected chunk is on p.18
- Q11: "Can probationary staff take sick leave?" — multi-hop, both required chunks missed
```

### Decision point after Step 3

If Recall@5 is below 0.70, stop here and investigate retrieval before scoring generation. A poor retriever producing bad answers will give you low generation scores — but that is a retrieval problem, not a generation problem. Fixing the wrong thing wastes time.

Common causes of low retrieval recall:
- Chunk size too large (relevant content spread across chunks, diluting the signal)
- Top-K too low (set to 2, but the right chunk is often rank 3)
- Embedding model domain mismatch (HR vocabulary not well represented)

If Recall@5 is 0.70 or above, proceed to Step 4.

---

## Step 4 — Score Generation

**Goal:** score how well the actual answers match your reference answers, across two dimensions: lexical overlap (BLEU + ROUGE) and semantic faithfulness (GPTScore).

### Install the scoring libraries

You need Python. If you do not have it installed, download it from python.org. Then:

```bash
pip install rouge-score nltk
```

`rouge-score` calculates both BLEU and ROUGE. `nltk` provides tokenisation that BLEU needs.

### BLEU and ROUGE — what they measure

**BLEU** measures how many n-grams (short word sequences) in your actual answer also appear in your reference answer. A score of 1.0 means every phrase in the answer matches the reference exactly. A score of 0.3 means there is partial overlap.

**ROUGE-L** measures the longest common subsequence — the longest stretch of words that appear in both answers in the same order (not necessarily adjacent). It is more flexible than BLEU about word order.

Both are purely lexical — they compare words, not meaning. "The employee receives 10 days" and "Staff are entitled to ten days of leave" say the same thing but score near zero overlap. This is why you also run GPTScore.

**What to expect on your first run:**
- Factual questions with short, specific answers: BLEU 0.3–0.6, ROUGE-L 0.4–0.7
- Paraphrase questions: BLEU often lower (0.1–0.3) even when the answer is correct
- Out-of-scope questions: not meaningful to score (there is no matching reference answer)

### Calculate scores for each row

For each row in your result file, compare `actual_answer` to `reference_answer`. Record the BLEU and ROUGE-L scores in the result file columns.

Skip out-of-scope and fictitious entity rows for BLEU/ROUGE — those rows are evaluated differently (did the system refuse? yes/no).

### GPTScore — what it measures

GPTScore uses an LLM to judge answer quality. You send the question, the retrieved chunk, and the actual answer to an LLM and ask it to rate:

- **Faithfulness** — does the answer only contain information from the retrieved chunk? (1–5)
- **Relevance** — does the answer actually address the question? (1–5)

GPTScore catches what BLEU and ROUGE miss:
- A correct paraphrase scores low on BLEU but high on GPTScore
- A confident hallucination can score high on BLEU (if the fabricated text happens to match your reference wording) but low on GPTScore faithfulness

### What to send to the LLM for scoring

Use this prompt template. Copy it into ChatGPT, Claude, or any LLM you have access to:

```
You are evaluating a RAG system answer.

Question: {question}
Retrieved context: {retrieved_chunk}
System answer: {actual_answer}

Rate the answer on two dimensions:

Faithfulness (1–5): Does the answer contain ONLY information present in the retrieved context?
  5 = every claim in the answer is directly supported by the context
  3 = mostly supported, but one detail seems to come from outside the context
  1 = answer contains significant information not present in the context

Relevance (1–5): Does the answer actually address the question asked?
  5 = directly and completely answers the question
  3 = partially answers but misses something important
  1 = does not address the question

Return your scores and a one-sentence explanation for each.
```

Record the scores in `gpt_score` and the explanation in `gpt_notes`.

**For out-of-scope and fictitious entity rows:** change the question to "Did the system correctly refuse to answer, or did it fabricate a response?" Rate 5 if it said "I don't know" or "I cannot find that in the document." Rate 1 if it gave a confident but fabricated answer.

### Record your generation scores

Add to your `results/scores.md`:

```
Generation
----------
Average BLEU (in-scope rows):     0.35
Average ROUGE-L (in-scope rows):  0.52
Average GPTScore faithfulness:    3.8 / 5
Average GPTScore relevance:       4.1 / 5

Hallucination rate (out-of-scope + fictitious entity rows):
  2 out of 5 rows → system fabricated an answer when it should have refused
  Hallucination rate: 0.40 ← HIGH — investigate system prompt

Non-response rate (in-scope factual rows):
  1 out of 8 rows → system refused despite the answer being clearly in the document
  Non-response rate: 0.13

Notable findings:
- Q7: BLEU=0.62, GPTScore faithfulness=2 — answer matches reference wording but adds
  a claim about "executive approval" not present in the retrieved chunk → hallucination
- Q3 (fictitious entity): system described a "Platinum Leave scheme" in detail → critical finding
```

---

## Step 5 — Interpret Your Baseline

Once you have both retrieval and generation scores recorded, read them as a system — not as individual numbers.

### The interpretation pattern

| Retrieval | Generation | What it tells you |
|---|---|---|
| High recall, high GPTScore | Both layers working | Healthy baseline |
| High recall, low GPTScore | Retriever works, LLM is the problem | Check temperature, system prompt, or top-K |
| Low recall, high GPTScore | LLM is salvaging bad retrieval — but it is probably hallucinating | Fix retrieval first |
| Low recall, low GPTScore | Both layers broken | Start with retrieval |

### What your baseline document looks like when complete

Your `results/scores.md` is your baseline. It should contain:

```
# Evaluation Baseline — Run 001

Date:          YYYY-MM-DD
Configuration:
  - Chunk size: 500 characters
  - Chunk overlap: 50 characters
  - Top-K: 3
  - Embedding model: text-embedding-3-small
  - LLM: gpt-4o-mini
  - System prompt version: v1

Dataset: 60 rows (20 factual, 10 paraphrase, 10 multi-hop, 8 out-of-scope, 6 fictitious entity, 6 adversarial)

Retrieval
  Recall@5:  0.80
  MRR:       0.72

Generation
  BLEU:              0.35
  ROUGE-L:           0.52
  GPTScore (faith):  3.8 / 5
  GPTScore (relev):  4.1 / 5

Failure rates
  Hallucination rate:  0.40 (2/5 out-of-scope rows fabricated)
  Non-response rate:   0.13 (1/8 in-scope rows refused)

Key findings
  - [finding 1]
  - [finding 2]

Next run will change: [whatever configuration change you plan to make]
```

Every future run gets its own numbered file (`run-002.csv`, `run-002 scores`). The goal is not a perfect score on run one — it is having a documented, repeatable record that you can compare as you change configuration.

---

## What Comes Next

Once you have your baseline:

| Next task | When to do it |
|---|---|
| Fix high hallucination rate | Before any other improvement work |
| Run Step 2–4 again after a prompt change | To see if the change helped or hurt |
| Change chunk size and re-run | A/B test — see [RAG Evaluation Playbook](rag-evaluation-playbook.md) |
| Expand golden dataset to 50+ rows | When you want statistically reliable comparisons |
| Add RAGAS evaluation metrics | When manual scoring becomes too slow for your dataset size |

The baseline is the thing. Once you have one good run documented, every other task becomes "compare to run 001."
