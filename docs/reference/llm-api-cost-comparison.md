# Cost-Effective LLM API Comparison — Frontier vs. Open-Source-Serving Providers

If you've hit Gemini's free-tier rate limit mid-evaluation run, this doc explains *why* that happens and lays out the alternatives — both frontier (closed) models and open-source models served via hosted APIs — with pricing and free-tier terms verified directly from each provider's own docs.

> **Snapshot, not a permanent reference.** Every figure below was fetched from an official provider page on **2026-07-01** and is cited at the point of use. Pricing, free tiers, and model lineups change every few months (the model lineup moved mid-research: Gemini's current Flash tier is 3.5/3.1, not 2.5). Re-check the source link before making a real decision — don't carry these numbers into next quarter.

---

## Why Gemini's free tier rate-limits you

Google's Gemini API has a genuine no-cost **Free Tier** — no billing account required, just an active project — on top of three paid usage tiers (Tier 1–3, unlocked by cumulative spend of $100–$1,000+). The catch: the [official rate-limits page](https://ai.google.dev/gemini-api/docs/rate-limits) does **not** publish fixed RPM/TPM/RPD numbers. It says limits "depend on a variety of factors (such as your usage tier) and can be viewed in Google AI Studio" — the actual ceiling is only visible per-account at `aistudio.google.com/rate-limit`, not on the docs page.

Two mechanics explain the rate-limit pain you're hitting:

1. **Limits are enforced per Google Cloud *project*, not per API key.** Creating a second API key inside the same project does not multiply your quota — you'd need a genuinely separate project.
2. **Three independent ceilings (RPM, TPM, RPD) are checked simultaneously.** A golden-dataset run that fires 60 sequential requests can blow through the requests-per-minute ceiling even if you're nowhere near your daily token budget — the error doesn't tell you which dimension you tripped.

> **What to test here:** before blaming "the model," check *which* limit you hit — log the HTTP 429 response body (Gemini includes a `retryDelay` and quota-metric name) rather than assuming it's a blanket daily cap. A regression suite that fires requests back-to-back is more likely to hit RPM than a human ever would; adding a small delay (or batching with a sleep) between golden-dataset rows is the first fix to try before switching providers.

---

## Frontier (closed) providers

| Provider | Model | Input $/1M | Output $/1M | Free tier | Context window | Source |
|---|---|---|---|---|---|---|
| Google | Gemini 3.1 Flash-Lite | $0.25 | $1.50 | Yes — limited model access, prompts used to improve Google's products, RPM/RPD/TPM not published | Not published on fetched pages | [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Google | Gemini 3.5 Flash | $1.50 | $9.00 | Yes, same terms | Not published on fetched pages | same |
| OpenAI | gpt-5.4-nano | $0.20 | $1.25 | Ambiguous — see note below | not confirmed | [developers.openai.com/api/docs/pricing](https://developers.openai.com/api/docs/pricing) |
| OpenAI | gpt-5.4-mini | $0.75 | $4.50 | Ambiguous | not confirmed | same |
| Anthropic | Claude Haiku 4.5 | $1.00 | $5.00 | None (one-time trial credit only) | 200K | [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| Anthropic | Claude Sonnet 5 (intro pricing, through 2026-08-31) | $2.00 | $10.00 | None | 1M | same |
| Anthropic | Claude Sonnet 5 (standard pricing, from 2026-09-01) | $3.00 | $15.00 | None | 1M | same |

**On OpenAI's "free tier":** the rate-limits page lists a "Free" row in its usage-tier table with a "$100/month" limit, alongside Tier 1–3 rows unlocked by paid spend. It's genuinely unclear from the fetched page whether that $100/month is a no-cost grant or just the rate-limit label assigned to a zero-spend account (with the dollar figure being a *spend cap*, not money given to you) — the pricing page itself shows no free line item for token usage. Confirm by checking `platform.openai.com/settings/organization/limits` while signed in before relying on it.

**Anthropic confirmed no recurring free tier** — verbatim from their FAQ: *"New users receive a small amount of free credits to test the API... Contact sales for information about extended trials."*

> **What to test here:** if you switch frontier providers mid-project, re-baseline your golden dataset. Different providers tokenize differently (a "1,000-token" prompt costs different dollar amounts and may even retrieve a different effective context window), so a regression comparison across providers needs cost-per-query and latency captured alongside the quality score, not quality alone.

---

## Cost-effective / open-source-serving providers

These providers serve open-weight models (Llama, Qwen, DeepSeek, gpt-oss, etc.) at a fraction of frontier pricing, often with much faster inference (Groq and Cerebras use custom chips, not GPUs).

| Provider | Model | Input $/1M | Output $/1M | Free tier | Source |
|---|---|---|---|---|---|
| **Groq** | gpt-oss-20b | $0.075 | $0.30 | **Yes — genuinely free, no expiry.** 30 RPM / 1K RPD / 8K TPM / 200K TPD on the free plan | [groq.com/pricing](https://groq.com/pricing) |
| Groq | gpt-oss-120b | $0.15 | $0.60 | Same free-plan structure (limits vary slightly by model) | same |
| Groq | llama-3.1-8b-instant | $0.05 | $0.08 | Free plan: 30 RPM / 14.4K RPD / 6K TPM / 500K TPD | same |
| Groq | llama-3.3-70b-versatile | $0.59 | $0.79 | Free plan: 30 RPM / 1K RPD / 12K TPM / 100K TPD | same |
| **Cerebras** | gpt-oss-120b | $0.35 | $0.75 | Free plan: 5 RPM / 30K TPM / 1M tokens/day (same model, paid plan just raises rate limits, not price) | [inference-docs.cerebras.ai](https://inference-docs.cerebras.ai/models/openai-oss) |
| Cerebras | gemma-4-31b (preview) | $0.99 | $1.49 | Free plan: same structure | same |
| **DeepSeek** | deepseek-v4-flash | $0.14 (cache-hit $0.0028) | $0.28 | None | [api-docs.deepseek.com/quick_start/pricing](https://api-docs.deepseek.com/quick_start/pricing) |
| DeepSeek | deepseek-v4-pro | $0.435 (cache-hit $0.003625) | $0.87 | None | same |
| **Mistral** | Mistral Small 4 | $0.15 | $0.60 | "Free mode" exists, exact RPM/TPM/monthly cap not publicly listed (login-gated) | [mistral.ai/pricing](https://mistral.ai/pricing/#api) |
| Mistral | Mistral Large 3 | $0.50 | $1.50 | same | same |
| Mistral | Mistral Medium 3.5 | $1.50 | $7.50 | same | same |
| **DeepInfra** | Meta-Llama-3.1-8B-Instruct | $0.02 | $0.05 | None — pay-as-you-go, card required | [deepinfra.com/pricing](https://deepinfra.com/pricing) |
| DeepInfra | Qwen3-235B-A22B-Instruct | $0.09 | $0.10 | None | same |
| **Together AI** | gpt-oss-20B | $0.05 | $0.20 | None — $5 minimum credit purchase, no free trial | [together.ai/pricing](https://www.together.ai/pricing) |
| Together AI | gpt-oss-120B | $0.15 | $0.60 | None | same |
| **Fireworks AI** | gpt-oss-20B | $0.07 (cache-hit $0.035) | $0.30 | $1 one-time free credit only | [fireworks.ai/pricing](https://fireworks.ai/pricing) |
| Fireworks AI | gpt-oss-120B | $0.15 (cache-hit $0.015) | $0.60 | same | same |
| **OpenRouter** | 22 models tagged `:free` (e.g. `openai/gpt-oss-120b:free`, `meta-llama/llama-3.3-70b-instruct:free`) | $0 | $0 | 20 RPM; **50 requests/day** if you've purchased <$10 lifetime credit, **1,000 requests/day** once you've purchased ≥$10 lifetime credit (a one-time threshold, not a balance check) | [openrouter.ai/docs/api/reference/limits](https://openrouter.ai/docs/api/reference/limits) |

> **What to test here:** when a provider claims "free tier," check whether it's (a) a genuinely free, permanent, rate-limited plan (Groq, Cerebras, OpenRouter's `:free` models), or (b) one-time trial credit that runs out (Fireworks' $1, Anthropic/OpenAI's trial credits). Confusing the two is the single most common reason a "free" eval pipeline suddenly starts billing — write a cost-per-run assertion into your eval script so a quota exhaustion shows up as a clear failure, not a silent charge.

<details>
<summary>Why this list skews toward Groq and OpenRouter for a learner with rate-limit pain</summary>

Cerebras' "free tier" is really the *same per-token price* as its paid tier, just capped at a much lower RPM/TPM — so it's free in the sense that you pay $0 until you exceed 1M tokens/day, but it's not a separate cheap pricing track. DeepInfra, Together AI, and Fireworks AI have **no recurring free tier at all** — they're pure pay-as-you-go (Together AI won't even let you start without a $5 minimum purchase).

That leaves two genuinely free, **non-expiring** options for repeated golden-dataset/RAGAS test runs without a credit card:
- **Groq** — free plan with per-model RPM/RPD/TPM/TPD caps that, for gpt-oss-120b, mean up to 1,000 requests/day at zero cost.
- **OpenRouter's `:free` models** — 22 models, 20 RPM, and either 50 or 1,000 requests/day depending on whether you've ever put $10 of credit on the account (a one-time unlock, not a recurring spend).

Both are a meaningfully higher daily request ceiling than Gemini's undocumented free-tier RPM, and neither requires you to track down a hidden per-account quota page to find out your actual limit.
</details>

---

## JSON mode and hallucination — generation quality notes for RAG

- **All six current DeepSeek V4 models** and **23 of Mistral's 24 listed models** support JSON mode / structured output — relevant if your eval harness or RAG answer formatting needs reliably parseable output. ([artificialanalysis.ai/providers/deepseek](https://artificialanalysis.ai/providers/deepseek), [artificialanalysis.ai/providers/mistral](https://artificialanalysis.ai/providers/mistral), cross-checked against each provider's own API docs)
- **Mistral's three largest current models** (Medium 3.5, Devstral 2, Large 3) share a **262K-token context window** — the largest in Mistral's current lineup. ([docs.mistral.ai model cards](https://docs.mistral.ai/models/mistral-large-3-25-12), confirmed directly)
- On the [Vectara hallucination leaderboard](https://github.com/vectara/hallucination-leaderboard) (last updated 2026-05-11), Google's previous-generation **Gemini 2.5 Flash-Lite measured 3.3% hallucination vs. 7.8% for Gemini 2.5 Flash** — Flash-Lite was *more* faithful than standard Flash on that benchmark, the opposite of what "lite = cheaper, lower quality" might suggest. This is 2.5-generation data; the leaderboard had not yet published 3.x-generation scores at fetch time, so treat it as a generational data point, not a current ranking — and note the leaderboard measures grounded short-document summarization specifically, a narrow proxy for full RAG generation quality, not a general-purpose score.

> **What to test here:** don't assume a "lite"/"mini"/"flash" model variant is automatically worse at faithfulness than its full-size sibling — the Gemini 2.5 case shows the opposite can be true. Run your own faithfulness check (RAGAS or GPTScore) on your actual document set before assuming the bigger model wins; size and hallucination rate aren't reliably correlated.

---

## Embedding models

Embedding-model pricing, dimensions, and free tiers (OpenAI, Google, Cohere, Voyage AI, Jina AI, and open-source BGE/E5 served via DeepInfra/Together/Fireworks) are covered separately — see **[Embedding Model API Comparison](embedding-model-pricing-comparison.md)**.

---

## Dify compatibility

Dify's basic ["Supported Providers" docs page](https://docs.dify.ai/en/cloud/use-dify/workspace/model-providers) undersells what's actually installable — its **plugin marketplace** natively supports far more providers than the docs page lists. Confirmed directly against the [marketplace](https://marketplace.dify.ai/) and the [official plugins repo](https://github.com/langgenius/dify-official-plugins) (70 provider folders) on 2026-07-01:

| Provider | Official Dify plugin? | Setup |
|---|---|---|
| Groq | ✅ Yes | API key only |
| OpenRouter | ✅ Yes (159K+ installs) | API key only |
| DeepSeek | ✅ Yes (1.16M+ installs) | API key only |
| Mistral | ✅ Yes (folder `mistralai`) | API key only |
| Together AI | ✅ Yes | API key only |
| Fireworks AI | ✅ Yes | API key only |
| SiliconFlow | ✅ Yes (568K+ installs) | API key only |
| Voyage AI (embeddings) | ✅ Yes | API key only |
| Jina AI (embeddings) | ✅ Yes | API key + base URL |
| Cohere (embeddings) | ✅ Yes | API key (+ optional base URL) |
| **Cerebras** | ❌ No official plugin | Must use the generic **"OpenAI-Compatible"** plugin with Cerebras's base URL (`https://api.cerebras.ai/v1`) |
| **DeepInfra** | ❌ No official plugin | Same workaround, base URL `https://api.deepinfra.com/v1/openai` |

For your **local Docker self-hosted Dify install**: plugin installation from the marketplace works the same as Dify Cloud (the admin UI's plugin dialog has a "Marketplace" tab, on by default), as long as the container has outbound internet access. Two extra install paths exist only for self-hosted: installing a downloaded `.difypkg` file directly (useful if marketplace installs ever fail — there's a known, unresolved [GitHub issue](https://github.com/langgenius/dify/issues/27720) about intermittent 404/500 errors on plugin download for some self-hosted instances), and installing from a GitHub repo URL for unlisted community plugins.

> **What to test here:** after installing a new model provider plugin in your local Dify, re-run a small smoke-test query before pointing your full golden dataset at it — confirm the model name in Dify's dropdown matches the model ID the provider's API actually expects (these occasionally drift, e.g. a plugin shipping with an older model ID after the provider renames/deprecates one).

---

## Recommendation for this project

Given you're hitting Gemini Flash free-tier limits during repeated eval runs (golden-dataset regression, RAGAS scoring):

1. **Try Groq's free tier first.** It has an official Dify plugin (API-key-only setup), a genuinely free non-expiring plan, and gpt-oss-120b is a capable, JSON-mode-supporting model at a documented 1,000 requests/day ceiling — almost certainly enough headroom for a 60-row golden dataset run.
2. **OpenRouter's `:free` models** are a good second option if you want access to 22 different free models (including Llama and Qwen variants) through one API key, and you're willing to put $10 of credit on the account once to unlock the 1,000/day tier instead of 50/day.
3. **DeepSeek V4 Flash** ($0.14/$0.28 per 1M, JSON mode supported) is the cheapest *paid* fallback if you outgrow free tiers — has an official Dify plugin with the highest install count of any provider checked (1.16M+), suggesting it's broadly battle-tested.
4. Avoid Together AI / Fireworks AI / DeepInfra for this specific problem — none has a recurring free tier, so they don't solve "I keep hitting rate limits while testing for free."

---

## Sources (fetched 2026-07-01)

- Google Gemini — [pricing](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- OpenAI — [pricing](https://developers.openai.com/api/docs/pricing), [rate limits](https://developers.openai.com/api/docs/guides/rate-limits)
- Anthropic — [pricing](https://platform.claude.com/docs/en/about-claude/pricing), [models overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- Groq — [pricing](https://groq.com/pricing), [rate limits](https://console.groq.com/docs/rate-limits)
- Cerebras — [model docs / pricing](https://inference-docs.cerebras.ai/models/openai-oss)
- DeepSeek — [pricing](https://api-docs.deepseek.com/quick_start/pricing)
- Mistral — [pricing](https://mistral.ai/pricing/#api), [usage limits](https://docs.mistral.ai/admin/billing-usage/usage-limits)
- DeepInfra — [pricing](https://deepinfra.com/pricing)
- Together AI — [pricing](https://www.together.ai/pricing), [billing docs](https://docs.together.ai/docs/billing-credits)
- Fireworks AI — [pricing](https://fireworks.ai/pricing), [serverless pricing docs](https://docs.fireworks.ai/serverless/pricing)
- OpenRouter — [models API](https://openrouter.ai/api/v1/models), [rate limits docs](https://openrouter.ai/docs/api/reference/limits)
- Dify — [model providers docs](https://docs.dify.ai/en/cloud/use-dify/workspace/model-providers), [official plugins repo](https://github.com/langgenius/dify-official-plugins), [plugin marketplace](https://marketplace.dify.ai/), [plugin install docs](https://docs.dify.ai/en/plugins/quick-start/install-plugins)
- Vectara hallucination leaderboard — [github.com/vectara/hallucination-leaderboard](https://github.com/vectara/hallucination-leaderboard)
- Artificial Analysis — [DeepSeek](https://artificialanalysis.ai/providers/deepseek), [Mistral](https://artificialanalysis.ai/providers/mistral)

> Re-check every price and rate limit above before relying on it for anything beyond casual learning — providers in this space change pricing and free-tier terms on the order of weeks, not years.
