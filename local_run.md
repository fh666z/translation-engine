## Running the Translation Engine Locally

This guide walks you through running the app on your machine for development and manual testing.

The app supports two backends:

- **Ollama** (local LLM server) – easiest for fully local development.
- **Vertex AI** (Google Cloud) – matches the production deployment on GCP.

---

## 1. Prerequisites

- Python 3.11+
- `git` (optional, if you cloned the repo)
- For **Ollama mode**:
  - Ollama installed and accessible from your shell (`ollama --version`).
- For **Vertex AI mode**:
  - `gcloud` CLI installed.
  - A GCP project with Vertex AI API enabled.

---

## 2. Create and activate a virtual environment

From the project root (`e:\workspace\translation-engine`):

```bash
cd e:\workspace\translation-engine

python -m venv .venv
.\.venv\Scripts\activate  # PowerShell / CMD on Windows

pip install --upgrade pip
pip install -r requirements.txt
```

Keep the virtual environment activated in any terminal where you run the app or tests.

---

## 3. Configure backend in `config.yaml` and `config_translation.yaml`

Open `config.yaml` in the project root and choose your provider:

### 3.1 Local Ollama (recommended for first run)

```yaml
provider_type: "ollama"

ollama:
  base_url: "http://localhost:11434"
  temperature: 0.7
  streaming: true
```

Leave the `vertex_ai` block as-is for now; it will be ignored while `provider_type` is `"ollama"`.
The runtime translation model is not read from `config.yaml`.

### 3.2 Vertex AI (optional, if you want to test against GCP)

Set:

```yaml
provider_type: "vertex_ai"

vertex_ai:
  project_id: "YOUR_PROJECT_ID"
  location: "YOUR_REGION"         # e.g. "europe-west1"
  embedding_model_id: "text-embedding-004"
```

Then authenticate once on your machine:

```bash
gcloud auth application-default login
```

### 3.3 Set the runtime model in `config_translation.yaml` (required)

Set:

```yaml
defaults:
  translation_model: "translategemma:4b"  # Ollama example
```

If `provider_type` is `"vertex_ai"`, set `defaults.translation_model` to your Vertex AI model ID
(for example `gemini-1.5-flash`).

---

## 4. Start the backend (Ollama mode only)

If you are using `provider_type: "ollama"`:

1. Ensure Ollama is installed:

   ```bash
   ollama --version
   ```

2. Start the Ollama server if it is not already running:

   ```bash
   ollama serve
   ```

3. In another terminal, pull the models you need (matching your `config_translation.yaml` and `config_context.yaml`):

   ```bash
   ollama pull translategemma
   ollama pull embeddinggemma
   ```

4. Quick connectivity check:

   ```bash
   curl http://localhost:11434/api/tags
   ```

If this returns a JSON list of models, the app will be able to reach Ollama.

---

## 5. Run the FastAPI app

With your virtual environment active (`.\.venv\Scripts\activate`), from the project root:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

You should see startup logs ending with something like:

```text
INFO:     Application startup complete.
```

### 5.1 Health check

In another terminal:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

### 5.2 HTML frontend

Open your browser at:

```text
http://localhost:8000/
```

You can:

- Enter text to translate.
- Choose **source language** (`Auto-detect` or explicit).
- Choose **target language**, **tone**, and **purpose of text**.
- Toggle **reflection**.
- Toggle **website context** and provide up to 3 URLs (these create a reusable context profile and trigger a background FAISS index rebuild).

If the backend (Ollama or Vertex AI) is not reachable, the page shows a clear error banner instead of a raw traceback.

---

## 6. Running tests locally

With the virtual environment active:

### 6.1 Full test suite

```bash
python -m pytest -q
```

### 6.2 Focused tests for recent functionality

```bash
python -m pytest \
  tests/test_frontend.py \
  tests/test_translation_options.py \
  tests/test_context_profiles.py \
  tests/test_vertex_ai_provider.py \
  tests/test_config_manager.py -q
```

The tests use stubs for optional native/cloud dependencies (`faiss`, `crawl4ai`, Ollama, Vertex AI), so you can run them even if those services are not available.

---

## 7. Typical local dev loop

1. **Activate env**: `.\.venv\Scripts\activate`
2. **Edit code or config** as needed.
3. **Run focused tests** for the area you changed.
4. **Run full suite** periodically: `python -m pytest -q`
5. **Start app**: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
6. **Manual sanity check**:
   - `GET /health`
   - A couple of test translations through the HTML frontend.

