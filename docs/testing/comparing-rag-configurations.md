# Comparing Two RAG Configurations

A configuration comparison is an experiment: you change one thing, measure the impact on your golden dataset, and decide whether the change is an improvement. Done well, it gives you evidence for a decision. Done poorly, it gives you numbers that feel like evidence but are not.

This document explains how to design the experiment, read the results, and make a defensible decision.

---

## What a Configuration Is

A RAG configuration is the complete set of settings that define how the pipeline behaves. Any of these can be varied:

| Layer | Examples of what can change |
|---|---|
| Ingestion | Chunk size, chunk overlap, chunking strategy |
| Retrieval | Embedding model, top-K value, retrieval mode (dense vs hybrid), re-ranking on/off |
| Generation | LLM model, system prompt wording, temperature |

Changing any one of these changes the configuration. A comparison is only meaningful when exactly one thing changes between the two runs.

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

## Common Traps

**Comparing to a stale baseline.** Run both configurations in the same session. Never compare today's experiment to last week's run.

**Changing two things at once.** If you change chunk size and switch to a different embedding model in the same re-index, any result is unattributable. Roll back to one variable.

**Reading only the average.** Always break down by query type. Averages hide the trade-offs that determine whether the change is right for your use case.

**Calling a noise-level difference a win.** A 2-point improvement on a 60-row dataset is not evidence. Resist shipping every marginal gain. Stability has value.

**Ignoring regressions in metrics you were not watching.** Define your full scorecard before running the experiment. If you only look at the metric you hoped to improve, you will miss regressions in the ones you did not check.

**Not documenting what you found.** The value of a comparison is not just the decision — it is the institutional knowledge that "we tried 300 chars and it broke multi-hop." Document every experiment result, including the ones where no meaningful difference was found. Negative results prevent you from running the same experiment again in six months.

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
- [Golden Dataset Guide](../../golden-dataset/guide.md) — the dataset that anchors every comparison run
- [Test Strategy](test-strategy.md) — when to run A/B experiments in the release cadence
