"""
Test script for database clients with logging.
Tests all database connections and logging functionality.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import MemgraphClient, QdrantClientLogger, RedisClientLogger
from logger import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO", environment="development")
logger = get_logger(__name__)


def test_memgraph():
    """Test Memgraph client with logging"""
    print("\n" + "="*60)
    print("🗄️  Testing Memgraph Client")
    print("="*60)
    
    try:
        client = MemgraphClient()
        
        # Test simple query
        print("\n1. Testing simple query...")
        client.execute("RETURN 1;")
        
        # Test create node
        print("\n2. Testing node creation...")
        client.execute(
            "CREATE (n:TestNode {id: $id, name: $name})",
            {"id": "test-1", "name": "Test Node"}
        )
        
        # Test query with fetch
        print("\n3. Testing query with fetch...")
        results = client.execute_and_fetch(
            "MATCH (n:TestNode {id: $id}) RETURN n",
            {"id": "test-1"}
        )
        print(f"   Found {len(results)} results")
        
        # Get stats
        print("\n4. Getting database stats...")
        stats = client.get_stats()
        print(f"   📊 Stats: {stats}")
        
        # Cleanup
        print("\n5. Cleanup...")
        client.execute("MATCH (n:TestNode) DETACH DELETE n;")
        
        client.close()
        
        print("\n✅ Memgraph client test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Memgraph client test FAILED: {e}")
        print("💡 Make sure Memgraph is running: docker-compose up -d memgraph")
        return False


def test_qdrant():
    """Test Qdrant client with logging"""
    print("\n" + "="*60)
    print("🔍 Testing Qdrant Client")
    print("="*60)
    
    try:
        client = QdrantClientLogger()
        
        # Test collection creation
        print("\n1. Testing collection operations...")
        collection_name = "test_collection"
        
        # Delete if exists
        try:
            client.delete_collection(collection_name)
        except:
            pass
        
        # Create collection
        print("\n2. Creating test collection...")
        client.create_collection(
            collection_name=collection_name,
            vector_size=384,
            distance=Distance.COSINE
        )
        
        # Test upsert
        print("\n3. Testing upsert...")
        from qdrant_client.models import PointStruct, Distance
        import numpy as np
        
        points = [
            PointStruct(
                id=f"point-{i}",
                vector=np.random.rand(384).tolist(),
                payload={"name": f"test-{i}"}
            )
            for i in range(10)
        ]
        
        client.upsert(collection_name, points, batch_size=5)
        
        # Test search
        print("\n4. Testing search...")
        query_vector = np.random.rand(384).tolist()
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=5
        )
        print(f"   Found {len(results)} results")
        
        # Get collection info
        print("\n5. Getting collection info...")
        info = client.get_collection(collection_name)
        print(f"   📦 Collection has {info.points_count} points")
        
        # Get stats
        print("\n6. Getting client stats...")
        stats = client.get_stats()
        print(f"   📊 Stats: {stats}")
        
        # Cleanup
        print("\n7. Cleanup...")
        client.delete_collection(collection_name)
        
        print("\n✅ Qdrant client test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Qdrant client test FAILED: {e}")
        print("💡 Make sure Qdrant is running: docker-compose up -d qdrant")
        return False


def test_redis():
    """Test Redis client with logging"""
    print("\n" + "="*60)
    print("💾 Testing Redis Client")
    print("="*60)
    
    try:
        client = RedisClientLogger()
        
        # Test ping
        print("\n1. Testing connection...")
        if client.ping():
            print("   ✅ PING successful")
        
        # Test set/get
        print("\n2. Testing SET/GET...")
        test_key = "test:key:123"
        test_value = b"Hello, Redis!"
        
        client.set(test_key, test_value, ex=60)
        
        # Test cache hit
        value = client.get(test_key)
        assert value == test_value, "Value mismatch!"
        print(f"   ✅ Cache HIT: {value.decode()}")
        
        # Test cache miss
        print("\n3. Testing cache miss...")
        missing = client.get("nonexistent:key")
        assert missing is None
        print("   ✅ Cache MISS handled correctly")
        
        # Test SETEX
        print("\n4. Testing SETEX...")
        client.setex("test:setex", 30, b"Expires in 30s")
        
        # Test keys
        print("\n5. Testing KEYS...")
        keys = client.keys("test:*")
        print(f"   Found {len(keys)} keys matching 'test:*'")
        
        # Get server info
        print("\n6. Getting server info...")
        info = client.get_info()
        print(f"   📊 Redis version: {info.get('version')}")
        
        # Get client stats
        print("\n7. Getting client stats...")
        stats = client.get_stats()
        print(f"   📊 Stats: {stats}")
        print(f"   📈 Hit rate: {stats['hit_rate']:.1%}")
        
        # Cleanup
        print("\n8. Cleanup...")
        deleted = client.delete(*keys)
        print(f"   Deleted {deleted} keys")
        
        client.close()
        
        print("\n✅ Redis client test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Redis client test FAILED: {e}")
        print("💡 Make sure Redis is running: docker-compose up -d redis")
        return False


def main():
    """Run all database client tests"""
    print("\n" + "="*60)
    print("🧪 Database Clients Test Suite")
    print("="*60)
    
    results = {
        "memgraph": test_memgraph(),
        "qdrant": test_qdrant(),
        "redis": test_redis()
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    for db_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {db_name.capitalize():12s}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nMake sure all Docker services are running:")
        print("  docker-compose up -d")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

