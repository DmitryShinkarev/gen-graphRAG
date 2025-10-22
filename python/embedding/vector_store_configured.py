"""
Enhanced VectorStore that uses configuration from settings.
Automatically applies Qdrant parameters from .env file.
"""

from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    HnswConfigDiff,
    OptimizersConfigDiff,
    SearchParams
)
import numpy as np
from uuid import uuid4
from datetime import datetime

from config import get_settings
from logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ConfiguredVectorStore:
    """
    Vector store that automatically uses configuration from settings.
    
    All Qdrant parameters can be controlled via .env file:
    - QDRANT_DISTANCE_METRIC
    - QDRANT_HNSW_M
    - QDRANT_HNSW_EF_CONSTRUCT
    - QDRANT_DEFAULT_LIMIT
    - QDRANT_SCORE_THRESHOLD
    - etc.
    """
    
    def __init__(self, collection_name: str = "java_methods"):
        """
        Initialize configured vector store.
        
        Args:
            collection_name: Name of the collection
        """
        self.collection_name = collection_name
        
        # Get configuration from settings
        self.embedding_dim = settings.llm.embedding_dimension
        self.distance = settings.qdrant.get_distance_enum()
        self.hnsw_m = settings.qdrant.hnsw_m
        self.hnsw_ef_construct = settings.qdrant.hnsw_ef_construct
        self.default_limit = settings.qdrant.default_limit
        self.score_threshold = settings.qdrant.score_threshold
        self.search_ef = settings.qdrant.search_ef
        
        logger.info(
            f"Initializing ConfiguredVectorStore: {collection_name}\n"
            f"  Distance: {settings.qdrant.distance_metric}\n"
            f"  HNSW m: {self.hnsw_m}\n"
            f"  HNSW ef_construct: {self.hnsw_ef_construct}\n"
            f"  Default limit: {self.default_limit}\n"
            f"  Score threshold: {self.score_threshold}"
        )
        
        # Connect to Qdrant
        try:
            self.client = QdrantClient(
                host=settings.database.qdrant_host,
                port=settings.database.qdrant_port,
                api_key=settings.database.qdrant_api_key,
                https=False,  # Use HTTP without SSL for local Docker
                prefer_grpc=False  # Use REST API instead of gRPC
            )
            logger.info(f"Connected to Qdrant at {settings.database.qdrant_host}:{settings.database.qdrant_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
        
        # Create collection with configured parameters
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist, using config parameters"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection with configured parameters...")
                
                # HNSW configuration from settings
                hnsw_config = HnswConfigDiff(
                    m=self.hnsw_m,
                    ef_construct=self.hnsw_ef_construct,
                    full_scan_threshold=settings.qdrant.full_scan_threshold,
                    max_indexing_threads=0  # Auto-detect
                )
                
                # Optimizer configuration from settings
                optimizer_config = OptimizersConfigDiff(
                    indexing_threshold=settings.qdrant.indexing_threshold
                )
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=self.distance,
                        hnsw_config=hnsw_config,
                        on_disk=settings.qdrant.on_disk_payload
                    ),
                    optimizers_config=optimizer_config
                )
                
                logger.info(
                    f"✅ Collection '{self.collection_name}' created with:\n"
                    f"  m={self.hnsw_m}, ef_construct={self.hnsw_ef_construct}\n"
                    f"  distance={settings.qdrant.distance_metric}"
                )
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise
    
    def upsert_batch(
        self,
        vectors: List[np.ndarray],
        payloads: List[Dict[str, Any]],
        point_ids: Optional[List[str]] = None,
        batch_size: int = 100
    ) -> List[str]:
        """
        Upsert vectors using configured batch size.
        
        Args:
            vectors: List of vectors
            payloads: List of metadata
            point_ids: Optional point IDs
            batch_size: Batch size
        
        Returns:
            List of point IDs
        """
        if point_ids is None:
            point_ids = [str(uuid4()) for _ in range(len(vectors))]
        
        # Add timestamps
        timestamp = datetime.utcnow().isoformat()
        for payload in payloads:
            payload["indexed_at"] = timestamp
        
        total_points = len(vectors)
        logger.info(f"Upserting {total_points} points (batch_size: {batch_size})")
        
        try:
            for i in range(0, total_points, batch_size):
                batch_end = min(i + batch_size, total_points)
                batch_vectors = vectors[i:batch_end]
                batch_payloads = payloads[i:batch_end]
                batch_ids = point_ids[i:batch_end]
                
                points = [
                    PointStruct(
                        id=pid,
                        vector=vec.tolist() if isinstance(vec, np.ndarray) else vec,
                        payload=payload
                    )
                    for pid, vec, payload in zip(batch_ids, batch_vectors, batch_payloads)
                ]
                
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                logger.debug(f"Batch {i//batch_size + 1} uploaded")
            
            logger.info(f"✅ Upserted {total_points} points successfully")
            return point_ids
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            raise
    
    def search(
        self,
        query_vector: np.ndarray,
        limit: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using configured parameters.
        
        Args:
            query_vector: Query vector
            limit: Max results (None = use config default)
            score_threshold: Min score (None = use config default)
            filter_conditions: Optional filters
        
        Returns:
            Search results
        """
        # Use config defaults if not provided
        limit = limit or self.default_limit
        score_threshold = score_threshold or self.score_threshold
        
        try:
            # Build search params with configured ef
            search_params = None
            if self.search_ef is not None:
                search_params = SearchParams(
                    hnsw_ef=self.search_ef,
                    exact=False
                )
            
            # Build filter
            query_filter = None
            if filter_conditions:
                query_filter = self._build_filter(filter_conditions)
            
            logger.debug(
                f"Searching: limit={limit}, threshold={score_threshold}, "
                f"ef={self.search_ef or 'auto'}"
            )
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist() if isinstance(query_vector, np.ndarray) else query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
                search_params=search_params
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
            
            logger.info(f"✅ Search returned {len(results)} results")
            if results:
                logger.debug(f"Top score: {results[0].score:.4f}")
            
            return formatted_results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _build_filter(self, conditions: Dict[str, Any]) -> Filter:
        """Build Qdrant filter"""
        from qdrant_client.models import FieldCondition, MatchValue
        
        field_conditions = []
        for field, value in conditions.items():
            field_conditions.append(
                FieldCondition(key=field, match=MatchValue(value=value))
            )
        
        return Filter(must=field_conditions)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            info = self.client.get_collection(self.collection_name)
            
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.value,
                "config": {
                    "distance": settings.qdrant.distance_metric,
                    "hnsw_m": self.hnsw_m,
                    "hnsw_ef_construct": self.hnsw_ef_construct,
                    "default_limit": self.default_limit,
                    "score_threshold": self.score_threshold
                }
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}
    
    def update_search_params(
        self,
        limit: Optional[int] = None,
        score_threshold: Optional[float] = None,
        search_ef: Optional[int] = None
    ) -> None:
        """
        Dynamically update search parameters (runtime override).
        
        Args:
            limit: New default limit
            score_threshold: New threshold
            search_ef: New search ef
        """
        if limit is not None:
            self.default_limit = limit
            logger.info(f"Updated default_limit: {limit}")
        
        if score_threshold is not None:
            self.score_threshold = score_threshold
            logger.info(f"Updated score_threshold: {score_threshold}")
        
        if search_ef is not None:
            self.search_ef = search_ef
            logger.info(f"Updated search_ef: {search_ef}")


if __name__ == "__main__":
    # Test configured vector store
    print("Testing ConfiguredVectorStore...")
    print("This uses parameters from .env file!\n")
    
    store = ConfiguredVectorStore(collection_name="test_configured")
    
    # Show configuration
    info = store.get_collection_info()
    print(f"\n📊 Collection info:")
    print(f"  Name: {info['name']}")
    print(f"  Config: {info.get('config', {})}")
    
    # Test dynamic update
    print(f"\n🔧 Testing dynamic parameter update...")
    store.update_search_params(limit=50, score_threshold=0.8)
    
    print(f"\n✅ ConfiguredVectorStore test completed!")
    print(f"\n💡 Edit .env file to change Qdrant parameters!")

