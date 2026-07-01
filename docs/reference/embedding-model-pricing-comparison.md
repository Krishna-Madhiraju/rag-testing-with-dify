# Embedding Model API Comparison — Cost, Dimensions, and Quality

Every RAG pipeline has to pick an embedding model at ingestion time — and as the [How RAG Works](../concepts/how-rag-works.md) doc explains, that choice is **load-bearing**: index with one model and query with another, and retrieval silently breaks, because each model defines its own vector coordinate system. Re-embedding a large corpus also costs real money, so it pays to compare providers *before* you commit, not after.

This doc is a snapshot, not a permanent reference — embedding pricing and model line-ups change every few months (Google shipped a brand-new model, Gemini Embedding 2, in the few months before this was written). Data below was pulled directly from each provider's official pricing/docs pages on **2026-07-01**. Where an official page would not yield a confirmed number (several providers gate per-token pricing behind a dashboard rather than a public page), that is flagged explicitly rather than guessed — see the **Confirmation status** column and the per-provider notes.

> **What to test here:** when comparing embedding providers for a project, the price-per-token line is the least of your worries. The real test surface is (1) dimension mismatch with your vector store schema, (2) max-input-token truncation silently dropping content from long chunks, and (3) retrieval quality on *your* domain vocabulary — MTEB is a general-purpose proxy, not a guarantee. Always run a small retrieval recall@K test on your own golden dataset before switching models (see [Comparing RAG Configurations](../testing/comparing-rag-configurations.md)).

---

## Summary table

| Provider | Model | Price / 1M tokens | Dimensions | Max input tokens | Free tier | Confirmation |
|---|---|---|---|---|---|---|
| OpenAI | `text-embedding-3-small` | $0.02 | 1536 (default, reducible) | 8,192 | None | ✅ Official |
| OpenAI | `text-embedding-3-large` | $0.13 | 3072 (default, reducible) | 8,192 | None | ✅ Official |
| Google (Gemini API) | `gemini-embedding-001` | $0.15 (batch: $0.075) | 128–3072, flexible (MRL) — recommended 768/1536/3072 | 2,048 | Free tier available; exact RPM/TPM caps not stated on the pricing page | ✅ Official (pricing); ⚠️ free-tier terms incomplete |
| Google (Gemini API) | `gemini-embedding-2` (multimodal, GA ~April 2026) | $0.20 text (batch: $0.10) | 128–3072, flexible (MRL) | 8,192 (text) | Free tier available; exact RPM/TPM caps not stated on the pricing page | ✅ Official (pricing); ⚠️ free-tier terms incomplete |
| Cohere | Embed v4 | **Not publicly listed** — only Model Vault dedicated-instance pricing ($4.00/hr small, $5.00/hr medium) appears on the official pricing page | 256 / 512 / 1024 / 1536 (default), Matryoshka | 128,000 | Not stated | ⚠️ Could not confirm serverless per-token price from an official page |
| Voyage AI | `voyage-4-large` | $0.12 | 1024 default (256/512/2048 selectable) | 32,000 | 200M tokens | ✅ Official |
| Voyage AI | `voyage-4` | $0.06 | 1024 default (256/512/2048 selectable) | 32,000 | 200M tokens | ✅ Official |
| Voyage AI | `voyage-4-lite` | $0.02 | 1024 default (256/512/2048 selectable) | 32,000 | 200M tokens | ✅ Official |
| Voyage AI | `voyage-context-3` | $0.18 | not separately confirmed | not separately confirmed | 200M tokens | ✅ Official (price/free tier); ⚠️ dims/context not confirmed |
| Voyage AI | `voyage-multilingual-2` | $0.12 | not separately confirmed | not separately confirmed | 50M tokens | ✅ Official (price/free tier) |
| Jina AI | `jina-embeddings-v3` | **Not confirmed via official fetch** — third-party sources cite ~$0.02–$0.05/1M | 1024 default, MRL down to 32 | 8,192 | 10M tokens on a new API key | ⚠️ Free tier official; price unconfirmed |
| Jina AI | `jina-embeddings-v4` | **Not confirmed via official fetch** | 2048 default (MRL down to 128) | 32,768 | 10M tokens on a new API key | ⚠️ Free tier official; price unconfirmed |
| DeepInfra (hosted OSS) | `BAAI/bge-large-en-v1.5` | $0.010 | 1024 | — | None | ✅ Official |
| DeepInfra (hosted OSS) | `BAAI/bge-m3` | $0.010 | 1024 | 8,192 | None | ✅ Official |
| DeepInfra (hosted OSS) | `intfloat/e5-large-v2` | $0.010 | 1024 | — | None | ✅ Official |
| DeepInfra (hosted OSS) | `intfloat/multilingual-e5-large` | $0.010 | 1024 | — | None | ✅ Official |
| Together AI (hosted OSS) | `multilingual-e5-large-instruct` | $0.02 | 1024 | — | None | ✅ Official (only embedding model on their public pricing page — no BGE listed) |
| Fireworks AI (hosted OSS) | BGE/Nomic tier, ≤150M params | $0.008 | model-dependent | model-dependent | None | ✅ Official (tiered by parameter count, not itemized per model on the pricing page) |
| Fireworks AI (hosted OSS) | BGE/Nomic tier, 150M–350M params (covers `bge-large`, `bge-m3`) | $0.016 | model-dependent | model-dependent | None | ✅ Official |

---

## Per-provider notes

### OpenAI

Fetched from `developers.openai.com/api/docs/models/text-embedding-3-small`, `.../text-embedding-3-large`, and `.../guides/embeddings` (the old `platform.openai.com` and `openai.com/api/pricing/` URLs now redirect there; `openai.com/api/pricing/` itself returned HTTP 403 to automated fetch). Both models can shorten their output vector via the `dimensions` API parameter without a proportional quality loss — useful if your vector store has a dimension ceiling.

### Google (Gemini API)

Fetched from `ai.google.dev/gemini-api/docs/pricing`, `.../docs/embeddings`, and `.../docs/models/gemini-embedding-2-preview`. Two models are live as of 2026-07-01:
- `gemini-embedding-001` — text-only, the long-standing model.
- `gemini-embedding-2` — Google's first **natively multimodal** embedding model (text, image, video, audio, PDF in one vector space), released to preview in March 2026 and GA around April 2026. Both share the same Matryoshka-style flexible-dimension design as OpenAI's v3 models.

The pricing page states a free tier exists for both models but does not publish exact rate-limit numbers (RPM/TPM/RPD) on that page — confirm current limits in the Google AI Studio console before relying on them for a CI pipeline.

### Cohere

This is the one provider where I could **not** find official, public, per-token serverless API pricing for Embed — despite fetching `cohere.com/pricing` (twice, including a live browser render to check for a hidden tab), `cohere.com/embed`, and `docs.cohere.com/docs/how-does-cohere-pricing-work`. All three only show:
- **Model Vault** (dedicated-instance) pricing: Embed 4 Small $4.00/hr or $2,500/mo, Embed 4 Medium $5.00/hr or $3,250/mo.
- A pointer ("see the dedicated pricing page") that circles back to the same page.

Multiple third-party aggregators cite **$0.10/1M tokens for Embed v3** and **~$0.12/1M tokens for Embed v4** (the latter matching AWS Bedrock's hosted price for `cohere.embed-v4-0`), but since the user's brief was to source from official pages only, treat these as **unconfirmed** until you check your own Cohere dashboard or request a quote. Dimensions (256/512/1024/1536, 1536 default) and the 128K context window for Embed v4 *were* confirmed directly from `docs.cohere.com/v2/docs/cohere-embed`.

### Voyage AI

Fetched from `docs.voyageai.com/docs/pricing` and `docs.voyageai.com/docs/embeddings`. Voyage has shipped a **voyage-4 generation** (large / standard / lite) since the v3 line many comparison articles still reference — confirm you're looking at current model names before quoting older voyage-3 pricing. The free tier is generous and uniform: **200M tokens** for every voyage-4-family model (`voyage-4-large`, `voyage-4`, `voyage-4-lite`, `voyage-context-3`, `voyage-code-3`), 50M tokens for `voyage-multilingual-2` and the specialized (finance/law/code-2) models. The Batch API adds a 12% discount on top.

### Jina AI

Fetched from `jina.ai/embeddings/` directly (twice) and could not get a dollar figure to render — the live page only exposes tiered **rate limits** (Free key: 100 RPM/100K TPM; Paid: 500 RPM/2M TPM; Premium: 5,000 RPM/50M TPM) and a "10 million free tokens on signup" offer, with actual token pricing apparently gated behind the account dashboard's "Buy tokens" flow. Third-party sources (not authoritative) put v3 around $0.02/1M tokens historically, with a pricing-model change in May 2025 that may have shifted top-up rates to ~$0.05/1M — **do not treat either number as confirmed**; check your dashboard directly. Dimensions/context length (v3: 1024d / 8,192 tokens; v4: 2048d / 32,768 tokens, multimodal) came from Jina's Hugging Face model card and model page, which is closer to primary-source than a blog but still not the pricing page itself.

### Open-source models via hosted inference (BGE / E5)

These were the most reliably confirmable, because all three providers publish a flat per-model or per-tier price directly on their pricing pages:

- **DeepInfra** (`deepinfra.com/models/embeddings`) lists `BAAI/bge-large-en-v1.5` and `BAAI/bge-m3` at $0.010/1M tokens, and the E5 family at $0.005–$0.010/1M tokens.
- **Together AI** (`together.ai/pricing`) only lists one embedding model publicly — `multilingual-e5-large-instruct` at $0.02/1M tokens. No BGE model appears on their public pricing page as of this fetch.
- **Fireworks AI** (`fireworks.ai/pricing`) prices embeddings by parameter-count tier rather than by name: $0.008/1M tokens up to 150M parameters, $0.016/1M tokens for 150M–350M parameters (which is where `bge-large` and `bge-m3` fall, per their model-catalog descriptions).

---

## MTEB retrieval scores — could not be directly verified

The user's brief asked for the [MTEB leaderboard](https://huggingface.co/spaces/mteb/leaderboard) itself as the source. That page is a JavaScript-rendered Hugging Face Space (Gradio/Docker app) that does not return usable data to an automated fetch — repeated attempts (direct fetch, the `?refresh=1` query, and the HF Spaces metadata API) only returned the page shell and Space metadata, not the score table.

What follows is therefore **secondary-sourced** (tech blogs and pricing-comparison sites referencing MTEB, not the leaderboard itself) and should be treated as approximate, with one important caveat: **MTEB v2 (2026) scores are not directly comparable to MTEB v1 scores**, and most embedding models were re-benchmarked when the leaderboard migrated. Verify on the live leaderboard before using these numbers to justify a model choice.

| Model | Approx. retrieval score (secondary sources) | Note |
|---|---|---|
| OpenAI `text-embedding-3-large` | ~64.6 | |
| Cohere Embed v4 | ~65.2 | |
| BGE-M3 | ~63.0 | |
| Jina `jina-embeddings-v3` | ~65.5 | claimed to outperform OpenAI large at a fraction of the cost |
| Voyage `voyage-3-large` | ~67.1 | |
| Google `gemini-embedding-2` | ~68.3 (MTEB English) | reported as current top score by a 5+ point margin, multimodal |

**Recommendation:** don't take this table to a design review. Open `huggingface.co/spaces/mteb/leaderboard` yourself, filter to the "Retrieval" task and your target language, and compare current models live — the rankings shift every time a new model ships, and a static snapshot like this one ages out within months.

---

## Sources (fetched 2026-07-01)

- OpenAI — [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small), [text-embedding-3-large](https://developers.openai.com/api/docs/models/text-embedding-3-large), [Embeddings guide](https://developers.openai.com/api/docs/guides/embeddings) (`openai.com/api/pricing/` returned HTTP 403 to automated fetch and could not be used directly)
- Google — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), [Embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings), [gemini-embedding-2-preview model card](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-2-preview), [official announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/)
- Cohere — [cohere.com/pricing](https://cohere.com/pricing), [cohere.com/embed](https://cohere.com/embed), [docs.cohere.com — Embed model details](https://docs.cohere.com/v2/docs/cohere-embed), [How Does Cohere's Pricing Work?](https://docs.cohere.com/docs/how-does-cohere-pricing-work) — none of these published serverless per-token Embed pricing at fetch time
- Voyage AI — [docs.voyageai.com/docs/pricing](https://docs.voyageai.com/docs/pricing), [docs.voyageai.com/docs/embeddings](https://docs.voyageai.com/docs/embeddings)
- Jina AI — [jina.ai/embeddings](https://jina.ai/embeddings/), [jina-embeddings-v4 model page](https://jina.ai/models/jina-embeddings-v4/) — no confirmed $/token figure on the official page at fetch time
- DeepInfra — [deepinfra.com/models/embeddings](https://deepinfra.com/models/embeddings)
- Together AI — [together.ai/pricing](https://www.together.ai/pricing)
- Fireworks AI — [fireworks.ai/pricing](https://fireworks.ai/pricing)
- MTEB leaderboard (unconfirmed via direct fetch — JS-rendered) — [huggingface.co/spaces/mteb/leaderboard](https://huggingface.co/spaces/mteb/leaderboard); secondary figures referenced from aggregator commentary, not the leaderboard itself

> Re-check all of the above before making a production decision — embedding pricing changes faster than this document will be updated.
