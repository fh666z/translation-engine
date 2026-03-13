"""Pydantic schemas for the Translation Engine API."""

from pydantic import BaseModel, HttpUrl


class TranslateRequest(BaseModel):
    text: str
    source_language: str | None = None
    target_language: str | None = None
    tone: str | None = None
    purpose_of_text: str | None = None
    auto_detect_source_language: bool = False
    use_context: bool = True
    use_reflection: bool = True


class TranslateSimpleRequest(BaseModel):
    text: str
    source_language: str | None = None
    target_language: str | None = None
    tone: str | None = None
    purpose_of_text: str | None = None
    auto_detect_source_language: bool = False
    use_context: bool = True


class TranslateResponse(BaseModel):
    source_text: str
    initial_translation: str
    reflection: str | None = None
    final_translation: str
    refinement_skipped: bool
    context_used: bool


class TranslateSimpleResponse(BaseModel):
    translation: str
    context_used: bool


class ContextStatusResponse(BaseModel):
    enabled: bool
    ready: bool
    chunk_count: int | None = None


class ContextWebsite(BaseModel):
    name: str | None = None
    url: HttpUrl
    description: str | None = None


class UpdateContextSourcesRequest(BaseModel):
    websites: list[ContextWebsite]


class ContextProfileResponse(BaseModel):
    profile_id: str
    ready: bool = False
    chunk_count: int | None = None


class HealthResponse(BaseModel):
    status: str

