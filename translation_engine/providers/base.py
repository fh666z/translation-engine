"""
Abstract base classes for provider interfaces.

These interfaces define contracts that concrete implementations must follow,
enabling dependency injection and easy swapping of implementations.
"""

from abc import ABC, abstractmethod
from typing import Iterator


class LLMProvider(ABC):
    """
    Abstract interface for Large Language Model providers.
    
    Implementations can wrap different LLM backends (Ollama, OpenAI, Anthropic, etc.)
    while providing a consistent interface.
    """
    
    @abstractmethod
    def generate(self, messages: list[dict]) -> str:
        """
        Generate a response from a list of messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Roles are typically 'system', 'user', 'assistant'.
        
        Returns:
            The generated response text.
        """
        pass
    
    @abstractmethod
    def stream(self, messages: list[dict]) -> Iterator[str]:
        """
        Stream response chunks from a list of messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
        
        Yields:
            String chunks of the response as they are generated.
        """
        pass


class EmbeddingProvider(ABC):
    """
    Abstract interface for embedding providers.
    
    Implementations can wrap different embedding backends (Ollama, OpenAI, etc.)
    while providing a consistent interface for vector operations.
    """
    
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            texts: List of text strings to embed.
        
        Returns:
            List of embedding vectors (each is a list of floats).
        """
        pass
    
    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """
        Generate embedding for a single query text.
        
        Args:
            text: The query text to embed.
        
        Returns:
            Embedding vector as a list of floats.
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            The number of dimensions in embedding vectors.
        """
        pass


class ContextProvider(ABC):
    """
    Abstract interface for context providers.
    
    Implementations can use different backends (FAISS, Pinecone, ChromaDB, etc.)
    for storing and retrieving contextual information.
    """
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if context retrieval is enabled.
        
        Returns:
            True if context is enabled in configuration.
        """
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """
        Check if the context index is built and ready for queries.
        
        Returns:
            True if context is available for retrieval.
        """
        pass
    
    @abstractmethod
    def build_index(self, force: bool = False) -> bool:
        """
        Build the context index from configured sources.
        
        Args:
            force: If True, rebuild even if already built.
        
        Returns:
            True if index was built successfully.
        """
        pass
    
    @abstractmethod
    def get_context(self, text: str) -> str:
        """
        Get relevant context for a given text.
        
        Args:
            text: The text to find context for.
        
        Returns:
            Formatted context string, or empty string if not available.
        """
        pass
    
    @abstractmethod
    def search(self, query: str, k: int = None) -> list[dict]:
        """
        Search for similar content in the index.
        
        Args:
            query: The search query.
            k: Number of results to return.
        
        Returns:
            List of result dicts with 'chunk', 'source', and 'distance' keys.
        """
        pass

