"""
Vector store implementation using Qdrant for semantic code search.
Stores code embeddings with metadata for efficient retrieval.
"""

from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams,
    CollectionInfo
)
import numpy as np
from uuid import uuid4
from datetime import datetime

from config import get_settings
from logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class VectorStore:
    """
    Vector database store using Qdrant.
    
    Features:
    - Efficient vector search
    - Metadata filtering
    - Batch operations
    - Collection management
    """
    
    def __init__(
        self,
        collection_name: str = "java_methods",
        embedding_dim: Optional[int] = None,
        distance: Optional[Distance] = None
    ):
        """
        Initialize vector store.
        
        Args:
            collection_name: Name of the Qdrant collection
            embedding_dim: Dimension of embeddings (None = use from config)
            distance: Distance metric (None = use from config)
        """
        self.collection_name = collection_name
        
        # Use config values if not provided
        self.embedding_dim = embedding_dim or settings.llm.embedding_dimension
        self.distance = distance or settings.qdrant.get_distance_enum()
        
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
        
        # Create collection if not exists
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=self.distance
                    )
                )
                logger.info(f"Collection '{self.collection_name}' created successfully")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    def clear(self) -> None:
        """Clear all vectors from the collection"""
        logger.info(f"Clearing collection: {self.collection_name}")
        
        try:
            # Delete and recreate collection for clean slate
            try:
                self.client.delete_collection(collection_name=self.collection_name)
                logger.info(f"Collection '{self.collection_name}' deleted")
            except Exception as e:
                logger.debug(f"Collection might not exist: {e}")
            
            # Recreate collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=self.distance
                )
            )
            logger.info(f"Collection '{self.collection_name}' recreated successfully")
        except Exception as e:
            logger.error(f"Failed to clear Qdrant collection: {e}")
            raise
    
    def upsert_point(
        self,
        vector: np.ndarray,
        payload: Dict[str, Any],
        point_id: Optional[str] = None
    ) -> str:
        """
        Insert or update a single vector point.
        
        Args:
            vector: Embedding vector
            payload: Metadata associated with the vector
            point_id: Optional point ID (auto-generated if None)
        
        Returns:
            Point ID
        """
        if point_id is None:
            point_id = str(uuid4())
        
        # Add timestamp
        payload["indexed_at"] = datetime.utcnow().isoformat()
        
        try:
            point = PointStruct(
                id=point_id,
                vector=vector.tolist() if isinstance(vector, np.ndarray) else vector,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.debug(f"Upserted point: {point_id}")
            return point_id
        except Exception as e:
            logger.error(f"Failed to upsert point: {e}")
            raise
    
    def upsert_batch(
        self,
        vectors: List[np.ndarray],
        payloads: List[Dict[str, Any]],
        point_ids: Optional[List[str]] = None,
        batch_size: int = 100
    ) -> List[str]:
        """
        Insert or update multiple vector points in batches.
        
        Args:
            vectors: List of embedding vectors
            payloads: List of metadata dictionaries
            point_ids: Optional list of point IDs
            batch_size: Batch size for upload
        
        Returns:
            List of point IDs
        """
        if len(vectors) != len(payloads):
            raise ValueError("Number of vectors and payloads must match")
        
        # Generate IDs if not provided
        if point_ids is None:
            point_ids = [str(uuid4()) for _ in range(len(vectors))]
        
        # Add timestamps
        timestamp = datetime.utcnow().isoformat()
        for payload in payloads:
            payload["indexed_at"] = timestamp
        
        # Process in batches
        total_points = len(vectors)
        logger.info(f"Upserting {total_points} points in batches of {batch_size}")
        
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
                
                logger.info(f"Upserted batch {i//batch_size + 1}/{(total_points-1)//batch_size + 1}")
            
            logger.info(f"Successfully upserted {total_points} points")
            return point_ids
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            raise
    
    def search(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Optional filters for payload fields
        
        Returns:
            List of search results with payload and score
        """
        try:
            # Build filter
            query_filter = None
            if filter_conditions:
                query_filter = self._build_filter(filter_conditions)
            
            # Search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist() if isinstance(query_vector, np.ndarray) else query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
            
            logger.debug(f"Search returned {len(results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _build_filter(self, conditions: Dict[str, Any]) -> Filter:
        """Build Qdrant filter from conditions"""
        field_conditions = []
        
        for field, value in conditions.items():
            field_conditions.append(
                FieldCondition(
                    key=field,
                    match=MatchValue(value=value)
                )
            )
        
        return Filter(must=field_conditions)
    
    def get_by_id(self, point_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a point by ID.
        
        Args:
            point_id: Point ID
        
        Returns:
            Point data or None if not found
        """
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            
            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload
                }
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve point {point_id}: {e}")
            return None
    
    def delete_by_id(self, point_ids: List[str]) -> bool:
        """
        Delete points by IDs.
        
        Args:
            point_ids: List of point IDs to delete
        
        Returns:
            True if successful
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids
            )
            logger.info(f"Deleted {len(point_ids)} points")
            return True
        except Exception as e:
            logger.error(f"Failed to delete points: {e}")
            return False
    
    def delete_by_filter(self, filter_conditions: Dict[str, Any]) -> bool:
        """
        Delete points matching filter conditions.
        
        Args:
            filter_conditions: Filter conditions
        
        Returns:
            True if successful
        """
        try:
            query_filter = self._build_filter(filter_conditions)
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=query_filter
            )
            logger.info(f"Deleted points matching filter: {filter_conditions}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete by filter: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Collection statistics
        """
        try:
            info = self.client.get_collection(self.collection_name)
            
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.value
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}
    
    def scroll_all_points(
        self,
        batch_size: int = 100,
        with_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all points from collection.
        
        Args:
            batch_size: Batch size for scrolling
            with_vectors: Whether to include vector data
        
        Returns:
            List of all points
        """
        all_points = []
        offset = None
        
        try:
            while True:
                points, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_vectors=with_vectors
                )
                
                if not points:
                    break
                
                for point in points:
                    all_points.append({
                        "id": point.id,
                        "payload": point.payload,
                        "vector": point.vector if with_vectors else None
                    })
                
                if offset is None:
                    break
            
            logger.info(f"Retrieved {len(all_points)} points from collection")
            return all_points
        except Exception as e:
            logger.error(f"Failed to scroll points: {e}")
            return []
    
    def clear_collection(self) -> bool:
        """
        Delete all points from collection.
        
        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()
            logger.info(f"Cleared collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False


if __name__ == "__main__":
    # Test the vector store
    print("Testing VectorStore...")
    
    # Initialize
    store = VectorStore(
        collection_name="test_collection",
        embedding_dim=384
    )
    
    # Get info
    info = store.get_collection_info()
    print(f"\n📊 Collection info: {info}")
    
    # Create test vectors
    test_vectors = [
        np.random.rand(384),
        np.random.rand(384),
        np.random.rand(384)
    ]
    
    test_payloads = [
        {
            "method_name": "testMethod1",
            "class_name": "TestClass",
            "package": "com.example"
        },
        {
            "method_name": "testMethod2",
            "class_name": "TestClass",
            "package": "com.example"
        },
        {
            "method_name": "testMethod3",
            "class_name": "AnotherClass",
            "package": "com.example.other"
        }
    ]
    
    # Upsert
    print("\n📤 Upserting test vectors...")
    ids = store.upsert_batch(test_vectors, test_payloads)
    print(f"✅ Upserted {len(ids)} vectors")
    
    # Search
    print("\n🔍 Searching...")
    query_vector = test_vectors[0]
    results = store.search(query_vector, limit=3)
    
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results):
        print(f"  {i+1}. Score: {result['score']:.4f} - {result['payload']['method_name']}")
    
    # Filter search
    print("\n🔍 Searching with filter...")
    results = store.search(
        query_vector,
        limit=3,
        filter_conditions={"class_name": "TestClass"}
    )
    print(f"Found {len(results)} results in TestClass")
    
    # Clean up
    print("\n🧹 Cleaning up...")
    store.clear_collection()
    print("✅ Test collection cleared")

