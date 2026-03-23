# translation-engine

LLM-based translation engine that uses configurable prompts, optional reflection, and website-based context, exposed through a FastAPI JSON API and a server-rendered HTML frontend.

## Project structure

- `translation_engine/` – Core engine package  
  - `config/` – YAML-backed configuration loading and dataclasses (`ConfigManager`, `OllamaConfig`, `VertexAIConfig`, etc.)  
  - `providers/` – LLM, embeddings, and FAISS context providers (Ollama + Vertex AI)  
  - `services/` – Translator, reflector, and translation pipeline  
  - `domain/` – Domain models for requests and results  
  - `engine.py` – Engine initializer wiring config, providers, and pipeline  
- `api/` – FastAPI application  
  - `main.py` – FastAPI app factory and entrypoint  
  - `dependencies.py` – Dependencies for accessing the shared engine  
  - `schemas.py` – Pydantic request/response models  
  - `routes_translation.py` – Translation endpoints  
  - `routes_context.py` – Context status, profile creation, and rebuild endpoints  
  - `routes_health.py` – Health check endpoint  
  - `routes_frontend.py` – Simple server-rendered HTML frontend  
- `templates/` – Jinja2 templates for the HTML frontend (mainly `index.html`)  
- `config.yaml` – provider selection (Ollama vs Vertex AI), provider connection/project settings, and app settings  
- `config_translation.yaml` – Translation defaults, reflection, and prompts  
- `config_context.yaml` – Website sources and FAISS context settings  
- `requirements.txt` – Python dependencies  
- `Dockerfile` – Container image definition (suitable for Cloud Run)

## Running locally (Ollama)

1. Install and start Ollama, then pull the required models:

   ```bash
   ollama pull translategemma
   ollama pull embeddinggemma
   ```

2. Create a virtual environment and install dependencies:

   ```bash
   cd translation-engine
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux

   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Run the API server:

   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

4. Open the HTML frontend:

   - Browser: `http://localhost:8000/`

   The frontend lets you:

   - Enter text to translate
   - Choose source and target language (`Auto-detect` is supported for source language)
   - Override tone and purpose of text per request
   - Toggle reflection
   - Create or reuse a website context profile with up to 3 URLs

   Note: context profile rebuilding is asynchronous. If you submit new websites,
   the first request may run without context while the profile index rebuilds in
   the background.

5. Test the API directly (examples):

   - Health:

     ```bash
     curl http://localhost:8000/health
     ```

   - Full translation pipeline:

     ```bash
     curl -X POST http://localhost:8000/api/v1/translate \
       -H "Content-Type: application/json" \
       -d "{\"text\": \"Our premium leather wallets are handcrafted with care.\", \"use_context\": true, \"use_reflection\": true}"
     ```

   - Simple translation:

     ```bash
     curl -X POST http://localhost:8000/api/v1/translate/simple \
       -H "Content-Type: application/json" \
       -d "{\"text\": \"Our premium leather wallets are handcrafted with care.\", \"use_context\": true}"
     ```

## Running against Vertex AI locally

To develop against Vertex AI instead of Ollama:

1. Set `provider_type: "vertex_ai"` and fill out the `vertex_ai` block in `config.yaml`:

   - `project_id` – your GCP project ID  
   - `location` – Vertex AI region (e.g. `europe-west1`)  
   - `embedding_model_id` – embedding model ID (e.g. `text-embedding-004`) if you want context indexing

2. Set the active runtime translation model in `config_translation.yaml`:

   - `defaults.translation_model` – model ID used at runtime for translation (and default reflection model when reflection model is not explicitly set)

3. Authenticate locally so the Vertex AI SDK can use your credentials:

   ```bash
   gcloud auth application-default login
   ```

4. Start the app as above:

   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

5. Use the HTML frontend at `http://localhost:8000/` or the JSON API endpoints as before.

## Context profiles

Website context is now isolated through **context profiles** instead of one
global mutable website list.

- Create a profile via `POST /api/v1/context/profiles`
- Rebuild a profile index via `POST /api/v1/context/profiles/{profile_id}/rebuild`
- Check general context readiness via `GET /api/v1/context/status`

This design is safer for Cloud Run because one user’s websites no longer
overwrite another user’s context within the same container. The FAISS indexes
are still in-memory per container, so they may need to be rebuilt after
instance restarts or scale-to-zero events.

## Deploying to Google Cloud

For a complete, step-by-step guide to configuring Google Cloud (Vertex AI, Cloud Run, Artifact Registry) and deploying this app, see:

- `setup_gcp.md`

That document covers:

- Creating / selecting a GCP project and enabling billing  
- Enabling required APIs and configuring Vertex AI models  
- Building and pushing the Docker image  
- Deploying the container to Cloud Run and verifying health and translation endpoints

