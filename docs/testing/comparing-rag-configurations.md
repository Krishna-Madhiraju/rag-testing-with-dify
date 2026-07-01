# Comparing Two RAG Configurations

A configuration comparison is an experiment: you change one thing, measure the impact on your golden dataset, and decide whether the change is an improvement. Done well, it gives you evidence for a decision. Done poorly, it gives you numbers that feel like evidence but are not.

This document explains how to design the experiment, read the results, and make a defensible decision. This is what the glossary calls **A/B Configuration Testing** — the term and this document describe the same thing.

---

## The Short Version: Who, What, When, Where, Why, How

| Question | Answer |
|---|---|
| **What** | Change exactly one RAG configuration setting, run the same golden dataset through both versions, and compare evaluation scores — not impressions — to decide which is better. |
| **Why** | A config change shipped on a hunch ("bigger chunks feel like they'd help") can silently regress something you weren't watching. A/B testing turns "I think this helps" into "multi-hop Recall@K moved from 0.42 to 0.68 while Faithfulness held at 0.90" — a claim a reviewer can check. |
| **Who** | The tester (or whoever owns retrieval quality) designs and runs the experiment. Declaring the winner is usually theirs too — except when there's a genuine trade-off with no clean winner (see [The Trade-Off Decision](#the-trade-off-decision)), which is a product/priority call and needs whoever owns that call in the room. |
| **When** | Before shipping any change to chunk size/overlap/strategy, embedding model, Top K, Score Threshold, Hybrid Search, Rerank Setting, LLM model, temperature, or system prompt. Also run one reactively when a finding demands it — e.g. `golden-dataset/findings.md` shows Context Precision at 0.624 against a Faithfulness of 0.906; that gap is itself the hypothesis for "try a smaller chunk size or a Rerank Model and see if precision recovers." |
| **Where** | Locally, against your own Dify Knowledge Base and Weaviate index. Never A/B test against a shared or production knowledge base — re-indexing for Config B disturbs anyone else querying it mid-experiment. |
| **How** | One variable, same golden dataset, same session, read the breakdown by query type before you look at the overall average. Full mechanics below. |

---

## What a Configuration Is

A RAG configuration is the complete set of settings that define how the pipeline behaves. Any of these can be varied:

| Layer | Examples of what can change |
|---|---|
| Ingestion | Chunk size, chunk overlap, chunking strategy |
| Retrieval | Embedding model, Top K, Score Threshold, retrieval mode (Vector Search vs Hybrid Search), Rerank Setting |
| Generation | LLM model, system prompt wording, temperature |

Changing any one of these changes the configuration. A comparison is only meaningful when exactly one thing changes between the two runs.

---

## Parameters You Can A/B Test — the Full Catalog

Organized by the same three layers as the table above. Ingestion-layer changes require a full re-index; retrieval- and generation-layer changes usually don't (they're settings on the Knowledge Base / Retrieval Settings panel and the Orchestrate tab, respectively).

### Ingestion layer (requires a re-index)

| Parameter | Mechanism — why it changes results | Values to try | Expected effect | Regression risk |
|---|---|---|---|---|
| Chunk size (Maximum chunk length) | Bigger chunks carry more surrounding context per embedding but dilute the vector's semantic focus; smaller chunks embed a tighter concept but may split an answer across a boundary | 500 / 1,000 / 1,500 / 2,000 characters | Larger → better Recall@K on multi-hop and context-completeness questions. Smaller → better Context Precision | Too small: boundary questions fail (the answer straddles two chunks, neither retrieves cleanly). Too large: Context Precision and Faithfulness drop — more irrelevant text rides along in every retrieved chunk |
| Chunk overlap | Repeating tokens between neighbouring chunks so a fact sitting on a chunk boundary appears whole in at least one chunk | 0% / 10–15% / 25% of chunk size | Higher overlap → better Recall@K specifically on paraphrase and boundary rows | Index size and embedding cost grow with overlap; too much creates near-duplicate chunks that can crowd genuinely different content out of the top-K |
| Chunking strategy | How boundaries are chosen: fixed character count vs. sentence/paragraph-aware splits vs. parent-child (small-to-big) dual indexing | Compare fixed-size vs. Dify's Parent-Child Chunking at similar sizes | Parent-child typically improves both precision (child chunk matches) and completeness (parent chunk returned) at once — see [Chunking Strategies § Parent-Child](chunking-strategies.md#parent-child-chunking-advanced) | Parent-child doubles storage and re-indexing time. Don't change size and strategy in the same run — pick one |

### Retrieval layer (re-index not required)

| Parameter | Mechanism | Values to try | Expected effect | Regression risk |
|---|---|---|---|---|
| Embedding model | Defines the vector coordinate system; every chunk must be re-embedded, and old and new vectors aren't comparable | Compare 2–3 candidates from [Embedding Model Pricing Comparison](../reference/embedding-model-pricing-comparison.md) | Recall@K shifts across all query types, most visibly on paraphrase rows (domain vocabulary fit) | Full re-index required — the most expensive single experiment on this list. Batch it last, once cheaper retrieval settings are already tuned |
| Top K | Number of chunks retrieved per query and handed to the LLM | 3 / 5 / 8 / 10 (Dify default is 3–4) | Higher K → better Context Recall (the right chunk is more likely to be somewhere in the set) | Higher K → lower Context Precision (more noise) and rising token cost; a very high K risks the "lost in the middle" effect, where the LLM under-weights chunks placed mid-context |
| Score Threshold | Minimum similarity score a chunk must clear to be returned at all, independent of Top K | Off (Dify default) vs. a fixed cutoff, e.g. 0.75 | A well-tuned threshold can improve Context Precision by dropping low-relevance chunks before they reach the LLM | Too strict a threshold silently returns zero chunks on a valid but loosely-phrased question — reads to a user as a false refusal. Keep it off while you're still learning what a "good" score looks like for your data |
| Retrieval mode: Vector Search vs. Hybrid Search | Vector Search is dense/semantic only; Hybrid Search runs dense + full-text (keyword) search simultaneously and re-ranks the combined results | Vector Search (baseline) vs. Hybrid Search | Hybrid typically helps queries with exact terms — policy section numbers, named roles, dates — that an embedding can blur | Hybrid Search always re-ranks, so switching to it also changes the Rerank Setting at the same time. Treat "Vector → Hybrid" as one combined variable, not two |
| Rerank Setting: Weighted Score vs. Rerank Model | A second pass re-scores the initial candidates — Weighted Score reuses the similarity scores already computed at no extra cost; a Rerank Model runs a cross-encoder that reads query + chunk together for a more accurate score | Weighted Score (no extra model) vs. a Rerank Model if one is installed | Improves Context Precision by pushing borderline-relevant chunks out of the final Top K, without touching the index | Adds latency per query; if the rerank model is a poor domain fit it can occasionally demote a genuinely good chunk — spot-check the retrieval inspector after enabling it |

### Generation layer (re-index not required)

| Parameter | Mechanism | Values to try | Expected effect | Regression risk |
|---|---|---|---|---|
| LLM model | Only the generation step changes; retrieval is untouched | Model A vs. Model B, same system prompt | Faithfulness and Answer Relevancy shift; per `findings.md`, weaker models are more likely to fabricate on adversarially-framed questions where a stronger model refuses | Context Recall and Context Precision should **not** move — if they do, something besides the LLM also changed, and the comparison is confounded |
| Temperature | Controls sampling randomness during generation — 0 is near-deterministic, higher values increase wording variety | 0 vs. 0.3 vs. 0.7 | Higher temperature increases lexical variety (lowers BLEU/ROUGE, which reward exact phrasing) without necessarily changing correctness | At temperature 0, re-running the same question should give near-identical answers. If it doesn't, the variance is likely coming from HNSW's *approximate* search returning slightly different chunks between runs, not from the LLM — check retrieval before blaming generation |
| System prompt wording | The instructions that tell the model how to use retrieved context and when to refuse | Baseline prompt vs. one with an explicit "only answer from the provided context; if it's not there, say so" instruction | Directly targets out-of-scope refusal rate and the false-premise adversarial failure mode ([Adversarial Testing § Failure Mode 2](adversarial-testing.md)) | An overly strict refusal instruction can increase false refusals on legitimate in-scope questions — watch Answer Relevancy on factual rows, not just the adversarial ones, after this change |

Every generation-layer change should leave Context Recall and Context Precision unchanged, since retrieval wasn't touched. If those metrics move too, treat it as a signal the comparison isn't actually isolated to one variable — see the scorecard table below.

---

## The Golden Rule: One Variable Per Run

If you change chunk size and switch to a better embedding model in the same re-index, and scores improve, you cannot tell which change caused the improvement — or whether one helped while the other silently regressed something you were not watching.

Always isolate the variable. Change one thing, measure, decide. Then change the next thing.

---

## The Controlled Experiment Design

### What stays constant

- The golden dataset — same questions, same reference answers, same expected chunks
- The LLM model and system prompt (unless the LLM is what you are testing)
- The evaluation scripts and scoring parameters

### What changes

Exactly one configuration setting.

### The baseline problem

Your baseline must be current. If you run Config A today and compare it to a Config B run from last week, you are also comparing whatever drifted in between — model API versions, document state, environmental differences. Always run both configurations back to back in the same session.

```
Correct order:
  1. Run Config A → save results as run-A
  2. Make exactly one change in Dify, re-index
  3. Run Config B → save results as run-B
  4. Compare run-A vs run-B

Wrong:
  Use run-001 from last week as the baseline for today's Config B run
  → You are not comparing two configurations, you are comparing two days
```

---

## The Scorecard: Which Metrics to Watch

Before running the experiment, decide which metrics you expect to change and which ones should stay stable. A metric that moves when it should not is a sign that something else changed alongside the variable you intended to vary.

| What you changed | Metrics likely to improve | Metrics to watch for regressions |
|---|---|---|
| Chunk size (larger) | Context Recall, multi-hop Recall@K | Context Precision, Faithfulness |
| Chunk size (smaller) | Context Precision | Context Recall, multi-hop Recall@K |
| Chunk overlap (added) | Recall@K on paraphrase and boundary rows | Context Precision |
| Chunking strategy | Context Recall, Recall@K overall | Faithfulness |
| Embedding model | Recall@K across all query types | Context Precision |
| Top-K (higher) | Context Recall | Context Precision (more noise enters) |
| LLM model | Faithfulness, Answer Relevancy | Context Recall (should not change — retrieval is unchanged) |
| System prompt | Out-of-scope refusal rate, Faithfulness | Answer Relevancy |

If Context Recall changes when you only changed the LLM, something else changed too. Go back and verify exactly what was modified.

---

## Reading Results: Breakdowns, Not Averages

The most common mistake in configuration comparison is reading overall averages and stopping there. Averages hide what is actually happening.

Consider this example — chunk size 300 chars vs 600 chars:

| Metric | Config A (300 chars) | Config B (600 chars) | Difference |
|---|---|---|---|
| Overall Recall@K | 0.71 | 0.74 | +3% |
| Overall Context Precision | 0.82 | 0.71 | −11% |
| Faithfulness | 0.88 | 0.84 | −4% |

If you stop here, the result looks like a modest gain with some worrying regressions — hard to call.

Now break it down by query type:

| Query type | Recall@K Config A | Recall@K Config B | Change |
|---|---|---|---|
| Factual | 0.90 | 0.90 | 0% |
| Paraphrase | 0.75 | 0.76 | +1% |
| Multi-hop | 0.42 | 0.68 | **+26%** |
| Out-of-scope | n/a | n/a | — |

The overall 3-point average gain masked a 26-point improvement on multi-hop rows — exactly the query type that small chunks break. The precision and faithfulness drops are real, but they are the price of larger chunks carrying more surrounding text. That is the actual trade-off, visible only in the breakdown.

**Always break results down by query type.** The breakdown is where the decision lives.

---

## What Counts as a Meaningful Difference

With a 60-row golden dataset, small differences in overall metrics are noise. A 2-point change could be sampling variation, not a real signal.

| Magnitude | How to read it |
|---|---|
| Under 3% on an overall metric | Likely noise — do not change configuration based on this |
| 3–8% on an overall metric | Possible signal — check whether it holds across query types |
| Over 8% on an overall metric | Credible improvement or regression — investigate the breakdown |
| Any change on a query type with 10+ rows | Worth taking seriously |
| Large gain on one query type, large drop on another | A genuine trade-off — needs a decision |

The right response to noise is not to pick the configuration that scored slightly higher. It is to declare no meaningful difference and keep the current configuration. Stability is worth more than chasing marginal score gains.

---

## Declaring a Winner: Three Questions

Before calling Config B the winner, answer all three questions:

**1. Did any metric meaningfully worsen?**
An improvement in one metric does not cancel out a regression in another. A configuration that improves recall by 10% but drops faithfulness from 0.88 to 0.72 is not a win — it means the system hallucinates more, even though it retrieves more. Define what "meaningfully worse" means before you run the experiment, not after you see the results.

**2. Is the improvement consistent across query types, or isolated to one?**
An improvement that only appears in one query type might mean the chunking setting was tuned to the specific phrasing of those questions rather than a genuine structural improvement. Add a few fresh questions from that category and re-check before committing.

**3. Do the out-of-scope and adversarial rows behave the same?**
These rows should not change between configurations unless you changed the system prompt or LLM. If hallucination rate or refusal rate changed after a chunk size change, something else changed too. Treat that as a warning signal.

If all three questions are satisfied — no meaningful regression, consistent across query types, adversarial rows stable — Config B is the winner.

---

## The Trade-Off Decision

Sometimes there is no clean winner. Config A has better precision; Config B has better recall. You must decide.

The right framework: **what is the primary failure mode you are trying to prevent?**

For the Orion HR Assistant:
- If users are getting hallucinated policies → optimise for precision and faithfulness; accept lower recall
- If users are getting "I don't know" on questions that are in the handbook → optimise for recall; accept some precision loss
- If users primarily ask multi-step benefit questions → optimise Recall@K on multi-hop rows specifically; treat precision loss as an acceptable trade-off

There is no universal answer. The decision depends on which failure mode causes more harm to your users. Document the trade-off and the reasoning. A future tester who finds Config B in production needs to understand why it was chosen and under what conditions the decision should be revisited.

---

## Do's and Don'ts

| Do | Don't |
|---|---|
| Run both configurations back-to-back in the same session, against the same golden dataset | Compare today's experiment to a run from last week or a previous session |
| Change exactly one setting per run | Change chunk size and switch embedding models in the same re-index — any result becomes unattributable |
| Decide your scorecard and "meaningful difference" thresholds *before* running the experiment | Decide, after seeing the numbers, which metrics matter and how big a change counts as real |
| Break results down by query type before reading the overall average | Stop at the overall average — it hides trade-offs like a 26-point multi-hop gain offset by a precision drop elsewhere |
| Apply the "under 3% is noise" rule (see [What Counts as a Meaningful Difference](#what-counts-as-a-meaningful-difference)) before calling a winner | Ship a config change because it scored 2 points higher, without checking whether that's inside the noise band |
| Define the full scorecard up front, including metrics you don't expect to move | Only look at the metric you hoped would improve, and miss a regression in one you didn't check |
| Re-check the out-of-scope and adversarial rows on every run, even when they weren't the target of the change | Assume adversarial/out-of-scope behaviour is unaffected just because the change was retrieval-only |
| Treat a genuine trade-off (Config A precision-favoured, Config B recall-favoured) as a product decision | Pick whichever configuration has the higher blended average when the two are actually trading off different failure modes |
| Batch expensive experiments (embedding model swaps, full re-indexes) last, after cheap settings are tuned | Re-embed the whole knowledge base repeatedly while still exploring cheap settings like Top K or Score Threshold |
| Document every result, including "no meaningful difference — kept current config" | Only write up the experiments that produced a clear winner — negative results are what stop the team re-running the same experiment in six months |

---

## The End-to-End Workflow

```
1. Pick ONE variable to change
2. Write down your hypothesis before running anything:
   "I expect Config B to improve X because Y"
3. Define your scorecard: which metrics should change, which should stay stable
4. Run Config A → save results
5. Change exactly one setting, re-index if required
6. Run Config B → save results
7. Compare metrics — overall first, then by query type
8. Check for regressions across the full scorecard
9. Apply the three-question test
10. Document the outcome: winner, trade-offs observed, reasoning
    If no meaningful difference: record the finding and keep current config
```

Step 10 is where most teams stop short. A well-documented experiment — even a negative one — is worth as much as the configuration change itself. The record is what prevents the team from repeating the same experiment, reaching the same conclusion, and shipping the same change six months later without realising it was already tried.

---

## See Also

- [RAG Evaluation Playbook](rag-evaluation-playbook.md) — how to execute evaluation runs and interpret metrics across a dataset
- [Chunking Strategies](chunking-strategies.md) — how chunk size, overlap, and strategy affect specific metric categories; the failure mode map
- [RAGAS Evaluation Metrics](ragas-evaluation-metrics.md) — Faithfulness, Answer Relevancy, Context Precision, Context Recall in detail
- [Adversarial Testing](adversarial-testing.md) — the false-premise failure mode a system-prompt A/B test targets
- [Embedding Model Pricing Comparison](../reference/embedding-model-pricing-comparison.md) — candidates to compare in an embedding-model A/B test
- [Golden Dataset Guide](../../golden-dataset/guide.md) — the dataset that anchors every comparison run
- [Golden Dataset Cross-Metric Findings](../../golden-dataset/findings.md) — a real run whose Context Precision/Faithfulness gap is a worked example of a finding that should trigger an A/B test
- [RAG Terminology Glossary](../concepts/glossary.md) — definitions for Score Threshold, Hybrid Search, Rerank Setting, and A/B Configuration Testing
- [Test Strategy](test-strategy.md) — when to run A/B experiments in the release cadence
