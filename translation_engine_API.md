# Translation Engine HTTP API

This document describes the HTTP API exposed by the Translation Engine FastAPI application so client applications can integrate without reading the Python source.

**Application:** FastAPI app in [`api/main.py`](api/main.py)  
**Title / version:** `Translation Engine API` / `1.0.0` (as configured in code)

---

## Base URL and running the server

Typical local startup (from the project root):

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Unless you configure a reverse proxy or different port, the **base URL** is:

```text
http://localhost:8000
```

All paths below are relative to that base (e.g. full translation URL: `http://localhost:8000/api/v1/translate`).

---

## Authentication and security

- **There is no API key, JWT, or session authentication** in the current implementation.
- The service is intended for trusted networks (local dev, private VPC, or a gateway that adds auth). **Do not expose it to the public internet without additional protection.**
- **CORS** is not configured in `api/main.py`. Browser-based clients on another origin may be blocked unless you add CORS middleware.

---

## Content types

| Area | Content type |
|------|----------------|
| JSON API (`/api/v1/...`, `/health`) | `application/json` for request bodies (where applicable) and JSON responses |
| HTML UI (`GET /`, `POST /translate`) | `text/html` |

Set header for JSON POST requests:

```http
Content-Type: application/json
```

---

## OpenAPI (interactive docs)

FastAPI generates OpenAPI automatically:

| URL | Description |
|-----|-------------|
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |

These reflect the same routes and schemas as this document and are useful for trying requests in a browser.

---

## Errors

| HTTP status | When |
|-------------|------|
| **422 Unprocessable Entity** | Request body or query fails **Pydantic** validation (wrong types, invalid URL in `ContextWebsite`, etc.). Response body follows FastAPI’s default validation error shape (`detail` array). |
| **503 Service Unavailable** | The LLM provider is unreachable (e.g. Ollama down). Raised as `ProviderUnavailableError` from **`POST /api/v1/translate`** and **`POST /api/v1/translate/simple`** only; `detail` is a human-readable string. **`GET /api/v1/translate/languages`** does not call the LLM and does not return 503 for provider outages. |
| **500 Internal Server Error** | Unexpected errors, including `RuntimeError` if the engine was not initialized on startup, or if context profile routes hit an uninitialized profile store (see context routes). |

There is **no** custom error envelope: clients should read `detail` (string or list) from the JSON body when present.

---

## Health

### `GET /health`

**Purpose:** Liveness check. Succeeds if startup completed and the shared `Engine` was stored on `app.state` (the handler resolves it via `Depends(get_engine)`).

**Response model:** `HealthResponse`

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Currently always `"ok"` when the handler returns. |

**Example:**

```bash
curl -s http://localhost:8000/health
```

```json
{"status":"ok"}
```

---

## Translation (JSON API)

Prefix: **`/api/v1/translate`**

The pipeline can use **website context** (FAISS + crawled sites) and **reflection** (critique + optional refinement). Behavior depends on `config.yaml` / `config_translation.yaml` / `config_context.yaml` and runtime index state.

Runtime model selection note:

- Active LLM model comes from `config_translation.yaml` -> `defaults.translation_model`.
- `config.yaml` controls provider selection (`provider_type`) plus provider connection/project settings.

### Field semantics (requests)

- Omitting optional fields lets the server fill defaults from the configured translation profile (see `TranslationPipeline` / `Translator` in code).
- **`source_language`:** If omitted, the API passes `"Auto-detect"` into the domain layer. If you send `"auto"` (case-insensitive) or set **`auto_detect_source_language`: true**, auto-detect behavior is applied in prompts.
- **`target_language`**, **`tone`**, **`purpose_of_text`:** When omitted, defaults come from the engine’s loaded `TranslationConfig` (YAML).
- **`target_audience`:** Not exposed on the JSON request schema; it always comes from YAML for JSON API calls.
- **`use_context`:** If `true`, context is used only when the index is ready and (for default index) `context_ready` is true. See [Context](#context-json-api).
- **`use_reflection`:** If `true`, reflection runs only when reflection is enabled in config and a reflector is wired; otherwise the pipeline behaves as if reflection were off.

**Limitation (context profiles):** The domain model supports `context_profile_id`, but **`TranslateRequest` and `TranslateSimpleRequest` do not include this field.** The JSON API therefore always uses the **default** context index when `use_context` is true, not a named profile. To use per-request profiles today, use the **HTML form** at `POST /translate` or extend the API schemas.

---

### `GET /api/v1/translate/languages`

**Purpose:** Return the ordered list of language labels the server suggests for `source_language` and `target_language` (same options as the HTML form). The set depends on **`defaults.translation_model`** in `config_translation.yaml` (e.g. `translategemma` uses the WMT24++ 55-language evaluation set plus `English` and `Auto-detect`). The translation endpoints still accept arbitrary strings for those fields; this endpoint is for discovery and UI dropdowns.

**Response model:** `SupportedLanguagesResponse`

| Field | Type | Description |
|-------|------|-------------|
| `languages` | array of strings | Ordered labels (e.g. `Auto-detect`, `English`, then model-specific targets). |

**Example:**

```bash
curl -s http://localhost:8000/api/v1/translate/languages
```

With `translation_model: translategemma`, the array has 57 entries (`Auto-detect`, `English`, then 55 WMT24++ targets). Example start of the response:

```json
{"languages":["Auto-detect","English","Arabic (Egypt)","Arabic (Saudi Arabia)","Bengali","Bulgarian"]}
```

Use `curl` or `/docs` to see the full list for your deployment.

**Engine:** Like `/health`, this route uses `get_engine`. If the engine was not initialized on startup, the request fails with **500** (`RuntimeError`), not 503.

---

### `POST /api/v1/translate`

**Purpose:** Full pipeline: optional context retrieval → initial translation → optional reflection → optional refinement.

**Request body:** `TranslateRequest`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | yes | — | Source text to translate. |
| `source_language` | string \| null | no | null → Auto-detect | Source language label for prompts. |
| `target_language` | string \| null | no | null → YAML default | Target language. |
| `tone` | string \| null | no | null → YAML default | Tone (e.g. formal). |
| `purpose_of_text` | string \| null | no | null → YAML default | Purpose of the text. |
| `auto_detect_source_language` | boolean | no | `false` | When true, prompt instructs the model to detect source language. |
| `use_context` | boolean | no | `true` | Whether to attach website context when available. |
| `use_reflection` | boolean | no | `true` | Whether to run reflection/refinement when configured. |

**Response:** `TranslateResponse`

| Field | Type | Description |
|-------|------|-------------|
| `source_text` | string | Echo of input text. |
| `initial_translation` | string | Output of the first translation step. |
| `reflection` | string \| null | Critique text if reflection ran; otherwise `null`. |
| `final_translation` | string | After refinement, or same as initial if refinement skipped/disabled. |
| `refinement_skipped` | boolean | `true` if refinement was not applied (e.g. “excellent” reflection or reflection off). |
| `context_used` | boolean | `true` if non-empty context was applied to the translation step. |

**Example:**

```bash
curl -s -X POST http://localhost:8000/api/v1/translate \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Hello world\",\"use_context\":false,\"use_reflection\":true}"
```

---

### `POST /api/v1/translate/simple`

**Purpose:** Single LLM translation call **without** reflection/refinement. Still supports context when enabled and ready.

**Request body:** `TranslateSimpleRequest` (same as `TranslateRequest` except **no** `use_reflection`)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `text` | string | yes | — |
| `source_language` | string \| null | no | null → Auto-detect |
| `target_language` | string \| null | no | null → YAML default |
| `tone` | string \| null | no | null → YAML default |
| `purpose_of_text` | string \| null | no | null → YAML default |
| `auto_detect_source_language` | boolean | no | `false` |
| `use_context` | boolean | no | `true` |

**Response:** `TranslateSimpleResponse`

| Field | Type | Description |
|-------|------|-------------|
| `translation` | string | Translated text. |
| `context_used` | boolean | `true` when `use_context` was true **and** the default context index was ready (`pipeline.context_ready`). |

**Example:**

```bash
curl -s -X POST http://localhost:8000/api/v1/translate/simple \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"Hello\",\"use_context\":false}"
```

---

## Context (JSON API)

Prefix: **`/api/v1/context`**

Context indexing uses a **FAISS**-backed provider when enabled in configuration. Several endpoints schedule work on a **background task**; they return immediately while the index rebuilds.

**Website limit:** `UpdateContextSourcesRequest` accepts a list, but **only the first three** entries are used (`payload.websites[:3]`).

---

### `GET /api/v1/context/status`

**Purpose:** Report whether context is enabled, whether the **default** index is ready, and chunk count when ready.

**Response:** `ContextStatusResponse`

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Context feature enabled in config and provider present. |
| `ready` | boolean | Default index built and usable. |
| `chunk_count` | integer \| null | Number of chunks when `ready`; otherwise `null`. |

---

### `POST /api/v1/context/rebuild`

**Purpose:** Rebuild the **default** context index in the background (`force=True`).

**Request body:** none

**Response:**

```json
{"started": true}
```

---

### `POST /api/v1/context/profiles`

**Purpose:** Create a **reusable context profile** record **without** starting a rebuild in this handler (caller should call rebuild separately).

**Request body:** `UpdateContextSourcesRequest`

| Field | Type | Description |
|-------|------|-------------|
| `websites` | array of `ContextWebsite` | Up to **3** used. |

`ContextWebsite`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string (URL) | yes | Must be a valid HTTP/HTTPS URL (`HttpUrl`). |
| `name` | string \| null | no | Display name; defaults to string form of `url` if omitted. |
| `description` | string \| null | no | Defaults to empty string if omitted. |

**Response:** `ContextProfileResponse`

| Field | Type | Description |
|-------|------|-------------|
| `profile_id` | string | New profile identifier. |
| `ready` | boolean | Always `false` in current implementation for this route. |
| `chunk_count` | null | Always `null` here. |

**Errors:** If the context profile store is missing, the code raises **`RuntimeError`** → **500**.

---

### `POST /api/v1/context/profiles/{profile_id}/rebuild`

**Purpose:** Schedule a **background** rebuild for an existing profile (`force=True`).

**Path parameter:** `profile_id` — string

**Behavior:**

- If the profile **does not exist**, the handler still returns **200** with `ContextProfileResponse(profile_id=..., ready=false, chunk_count=null)` and **does not** enqueue a task.
- If the profile exists, a background task runs `initialize_context_profile(profile, True)`.

**Response:** `ContextProfileResponse` (same shape as above; `ready` is `false` in the immediate response).

---

### `POST /api/v1/context/sources`

**Purpose:** Create a **new** context profile from the given websites and schedule its index rebuild in the background. Intended for “update sources” flows in the API.

**Request body:** `UpdateContextSourcesRequest` (same as profiles)

**Response:** `ContextStatusResponse`

Typical immediate values after scheduling:

- `enabled`: `true` if profile store exists; if store is missing, returns `enabled: false`, `ready: false`, `chunk_count: null`.
- `ready`: `false` (rebuild is asynchronous).
- `chunk_count`: `null`

**Note:** This endpoint **creates a new profile** each time; it does not replace a named profile by ID. Use profile APIs if you need stable IDs across updates.

---

## HTML frontend (browser)

These routes are for **server-rendered** UI, not typical machine-to-machine JSON clients.

### `GET /`

Returns the main translation form (Jinja template `templates/index.html`) with defaults from configuration.

### `POST /translate`

**Content type:** `application/x-www-form-urlencoded` (HTML form).

**Form fields (representative):**

| Field | Description |
|-------|-------------|
| `text` | Source text (required). |
| `source_language`, `target_language`, `tone`, `purpose_of_text` | Strings from the form. |
| `use_reflection` | Checkbox (absent = false). |
| `use_context` | Checkbox (absent = false). |
| `website1`, `website2`, `website3` | Optional URL strings for context (up to 3 non-empty). |
| `context_profile_id` | Optional; when updating context, ties to an existing profile id when present. |

When context websites are provided with `use_context`, the server may create/update a **context profile** and enqueue a **background** index rebuild; the page can show a notice that the index may not be ready until a later request.

On provider failure, the page renders an error message instead of raising JSON 503.

---

## Integration checklist for app developers

1. **Health:** Poll `GET /health` after deploy.
2. **Languages:** Call `GET /api/v1/translate/languages` to populate source/target dropdowns (list depends on `defaults.translation_model` in `config_translation.yaml`).
3. **Translate:** Use `POST /api/v1/translate` for quality pipeline or `/api/v1/translate/simple` for latency.
4. **Context:** If you rely on website context, poll `GET /api/v1/context/status` until `ready` is true, or call rebuild and wait before expecting `context_used: true`.
5. **Profiles:** Use `POST /api/v1/context/profiles` + `POST /api/v1/context/profiles/{id}/rebuild` for reusable indexes; today, **use those profile IDs from the HTML UI or custom server code**—the public JSON translate endpoints do not accept `context_profile_id` yet.
6. **Failures:** Handle **503** on the translate **POST** endpoints when the LLM backend is down.
7. **Docs:** Use `/docs` to confirm schemas match your client version after upgrades.

---

## Changelog pointer

Behavior is defined by the repository at the time you deploy. After pulling new commits, re-check:

- [`api/schemas.py`](api/schemas.py) — request/response models  
- [`api/routes_translation.py`](api/routes_translation.py) — translation mapping and defaults  
- [`api/routes_context.py`](api/routes_context.py) — context and profile behavior  
- [`translation_engine/supported_languages.py`](translation_engine/supported_languages.py) — language lists keyed by `translation_model`  
