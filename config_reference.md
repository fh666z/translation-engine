## Configuration Reference

This document explains the configuration files and how they interact with the translation engine and UI.

There are three main YAML configuration files:

- `config.yaml`
- `config_translation.yaml`
- `config_context.yaml`

All of them live in the project root and are loaded by `translation_engine/config/manager.py`.

---

## `config.yaml` – provider and app settings

Example:

```yaml
provider_type: "ollama"  # or "vertex_ai"

ollama:
  base_url: "http://localhost:11434"
  temperature: 0.7
  streaming: true

vertex_ai:
  project_id: "YOUR_GCP_PROJECT_ID"
  location: "YOUR_VERTEX_REGION"
  embedding_model_id: "text-embedding-004"

app:
  name: "Translation Engine API"
  show_emojis: true
```

### Fields

- **`provider_type`**
  - `"ollama"` – use the local Ollama backend (`OllamaLLMProvider` + `OllamaEmbeddingProvider`).
  - `"vertex_ai"` – use Google Cloud Vertex AI (`VertexAILLMProvider` + `VertexAIEmbeddingProvider`).

- **`ollama`**
  - Runtime translation model is sourced from `config_translation.yaml` (`defaults.translation_model`).
  - `base_url` – URL of the Ollama server (default `http://localhost:11434`).
  - `temperature` – sampling temperature for generation.
  - `streaming` – whether streaming responses are enabled by default.

- **`vertex_ai`**
  - `project_id` – GCP project ID where Vertex AI is enabled.
  - `location` – Vertex AI region (e.g. `europe-west1`).
  - Runtime translation model is sourced from `config_translation.yaml` (`defaults.translation_model`).
  - `embedding_model_id` – text embedding model ID used by the context index.

- **`app`**
  - `name` – application display name.
  - `show_emojis` – referenced in the UI or prompts if you choose to surface emojis.

### How it is used

- `ConfigManager._load_main_config()` reads these values and populates:
  - `config.provider_type`
  - `config.ollama` (`OllamaConfig`)
  - `config.vertex_ai` (`VertexAIConfig`) when `provider_type == "vertex_ai"`.
  - `config.app` (`AppConfig`)

- `translation_engine/engine.py` uses:
  - `config.provider_type` to decide which LLM and embedding provider to instantiate.
  - `config.ollama` / `config.vertex_ai` for transport/project settings.
  - `config_translation.yaml -> defaults.translation_model` as the active runtime LLM model for both Ollama and Vertex AI.

- Request-level overrides:
  - The JSON API and HTML frontend can override:
    - source language
    - target language
    - tone
    - purpose of text
  - These values flow into `TranslationOptions` and override the YAML defaults for that request only.

---

## `config_translation.yaml` – translation defaults and prompts

Example:

```yaml
defaults:
  translation_model: "translategemma"
  source_language: "English"
  target_language: "German"
  target_audience: "Customers purchasing online"
  tone: "Professional, enthusiastic, and slightly assertive"
  purpose_of_text: "To build brand awareness"
  specific_vocabulary_preferences: ""
  cultural_considerations: ""
  length_constraints: ""
  key_phrases_to_preserve: ""
  instructions: "None"

reflection:
  enabled: true
  use_separate_model: false
  reflection_model: "translategemma"
  skip_keywords:
    - "excellent"
    - "accurate"
    - "no issues"
    - "no changes needed"
    - "well-translated"
    - "correctly translated"
  debug_logging: true

prompts:
  system: |
    ... system prompt template for translation ...

  reflection_system: |
    ... system prompt template for reflection ...

  refinement_system: |
    ... system prompt template for refinement ...
```

### Fields

- **`defaults`** (`TranslationConfig`)
  - `translation_model` – active runtime model ID (required). Used by the translation provider for both Ollama and Vertex AI.
  - `source_language` – default source language name (e.g. `"English"`).
  - `target_language` – default target language name (e.g. `"German"`).
  - `target_audience` – description of the intended reader/audience.
  - `tone` – default tone (e.g. `"Professional"`).
  - `purpose_of_text` – description of the text’s purpose (e.g. `"To inform"`).
  - `specific_vocabulary_preferences` – optional glossary/terminology preferences.
  - `cultural_considerations` – notes on cultural or regional specifics.
  - `length_constraints` – instructions on shortening/expanding translations.
  - `key_phrases_to_preserve` – phrases that should remain unchanged.
  - `instructions` – additional free-form instructions.

- **`reflection`** (`ReflectionConfig`)
  - `enabled` – whether the reflection/refinement pipeline is enabled.
  - `use_separate_model` – whether to use a separate model for reflection.
  - `reflection_model` – model name/ID for reflection (Ollama or Vertex AI).
  - `skip_keywords` – list of substrings; if any appear in the reflection feedback, refinement is skipped.
  - `debug_logging` – when `true`, logs reflection/refinement details.

- **`prompts`** (`PromptsConfig`)
  - `system` – base system prompt template for translation. Receives placeholders:
    - `{SOURCE_LANG}`, `{SOURCE_CODE}`, `{TARGET_LANG}`, `{TARGET_CODE}`,
      `{TARGET_AUDIENCE}`, `{TONE}`, `{PURPOSE_OF_TEXT}`, etc.
  - `reflection_system` – system prompt template used in reflection.
  - `refinement_system` – system prompt template used for refinement.

### How it is used

- `ConfigManager._load_translation_config()` populates:
  - `config.translation` (`TranslationConfig`)
  - `config.reflection` (`ReflectionConfig`)
  - `config.prompts` (`PromptsConfig`)

- `Translator` uses:
  - `config.translation` and `config.prompts.system` to build the main system prompt.
  - `TranslationOptions` to override defaults per request.

- `Reflector` uses:
  - `config.translation`, `config.reflection`, and `config.prompts.reflection_system` / `config.prompts.refinement_system` to build reflection/refinement prompts.

- The HTML frontend uses `config.translation` values as **initial defaults** in the form, but submitted values override them at request time.

---

## `config_context.yaml` – context indexing configuration

Example:

```yaml
context_sources:
  enabled: true
  embedding_model: "embeddinggemma"
  chunk_size: 1000
  chunk_overlap: 50
  top_k: 3
  max_context_length: 2000

  websites:
    - name: "Biking News, Tips and Tricks"
      url: "https://bikeradar.com/"
      description: "The world's best biking advice"
```

### Fields

- **`context_sources`** (`ContextConfig`)
  - `enabled` – global switch for context indexing.
  - `embedding_model` – logical name of the embedding model.
    - With Ollama: used as the model name for `OllamaEmbeddingProvider`.
    - With Vertex AI: informational label; actual embedding model ID is controlled via `vertex_ai.embedding_model_id` in `config.yaml`.
  - `chunk_size` – maximum characters per chunk when splitting website text.
  - `chunk_overlap` – overlap between chunks, in characters.
  - `top_k` – how many nearest chunks to retrieve per query.
  - `max_context_length` – maximum combined length of retrieved context text.
  - `websites` – initial list of websites (name/url/description) to index.

### How it is used

- `ConfigManager._load_context_config()` fills:
  - `config.context` (`ContextConfig`)

- `translation_engine/engine.py` uses:
  - `config.context` to construct a `FAISSContextProvider` when `enabled` is `true`.

- `FAISSContextProvider`:
  - Starts with `ContextConfig.websites` as its default profile.
  - Maintains in-memory FAISS index state per profile ID.
  - Uses `embedding_model`/embedding provider to compute vectors.
  - Exposes:
    - `build_index(force=False)` for the default profile
    - `build_profile_index(profile_id, websites, force=False)` for reusable profiles
    - `get_profile_context(profile_id, text)` for profile-specific retrieval

- `translation_engine/context_profiles.py`
  - Stores reusable website sets in `ContextProfile` objects.
  - The current implementation uses `InMemoryContextProfileStore`.
  - Important: profile metadata is process-local today, and FAISS indexes are also in-memory per Cloud Run instance.

- `TranslationPipeline`:
  - Calls `context_provider.get_context(text)` when:
    - Context is enabled and ready.
    - The request asks to use context.

---

## Interaction with the HTML frontend and APIs

### HTML frontend (`routes_frontend.py`)

- Uses `config.translation` to prefill:
  - Source language
  - Target language
  - Tone
  - Purpose of text

- Allows the user to:
  - Enter custom text.
  - Toggle reflection and context.
  - Provide up to 3 websites.
  - Reuse a generated `context_profile_id` on subsequent submissions.

- When context is enabled and websites are provided:
  - Creates or updates a context profile.
  - Triggers a background rebuild for that profile.
  - Continues the request immediately; context may not be available until the rebuild completes.

### Context API

- `GET /api/v1/context/status`
  - Returns whether context is enabled/ready and how many chunks are indexed.

- `POST /api/v1/context/rebuild`
  - Rebuilds the default config-based index.

- `POST /api/v1/context/profiles`
  - Creates a new reusable context profile and returns a `profile_id`.

- `POST /api/v1/context/profiles/{profile_id}/rebuild`
  - Rebuilds the FAISS index for a specific reusable context profile.

- `POST /api/v1/context/sources`
  - Legacy shortcut that creates a profile and schedules a background rebuild.

---

## Summary

- Use **`config.yaml`** to choose the backend (Ollama vs Vertex AI) and set provider connection/project settings.
- Use **`config_translation.yaml`** to define the runtime translation model, translation defaults, reflection behaviour, and prompt templates.
- Use **`config_context.yaml`** to configure context indexing behaviour and initial default websites, with the option to create reusable runtime profiles via the API or HTML frontend.

These configuration layers allow you to:

- Run locally on Ollama with minimal changes.
- Switch to Vertex AI on GCP with the same core engine code.
- Adjust translation behaviour per request and create reusable context profiles without modifying Python code.

