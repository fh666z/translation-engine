import sys
import types


def _ensure_module(name: str, module: types.ModuleType) -> None:
    if name not in sys.modules:
        sys.modules[name] = module


# Stub optional native / cloud dependencies so unit tests can import modules
# without requiring the full runtime stack.
faiss_module = types.ModuleType("faiss")


class _FakeIndexFlatL2:
    def __init__(self, dim: int):
        self.dim = dim

    def add(self, vectors):
        self.vectors = vectors

    def search(self, query_array, k):
        return [[0.0] * k], [[0] * k]


faiss_module.IndexFlatL2 = _FakeIndexFlatL2
_ensure_module("faiss", faiss_module)

crawl4ai_module = types.ModuleType("crawl4ai")


class _FakeAsyncWebCrawler:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def arun(self, url: str):
        return types.SimpleNamespace(success=True, markdown="stub content", error_message="")


crawl4ai_module.AsyncWebCrawler = _FakeAsyncWebCrawler
_ensure_module("crawl4ai", crawl4ai_module)

google_module = types.ModuleType("google")
google_cloud_module = types.ModuleType("google.cloud")
google_aiplatform_module = types.ModuleType("google.cloud.aiplatform")
google_aiplatform_module.init = lambda *args, **kwargs: None
_ensure_module("google", google_module)
_ensure_module("google.cloud", google_cloud_module)
_ensure_module("google.cloud.aiplatform", google_aiplatform_module)

vertexai_module = types.ModuleType("vertexai")
vertexai_module.init = lambda *args, **kwargs: None
vertexai_generative_module = types.ModuleType("vertexai.generative_models")
vertexai_language_module = types.ModuleType("vertexai.language_models")


class _FakeGenerativeModel:
    def __init__(self, model_id: str):
        self.model_id = model_id

    def generate_content(self, prompt, stream: bool = False):
        if stream:
            return [types.SimpleNamespace(text="stub")]
        return types.SimpleNamespace(text="stub")


class _FakeTextEmbeddingModel:
    @classmethod
    def from_pretrained(cls, model_id: str):
        return cls()

    def get_embeddings(self, texts):
        return [types.SimpleNamespace(values=[0.1, 0.2, 0.3]) for _ in texts]


vertexai_generative_module.GenerativeModel = _FakeGenerativeModel
vertexai_language_module.TextEmbeddingModel = _FakeTextEmbeddingModel
_ensure_module("vertexai", vertexai_module)
_ensure_module("vertexai.generative_models", vertexai_generative_module)
_ensure_module("vertexai.language_models", vertexai_language_module)

langchain_ollama_module = types.ModuleType("langchain_ollama")


class _FakeChatOllama:
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, messages):
        return types.SimpleNamespace(content="stub")

    def stream(self, messages):
        return [types.SimpleNamespace(content="stub")]


class _FakeOllamaEmbeddings:
    def __init__(self, *args, **kwargs):
        pass

    def embed_documents(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    def embed_query(self, text):
        return [0.1, 0.2, 0.3]


langchain_ollama_module.ChatOllama = _FakeChatOllama
langchain_ollama_module.OllamaEmbeddings = _FakeOllamaEmbeddings
_ensure_module("langchain_ollama", langchain_ollama_module)

langchain_core_module = types.ModuleType("langchain_core")
langchain_core_messages_module = types.ModuleType("langchain_core.messages")


class _FakeMessage:
    def __init__(self, content):
        self.content = content


langchain_core_messages_module.AIMessage = _FakeMessage
langchain_core_messages_module.HumanMessage = _FakeMessage
langchain_core_messages_module.SystemMessage = _FakeMessage
_ensure_module("langchain_core", langchain_core_module)
_ensure_module("langchain_core.messages", langchain_core_messages_module)

