# 📊 Database Clients with Logging

## Overview

Specialized database clients with comprehensive logging for:
- **Memgraph** - Graph database
- **Qdrant** - Vector database  
- **Redis** - Cache layer

Each client logs all operations, performance metrics, and errors.

## Features

### All Clients Provide:

✅ **Detailed operation logging**
- Start/completion of operations
- Duration tracking
- Success/failure status

✅ **Performance metrics**
- Operation counts
- Average execution times
- Total duration

✅ **Error handling**
- Detailed error messages
- Stack traces in logs
- Graceful degradation

✅ **Statistics**
- Client-level stats
- Database-level stats
- Performance insights

## Usage

### MemgraphClient

```python
from database import MemgraphClient

# Initialize (auto-connects and logs)
client = MemgraphClient()

# Execute query
client.execute(
    "CREATE (n:Person {id: $id, name: $name})",
    {"id": "1", "name": "John"}
)

# Execute and fetch
results = client.execute_and_fetch(
    "MATCH (n:Person {id: $id}) RETURN n",
    {"id": "1"}
)

# Get statistics
stats = client.get_stats()
print(f"Executed {stats['operations']} queries")

# Close
client.close()
```

**Logs:**
```
[INFO] database.memgraph: Initializing Memgraph client: localhost:7687
[INFO] database.memgraph: ✅ Connected to Memgraph in 0.123s
[DEBUG] database.memgraph: Executing query: CREATE (n:Person...
[INFO] database.memgraph: ✅ Query executed in 0.045s (total queries: 1)
```

### QdrantClientLogger

```python
from database import QdrantClientLogger
from qdrant_client.models import PointStruct, Distance
import numpy as np

# Initialize
client = QdrantClientLogger()

# Create collection
client.create_collection(
    collection_name="vectors",
    vector_size=384,
    distance=Distance.COSINE
)

# Upsert vectors
points = [
    PointStruct(
        id="1",
        vector=np.random.rand(384).tolist(),
        payload={"name": "test"}
    )
]

client.upsert("vectors", points)

# Search
query_vector = np.random.rand(384).tolist()
results = client.search(
    collection_name="vectors",
    query_vector=query_vector,
    limit=10
)

# Get statistics
stats = client.get_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

**Logs:**
```
[INFO] database.qdrant: Initializing Qdrant client: localhost:6333
[INFO] database.qdrant: ✅ Connected to Qdrant in 0.089s (0 collections)
[INFO] database.qdrant: Creating collection 'vectors' (size: 384, distance: cosine)
[INFO] database.qdrant: ✅ Collection created in 0.234s
[INFO] database.qdrant: Upserting 1 points to 'vectors' (batch_size: 100)
[INFO] database.qdrant: ✅ Upserted 1 points in 0.056s (17.9 points/sec)
[DEBUG] database.qdrant: Searching in 'vectors' (limit: 10, threshold: None)
[INFO] database.qdrant: ✅ Search returned 1 results in 0.012s
```

### RedisClientLogger

```python
from database import RedisClientLogger

# Initialize
client = RedisClientLogger()

# Set value
client.set("key", b"value", ex=60)

# Get value (cache hit)
value = client.get("key")

# Get value (cache miss)
missing = client.get("nonexistent")

# Get statistics
stats = client.get_stats()
print(f"Cache hit rate: {stats['hit_rate']:.1%}")

# Close
client.close()
```

**Logs:**
```
[INFO] database.redis: Initializing Redis client: localhost:6379 (db: 0)
[INFO] database.redis: ✅ Connected to Redis in 0.012s
[DEBUG] database.redis: SET key... (5 bytes, ttl: 60s)
[DEBUG] database.redis: ✅ SET completed in 0.003s
[DEBUG] database.redis: GET key...
[DEBUG] database.redis: ✅ Cache HIT for key... (5 bytes in 0.002s)
[DEBUG] database.redis: GET nonexistent...
[DEBUG] database.redis: ❌ Cache MISS for nonexistent... (0.001s)
[INFO] database.redis: 📊 Redis stats: 3 ops, hit rate: 50.0%
```

## Log Levels

Each client logs at different levels:

### DEBUG
- Individual operations
- Query details
- Cache hits/misses
- Parameter values

### INFO
- Connection status
- Operation summaries
- Performance metrics
- Statistics

### WARNING
- Destructive operations (delete, flush)
- Slow queries
- Retry attempts

### ERROR
- Connection failures
- Query errors
- Timeout errors
- Invalid operations

## Configuration

Logging configured in `logger.py`:

```python
from logger import setup_logging

# Development (colored console)
setup_logging(level="DEBUG", environment="development")

# Production (JSON logs)
setup_logging(level="INFO", environment="production", log_file="logs/app.log")
```

## Performance Tracking

All clients track:

| Metric | Description |
|--------|-------------|
| `operation_count` | Total operations |
| `total_duration` | Total time spent |
| `avg_operation_time` | Average per operation |

Additionally:

- **Qdrant**: `search_count`, `upsert_count`
- **Redis**: `cache_hits`, `cache_misses`, `hit_rate`
- **Memgraph**: `query_count`

## Testing

```bash
# Test all clients
python test_database_loggers.py

# Or use the script
./test_db_clients.sh
```

Expected output:
```
🧪 Database Clients Test Suite
═══════════════════════════════════

🗄️  Testing Memgraph Client
✅ Memgraph client test PASSED

🔍 Testing Qdrant Client
✅ Qdrant client test PASSED

💾 Testing Redis Client
✅ Redis client test PASSED

═══════════════════════════════════
🎉 ALL TESTS PASSED!
```

## Integration with Existing Code

Update existing code to use logged clients:

### Before:
```python
from pymemgraph import Memgraph

conn = Memgraph(host="localhost", port=7687)
conn.execute("MATCH (n) RETURN n")
```

### After:
```python
from database import MemgraphClient

client = MemgraphClient()  # Auto-logs connection
client.execute("MATCH (n) RETURN n")  # Logs query + duration
```

### Before:
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)
client.upsert(...)
```

### After:
```python
from database import QdrantClientLogger

client = QdrantClientLogger()  # Auto-logs connection
client.upsert(...)  # Logs operation + performance
```

### Before:
```python
import redis

r = redis.Redis(host="localhost", port=6379)
r.get("key")
```

### After:
```python
from database import RedisClientLogger

client = RedisClientLogger()  # Auto-logs connection
client.get("key")  # Logs cache hit/miss
```

## Benefits

1. **Debugging** - See exactly what's happening
2. **Performance** - Track slow operations
3. **Monitoring** - Aggregate logs for insights
4. **Troubleshooting** - Detailed error context
5. **Optimization** - Identify bottlenecks

## Example Log Output

```
2024-10-12 15:30:01 | INFO     | database.memgraph  | Initializing Memgraph client: localhost:7687
2024-10-12 15:30:01 | INFO     | database.memgraph  | ✅ Connected to Memgraph in 0.123s
2024-10-12 15:30:02 | DEBUG    | database.memgraph  | Executing query: MATCH (n:Method) RETURN...
2024-10-12 15:30:02 | INFO     | database.memgraph  | ✅ Query executed in 0.045s (total queries: 1)

2024-10-12 15:30:03 | INFO     | database.qdrant    | Initializing Qdrant client: localhost:6333
2024-10-12 15:30:03 | INFO     | database.qdrant    | ✅ Connected to Qdrant in 0.089s (1 collections)
2024-10-12 15:30:04 | INFO     | database.qdrant    | Upserting 100 points to 'java_methods'
2024-10-12 15:30:04 | INFO     | database.qdrant    | ✅ Upserted 100 points in 0.234s (427.4 points/sec)

2024-10-12 15:30:05 | INFO     | database.redis     | Initializing Redis client: localhost:6379 (db: 0)
2024-10-12 15:30:05 | INFO     | database.redis     | ✅ Connected to Redis in 0.012s
2024-10-12 15:30:06 | DEBUG    | database.redis     | GET embedding:all-MiniLM:abc123...
2024-10-12 15:30:06 | DEBUG    | database.redis     | ✅ Cache HIT for embedding:... (1536 bytes in 0.002s)
2024-10-12 15:30:07 | INFO     | database.redis     | 📊 Redis stats: 10 ops, hit rate: 80.0%
```

## Files

```
python/database/
├── __init__.py              # Exports
├── README.md                # This file
├── memgraph_client.py       # Memgraph with logging
├── qdrant_client.py         # Qdrant with logging
└── redis_client.py          # Redis with logging
```

## Next Steps

1. ✅ Database clients created
2. 🔄 Update existing code to use logged clients
3. 📊 Monitor logs during development
4. 🎯 Analyze performance metrics

---

**Created**: 2024-10-12  
**Author**: Java Unit Test Agent Team

