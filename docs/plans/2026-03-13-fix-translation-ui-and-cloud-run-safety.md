# Translation UI And Cloud Run Safety Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the new frontend controls actually affect translation output, fix context handling so it is safe and predictable on Cloud Run, and bring the documentation back in sync with the real behavior.

**Architecture:** Introduce request-level translation options that flow from the HTML form and JSON API into prompt generation, then replace the current global mutable website state with explicit context profiles so context sources are isolated per user/workflow instead of shared per container. Keep Cloud Run + Vertex AI as the target deployment model, but document the limits of in-memory FAISS caching and persist profile metadata outside process memory.

**Tech Stack:** FastAPI, Jinja2, Pydantic, dataclasses, FAISS, Crawl4AI, Vertex AI, pytest, httpx / FastAPI TestClient, optional Firestore + Cloud Storage for profile persistence.

---

### Task 1: Add Regression Tests For The Broken Requirements

**Files:**
- Create: `tests/test_frontend.py`
- Create: `tests/test_translation_options.py`
- Create: `tests/test_context_profiles.py`
- Modify: `requirements.txt`

**Step 1: Write the failing frontend test**

```python
def test_frontend_submission_passes_runtime_translation_options(client):
    response = client.post(
        "/translate",
        data={
            "text": "Hello world",
            "source_language": "English",
            "target_language": "German",
            "tone": "Friendly",
            "purpose_of_text": "Marketing",
            "use_reflection": "on",
        },
    )
    assert response.status_code == 200
    assert "English → German" in response.text
```

**Step 2: Write the failing pipeline/options test**

```python
def test_request_overrides_change_prompt_values(fake_llm):
    translator = Translator(llm=fake_llm, config=base_config, prompts=prompts)
    request_options = TranslationOptions(
        source_language="English",
        target_language="German",
        tone="Friendly",
        purpose_of_text="Marketing",
    )
    translator.translate("Hello", context="", options=request_options)
    assert "Friendly" in fake_llm.last_system_prompt
    assert "Marketing" in fake_llm.last_system_prompt
```

**Step 3: Write the failing context-isolation test**

```python
def test_context_profiles_do_not_overwrite_each_other(profile_store, pipeline):
    profile_a = create_profile(["https://a.example"])
    profile_b = create_profile(["https://b.example"])
    assert profile_a.id != profile_b.id
    assert profile_store.get(profile_a.id).websites != profile_store.get(profile_b.id).websites
```

**Step 4: Run tests to verify they fail**

Run: `pytest tests/test_frontend.py tests/test_translation_options.py tests/test_context_profiles.py -q`

Expected: FAIL because runtime translation options and isolated context profiles do not exist yet.

**Step 5: Commit**

```bash
git add requirements.txt tests/test_frontend.py tests/test_translation_options.py tests/test_context_profiles.py
git commit -m "test: add coverage for runtime translation options and context isolation"
```

---

### Task 2: Add Request-Level Translation Options

**Files:**
- Modify: `translation_engine/domain/models.py`
- Modify: `api/schemas.py`
- Modify: `translation_engine/services/translator.py`
- Modify: `translation_engine/services/reflector.py`
- Modify: `translation_engine/services/pipeline.py`

**Step 1: Extend the domain model with explicit options**

```python
@dataclass
class TranslationOptions:
    source_language: str
    target_language: str
    tone: str
    purpose_of_text: str
    target_audience: str | None = None
    auto_detect_source_language: bool = False


@dataclass
class TranslationRequest:
    text: str
    use_context: bool = True
    use_reflection: bool = True
    options: TranslationOptions | None = None
```

**Step 2: Add API schema fields**

```python
class TranslateRequest(BaseModel):
    text: str
    source_language: str | None = None
    target_language: str | None = None
    tone: str | None = None
    purpose_of_text: str | None = None
    auto_detect_source_language: bool = False
    use_context: bool = True
    use_reflection: bool = True
```

**Step 3: Make `Translator` build prompts from request overrides**

```python
def _effective_config(self, options: TranslationOptions | None) -> TranslationConfig:
    # return a copy of self.config with request-level overrides applied
```

**Step 4: Make `Reflector` use the same effective options**

```python
def reflect(self, original: str, translation: str, options: TranslationOptions | None = None) -> ReflectionResult:
    ...
```

**Step 5: Thread options through `TranslationPipeline.execute()`**

```python
initial_translation = self.translator.translate(request.text, context, request.options)
reflection_result = self.reflector.reflect(request.text, initial_translation, request.options)
```

**Step 6: Run targeted tests**

Run: `pytest tests/test_translation_options.py -q`

Expected: PASS

**Step 7: Commit**

```bash
git add translation_engine/domain/models.py api/schemas.py translation_engine/services/translator.py translation_engine/services/reflector.py translation_engine/services/pipeline.py
git commit -m "feat: support runtime translation option overrides"
```

---

### Task 3: Wire Frontend And JSON API To The New Runtime Options

**Files:**
- Modify: `api/routes_translation.py`
- Modify: `api/routes_frontend.py`
- Modify: `templates/index.html`

**Step 1: Pass runtime options from JSON API**

```python
request = DomainTranslationRequest(
    text=payload.text,
    use_context=payload.use_context,
    use_reflection=payload.use_reflection,
    options=TranslationOptions(
        source_language=payload.source_language or defaults.source_language,
        target_language=payload.target_language or defaults.target_language,
        tone=payload.tone or defaults.tone,
        purpose_of_text=payload.purpose_of_text or defaults.purpose_of_text,
        auto_detect_source_language=payload.auto_detect_source_language,
    ),
)
```

**Step 2: Pass runtime options from the HTML form**

```python
options = TranslationOptions(
    source_language=source_language,
    target_language=target_language,
    tone=tone,
    purpose_of_text=purpose_of_text,
    auto_detect_source_language=(source_language == "auto"),
)
```

**Step 3: Fix the result view to show submitted values**

```html
{{ form.source_language if form else defaults.source_language }} →
{{ form.target_language if form else defaults.target_language }}
```

**Step 4: Replace free-text source language with explicit auto-detect affordance**

```html
<select id="source_language" name="source_language">
  <option value="auto">Auto-detect</option>
  ...
</select>
```

**Step 5: Run frontend tests**

Run: `pytest tests/test_frontend.py -q`

Expected: PASS

**Step 6: Commit**

```bash
git add api/routes_translation.py api/routes_frontend.py templates/index.html
git commit -m "feat: connect frontend and API inputs to translation prompts"
```

---

### Task 4: Replace Global Website State With Context Profiles

**Files:**
- Create: `translation_engine/context_profiles.py`
- Modify: `translation_engine/providers/context.py`
- Modify: `translation_engine/domain/models.py`
- Modify: `api/schemas.py`
- Modify: `api/routes_context.py`
- Modify: `api/routes_frontend.py`
- Modify: `translation_engine/engine.py`

**Step 1: Introduce a context profile model**

```python
@dataclass
class ContextProfile:
    id: str
    websites: list[dict]
    updated_at: datetime
```

**Step 2: Add a store abstraction**

```python
class ContextProfileStore(Protocol):
    def save(self, profile: ContextProfile) -> None: ...
    def get(self, profile_id: str) -> ContextProfile | None: ...
```

**Step 3: Implement a minimal store**

```python
class InMemoryContextProfileStore:
    ...
```

**Step 4: Change FAISS usage from “single mutable website list” to “cache by profile id”**

```python
def build_index(self, profile: ContextProfile, force: bool = False) -> bool:
    # maintain indexes keyed by profile.id instead of one global _index
```

**Step 5: Update the API to create/update profiles explicitly**

```python
@router.post("/profiles")
def create_context_profile(...):
    ...

@router.post("/profiles/{profile_id}/rebuild")
def rebuild_profile(...):
    ...
```

**Step 6: Update the frontend to use a profile id**

```python
# create/reuse a profile for the submitted websites and pass profile_id into TranslationRequest
```

**Step 7: Run isolation tests**

Run: `pytest tests/test_context_profiles.py -q`

Expected: PASS

**Step 8: Commit**

```bash
git add translation_engine/context_profiles.py translation_engine/providers/context.py translation_engine/domain/models.py api/schemas.py api/routes_context.py api/routes_frontend.py translation_engine/engine.py
git commit -m "feat: isolate website context by profile instead of global state"
```

---

### Task 5: Make Context Rebuilds Safe For Cloud Run

**Files:**
- Modify: `api/routes_frontend.py`
- Modify: `api/routes_context.py`
- Modify: `translation_engine/services/pipeline.py`
- Modify: `architecture.md`
- Modify: `setup_gcp.md`

**Step 1: Remove synchronous rebuilds from `/translate`**

```python
# frontend route should submit or attach a context profile id, not crawl during translation
```

**Step 2: Add explicit asynchronous rebuild workflow**

```python
@router.post("/profiles/{profile_id}/rebuild")
def rebuild_context_profile(background_tasks: BackgroundTasks, ...):
    ...
```

**Step 3: Make translation behavior explicit when a profile is not ready**

```python
if request.use_context and request.context_profile_id and not self.context_provider.is_ready(request.context_profile_id):
    # either fail fast with 409/422 or continue without context based on policy
```

**Step 4: Document the production trade-off**

```markdown
Cloud Run instances may cold start with empty in-memory caches; persisted profile metadata is durable, while FAISS indexes are rebuilt lazily per instance.
```

**Step 5: Run tests**

Run: `pytest tests/test_frontend.py tests/test_context_profiles.py -q`

Expected: PASS

**Step 6: Commit**

```bash
git add api/routes_frontend.py api/routes_context.py translation_engine/services/pipeline.py architecture.md setup_gcp.md
git commit -m "fix: decouple context rebuilding from translation requests"
```

---

### Task 6: Harden Vertex AI Provider Behavior

**Files:**
- Modify: `translation_engine/providers/vertex_ai.py`
- Create: `tests/test_vertex_ai_provider.py`

**Step 1: Add a failing provider test**

```python
def test_vertex_provider_handles_empty_text_response(mock_model):
    ...
```

**Step 2: Preserve structured prompts and add generation config**

```python
response = self._model.generate_content(
    prompt,
    generation_config={"temperature": 0.2},
)
```

**Step 3: Add defensive error handling**

```python
try:
    response = self._model.generate_content(prompt)
except Exception as exc:
    raise RuntimeError(f"Vertex AI generation failed: {exc}") from exc
```

**Step 4: Validate streamed chunks and empty responses**

```python
text = getattr(response, "text", "") or ""
if not text:
    raise RuntimeError("Vertex AI returned an empty response")
```

**Step 5: Run tests**

Run: `pytest tests/test_vertex_ai_provider.py -q`

Expected: PASS

**Step 6: Commit**

```bash
git add translation_engine/providers/vertex_ai.py tests/test_vertex_ai_provider.py
git commit -m "fix: harden vertex ai provider error handling"
```

---

### Task 7: Bring Documentation Back In Sync With Real Behavior

**Files:**
- Modify: `README.md`
- Modify: `setup_gcp.md`
- Modify: `architecture.md`
- Modify: `config_reference.md`

**Step 1: Update docs to describe real runtime overrides**

```markdown
The frontend and JSON API can override source language, target language, tone, and purpose per request.
```

**Step 2: Update docs to describe context profiles instead of one shared website list**

```markdown
Context websites are stored in named or generated profiles and rebuilt asynchronously.
```

**Step 3: Document the auto-detect behavior**

```markdown
Selecting `Auto-detect` sets `auto_detect_source_language=true`, which changes the translation prompt behavior.
```

**Step 4: Run a doc sanity pass**

Run: `rg "set_websites|global state|instance" README.md setup_gcp.md architecture.md config_reference.md`

Expected: No stale references to the old behavior.

**Step 5: Commit**

```bash
git add README.md setup_gcp.md architecture.md config_reference.md
git commit -m "docs: align docs with runtime translation and context behavior"
```

---

### Task 8: End-To-End Verification

**Files:**
- Test: `tests/test_frontend.py`
- Test: `tests/test_translation_options.py`
- Test: `tests/test_context_profiles.py`
- Test: `tests/test_vertex_ai_provider.py`

**Step 1: Run the focused test suite**

Run: `pytest tests/test_frontend.py tests/test_translation_options.py tests/test_context_profiles.py tests/test_vertex_ai_provider.py -q`

Expected: PASS

**Step 2: Run app smoke tests locally**

Run:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

**Step 3: Verify a manual UI flow**

1. Open `http://127.0.0.1:8000/`
2. Submit a translation with custom source/target language and tone
3. Confirm the result badge and output reflect the submitted values
4. Create two different context profiles and confirm they do not overwrite each other

**Step 4: Commit**

```bash
git add .
git commit -m "test: verify translation UI and cloud run safety fixes"
```

