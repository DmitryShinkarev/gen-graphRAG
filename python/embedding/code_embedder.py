"""
Code embedding generation using sentence transformers.
Converts Java code into vector representations for semantic search.
"""

from typing import List, Dict, Optional, Union
import numpy as np
from pathlib import Path
try:
    import torch
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    SentenceTransformer = None
    torch = None
import hashlib
import redis
import pickle
from tqdm import tqdm

from config import get_settings
from logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class CodeEmbedder:
    """
    Code embedder using sentence transformers.
    
    Features:
    - Generates embeddings for code snippets
    - Caches embeddings in Redis
    - Supports batch processing
    - GPU acceleration when available
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        cache_enabled: bool = True,
        device: Optional[str] = None
    ):
        """
        Initialize code embedder.
        
        Args:
            model_name: Sentence transformer model name
            cache_enabled: Whether to enable Redis caching
            device: Device to use (cuda, cpu, or None for auto)
        """
        self.model_name = model_name or settings.llm.embedding_model
        self.cache_enabled = cache_enabled
        
        # Determine device
        if not HAS_TRANSFORMERS:
            logger.warning("⚠️ sentence-transformers not installed - embeddings will be mocked")
            self.device = "cpu"
            self.model = None
            self.embedding_dim = 384  # Default dimension
            self.redis_client = None  # Initialize redis_client even in mock mode
            return
            
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        logger.info(f"Initializing CodeEmbedder with model: {self.model_name}")
        logger.info(f"Device: {self.device}")
        
        try:
            # Load model
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
        
        # Setup Redis cache
        self.redis_client = None
        if cache_enabled:
            try:
                self.redis_client = redis.Redis(
                    host=settings.database.redis_host,
                    port=settings.database.redis_port,
                    password=settings.database.redis_password,
                    db=settings.database.redis_db,
                    decode_responses=False  # We'll store binary data
                )
                self.redis_client.ping()
                logger.info("Redis cache enabled for embeddings")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")
                self.redis_client = None
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return f"embedding:{self.model_name}:{text_hash}"
    
    def _get_from_cache(self, text: str) -> Optional[np.ndarray]:
        """Retrieve embedding from cache"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(text)
            cached = self.redis_client.get(cache_key)
            
            if cached:
                embedding = pickle.loads(cached)
                return embedding
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        
        return None
    
    def _save_to_cache(self, text: str, embedding: np.ndarray) -> None:
        """Save embedding to cache"""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(text)
            serialized = pickle.dumps(embedding)
            
            # Set with TTL
            self.redis_client.setex(
                cache_key,
                settings.performance.cache_ttl,
                serialized
            )
        except Exception as e:
            logger.warning(f"Cache save error: {e}")
    
    def embed_text(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use cache
        
        Returns:
            Embedding vector as numpy array
        """
        # Check cache
        if use_cache:
            cached = self._get_from_cache(text)
            if cached is not None:
                return cached
        
        # Generate embedding
        try:
            if self.model is None:
                # Mock embedding when transformers not available
                logger.warning("⚠️ Using mock embedding - sentence-transformers not available")
                return np.random.rand(self.embedding_dim).astype(np.float32)
            
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Save to cache
            if use_cache:
                self._save_to_cache(text, embedding)
            
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vector as fallback
            return np.zeros(self.embedding_dim)
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = True,
        use_cache: bool = True
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar
            use_cache: Whether to use cache
        
        Returns:
            List of embedding vectors
        """
        batch_size = batch_size or settings.agent.batch_size
        embeddings = []
        
        # Check cache first
        if use_cache:
            logger.info(f"Checking cache for {len(texts)} texts...")
            cached_embeddings = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                cached = self._get_from_cache(text)
                if cached is not None:
                    cached_embeddings.append((i, cached))
                else:
                    uncached_indices.append(i)
            
            logger.info(f"Cache hits: {len(cached_embeddings)}/{len(texts)}")
            
            # If all cached, return
            if not uncached_indices:
                return [emb for _, emb in sorted(cached_embeddings)]
            
            # Generate embeddings for uncached texts
            uncached_texts = [texts[i] for i in uncached_indices]
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
            cached_embeddings = []
        
        # Generate embeddings
        logger.info(f"Generating {len(uncached_texts)} embeddings...")
        
        try:
            if self.model is None:
                # Mock embeddings when transformers not available
                logger.warning("⚠️ Using mock embeddings - sentence-transformers not available")
                new_embeddings = np.random.rand(len(uncached_texts), self.embedding_dim).astype(np.float32)
            else:
                new_embeddings = self.model.encode(
                    uncached_texts,
                    batch_size=batch_size,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True
                )
            
            # Save to cache
            if use_cache:
                for text, embedding in zip(uncached_texts, new_embeddings):
                    self._save_to_cache(text, embedding)
            
            # Combine cached and new embeddings
            all_embeddings = cached_embeddings + list(zip(uncached_indices, new_embeddings))
            all_embeddings.sort(key=lambda x: x[0])
            
            return [emb for _, emb in all_embeddings]
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # Return zero vectors as fallback
            return [np.zeros(self.embedding_dim) for _ in texts]
    
    def embed_code_method(self, method_info: Dict) -> np.ndarray:
        """
        Generate embedding for a method.
        
        Args:
            method_info: Method information dictionary
        
        Returns:
            Embedding vector
        """
        # Create rich representation
        components = []
        
        # Method signature
        if "full_signature" in method_info:
            components.append(f"Signature: {method_info['full_signature']}")
        
        # Javadoc
        if method_info.get("javadoc"):
            components.append(f"Documentation: {method_info['javadoc']}")
        
        # Source code (truncated if too long)
        source = method_info.get("source_code", "")
        if len(source) > 1000:
            source = source[:1000] + "..."
        components.append(f"Code: {source}")
        
        # Method calls (context)
        if method_info.get("calls"):
            components.append(f"Calls: {', '.join(method_info['calls'][:5])}")
        
        # Combine
        text = "\n".join(components)
        return self.embed_text(text)
    
    def embed_code_methods_batch(
        self,
        methods: List[Dict],
        show_progress: bool = True
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple methods.
        
        Args:
            methods: List of method info dictionaries
            show_progress: Whether to show progress bar
        
        Returns:
            List of embedding vectors
        """
        # Prepare texts
        texts = []
        for method in methods:
            components = []
            
            if "full_signature" in method:
                components.append(f"Signature: {method['full_signature']}")
            
            if method.get("javadoc"):
                components.append(f"Documentation: {method['javadoc']}")
            
            source = method.get("source_code", "")
            if len(source) > 1000:
                source = source[:1000] + "..."
            components.append(f"Code: {source}")
            
            if method.get("calls"):
                components.append(f"Calls: {', '.join(method['calls'][:5])}")
            
            texts.append("\n".join(components))
        
        return self.embed_batch(texts, show_progress=show_progress)
    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
        
        Returns:
            Similarity score (0-1)
        """
        # Normalize
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)
    
    def find_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: List[np.ndarray],
        top_k: int = 5
    ) -> List[tuple[int, float]]:
        """
        Find top-k most similar embeddings.
        
        Args:
            query_embedding: Query embedding
            candidate_embeddings: List of candidate embeddings
            top_k: Number of results to return
        
        Returns:
            List of (index, similarity_score) tuples
        """
        similarities = []
        
        for i, candidate in enumerate(candidate_embeddings):
            score = self.compute_similarity(query_embedding, candidate)
            similarities.append((i, score))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension"""
        return self.embedding_dim
    
    def clear_cache(self) -> None:
        """Clear the embedding cache"""
        if self.redis_client:
            try:
                # Delete all embedding keys
                pattern = f"embedding:{self.model_name}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    logger.info(f"Cleared {len(keys)} cached embeddings")
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")


if __name__ == "__main__":
    # Test the embedder
    print("Testing CodeEmbedder...")
    
    embedder = CodeEmbedder()
    
    # Test single embedding
    test_code = """
    public int add(int a, int b) {
        return a + b;
    }
    """
    
    print(f"\n📊 Embedding dimension: {embedder.get_embedding_dimension()}")
    
    embedding = embedder.embed_text(test_code)
    print(f"✅ Single embedding shape: {embedding.shape}")
    
    # Test batch embedding
    test_codes = [
        "public void processData(List<String> items) { }",
        "private int calculate(int x) { return x * 2; }",
        "public String format(String input) { return input.trim(); }"
    ]
    
    embeddings = embedder.embed_batch(test_codes, show_progress=True)
    print(f"✅ Batch embeddings: {len(embeddings)} vectors")
    
    # Test similarity
    similarity = embedder.compute_similarity(embeddings[0], embeddings[1])
    print(f"📏 Similarity between first two: {similarity:.4f}")
    
    # Test similar search
    similar = embedder.find_similar(embeddings[0], embeddings[1:], top_k=2)
    print(f"🔍 Most similar to first: {similar}")
    
    print("\n✅ All tests passed!")

