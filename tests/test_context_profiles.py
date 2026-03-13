from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes_context import router as context_router


class FakePipeline:
    @property
    def context_enabled(self) -> bool:
        return True

    @property
    def context_ready(self) -> bool:
        return False

    def initialize_context(self, force: bool = False) -> bool:
        return True


class FakeContextProvider:
    chunk_count = 0

    def set_websites(self, websites):
        self.websites = websites


@dataclass
class FakeEngine:
    pipeline: FakePipeline
    context_provider: FakeContextProvider


def create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(context_router)
    app.state.engine = FakeEngine(
        pipeline=FakePipeline(),
        context_provider=FakeContextProvider(),
    )
    return TestClient(app)


def test_context_profiles_can_be_created_without_overwriting_existing_profiles():
    client = create_test_client()

    response_one = client.post(
        "/api/v1/context/profiles",
        json={"websites": [{"url": "https://example.com/a"}]},
    )
    response_two = client.post(
        "/api/v1/context/profiles",
        json={"websites": [{"url": "https://example.com/b"}]},
    )

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    assert response_one.json()["profile_id"] != response_two.json()["profile_id"]

