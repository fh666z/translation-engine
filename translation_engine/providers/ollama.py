"""
Ollama-based implementations of LLM and Embedding providers.

Uses LangChain's Ollama integration for local LLM inference.
"""

from typing import Iterator, Optional

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from translation_engine.config.models import OllamaConfig
from translation_engine.providers.base import EmbeddingProvider, LLMProvider


class OllamaLLMProvider(LLMProvider):
    """
    Ollama-based LLM provider using LangChain.
    
    Wraps ChatOllama to provide a consistent interface for text generation.
    """
    
    def __init__(self, config: OllamaConfig):
        """
        Initialize the Ollama LLM provider.
        
        Args:
            config: Ollama configuration with model, base_url, temperature, etc.
        """
        self.config = config
        self._client = ChatOllama(
            model=config.model,
            base_url=config.base_url,
            temperature=config.temperature,
            streaming=config.streaming,
        )
        # Non-streaming client for generate()
        self._client_sync = ChatOllama(
            model=config.model,
            base_url=config.base_url,
            temperature=config.temperature,
            streaming=False,
        )
    
    def _convert_messages(self, messages: list[dict]) -> list:
        """Convert dict messages to LangChain message objects."""
        converted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                converted.append(SystemMessage(content=content))
            elif role == "assistant":
                converted.append(AIMessage(content=content))
            else:  # "user" or default
                converted.append(HumanMessage(content=content))
        
        return converted
    
    def generate(self, messages: list[dict]) -> str:
        """
        Generate a response from messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
        
        Returns:
            The generated response text.
        """
        langchain_messages = self._convert_messages(messages)
        response = self._client_sync.invoke(langchain_messages)
        return response.content
    
    def stream(self, messages: list[dict]) -> Iterator[str]:
        """
        Stream response chunks from messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
        
        Yields:
            String chunks of the response.
        """
        langchain_messages = self._convert_messages(messages)
        for chunk in self._client.stream(langchain_messages):
            yield chunk.content


class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Ollama-based embedding provider using LangChain.
    
    Wraps OllamaEmbeddings to provide a consistent interface for vector operations.
    """
    
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
    ):
        """
        Initialize the Ollama embedding provider.
        
        Args:
            model: Name of the embedding model (e.g., 'nomic-embed-text').
            base_url: Ollama server URL.
        """
        self.model = model
        self.base_url = base_url
        self._embeddings = OllamaEmbeddings(
            model=model,
            base_url=base_url,
        )
        self._dimension: Optional[int] = None
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            texts: List of text strings to embed.
        
        Returns:
            List of embedding vectors.
        """
        vectors = self._embeddings.embed_documents(texts)
        
        # Cache dimension from first embedding
        if vectors and self._dimension is None:
            self._dimension = len(vectors[0])
        
        return vectors
    
    def embed_query(self, text: str) -> list[float]:
        """
        Generate embedding for a single query.
        
        Args:
            text: The query text to embed.
        
        Returns:
            Embedding vector as a list of floats.
        """
        vector = self._embeddings.embed_query(text)
        
        # Cache dimension from first embedding
        if self._dimension is None:
            self._dimension = len(vector)
        
        return vector
    
    @property
    def dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Note: This requires at least one embedding to have been generated,
        or it will generate a test embedding to determine the dimension.
        
        Returns:
            The number of dimensions in embedding vectors.
        """
        if self._dimension is None:
            # Generate a test embedding to get dimension
            test_vector = self.embed_query("test")
            self._dimension = len(test_vector)
        return self._dimension

