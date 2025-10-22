"""Database clients with logging for all databases"""

# Import SQLite graph client
from .sqlite_graph_client import SQLiteGraphClient

# Import legacy Memgraph client if available
try:
    from .memgraph_client import MemgraphClient
    HAS_MEMGRAPH = True
except ImportError:
    HAS_MEMGRAPH = False
    MemgraphClient = None

from .qdrant_client import QdrantClientLogger
from .redis_client import RedisClientLogger

__all__ = ["SQLiteGraphClient", "MemgraphClient", "QdrantClientLogger", "RedisClientLogger"]

