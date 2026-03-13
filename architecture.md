## Architecture Overview

This document describes the high-level architecture of the translation engine, including the core components, FastAPI application, context indexing, and the integration with Google Cloud Vertex AI.

---

## Core components

At the heart of the system is the **Engine**, which wires together configuration, providers, services, and the translation pipeline.

- `translation_engine/config/manager.py` – `ConfigManager`
  - Loads configuration from:
    - `config.yaml` – provider selection (Ollama vs Vertex AI) and app settings
    - `config_translation.yaml` – translation defaults, reflection, prompts
    - `config_context.yaml` – context indexing configuration
  - Exposes typed config objects: `OllamaConfig`, `VertexAIConfig`, `TranslationConfig`, `ReflectionConfig`, `ContextConfig`, `PromptsConfig`.

- `translation_engine/providers/*`
  - `ollama.py`
    - `OllamaLLMProvider` – wraps a local Ollama `ChatOllama` model.
    - `OllamaEmbeddingProvider` – uses Ollama embeddings as a vector backend.
  - `vertex_ai.py`
    - `VertexAILLMProvider` – wraps a Vertex AI `GenerativeModel` (e.g. Gemini / Gemma / TranslateGemma).
    - `VertexAIEmbeddingProvider` – uses Vertex AI text embedding models (e.g. `text-embedding-004`).
  - `context.py`
    - `FAISSContextProvider` – FAISS-based in-memory vector store built from website content.

- `translation_engine/services/*`
  - `translator.py` – Builds prompts from configuration and optional context, then calls `LLMProvider.generate/stream`.
  - `reflector.py` – Implements the reflection + refinement pattern using the LLM.
  - `pipeline.py` – `TranslationPipeline` orchestrating:
    - Optional context retrieval
    - Initial translation
    - Optional reflection
    - Optional refinement

- `translation_engine/domain/models.py`
  - `TranslationOptions`, `TranslationRequest`, `ReflectionResult`, `TranslationResult` – internal dataclasses for pipeline inputs/outputs.

- `translation_engine/context_profiles.py`
  - `ContextProfile` – reusable website set identified by `profile_id`.
  - `InMemoryContextProfileStore` – current storage for context profiles.

- `translation_engine/engine.py`
  - `create_engine()`:
    - Loads configuration.
    - Chooses **LLM provider** based on `provider_type`:
      - `"ollama"` → `OllamaLLMProvider`.
      - `"vertex_ai"` → `VertexAILLMProvider`.
    - Creates a context provider (`FAISSContextProvider`) with either Ollama or Vertex AI embeddings.
    - Creates `Translator`, `Reflector`, and `TranslationPipeline`.

---

## FastAPI application and frontend

The FastAPI layer lives under `api/`:

- `api/main.py`
  - Creates the FastAPI app.
  - On startup, calls `create_engine()` and stores the resulting `Engine` on `app.state.engine`.
  - Includes routers for:
    - `routes_frontend.py`
    - `routes_translation.py`
    - `routes_context.py`
    - `routes_health.py`

- `api/dependencies.py`
  - `get_engine()` – retrieves the shared `Engine` instance from app state.
  - `get_pipeline()` – convenience dependency returning `engine.pipeline`.

- `api/routes_translation.py`
  - `/api/v1/translate` – runs the full pipeline (translation + optional reflection).
  - `/api/v1/translate/simple` – runs a translation without reflection.

- `api/routes_context.py`
  - `/api/v1/context/status` – exposes whether context is enabled/ready and the number of indexed chunks.
  - `/api/v1/context/rebuild` – triggers a background rebuild of the default context index from config websites.
  - `/api/v1/context/profiles` – creates a reusable context profile with up to 3 websites.
  - `/api/v1/context/profiles/{profile_id}/rebuild` – triggers a background rebuild for a stored context profile.
  - `/api/v1/context/sources` – legacy shortcut that creates a profile and rebuilds it in the background.

- `api/routes_health.py`
  - `/health` – simple liveness endpoint.

- `api/routes_frontend.py`
  - `GET /` – renders the main HTML form (`templates/index.html`), using defaults from `TranslationConfig` and `ContextConfig`.
  - `POST /translate` – handles form submission:
    - Reads text, language/tone/purpose fields, reflection/context toggles, and up to 3 websites.
    - Builds request-level `TranslationOptions`.
    - If websites are provided, creates or reuses a `ContextProfile`, then triggers an asynchronous background rebuild for that profile.
    - Builds a `TranslationRequest` and calls `engine.pipeline.execute(...)`.
    - Renders the final translation and optional reflection feedback.

The HTML frontend lives in:

- `templates/index.html` – server-rendered UI with:
  - Text area for source text.
  - Inputs for source/target language, tone, purpose of text.
  - Checkboxes for reflection + context.
  - Three optional website URL fields.
  - A result card showing the final translation and reflection feedback.

---

## Context indexing and retrieval

The context subsystem is responsible for:

1. Fetching website content.
2. Chunking it into overlapping text segments.
3. Embedding each chunk.
4. Building a FAISS index for similarity search.
5. Returning a concatenated context string for the translator.

Key pieces:

- `translation_engine/providers/context.py` – `FAISSContextProvider`
  - Tracks:
    - A per-profile in-memory FAISS index state keyed by profile ID.
    - Chunks and metadata per profile.
  - Methods:
    - `build_index(force=False)` – rebuilds the default profile from config websites.
    - `build_profile_index(profile_id, websites, force=False)` – builds a specific profile’s FAISS index.
    - `search_profile(profile_id, query, k=None)` – runs similarity search for a specific profile.
    - `get_profile_context(profile_id, text)` – formats profile-specific context for prompt inclusion.

The **same provider** works with either:

- `OllamaEmbeddingProvider` (local dev, `provider_type="ollama"`), or
- `VertexAIEmbeddingProvider` (production, `provider_type="vertex_ai"`).

---

## Deployment architecture (Cloud Run + Vertex AI)

In the recommended GCP deployment, the flow looks like this:

```mermaid
flowchart TD
  client[Client / Browser] -->|HTTPS| cloudRun[Cloud Run: FastAPI + HTML]
  cloudRun -->|Config + services| engine[Engine]

  engine --> pipeline[TranslationPipeline]
  pipeline --> translator[Translator]
  pipeline --> reflector[Reflector]
  pipeline --> ctxProvider[FAISSContextProvider]

  translator -->|generate()| vertexLLM[Vertex AI GenerativeModel]
  ctxProvider -->|embed()| vertexEmb[Vertex AI EmbeddingModel]
```

- The **Cloud Run container** runs:
  - This FastAPI app (API + HTML).
  - The FAISS context index in-memory.
- **Vertex AI** provides:
  - Generative LLM for translation and reflection.
  - Text embedding model for website context indexing.

Scaling behaviour:

- Cloud Run can spin up multiple instances of the container as traffic grows.
- Each instance has its own in-memory FAISS cache, keyed by context profile ID:
  - Initially empty on cold start.
  - Rebuilt lazily or via explicit rebuild endpoints.
  - Not shared across instances, so profile metadata may persist while the FAISS cache must be rebuilt per instance.

---

## Data flow: full translation request

The full pipeline (`/api/v1/translate`) follows this sequence:

```mermaid
flowchart TD
  A[Client sends request] --> B[FastAPI route /api/v1/translate]
  B --> C[TranslationPipeline.execute(request)]

  C --> D{Use context?}
  D -->|yes & profile ready| E[FAISSContextProvider.get_profile_context(profileId,text)]
  D -->|yes & default ready| F[FAISSContextProvider.get_context(text)]
  D -->|no or not ready| G[context = ""]

  E --> H[Translator.translate(text, context, options)]
  F --> H[Translator.translate(text, context, options)]
  G --> H[Translator.translate(text, context, options)]

  H --> I{Use reflection?}
  I -->|no| J[Result: initial == final]
  I -->|yes| K[Reflector.reflect(original, initial, options)]
  K --> L{Excellent?}
  L -->|yes| J
  L -->|no| M[Reflector.refine(original, initial, feedback, options)]
  M --> N[Result: refined final]

  J --> O[Return TranslationResult]
  N --> O
```

Each LLM call (translation, reflection, refinement, and embeddings) goes through the configured provider:

- Local dev: Ollama.
- GCP: Vertex AI.

