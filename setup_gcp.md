## Setup on Google Cloud Platform (GCP)

This guide walks you through configuring Google Cloud and deploying the translation engine to **Cloud Run** using **Vertex AI** as the LLM backend.

The high-level architecture:

- Cloud Run service running this FastAPI app (API + HTML frontend)
- Vertex AI generative model (e.g. `gemini-1.5-flash` or a Gemma/TranslateGemma model)
- Optional Vertex AI text embedding model (e.g. `text-embedding-004`) for context indexing
- In-memory FAISS indexes per Cloud Run instance, keyed by reusable context profile IDs

---

## 1. Prerequisites

- A Google account.
- `gcloud` CLI installed locally.
- A cloned copy of this repository on your machine.

---

## 2. Create or select a GCP project

1. Go to the Google Cloud Console and either:
   - Create a new project (e.g. `translation-engine`), or
   - Select an existing project.

2. Ensure **billing** is enabled for that project.

3. In a terminal, set the project as default:

   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

4. Choose a default region for Cloud Run / Vertex AI (e.g. `europe-west1`):

   ```bash
   gcloud config set run/region europe-west1
   ```

---

## 3. Enable required APIs

Enable the following APIs in your project:

- Cloud Run API
- Artifact Registry API
- Vertex AI API

`cloudbuild.googleapis.com` is only needed if you plan to use Cloud Build-based
image builds (for example, `gcloud builds submit`). The commands in this guide
use local Docker build/push, so Cloud Build is optional here.

You can do this from the Console, or via CLI:

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com
```

---

## 4. Configure Vertex AI models

### 4.1 Choose a generative model

Pick a Vertex AI generative model that fits your cost/latency needs, for example:

- `gemini-1.5-flash`
- A Gemma / TranslateGemma model available in Vertex AI Model Garden (check the current docs for exact IDs).

Note the **model ID** and the **location/region** where it is available (e.g. `europe-west1`).

### 4.2 Choose an embedding model (required when context is enabled)

If you want to use website-based context features in production
(`config_context.yaml` -> `context_sources.enabled: true`), choose a text
embedding model, e.g.:

- `text-embedding-004`

---

## 5. Update `config.yaml` for production

In the repository root, open `config.yaml` and set:

```yaml
provider_type: "vertex_ai"

vertex_ai:
  project_id: "YOUR_PROJECT_ID"
  location: "europe-west1"
  model_id: "gemini-1.5-flash"        # or another supported Vertex AI model
  embedding_model_id: "text-embedding-004"
```

Leave the `ollama` block intact – it can still be used for local development if you switch `provider_type` back to `"ollama"`.

Commit or otherwise persist this production config as appropriate for your workflow.

Important configuration note:

- This app reads provider/runtime settings from YAML files in the repo root
  (`config.yaml`, `config_translation.yaml`, `config_context.yaml`).
- Cloud Run environment variables are not currently used to configure
  `vertex_ai.project_id`, `vertex_ai.location`, `vertex_ai.model_id`, or
  `vertex_ai.embedding_model_id`.
- If you omit `embedding_model_id` while `context_sources.enabled: true`, startup
  will fail in Vertex AI mode. It is only optional when context is disabled.

---

## 6. Build and push the Docker image

### 6.1 Create an Artifact Registry repository

1. In the Cloud Console, go to **Artifact Registry → Repositories**.
2. Create a new **Docker** repository, e.g.:
   - Name: `translation-engine`
   - Format: Docker
   - Location: `europe-west1` (or your chosen region)

### 6.2 Configure Docker authentication

Run:

```bash
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

Replace `europe-west1` with your region if different.

### 6.3 Build and push the image

From the root of this repo:

```bash
PROJECT_ID="$(gcloud config get-value project)"
REGION="europe-west1"
REPO="translation-engine"
IMAGE_NAME="api"

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:latest"

docker build -t "${IMAGE_URI}" .
docker push "${IMAGE_URI}"
```

This builds the container using the `Dockerfile` in the repo and pushes it to Artifact Registry.

---

## 7. Deploy to Cloud Run

### 7.1 Choose or create a service account

For simple setups you can use the default compute service account, but it must have permission to call Vertex AI.

Grant the **Vertex AI User** role to the service account you plan to use with Cloud Run, for example:

```bash
SERVICE_ACCOUNT="YOUR_SERVICE_ACCOUNT_EMAIL"  # e.g. PROJECT_NUMBER-compute@developer.gserviceaccount.com

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user"
```

### 7.2 Deploy the Cloud Run service

Deploy the image, specifying the service account and allowing unauthenticated access (you can restrict this later if needed):

```bash
gcloud run deploy translation-engine-api \
  --image="${IMAGE_URI}" \
  --platform=managed \
  --region="${REGION}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --allow-unauthenticated \
  --max-instances=3 \
  --cpu=1 \
  --memory=1Gi \
  --timeout=120
```

Adjust `max-instances`, `cpu`, `memory`, and `timeout` based on your expected workload and model latency.

The command will output a **Cloud Run URL**, e.g.:

```text
https://translation-engine-api-xxxxxxxxx-uc.a.run.app
```

---

## 8. Verify the deployment

### 8.1 Health check

Call the health endpoint:

```bash
curl "${CLOUD_RUN_URL}/health"
```

You should get JSON like:

```json
{"status": "ok"}
```

### 8.2 HTML frontend

Open the Cloud Run URL in a browser:

- `https://translation-engine-api-…a.run.app/`

You should see the translation form where you can:

- Enter text
- Set source/target language, tone, purpose
- Enable/disable reflection
- Optionally enable context and provide up to 3 websites

Submit a translation request and confirm you get a response.

If you enter websites, the frontend creates or updates a **context profile**
and starts rebuilding that profile’s FAISS index in the background. The first
request may complete before the profile is ready, so context might not be used
until the next request.

### 8.3 API tests

Test the JSON API:

```bash
curl -X POST "${CLOUD_RUN_URL}/api/v1/translate/simple" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Our premium leather wallets are handcrafted with care.\", \"use_context\": false}"
```

You should receive a JSON response with a `translation` field.

---

## 9. Using context indexing in production

### 9.1 Configure defaults (optional)

In `config_context.yaml`, you can enable context and set initial websites:

```yaml
context_sources:
  enabled: true
  embedding_model: "text-embedding-004"  # for Vertex AI; name is informational here
  chunk_size: 1000
  chunk_overlap: 50
  top_k: 3
  max_context_length: 2000
  websites: []
```

### 9.2 Create reusable context profiles

Create a profile with up to 3 websites:

```bash
curl -X POST "${CLOUD_RUN_URL}/api/v1/context/profiles" \
  -H "Content-Type: application/json" \
  -d '{
        "websites": [
          {"name": "Docs", "url": "https://example.com/docs"},
          {"name": "Blog", "url": "https://example.com/blog"}
        ]
      }'
```

The response contains a `profile_id`.

### 9.3 Rebuild a profile index

```bash
curl -X POST "${CLOUD_RUN_URL}/api/v1/context/profiles/PROFILE_ID/rebuild"
```

This schedules a rebuild in the background.

### 9.4 Check readiness

At the moment, the API exposes general context readiness via:

```bash
curl "${CLOUD_RUN_URL}/api/v1/context/status"
```

For production, remember:

- Profile metadata is process-local in the current implementation.
- FAISS indexes are per-container and in-memory.
- A Cloud Run cold start or a new instance will require profile indexes to be rebuilt on that instance.

### 9.5 Legacy sources endpoint

The older `/api/v1/context/sources` endpoint still creates a profile and
starts a background rebuild, but the preferred flow is:

1. `POST /api/v1/context/profiles`
2. `POST /api/v1/context/profiles/{profile_id}/rebuild`

You can still update the websites used to build the context index via:

```bash
curl -X POST "${CLOUD_RUN_URL}/api/v1/context/sources" \
  -H "Content-Type: application/json" \
  -d '{
        "websites": [
          {"name": "Docs", "url": "https://example.com/docs"},
          {"name": "Blog", "url": "https://example.com/blog"}
        ]
      }'
```

This schedules an index rebuild in the background. Check status:

```bash
curl "${CLOUD_RUN_URL}/api/v1/context/status"
```

You should see `enabled: true`, and once the default index is ready, `ready: true`
with a non-zero `chunk_count`.

You can do the same via the HTML frontend by enabling **Use website context** and providing up to 3 URLs in the form.

---

## 10. Monitoring, logging, and cost control

- **Logs**:  
  Cloud Run logs are available in **Cloud Logging**; filter by the Cloud Run service name.

- **Vertex AI usage**:  
  Use the Vertex AI section of the console to monitor request volumes, latency, and token usage, which directly ties to cost.

- **Scaling**:  
  Tune:
  - `max-instances` (upper bound on concurrent containers)
  - `--concurrency` (requests per container)
  - `--timeout` (max request duration)

  to balance latency and cost.

- **Authentication**:  
  For public demos you can allow unauthenticated access. For production, consider:
  - Requiring IAM-based auth for Cloud Run.
  - Putting an API gateway or Cloud Load Balancer with authentication in front.

This completes the end-to-end setup for running the translation engine on GCP with Cloud Run + Vertex AI.

