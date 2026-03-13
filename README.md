# translation-engine

LLM-based translation engine that also uses context, exposed via a FastAPI REST API and an optional HTML frontend.

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
  - `routes_context.py` – Context status, sources update, and rebuild endpoints  
  - `routes_health.py` – Health check endpoint  
  - `routes_frontend.py` – Simple server-rendered HTML frontend  
- `templates/` – Jinja2 templates for the HTML frontend (mainly `index.html`)  
- `config.yaml` – LLM provider selection (Ollama vs Vertex AI) and app settings  
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
   - `model_id` – generative model ID (e.g. `gemini-1.5-flash`)  
   - `embedding_model_id` – embedding model ID (e.g. `text-embedding-004`) if you want context indexing

2. Authenticate locally so the Vertex AI SDK can use your credentials:

   ```bash
   gcloud auth application-default login
   ```

3. Start the app as above:

   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

4. Use the HTML frontend at `http://localhost:8000/` or the JSON API endpoints as before.

## Deploying to Google Cloud

For a complete, step-by-step guide to configuring Google Cloud (Vertex AI, Cloud Run, Artifact Registry) and deploying this app, see:

- `setup_gcp.md`

That document covers:

- Creating / selecting a GCP project and enabling billing  
- Enabling required APIs and configuring Vertex AI models  
- Building and pushing the Docker image  
- Deploying the container to Cloud Run and verifying health and translation endpoints

