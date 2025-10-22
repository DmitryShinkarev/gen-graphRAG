"""
Configuration management for Java Unit Test Agent.
Uses pydantic-settings for environment variable validation and type safety.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database connection settings"""
    
    # SQLite (Graph Database)
    use_graph_db: bool = Field(default=True, description="Use SQLite graph database (True) or NetworkX in-memory (False)")
    sqlite_graph_db_path: str = Field(default="data/code_graph.db", description="Path to SQLite graph database file")
    
    # Qdrant (Vector Database)
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key")
    
    # Redis (Cache)
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LLMSettings(BaseSettings):
    """LLM and AI model settings"""
    
    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model name")
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature")
    openai_max_tokens: int = Field(default=4096, ge=1, description="Max tokens")
    
    # Embedding model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence transformer model"
    )
    embedding_dimension: int = Field(default=384, description="Embedding vector dimension")
    
    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or v.startswith("sk-your-"):
            raise ValueError("Please set a valid OpenAI API key in .env file")
        return v
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings"""
    
    # Langfuse (LLM Tracing)
    langfuse_public_key: Optional[str] = Field(default=None, description="Langfuse public key")
    langfuse_secret_key: Optional[str] = Field(default=None, description="Langfuse secret key")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", description="Langfuse host")
    
    # Sentry (Error Tracking)
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN")
    sentry_environment: str = Field(default="development", description="Sentry environment")
    
    # LangChain Tracing
    langchain_tracing_v2: bool = Field(default=False, description="Enable LangChain tracing")
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        description="LangChain endpoint"
    )
    langchain_api_key: Optional[str] = Field(default=None, description="LangChain API key")
    langchain_project: str = Field(
        default="java-unit-test-agent",
        description="LangChain project name"
    )
    
    # Metrics
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class APISettings(BaseSettings):
    """API server settings"""
    
    python_api_port: int = Field(default=8000, description="Python API port")
    admin_ui_port: int = Field(default=5173, description="Admin UI port")
    
    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="CORS allowed origins"
    )
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class QdrantSettings(BaseSettings):
    """Qdrant vector database configuration"""
    
    # Collection settings
    distance_metric: str = Field(default="Cosine", description="Distance metric")
    
    # HNSW Index parameters
    hnsw_m: int = Field(default=16, ge=4, le=64, description="HNSW m parameter")
    hnsw_ef_construct: int = Field(default=100, ge=50, le=2000, description="HNSW ef_construct")
    full_scan_threshold: int = Field(default=10000, ge=1000, description="Full scan threshold")
    
    # Search parameters
    search_ef: Optional[int] = Field(default=None, description="Search ef (None = use ef_construct)")
    default_limit: int = Field(default=20, ge=1, description="Default search limit")
    score_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Min similarity score")
    
    # Optimization parameters
    indexing_threshold: int = Field(default=1000, ge=100, description="Start indexing after N vectors")
    on_disk_payload: bool = Field(default=False, description="Store payload on disk")
    
    # Preset override (optional)
    preset: Optional[str] = Field(default=None, description="Preset name (overrides other settings)")
    
    model_config = SettingsConfigDict(env_file=".env", env_prefix="QDRANT_", extra="ignore")
    
    def get_distance_enum(self):
        """Convert string to Qdrant Distance enum"""
        from qdrant_client.models import Distance
        
        distance_map = {
            "Cosine": Distance.COSINE,
            "Euclid": Distance.EUCLID,
            "Dot": Distance.DOT,
            "Manhattan": Distance.MANHATTAN
        }
        return distance_map.get(self.distance_metric, Distance.COSINE)


class AgentSettings(BaseSettings):
    """Agent system settings"""
    
    max_concurrent_tasks: int = Field(default=5, ge=1, description="Max concurrent tasks")
    agent_timeout: int = Field(default=300, ge=10, description="Agent timeout in seconds")
    enable_guardrails: bool = Field(default=True, description="Enable agent guardrails")
    max_retry_attempts: int = Field(default=3, ge=1, description="Max retry attempts")
    
    # Code analysis
    max_method_complexity: int = Field(default=15, ge=1, description="Max method complexity")
    batch_size: int = Field(default=32, ge=1, description="Embedding batch size")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class PerformanceSettings(BaseSettings):
    """Performance and caching settings"""
    
    cache_ttl: int = Field(default=3600, ge=0, description="Cache TTL in seconds")
    websocket_reconnect_interval: int = Field(
        default=5000,
        ge=1000,
        description="WebSocket reconnect interval in ms"
    )
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Settings(BaseSettings):
    """Main application settings"""
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")
    
    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    api: APISettings = Field(default_factory=APISettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    def check_services_health(self) -> dict[str, bool]:
        """Check health of all configured services"""
        health = {}
        
        # Check SQLite graph database
        try:
            from pathlib import Path
            db_path = Path(self.database.sqlite_graph_db_path)
            
            # Check if database file exists and is accessible
            if db_path.exists():
                # Try to connect to verify it's a valid SQLite database
                import sqlite3
                conn = sqlite3.connect(str(db_path), timeout=1.0)
                conn.execute("SELECT 1")
                conn.close()
                health["sqlite_graph"] = True
            else:
                # Database doesn't exist yet, but directory should be writable
                db_path.parent.mkdir(parents=True, exist_ok=True)
                health["sqlite_graph"] = True
            
        except Exception as e:
            logger.error(f"SQLite graph database health check failed: {e}")
            health["sqlite_graph"] = False
        
        # Check Qdrant
        try:
            import httpx
            response = httpx.get(
                f"http://{self.database.qdrant_host}:{self.database.qdrant_port}/",
                timeout=2.0
            )
            health["qdrant"] = response.status_code == 200
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            health["qdrant"] = False
        
        # Check Redis
        try:
            import redis
            r = redis.Redis(
                host=self.database.redis_host,
                port=self.database.redis_port,
                password=self.database.redis_password,
                db=self.database.redis_db,
                socket_timeout=2
            )
            health["redis"] = r.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            health["redis"] = False
        
        return health
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() in ["production", "prod"]
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() in ["development", "dev"]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance (Singleton pattern).
    This function is cached to ensure we only load settings once.
    """
    try:
        settings = Settings()
        logger.info(f"Settings loaded successfully for environment: {settings.environment}")
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise


# Global settings instance
settings = get_settings()


if __name__ == "__main__":
    # Test configuration
    print("=" * 60)
    print("Java Unit Test Agent - Configuration")
    print("=" * 60)
    
    print(f"\n🌍 Environment: {settings.environment}")
    print(f"🐛 Debug: {settings.debug}")
    print(f"📊 Log Level: {settings.log_level}")
    
    print(f"\n🗄️  SQLite Graph: {settings.database.sqlite_graph_db_path}")
    print(f"🔍 Qdrant: {settings.database.qdrant_host}:{settings.database.qdrant_port}")
    print(f"💾 Redis: {settings.database.redis_host}:{settings.database.redis_port}")
    
    print(f"\n🤖 LLM Model: {settings.llm.openai_model}")
    print(f"📐 Embedding Model: {settings.llm.embedding_model}")
    
    print(f"\n🚀 API Port: {settings.api.python_api_port}")
    print(f"🎨 UI Port: {settings.api.admin_ui_port}")
    
    print(f"\n🔍 Qdrant Configuration:")
    print(f"  Distance: {settings.qdrant.distance_metric}")
    print(f"  HNSW m: {settings.qdrant.hnsw_m}")
    print(f"  HNSW ef_construct: {settings.qdrant.hnsw_ef_construct}")
    print(f"  Search limit: {settings.qdrant.default_limit}")
    print(f"  Score threshold: {settings.qdrant.score_threshold}")
    if settings.qdrant.preset:
        print(f"  Preset: {settings.qdrant.preset}")
    
    print("\n🏥 Services Health Check:")
    health = settings.check_services_health()
    for service, status in health.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {service.capitalize()}: {'Healthy' if status else 'Unavailable'}")
    
    print("\n" + "=" * 60)

