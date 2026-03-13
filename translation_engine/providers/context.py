"""
FAISS-based context provider for context-aware translation.

Builds an in-memory FAISS index from website content using Crawl4AI
for fetching and the embedding provider for vectorization.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

import faiss
import numpy as np
from crawl4ai import AsyncWebCrawler

from translation_engine.config.models import ContextConfig
from translation_engine.providers.base import ContextProvider, EmbeddingProvider


logger = logging.getLogger(__name__)

DEFAULT_PROFILE_ID = "__default__"


@dataclass
class ProfileIndexState:
    """In-memory FAISS index state for a specific context profile."""

    websites: list[dict] = field(default_factory=list)
    index: Optional[faiss.IndexFlatL2] = None
    chunks: list[str] = field(default_factory=list)
    chunk_sources: list[dict] = field(default_factory=list)
    is_built: bool = False
    embedding_dim: Optional[int] = None


class FAISSContextProvider(ContextProvider):
    """
    FAISS-based implementation of the ContextProvider interface.
    
    Uses Crawl4AI to fetch website content and builds an in-memory
    FAISS index for fast similarity search. The index is built on
    first use and discarded when the application exits.
    """
    
    def __init__(
        self,
        config: ContextConfig,
        embedding_provider: EmbeddingProvider,
    ):
        """
        Initialize the FAISS context provider.
        
        Args:
            config: Context configuration with websites, chunk settings, etc.
            embedding_provider: Provider for generating embeddings.
        """
        self.config = config
        self.embeddings = embedding_provider
        self._profiles: dict[str, ProfileIndexState] = {
            DEFAULT_PROFILE_ID: ProfileIndexState(websites=list(config.websites))
        }

    def _get_profile_state(self, profile_id: str = DEFAULT_PROFILE_ID) -> ProfileIndexState:
        return self._profiles.setdefault(profile_id, ProfileIndexState())
    
    def is_enabled(self) -> bool:
        """Check if context is enabled in configuration."""
        return self.config.enabled
    
    def is_ready(self) -> bool:
        """Check if the index has been built and is ready for queries."""
        return self.is_profile_ready(DEFAULT_PROFILE_ID)

    def is_profile_ready(self, profile_id: str) -> bool:
        """Check if a specific profile index is built and ready."""
        state = self._get_profile_state(profile_id)
        return state.is_built and state.index is not None
    
    @property
    def chunk_count(self) -> int:
        """Get the number of chunks in the index."""
        return self.get_profile_chunk_count(DEFAULT_PROFILE_ID)

    def get_profile_chunk_count(self, profile_id: str) -> int:
        """Get the number of chunks for a specific profile."""
        return len(self._get_profile_state(profile_id).chunks)
    
    async def _fetch_website(self, url: str) -> str:
        """
        Fetch a website and return clean markdown content.
        
        Args:
            url: The URL to fetch.
        
        Returns:
            Clean markdown content from the website.
        """
        logger.info(f"Fetching website: {url}")
        
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                
                if result.success:
                    logger.info(f"Successfully fetched {url} ({len(result.markdown)} chars)")
                    return result.markdown
                else:
                    logger.warning(f"Failed to fetch {url}: {result.error_message}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""
    
    def _chunk_text(self, text: str, source_info: dict) -> list[tuple[str, dict]]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: The text to chunk.
            source_info: Metadata about the source (name, url, description).
        
        Returns:
            List of (chunk_text, source_info) tuples.
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at a sentence or word boundary
            if end < len(text):
                last_period = chunk.rfind(". ")
                last_newline = chunk.rfind("\n")
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size // 2:
                    chunk = chunk[: break_point + 1]
                    end = start + break_point + 1
            
            chunk = chunk.strip()
            if chunk:
                chunks.append((chunk, source_info))
            
            # Move start with overlap
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    async def _build_index_async(
        self,
        force: bool = False,
        profile_id: str = DEFAULT_PROFILE_ID,
        websites: Optional[list[dict]] = None,
    ) -> bool:
        """
        Build the FAISS index from configured websites (async).
        
        Args:
            force: If True, rebuild even if already built.
        
        Returns:
            True if index was built successfully.
        """
        if not self.config.enabled:
            logger.info("Context sources are disabled in config")
            return False
        
        state = self._get_profile_state(profile_id)
        if websites is not None:
            state.websites = websites

        if state.is_built and not force:
            logger.info("Index already built, skipping")
            return True
        
        if not state.websites:
            logger.warning("No websites configured in context_sources")
            return False
        
        logger.info("Building context index from %d websites for profile %s...", len(state.websites), profile_id)
        
        # Fetch all websites and chunk content
        all_chunks = []
        
        for site in state.websites:
            url = site.get("url", "")
            name = site.get("name", url)
            description = site.get("description", "")
            
            if not url:
                continue
            
            source_info = {
                "name": name,
                "url": url,
                "description": description,
            }
            
            content = await self._fetch_website(url)
            if content:
                chunks = self._chunk_text(content, source_info)
                all_chunks.extend(chunks)
                logger.info(f"  - {name}: {len(chunks)} chunks")
        
        if not all_chunks:
            logger.warning("No content fetched from any website")
            return False
        
        # Separate chunks and their sources
        state.chunks = [chunk for chunk, _ in all_chunks]
        state.chunk_sources = [source for _, source in all_chunks]
        
        logger.info("Generating embeddings for %d chunks...", len(state.chunks))
        
        # Generate embeddings
        vectors = self.embeddings.embed_documents(state.chunks)
        embeddings_array = np.array(vectors, dtype=np.float32)
        state.embedding_dim = embeddings_array.shape[1]
        
        # Build FAISS index
        state.index = faiss.IndexFlatL2(state.embedding_dim)
        state.index.add(embeddings_array)
        
        state.is_built = True
        logger.info(
            "Context index built successfully for profile %s (%d chunks, dim=%d)",
            profile_id,
            len(state.chunks),
            state.embedding_dim,
        )
        
        return True
    
    def build_index(self, force: bool = False) -> bool:
        """
        Build the FAISS index from configured websites (sync wrapper).
        
        Args:
            force: If True, rebuild even if already built.
        
        Returns:
            True if index was built successfully.
        """
        return asyncio.run(self._build_index_async(force))

    def build_profile_index(
        self,
        profile_id: str,
        websites: list[dict],
        force: bool = False,
    ) -> bool:
        """Build or rebuild the index for a specific context profile."""
        return asyncio.run(
            self._build_index_async(
                force=force,
                profile_id=profile_id,
                websites=websites,
            )
        )
    
    def search(self, query: str, k: Optional[int] = None) -> list[dict]:
        """
        Search the index for chunks similar to the query.
        
        Args:
            query: The search query.
            k: Number of results to return (defaults to config top_k).
        
        Returns:
            List of dicts with 'chunk', 'source', and 'distance' keys.
        """
        return self.search_profile(DEFAULT_PROFILE_ID, query, k)

    def search_profile(
        self,
        profile_id: str,
        query: str,
        k: Optional[int] = None,
    ) -> list[dict]:
        """Search the FAISS index for a specific profile."""
        state = self._get_profile_state(profile_id)
        if not self.is_profile_ready(profile_id):
            return []

        k = k or self.config.top_k
        k = min(k, len(state.chunks))

        query_vector = self.embeddings.embed_query(query)
        query_array = np.array([query_vector], dtype=np.float32)
        distances, indices = state.index.search(query_array, k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(state.chunks):
                results.append(
                    {
                        "chunk": state.chunks[idx],
                        "source": state.chunk_sources[idx],
                        "distance": float(distances[0][i]),
                    }
                )
        return results
    
    def get_context(self, text: str) -> str:
        """
        Get relevant context for a translation task.
        
        Args:
            text: The source text to find context for.
        
        Returns:
            Formatted context string to include in the prompt.
        """
        return self.get_profile_context(DEFAULT_PROFILE_ID, text)

    def get_profile_context(self, profile_id: str, text: str) -> str:
        """Get formatted context for a specific profile."""
        if not self.is_profile_ready(profile_id):
            return ""

        results = self.search_profile(profile_id, text)
        if not results:
            return ""

        context_parts = []
        total_length = 0

        for result in results:
            chunk = result["chunk"]
            source = result["source"]
            entry = f"[From: {source['name']}]\n{chunk}"
            if total_length + len(entry) > self.config.max_context_length:
                break

            context_parts.append(entry)
            total_length += len(entry) + 2

        return "\n\n".join(context_parts)


