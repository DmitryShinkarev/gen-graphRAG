"""
Qdrant configuration for vector indexing and search.
Allows flexible configuration of collection parameters, search settings, and optimization.
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
from qdrant_client.models import Distance, VectorParams, HnswConfigDiff, OptimizersConfigDiff
import yaml
from pathlib import Path

from logger import get_logger

logger = get_logger("database.qdrant.config")


class DistanceMetric(str, Enum):
    """Supported distance metrics"""
    COSINE = "Cosine"
    EUCLIDEAN = "Euclid"
    DOT = "Dot"
    MANHATTAN = "Manhattan"


class IndexType(str, Enum):
    """Index types for different use cases"""
    HNSW = "hnsw"  # Default: fast approximate search
    FLAT = "flat"  # Exact search, slower but accurate


@dataclass
class HNSWConfig:
    """
    HNSW (Hierarchical Navigable Small World) index configuration.
    
    Parameters affect search quality vs performance tradeoff.
    """
    # M: Number of edges per node in the graph
    # Higher = better recall, more memory
    # Range: 4-64, Default: 16
    m: int = 16
    
    # ef_construct: Size of dynamic candidate list during construction
    # Higher = better quality index, slower indexing
    # Range: 100-2000, Default: 100
    ef_construct: int = 100
    
    # full_scan_threshold: When to use brute force
    # Below this number of vectors, use exact search
    full_scan_threshold: int = 10000
    
    # max_indexing_threads: Parallel indexing threads
    # 0 = auto-detect
    max_indexing_threads: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Qdrant"""
        return {
            "m": self.m,
            "ef_construct": self.ef_construct,
            "full_scan_threshold": self.full_scan_threshold,
            "max_indexing_threads": self.max_indexing_threads
        }
    
    def to_qdrant_config(self) -> HnswConfigDiff:
        """Convert to Qdrant HnswConfigDiff"""
        return HnswConfigDiff(
            m=self.m,
            ef_construct=self.ef_construct,
            full_scan_threshold=self.full_scan_threshold,
            max_indexing_threads=self.max_indexing_threads
        )


@dataclass
class OptimizerConfig:
    """
    Optimizer configuration for background optimization tasks.
    """
    # deleted_threshold: Trigger vacuum when this ratio of vectors deleted
    deleted_threshold: float = 0.2
    
    # vacuum_min_vector_number: Min vectors before vacuum
    vacuum_min_vector_number: int = 1000
    
    # default_segment_number: Number of segments to create
    default_segment_number: int = 0  # 0 = auto
    
    # max_segment_size: Max segment size in KB
    max_segment_size: Optional[int] = None
    
    # memmap_threshold: Threshold for memory mapping
    memmap_threshold: Optional[int] = None
    
    # indexing_threshold: Start indexing after this many vectors
    indexing_threshold: int = 20000
    
    # flush_interval_sec: How often to flush to disk
    flush_interval_sec: int = 5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "deleted_threshold": self.deleted_threshold,
            "vacuum_min_vector_number": self.vacuum_min_vector_number,
            "default_segment_number": self.default_segment_number,
            "max_segment_size": self.max_segment_size,
            "memmap_threshold": self.memmap_threshold,
            "indexing_threshold": self.indexing_threshold,
            "flush_interval_sec": self.flush_interval_sec
        }
    
    def to_qdrant_config(self) -> OptimizersConfigDiff:
        """Convert to Qdrant OptimizersConfigDiff"""
        return OptimizersConfigDiff(
            deleted_threshold=self.deleted_threshold,
            vacuum_min_vector_number=self.vacuum_min_vector_number,
            default_segment_number=self.default_segment_number,
            max_segment_size=self.max_segment_size,
            memmap_threshold=self.memmap_threshold,
            indexing_threshold=self.indexing_threshold,
            flush_interval_sec=self.flush_interval_sec
        )


@dataclass
class SearchConfig:
    """
    Search configuration parameters.
    
    Controls search quality and performance.
    """
    # ef: Size of dynamic candidate list during search
    # Higher = better recall, slower search
    # Range: limit to 10000, Default: None (uses ef_construct)
    ef: Optional[int] = None
    
    # exact: Force exact search (ignore HNSW)
    exact: bool = False
    
    # Default limit for search results
    default_limit: int = 10
    
    # Default score threshold (0.0 to 1.0)
    # Only return results with score >= threshold
    default_score_threshold: Optional[float] = None
    
    # Return vector in search results
    with_vectors: bool = False
    
    # Return payload in search results
    with_payload: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "ef": self.ef,
            "exact": self.exact,
            "default_limit": self.default_limit,
            "default_score_threshold": self.default_score_threshold,
            "with_vectors": self.with_vectors,
            "with_payload": self.with_payload
        }


@dataclass
class CollectionConfig:
    """
    Complete configuration for a Qdrant collection.
    """
    # Collection name
    name: str
    
    # Vector size (dimension)
    vector_size: int = 384
    
    # Distance metric
    distance: DistanceMetric = DistanceMetric.COSINE
    
    # HNSW index configuration
    hnsw_config: HNSWConfig = field(default_factory=HNSWConfig)
    
    # Optimizer configuration
    optimizer_config: OptimizerConfig = field(default_factory=OptimizerConfig)
    
    # Search configuration
    search_config: SearchConfig = field(default_factory=SearchConfig)
    
    # On-disk payload storage (saves RAM)
    on_disk_payload: bool = False
    
    # Replication factor (for clusters)
    replication_factor: int = 1
    
    # Write consistency factor
    write_consistency_factor: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "vector_size": self.vector_size,
            "distance": self.distance.value,
            "hnsw_config": self.hnsw_config.to_dict(),
            "optimizer_config": self.optimizer_config.to_dict(),
            "search_config": self.search_config.to_dict(),
            "on_disk_payload": self.on_disk_payload,
            "replication_factor": self.replication_factor,
            "write_consistency_factor": self.write_consistency_factor
        }
    
    def get_vector_params(self) -> VectorParams:
        """Get VectorParams for Qdrant"""
        distance_map = {
            DistanceMetric.COSINE: Distance.COSINE,
            DistanceMetric.EUCLIDEAN: Distance.EUCLID,
            DistanceMetric.DOT: Distance.DOT,
            DistanceMetric.MANHATTAN: Distance.MANHATTAN
        }
        
        return VectorParams(
            size=self.vector_size,
            distance=distance_map[self.distance],
            hnsw_config=self.hnsw_config.to_qdrant_config(),
            on_disk=self.on_disk_payload
        )


class QdrantConfigManager:
    """
    Manager for Qdrant configurations.
    
    Provides pre-configured setups for different use cases and
    allows loading custom configurations from YAML files.
    """
    
    # Preset configurations
    PRESETS = {
        "default": CollectionConfig(
            name="default",
            vector_size=384,
            distance=DistanceMetric.COSINE,
            hnsw_config=HNSWConfig(
                m=16,
                ef_construct=100
            ),
            search_config=SearchConfig(
                default_limit=10,
                default_score_threshold=0.7
            )
        ),
        
        "high_quality": CollectionConfig(
            name="high_quality",
            vector_size=384,
            distance=DistanceMetric.COSINE,
            hnsw_config=HNSWConfig(
                m=64,  # More edges = better recall
                ef_construct=200,  # Better index quality
                full_scan_threshold=5000
            ),
            search_config=SearchConfig(
                ef=128,  # Better search quality
                default_limit=20,
                default_score_threshold=0.8
            )
        ),
        
        "fast_indexing": CollectionConfig(
            name="fast_indexing",
            vector_size=384,
            distance=DistanceMetric.COSINE,
            hnsw_config=HNSWConfig(
                m=8,  # Fewer edges = faster indexing
                ef_construct=50,  # Faster construction
                max_indexing_threads=4  # Parallel indexing
            ),
            optimizer_config=OptimizerConfig(
                indexing_threshold=10000,  # Start indexing earlier
                flush_interval_sec=10  # Less frequent flushing
            ),
            search_config=SearchConfig(
                default_limit=10,
                default_score_threshold=0.6
            )
        ),
        
        "memory_efficient": CollectionConfig(
            name="memory_efficient",
            vector_size=384,
            distance=DistanceMetric.COSINE,
            hnsw_config=HNSWConfig(
                m=8,  # Less memory
                ef_construct=64
            ),
            on_disk_payload=True,  # Store payloads on disk
            optimizer_config=OptimizerConfig(
                memmap_threshold=50000  # Use memory mapping
            ),
            search_config=SearchConfig(
                with_vectors=False  # Don't return vectors (saves bandwidth)
            )
        ),
        
        "large_scale": CollectionConfig(
            name="large_scale",
            vector_size=384,
            distance=DistanceMetric.COSINE,
            hnsw_config=HNSWConfig(
                m=32,
                ef_construct=128,
                full_scan_threshold=100000
            ),
            optimizer_config=OptimizerConfig(
                indexing_threshold=50000,
                default_segment_number=8,
                max_segment_size=100000
            ),
            search_config=SearchConfig(
                ef=256,
                default_limit=50
            )
        )
    }
    
    @classmethod
    def get_preset(cls, preset_name: str) -> CollectionConfig:
        """
        Get a preset configuration.
        
        Args:
            preset_name: Name of preset (default, high_quality, fast_indexing, etc.)
        
        Returns:
            CollectionConfig instance
        """
        if preset_name not in cls.PRESETS:
            logger.warning(f"Unknown preset '{preset_name}', using 'default'")
            preset_name = "default"
        
        config = cls.PRESETS[preset_name]
        logger.info(f"Loaded preset configuration: {preset_name}")
        return config
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> CollectionConfig:
        """
        Load configuration from YAML file.
        
        Args:
            yaml_path: Path to YAML file
        
        Returns:
            CollectionConfig instance
        """
        try:
            logger.info(f"Loading Qdrant config from: {yaml_path}")
            
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Parse HNSW config
            hnsw_data = data.get("hnsw_config", {})
            hnsw_config = HNSWConfig(
                m=hnsw_data.get("m", 16),
                ef_construct=hnsw_data.get("ef_construct", 100),
                full_scan_threshold=hnsw_data.get("full_scan_threshold", 10000),
                max_indexing_threads=hnsw_data.get("max_indexing_threads", 0)
            )
            
            # Parse optimizer config
            opt_data = data.get("optimizer_config", {})
            optimizer_config = OptimizerConfig(
                deleted_threshold=opt_data.get("deleted_threshold", 0.2),
                vacuum_min_vector_number=opt_data.get("vacuum_min_vector_number", 1000),
                default_segment_number=opt_data.get("default_segment_number", 0),
                max_segment_size=opt_data.get("max_segment_size"),
                memmap_threshold=opt_data.get("memmap_threshold"),
                indexing_threshold=opt_data.get("indexing_threshold", 20000),
                flush_interval_sec=opt_data.get("flush_interval_sec", 5)
            )
            
            # Parse search config
            search_data = data.get("search_config", {})
            search_config = SearchConfig(
                ef=search_data.get("ef"),
                exact=search_data.get("exact", False),
                default_limit=search_data.get("default_limit", 10),
                default_score_threshold=search_data.get("default_score_threshold"),
                with_vectors=search_data.get("with_vectors", False),
                with_payload=search_data.get("with_payload", True)
            )
            
            # Parse distance metric
            distance_str = data.get("distance", "Cosine")
            distance = DistanceMetric(distance_str)
            
            # Create collection config
            config = CollectionConfig(
                name=data.get("name", "default"),
                vector_size=data.get("vector_size", 384),
                distance=distance,
                hnsw_config=hnsw_config,
                optimizer_config=optimizer_config,
                search_config=search_config,
                on_disk_payload=data.get("on_disk_payload", False),
                replication_factor=data.get("replication_factor", 1),
                write_consistency_factor=data.get("write_consistency_factor", 1)
            )
            
            logger.info(f"✅ Loaded config for collection: {config.name}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config from {yaml_path}: {e}")
            raise
    
    @classmethod
    def save_to_yaml(cls, config: CollectionConfig, yaml_path: Path) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config: CollectionConfig to save
            yaml_path: Path to save YAML
        """
        try:
            logger.info(f"Saving config to: {yaml_path}")
            
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(yaml_path, 'w') as f:
                yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"✅ Config saved to: {yaml_path}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    @classmethod
    def create_custom(
        cls,
        name: str,
        vector_size: int = 384,
        **kwargs
    ) -> CollectionConfig:
        """
        Create custom configuration.
        
        Args:
            name: Collection name
            vector_size: Vector dimension
            **kwargs: Additional parameters
        
        Returns:
            CollectionConfig instance
        """
        logger.info(f"Creating custom config: {name}")
        
        # Start with default
        config = cls.get_preset("default")
        config.name = name
        config.vector_size = vector_size
        
        # Override with kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config


# Preset configurations for different scenarios
JAVA_METHODS_CONFIG = CollectionConfig(
    name="java_methods",
    vector_size=384,  # sentence-transformers/all-MiniLM-L6-v2
    distance=DistanceMetric.COSINE,
    hnsw_config=HNSWConfig(
        m=16,  # Balanced
        ef_construct=100,  # Good quality
        full_scan_threshold=5000
    ),
    optimizer_config=OptimizerConfig(
        indexing_threshold=1000,  # Index after 1K vectors
        flush_interval_sec=30
    ),
    search_config=SearchConfig(
        default_limit=20,  # Return top 20 similar methods
        default_score_threshold=0.6,  # Min 60% similarity
        with_vectors=False,  # Don't return vectors (save bandwidth)
        with_payload=True  # Return metadata
    )
)

JAVA_CLASSES_CONFIG = CollectionConfig(
    name="java_classes",
    vector_size=384,
    distance=DistanceMetric.COSINE,
    hnsw_config=HNSWConfig(
        m=24,  # More edges for better class matching
        ef_construct=150
    ),
    search_config=SearchConfig(
        default_limit=10,
        default_score_threshold=0.7  # Higher threshold for classes
    )
)

JAVA_DOCUMENTATION_CONFIG = CollectionConfig(
    name="java_documentation",
    vector_size=384,
    distance=DistanceMetric.COSINE,
    hnsw_config=HNSWConfig(
        m=32,  # Higher quality for documentation
        ef_construct=200
    ),
    search_config=SearchConfig(
        ef=100,  # Better search quality
        default_limit=15,
        default_score_threshold=0.5  # Lower threshold for docs
    )
)


def get_config_for_collection(collection_name: str) -> CollectionConfig:
    """
    Get configuration for a specific collection.
    
    Args:
        collection_name: Name of collection
    
    Returns:
        CollectionConfig instance
    """
    configs = {
        "java_methods": JAVA_METHODS_CONFIG,
        "java_classes": JAVA_CLASSES_CONFIG,
        "java_documentation": JAVA_DOCUMENTATION_CONFIG
    }
    
    if collection_name in configs:
        logger.info(f"Using predefined config for: {collection_name}")
        return configs[collection_name]
    
    logger.info(f"No predefined config for '{collection_name}', using default")
    config = QdrantConfigManager.get_preset("default")
    config.name = collection_name
    return config


if __name__ == "__main__":
    # Example: Create and save configurations
    import sys
    
    # Create config directory
    config_dir = Path(__file__).parent.parent.parent / "config" / "qdrant"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    print("Creating Qdrant configuration files...")
    
    # Save preset configurations
    presets = ["default", "high_quality", "fast_indexing", "memory_efficient", "large_scale"]
    
    for preset_name in presets:
        config = QdrantConfigManager.get_preset(preset_name)
        config.name = preset_name
        
        yaml_path = config_dir / f"{preset_name}.yaml"
        QdrantConfigManager.save_to_yaml(config, yaml_path)
        print(f"✅ Saved: {yaml_path}")
    
    # Save collection-specific configs
    QdrantConfigManager.save_to_yaml(
        JAVA_METHODS_CONFIG,
        config_dir / "java_methods.yaml"
    )
    
    QdrantConfigManager.save_to_yaml(
        JAVA_CLASSES_CONFIG,
        config_dir / "java_classes.yaml"
    )
    
    QdrantConfigManager.save_to_yaml(
        JAVA_DOCUMENTATION_CONFIG,
        config_dir / "java_documentation.yaml"
    )
    
    print(f"\n✅ All configurations saved to: {config_dir}")
    print("\nEdit these YAML files to customize Qdrant behavior!")
    
    # Show example
    print("\n" + "="*60)
    print("Example configuration (java_methods):")
    print("="*60)
    print(yaml.dump(JAVA_METHODS_CONFIG.to_dict(), default_flow_style=False))

