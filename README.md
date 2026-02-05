# translation-engine

LLM-based translation engine that also uses context, exposed via a FastAPI REST API.

## Project structure

- `translation_engine/` – Core engine package
  - `config/` – YAML-backed configuration loading and dataclasses
  - `providers/` – LLM, embeddings, and FAISS context providers
  - `services/` – Translator, reflector, and translation pipeline
  - `domain/` – Domain models for requests and results
  - `engine.py` – Engine initializer wiring config, providers, and pipeline
- `api/` – FastAPI application
  - `main.py` – FastAPI app factory and entrypoint
  - `dependencies.py` – Dependencies for accessing the shared engine
  - `schemas.py` – Pydantic request/response models
  - `routes_translation.py` – Translation endpoints
  - `routes_context.py` – Context status and rebuild endpoints
  - `routes_health.py` – Health check endpoint
- `config.yaml` – Ollama and app settings
- `config_translation.yaml` – Translation defaults, reflection, and prompts
- `config_context.yaml` – Website sources and FAISS context settings
- `requirements.txt` – Python dependencies

## Running locally

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

4. Test the API (examples):

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

## VPS deployment (high level)

On a Linux VPS:

1. Install system dependencies and Ollama, pull the same models as above.
2. Clone this repository and create a Python virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run the API with a process manager, for example a systemd service that executes:

   ```bash
   /path/to/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2
   ```

5. Put Nginx (or Caddy) in front as a reverse proxy:
   - Terminate HTTPS with Let's Encrypt certificates.
   - Proxy `/` or `/api/` to `http://127.0.0.1:8000`.
   - Set appropriate timeouts for long-running translation requests.

