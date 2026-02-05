"""
FAISS-based context provider for context-aware translation.

Builds an in-memory FAISS index from website content using Crawl4AI
for fetching and the embedding provider for vectorization.
"""

import asyncio
import logging
from typing import Optional

import faiss
import numpy as np
from crawl4ai import AsyncWebCrawler

from translation_engine.config.models import ContextConfig
from translation_engine.providers.base import ContextProvider, EmbeddingProvider


logger = logging.getLogger(__name__)


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
        
        # Index state
        self._index: Optional[faiss.IndexFlatL2] = None
        self._chunks: list[str] = []
        self._chunk_sources: list[dict] = []
        self._is_built = False
        self._embedding_dim: Optional[int] = None
    
    def is_enabled(self) -> bool:
        """Check if context is enabled in configuration."""
        return self.config.enabled
    
    def is_ready(self) -> bool:
        """Check if the index has been built and is ready for queries."""
        return self._is_built and self._index is not None
    
    @property
    def chunk_count(self) -> int:
        """Get the number of chunks in the index."""
        return len(self._chunks)
    
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
    
    async def _build_index_async(self, force: bool = False) -> bool:
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
        
        if self._is_built and not force:
            logger.info("Index already built, skipping")
            return True
        
        websites = self.config.websites
        if not websites:
            logger.warning("No websites configured in context_sources")
            return False
        
        logger.info(f"Building context index from {len(websites)} websites...")
        
        # Fetch all websites and chunk content
        all_chunks = []
        
        for site in websites:
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
        self._chunks = [chunk for chunk, _ in all_chunks]
        self._chunk_sources = [source for _, source in all_chunks]
        
        logger.info(f"Generating embeddings for {len(self._chunks)} chunks...")
        
        # Generate embeddings
        vectors = self.embeddings.embed_documents(self._chunks)
        embeddings_array = np.array(vectors, dtype=np.float32)
        self._embedding_dim = embeddings_array.shape[1]
        
        # Build FAISS index
        self._index = faiss.IndexFlatL2(self._embedding_dim)
        self._index.add(embeddings_array)
        
        self._is_built = True
        logger.info(
            "Context index built successfully (%d chunks, dim=%d)",
            len(self._chunks),
            self._embedding_dim,
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
    
    def search(self, query: str, k: Optional[int] = None) -> list[dict]:
        """
        Search the index for chunks similar to the query.
        
        Args:
            query: The search query.
            k: Number of results to return (defaults to config top_k).
        
        Returns:
            List of dicts with 'chunk', 'source', and 'distance' keys.
        """
        if not self.is_ready():
            return []
        
        k = k or self.config.top_k
        k = min(k, len(self._chunks))  # Don't request more than we have
        
        # Embed the query
        query_vector = self.embeddings.embed_query(query)
        query_array = np.array([query_vector], dtype=np.float32)
        
        # Search the index
        distances, indices = self._index.search(query_array, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self._chunks):
                results.append(
                    {
                        "chunk": self._chunks[idx],
                        "source": self._chunk_sources[idx],
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
        if not self.is_ready():
            return ""
        
        results = self.search(text)
        
        if not results:
            return ""
        
        # Format results as context
        context_parts = []
        total_length = 0
        
        for result in results:
            chunk = result["chunk"]
            source = result["source"]
            
            # Check if adding this chunk would exceed the limit
            entry = f"[From: {source['name']}]\n{chunk}"
            if total_length + len(entry) > self.config.max_context_length:
                break
            
            context_parts.append(entry)
            total_length += len(entry) + 2  # +2 for separator
        
        return "\n\n".join(context_parts)

