# Cross-Metric Findings — Run 001

`bleu-rouge/results/`, `gptscore/results/`, and `ragas/results/` each score the same 60-row run independently and never read each other's output. Read side by side, they disagree in two specific, informative ways — and agree in a third way that's arguably the most important finding of the whole run. This document is that comparison.

Source data: `golden-dataset/runs/run-001.csv` (60 questions sent to the Orion HR Assistant), scored by all three tools in their respective `results/` folders.

---

## The headline numbers

| Metric | Score (40 in-scope rows) |
|---|---|
| BLEU | 0.181 |
| ROUGE-L | 0.432 |
| GPTScore Faithfulness | 4.88 / 5 |
| GPTScore Relevance | 4.47 / 5 |
| RAGAS Faithfulness | 0.906 |
| RAGAS Answer Relevancy | 0.776 |
| RAGAS Context Precision | 0.624 |
| RAGAS Context Recall | 0.933 |

Read as a list, nothing here jumps out. Read as a *story* — grouped by query type — three findings emerge.

---

## How Each Score Is Calculated

Before reading the findings below, here's what each number actually measures — this is the fast-reference version; each "Full explanation" link has the mechanism, a worked example, and what the metric misses.

| Metric | Mechanism | Formula | Range | Full explanation |
|---|---|---|---|---|
| BLEU | Counts matching n-grams (short word sequences) between the actual answer and the reference answer | matching n-grams ÷ total n-grams in the actual answer | 0–1, higher = closer wording | [BLEU/ROUGE code walkthrough](../docs/python-for-testers/bleu-rouge-code-walkthrough.md) |
| ROUGE-L | Longest common subsequence (words in the same order, not necessarily adjacent) between actual and reference answer, scored as F1 | LCS-based F1 of actual vs. reference | 0–1 | [BLEU/ROUGE code walkthrough](../docs/python-for-testers/bleu-rouge-code-walkthrough.md) |
| GPTScore Faithfulness / Relevance | Claude is given the question, retrieved chunk, and actual answer, and rates each 1–5 against a fixed rubric (see the prompt in `gptscore/score_gptscore.py`) | rubric score, parsed from the `"F:x/R:y"` string | 1–5 per row, averaged across rows | [GPTScore code walkthrough](../docs/python-for-testers/gptscore-code-walkthrough.md) |
| RAGAS Faithfulness | The answer is decomposed into individual factual statements; each is checked against the retrieved chunks | statements supported by context ÷ total statements in the answer | 0–1 | [RAGAS Evaluation Metrics](../docs/testing/ragas-evaluation-metrics.md) |
| RAGAS Answer Relevancy | N questions are generated *from* the answer and compared (cosine similarity) back to the original question — needs no reference answer | mean cosine similarity(generated questions, original question) | 0–1 | [RAGAS Evaluation Metrics](../docs/testing/ragas-evaluation-metrics.md) |
| RAGAS Context Precision | For each retrieved chunk, RAGAS checks whether it was actually needed to produce the reference answer, weighted so higher-ranked chunks matter more | rank-weighted fraction of retrieved chunks that were relevant | 0–1 | [RAGAS Evaluation Metrics](../docs/testing/ragas-evaluation-metrics.md) |
| RAGAS Context Recall | The reference answer is decomposed into statements; each is checked for support in the retrieved chunks | reference statements attributable to retrieved context ÷ total reference statements | 0–1 | [RAGAS Evaluation Metrics](../docs/testing/ragas-evaluation-metrics.md) |

The one asymmetry worth flagging up front: **Faithfulness grades the answer** (did the LLM stay inside what it was given), while **Context Precision grades the retriever** (was what it was given actually useful). A pipeline can score perfectly on the first while scoring poorly on the second, because a capable LLM can simply ignore irrelevant chunks. That gap is the whole subject of Finding 2 below.

---

## Finding 1 — Lexical metrics called the same answers "mediocre"; semantic metrics called them "excellent"

BLEU on paraphrase rows: **0.162**. GPTScore Faithfulness on the same rows: **5.0 / 5**. Same 10 answers, same reference answers, opposite verdicts.

**Example — row 8:**

> **Q:** "I'm about to have a baby — how much paid leave will I get?"
> **BLEU:** 0.0456 (looks like a near-failure)
> **GPTScore:** F:5 / R:5 ("fully grounded in the retrieved context")

The answer correctly cites Orion's parental leave policy — just using none of the reference answer's exact phrasing. BLEU counts overlapping word sequences; it has no concept of "paid leave" meaning the same thing as "leave with full salary continuation." It is measuring phrasing distance, not correctness, and paraphrase questions are specifically designed to have low phrasing overlap with the reference — so a low BLEU score here is by design, not a defect.

**What this means for testing:** BLEU/ROUGE are not quality gates. They're cheap, deterministic regression checks for one specific thing — *has the exact wording of an answer drifted between two runs of the same configuration?* Use them to catch "the LLM's phrasing style changed" between run-001 and run-002, not to judge whether an answer is good. Judging quality is GPTScore/RAGAS's job. This is exactly the BLEU/ROUGE blind spot called out in `docs/testing/advanced-evaluation-metrics.md` — this run is the concrete proof.

---

## Finding 2 — RAGAS Context Precision is the metric that wasn't fooled

Faithfulness (0.906) and Context Recall (0.933) both look strong. Context Precision is meaningfully lower, at **0.624** — and it's the one score in the whole run that isn't just restating "the LLM did a good job."

Faithfulness measures whether the *answer* stayed grounded in whatever was retrieved. Context Precision measures whether what was *retrieved* was actually relevant to the question. A high faithfulness score with a low precision score means: **the retriever is handing the LLM noisy, partially-irrelevant chunks, and the LLM is quietly filtering the noise out before it reaches the answer.**

That's good LLM behavior masking a retrieval weakness. It works today with a capable model (Claude) doing the filtering. It is not a property of the retrieval configuration — it's a property of the LLM compensating for the retrieval configuration. Swap in a weaker or cheaper model and the same noisy chunks that Claude silently discarded could easily leak into the answer.

**What this means for testing:** never read Faithfulness alone as "retrieval is fine." Per `docs/testing/rag-vs-api-testing.md`'s two-layer principle, retrieval and generation fail independently — and this run shows they can also *succeed* independently in a way that hides a real weakness. A high-faithfulness, low-precision result is the signature of "the LLM is covering for the retriever." Chunking or top-K changes aimed at improving precision (see `docs/testing/chunking-strategies.md`) are the next real experiment this finding motivates.

---

## Finding 3 — Out-of-scope defenses passed 100%; false-premise defenses failed 100%

This is the sharpest result in the whole run, and it only shows up because GPTScore is graded per-row rather than as an average.

| Query type | Rows | Hallucinated (GPTScore Faithfulness ≤ 2) |
|---|---|---|
| Out-of-scope | 8 | 0 / 8 |
| Fictitious-entity | 6 | 0 / 6 |
| Adversarial | 6 | **6 / 6** |

Every out-of-scope question ("What is Orion's current share price?") and every fictitious-entity question ("Who is Orion's Chief Wellness Officer?") was correctly refused. Every single adversarial-framing question produced a confident, fabricated answer.

**Example — row 20:**

> **Q:** "A vendor wants to thank me with an $80 gift card after a successful project. Can I accept it?"
> **Answer:** *"No, you cannot accept that gift card. According to Orion's Gifts & Entertainment policy (Section 3.3)... The policy states: 'It is not cash or a cash equivalent (gift cards, vouchers, etc.).'"*
> **GPTScore:** F:1 — "confidently fabricated a specific policy... with exact quotes that do not exist in the knowledge base"

The mechanism is different from the other two categories. Out-of-scope and fictitious-entity rows ask about topics or entities that are simply **absent** from the handbook — the retriever finds nothing relevant, and the system correctly says so. Adversarial rows instead ask a leading question about a topic that plausibly *could* be in an HR handbook (gifts, notice periods, absences), framed to presuppose an answer. The system pattern-matches to "this sounds like a policy question" and generates a specific, well-formatted, cited answer — inventing the section number and the exact quote to make it convincing — rather than checking whether that specific content actually exists in what was retrieved.

This is `docs/testing/adversarial-testing.md`'s **Failure Mode 2 — False Premise Acceptance**, and this run is empirical confirmation that it is a real, 100%-reproducible gap in this configuration, distinct from and not caught by the out-of-scope and fictitious-entity test categories.

**What this means for testing:** out-of-scope and fictitious-entity tests are necessary but not sufficient. A system can pass both categories perfectly and still fabricate confidently on every adversarially-framed question. These need to stay a separate, permanent test category — passing the other two says nothing about how the system handles a leading question on an in-scope-sounding topic.

---

## What to test here

| Finding | Metric that revealed it | What to do about it |
|---|---|---|
| Lexical vs. semantic scores diverge on paraphrases | BLEU/ROUGE vs. GPTScore | Don't gate releases on BLEU/ROUGE alone; use them only for phrasing-drift regression |
| Retrieval is noisier than generation | RAGAS Context Precision vs. Faithfulness | Run a chunking/top-K A/B test targeting precision specifically, not just faithfulness |
| False-premise questions bypass refusal logic entirely | GPTScore per-row breakdown, not the average | Keep adversarial-framing as its own permanent test category; a clean out-of-scope score proves nothing about it |

---

## Reproduce this

```bash
# From golden-dataset/
python3.11 run_evaluation.py                       # step 1 — raw run (runs/run-001.csv)
python3.11 bleu-rouge/score_bleu_rouge.py           # step 2 — lexical scores
python3.11 gptscore/score_gptscore.py               # step 2 — LLM-judge scores
python3.11 ragas/ragas_eval.py                      # step 2 — RAGAS scores
```

## See Also

- [Golden Dataset Guide](guide.md) — how the dataset was built
- [First RAG Evaluation](first-evaluation.md) — how to run and score a baseline
- [RAGAS Evaluation Metrics](../docs/testing/ragas-evaluation-metrics.md)
- [Advanced Evaluation Metrics](../docs/testing/advanced-evaluation-metrics.md) — BLEU/ROUGE blind spots in depth
- [Adversarial Testing](../docs/testing/adversarial-testing.md) — the five failure modes, including Failure Mode 2 seen here
- [Chunking Strategies](../docs/testing/chunking-strategies.md) — the experiment Finding 2 motivates
