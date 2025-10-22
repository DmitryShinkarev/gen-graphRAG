"""
Qdrant database client with detailed logging.
Wraps qdrant-client with logging for all vector operations.
"""

from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    SearchParams
)
import numpy as np
from datetime import datetime
import time

from config import get_settings
from logger import get_logger

settings = get_settings()
logger = get_logger("qdrant")  # Use dedicated qdrant logger


class QdrantClientLogger:
    """
    Qdrant database client with comprehensive logging.
    
    Logs all vector operations, search queries, and performance metrics.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Qdrant client.
        
        Args:
            host: Qdrant host
            port: Qdrant port
            api_key: API key (optional)
        """
        self.host = host or settings.database.qdrant_host
        self.port = port or settings.database.qdrant_port
        self.api_key = api_key or settings.database.qdrant_api_key
        
        self.operation_count = 0
        self.total_duration = 0.0
        self.search_count = 0
        self.upsert_count = 0
        
        logger.info(f"Initializing Qdrant client: {self.host}:{self.port}")
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Qdrant"""
        try:
            start_time = time.time()
            
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                timeout=30.0
            )
            
            # Test connection
            collections = self.client.get_collections()
            
            duration = time.time() - start_time
            logger.info(
                f"✅ Connected to Qdrant in {duration:.3f}s "
                f"({len(collections.collections)} collections)"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise
    
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE
    ) -> None:
        """
        Create a collection.
        
        Args:
            collection_name: Collection name
            vector_size: Vector dimension
            distance: Distance metric
        """
        start_time = time.time()
        self.operation_count += 1
        
        try:
            logger.info(
                f"Creating collection '{collection_name}' "
                f"(size: {vector_size}, distance: {distance.value})"
            )
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            logger.info(f"✅ Collection created in {duration:.3f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Failed to create collection after {duration:.3f}s: {e}")
            raise
    
    def upsert(
        self,
        collection_name: str,
        points: List[PointStruct],
        batch_size: int = 100
    ) -> None:
        """
        Upsert points to collection.
        
        Args:
            collection_name: Collection name
            points: List of points
            batch_size: Batch size for upload
        """
        start_time = time.time()
        self.operation_count += 1
        self.upsert_count += 1
        
        try:
            logger.info(
                f"Upserting {len(points)} points to '{collection_name}' "
                f"(batch_size: {batch_size})"
            )
            
            # Process in batches
            total_points = len(points)
            for i in range(0, total_points, batch_size):
                batch = points[i:i + batch_size]
                
                batch_start = time.time()
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch
                )
                batch_duration = time.time() - batch_start
                
                logger.debug(
                    f"Batch {i//batch_size + 1}/{(total_points-1)//batch_size + 1} "
                    f"uploaded in {batch_duration:.3f}s"
                )
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            logger.info(
                f"✅ Upserted {total_points} points in {duration:.3f}s "
                f"({total_points/duration:.1f} points/sec)"
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Upsert failed after {duration:.3f}s: {e}")
            raise
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        query_filter: Optional[Filter] = None
    ) -> List[Any]:
        """
        Search for similar vectors.
        
        Args:
            collection_name: Collection name
            query_vector: Query vector
            limit: Max results
            score_threshold: Min score
            query_filter: Optional filter
        
        Returns:
            Search results
        """
        start_time = time.time()
        self.operation_count += 1
        self.search_count += 1
        
        try:
            logger.debug(
                f"Searching in '{collection_name}' "
                f"(limit: {limit}, threshold: {score_threshold})"
            )
            
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            logger.info(
                f"✅ Search returned {len(results)} results in {duration:.3f}s"
            )
            
            if results:
                logger.debug(f"Top score: {results[0].score:.4f}")
            
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Search failed after {duration:.3f}s: {e}")
            raise
    
    def get_collection(self, collection_name: str) -> Any:
        """
        Get collection information.
        
        Args:
            collection_name: Collection name
        
        Returns:
            Collection info
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Getting collection info: {collection_name}")
            
            info = self.client.get_collection(collection_name)
            
            duration = time.time() - start_time
            
            logger.info(
                f"✅ Collection '{collection_name}': "
                f"{info.points_count} points, "
                f"{info.vectors_count} vectors "
                f"(fetched in {duration:.3f}s)"
            )
            
            return info
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Failed to get collection after {duration:.3f}s: {e}")
            raise
    
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection.
        
        Args:
            collection_name: Collection name
        """
        start_time = time.time()
        
        try:
            logger.warning(f"⚠️  Deleting collection: {collection_name}")
            
            self.client.delete_collection(collection_name)
            
            duration = time.time() - start_time
            logger.info(f"✅ Collection deleted in {duration:.3f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Failed to delete collection after {duration:.3f}s: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "host": self.host,
            "port": self.port,
            "operations": self.operation_count,
            "searches": self.search_count,
            "upserts": self.upsert_count,
            "total_duration": self.total_duration,
            "avg_operation_time": self.total_duration / self.operation_count if self.operation_count > 0 else 0
        }
        
        logger.info(f"📊 Qdrant stats: {stats}")
        return stats
    
    def __repr__(self) -> str:
        return (
            f"<QdrantClient {self.host}:{self.port} "
            f"(ops: {self.operation_count}, searches: {self.search_count})>"
        )


if __name__ == "__main__":
    # Test Qdrant client
    print("Testing QdrantClientLogger...")
    
    try:
        client = QdrantClientLogger()
        
        # Get collections
        collections = client.client.get_collections()
        print(f"\n📦 Collections: {[c.name for c in collections.collections]}")
        
        # Get stats
        stats = client.get_stats()
        print(f"\n📊 Stats: {stats}")
        
        print("\n✅ QdrantClientLogger test passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("💡 Make sure Qdrant is running: docker-compose up -d qdrant")

