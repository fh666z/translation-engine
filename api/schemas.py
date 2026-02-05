"""Pydantic schemas for the Translation Engine API."""

from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str
    use_context: bool = True
    use_reflection: bool = True


class TranslateSimpleRequest(BaseModel):
    text: str
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


class HealthResponse(BaseModel):
    status: str

