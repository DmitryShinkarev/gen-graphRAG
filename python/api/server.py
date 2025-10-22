"""
FastAPI server for Java Unit Test Agent.
Provides REST API for Continue.dev integration and agent operations.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime
import json

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.indexer_agent import IndexerAgent
from agents.researcher_agent import ResearcherAgent
from agents.analyst_agent import AnalystAgent
from agents.generator_agent import GeneratorAgent
from agents.critic_agent import CriticAgent
from agents.coverage_agent_gradle import CoverageAgentGradle
from agents.base import AgentState
from graph.graph_builder import CodeGraph
from embedding import CodeEmbedder, VectorStore
from compilation import JavaTestCompiler
from config import get_settings
from logger import setup_logging, setup_all_loggers, get_logger

# Import API routes

# Setup
settings = get_settings()

def setup_langsmith_tracing():
    """Setup LangSmith tracing for LLM monitoring"""
    try:
        # Set LangSmith environment variables
        if settings.monitoring.langchain_tracing_v2:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            
            if settings.monitoring.langchain_api_key:
                os.environ["LANGCHAIN_API_KEY"] = settings.monitoring.langchain_api_key
                os.environ["LANGCHAIN_PROJECT"] = settings.monitoring.langchain_project
                os.environ["LANGCHAIN_ENDPOINT"] = settings.monitoring.langchain_endpoint
                
                logger.info("✅ LangSmith tracing enabled")
                logger.info(f"   Project: {settings.monitoring.langchain_project}")
                logger.info(f"   Endpoint: {settings.monitoring.langchain_endpoint}")
                
                # Test LangSmith connection
                try:
                    from langsmith import Client
                    client = Client()
                    # Try to list projects to verify connection
                    projects = list(client.list_projects(limit=1))
                    logger.info("✅ LangSmith connection verified")
                except Exception as e:
                    logger.warning(f"⚠️ LangSmith connection failed: {e}")
                    logger.info("   Tracing will be disabled")
                    os.environ["LANGCHAIN_TRACING_V2"] = "false"
            else:
                logger.warning("⚠️ LangSmith API key not provided, tracing disabled")
                os.environ["LANGCHAIN_TRACING_V2"] = "false"
        else:
            logger.info("ℹ️ LangSmith tracing disabled in configuration")
            
    except Exception as e:
        logger.error(f"❌ Failed to setup LangSmith tracing: {e}")
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Setup main application logging with absolute path
project_root = Path(__file__).parent.parent.parent
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

setup_logging(
    level=settings.log_level,
    log_file=str(logs_dir / "main.log"),
    environment=settings.environment,
    enable_sentry=False,
    sentry_dsn=settings.monitoring.sentry_dsn,
    file_format="detailed"  # Use human-readable format for logs
)

# Setup component-specific loggers with absolute path
component_loggers = setup_all_loggers(
    base_level=settings.log_level,
    logs_dir=str(logs_dir),
    environment=settings.environment,
    file_format="detailed"  # Use human-readable format for logs
)

# Get API logger
logger = get_logger("api")

# Initialize LangSmith tracing after logger is ready
setup_langsmith_tracing()

# FastAPI app
app = FastAPI(
    title="Java Unit Test Agent API",
    description="AI-powered Java test generation with Continue.dev integration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for Continue.dev and web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers

# Global components
graph: Optional[CodeGraph] = None
embedder: Optional[CodeEmbedder] = None
vector_store: Optional[VectorStore] = None
indexer_agent: Optional[IndexerAgent] = None
researcher_agent: Optional[ResearcherAgent] = None
analyst_agent: Optional[AnalystAgent] = None
generator_agent: Optional[GeneratorAgent] = None
critic_agent: Optional[CriticAgent] = None
coverage_agent: Optional[CoverageAgentGradle] = None
test_compiler: Optional[JavaTestCompiler] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

manager = ConnectionManager()

# Pydantic models
class IndexRequest(BaseModel):
    """Request to index a Java project"""
    project_path: str = Field(..., description="Path to Java project")
    force: bool = Field(default=False, description="Force re-indexing")
    project_id: Optional[str] = Field(default=None, description="Project identifier")
    clear_before: bool = Field(default=True, description="Clear databases before indexing (recommended)")

class IndexResponse(BaseModel):
    """Response from project indexing"""
    status: str = Field(..., description="Status: success, error, or completed_with_errors")
    indexed_files: int = Field(..., description="Number of indexed files")
    parsed_classes: int = Field(..., description="Number of parsed classes")
    methods_count: int = Field(..., description="Total methods found")
    steps: List[str] = Field(..., description="Completed steps")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    project_id: str = Field(..., description="Project identifier")
    duration: float = Field(..., description="Processing time in seconds")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    components: Dict[str, bool]

class StatsResponse(BaseModel):
    """Project statistics"""
    methods_in_graph: int
    vectors_stored: int
    collection_status: str
    indexed_files: int = 0

class TestGenerationRequest(BaseModel):
    """Request to generate test for a method"""
    target_method: str = Field(..., description="Method name or ID")
    class_name: Optional[str] = Field(None, description="Class containing the method")
    file_path: Optional[str] = Field(None, description="Path to Java file")
    project_id: Optional[str] = Field(default="default", description="Project identifier")

class TestGenerationResponse(BaseModel):
    """Response from test generation"""
    status: str = Field(..., description="Status: success or error")
    test_code: str = Field(..., description="Generated test code")
    quality_score: float = Field(..., description="Quality score 0-100")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    method_name: str = Field(..., description="Target method name")
    duration: float = Field(..., description="Generation time in seconds")
    coverage_metrics: Optional[Dict[str, float]] = Field(None, description="Real coverage metrics")
    real_coverage_measured: bool = Field(False, description="Whether real coverage was measured")

class TestCompilationRequest(BaseModel):
    """Request to compile Java test code"""
    test_code: str = Field(..., description="Java test code to compile")
    source_files: Optional[List[str]] = Field(None, description="Additional source files to include")
    additional_classpath: Optional[List[str]] = Field(None, description="Additional classpath entries")

class TestCompilationResponse(BaseModel):
    """Response from test compilation"""
    status: str = Field(..., description="Status: success or error")
    success: bool = Field(..., description="Whether compilation succeeded")
    errors: List[str] = Field(default_factory=list, description="Compilation errors")
    warnings: List[str] = Field(default_factory=list, description="Compilation warnings")
    compiled_files: List[str] = Field(default_factory=list, description="Generated .class files")
    classpath: List[str] = Field(default_factory=list, description="Used classpath")
    compilation_time: float = Field(..., description="Compilation time in seconds")
    return_code: int = Field(..., description="javac return code")
    stdout: str = Field("", description="javac stdout")
    stderr: str = Field("", description="javac stderr")

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global graph, embedder, vector_store, indexer_agent
    global researcher_agent, analyst_agent, generator_agent, critic_agent, coverage_agent, test_compiler
    
    logger.info("🚀 Starting Java Unit Test Agent API...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    try:
        # Check services health
        health = settings.check_services_health()
        logger.info(f"Services health: {health}")
        
        # Initialize components
        logger.info("Initializing code graph...")
        use_graph_db = settings.database.use_graph_db
        logger.info(f"Graph mode: {'SQLite' if use_graph_db else 'NetworkX (in-memory)'}")
        graph = CodeGraph(use_graph_db=use_graph_db, project_id="default")
        
        logger.info("Initializing code embedder...")
        embedder = CodeEmbedder()
        
        logger.info("Initializing vector store...")
        try:
            vector_store = VectorStore(
                collection_name="java_methods",
                embedding_dim=embedder.get_embedding_dimension()
            )
            logger.info("✅ Vector store connected")
        except Exception as e:
            logger.warning(f"⚠️  Vector store unavailable: {e} - will work without it")
            vector_store = None
        
        logger.info("Initializing indexer agent...")
        indexer_agent = IndexerAgent(
            graph=graph,
            embedder=embedder,
            vector_store=vector_store,
            project_id="default"
        )
        
        # Initialize test generation agents
        logger.info("Initializing test generation agents...")
        researcher_agent = ResearcherAgent(
            graph=graph,
            embedder=embedder,
            vector_store=vector_store
        )
        logger.info("🔄 Initializing AnalystAgent...")
        try:
            analyst_agent = AnalystAgent()
            logger.info(f"✅ AnalystAgent initialized: {analyst_agent.name}")
            logger.info(f"   Role: {analyst_agent.role}")
            logger.info(f"   Temperature: {analyst_agent.temperature}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AnalystAgent: {e}")
            analyst_agent = None
            raise
        
        logger.info("🔄 Initializing GeneratorAgent...")
        generator_agent = GeneratorAgent(test_framework="junit5", graph=graph)
        logger.info("🔄 Initializing CriticAgent...")
        critic_agent = CriticAgent()
        logger.info("🔄 Initializing CoverageAgent...")
        coverage_agent = CoverageAgentGradle()
        logger.info("🔄 Initializing JavaTestCompiler...")
        test_compiler = JavaTestCompiler()
        logger.info("✅ Test generation agents ready (RAG + Analysis enabled)")
        
        # Debug: Verify all agents are initialized
        logger.info("🔍 Agent initialization verification:")
        logger.info(f"   • researcher_agent: {'✅' if researcher_agent else '❌'}")
        logger.info(f"   • analyst_agent: {'✅' if analyst_agent else '❌'}")
        logger.info(f"   • generator_agent: {'✅' if generator_agent else '❌'}")
        logger.info(f"   • critic_agent: {'✅' if critic_agent else '❌'}")
        logger.info(f"   • coverage_agent: {'✅' if coverage_agent else '❌'}")
        logger.info(f"   • test_compiler: {'✅' if test_compiler else '❌'}")
        
        logger.info("✅ API ready! Access docs at http://localhost:8000/docs")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Java Unit Test Agent API...")

# API Endpoints

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Java Unit Test Agent API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "index": "POST /api/index/project",
            "index_simple": "GET /index?project_path=/path/to/project",
            "stats": "GET /api/stats",
            "websocket": "WS /ws"
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0",
        components={
            "graph": graph is not None,
            "embedder": embedder is not None,
            "vector_store": vector_store is not None,
            "indexer_agent": indexer_agent is not None,
            "analyst_agent": analyst_agent is not None,
            "test_compiler": test_compiler is not None
        }
    )

@app.post("/api/clear", tags=["Database Management"])
async def clear_databases():
    """
    Clear all databases (SQLite, Qdrant, Redis).
    
    This will:
    1. Clear all entities and relationships from SQLite
    2. Delete and recreate Qdrant collection
    3. Flush Redis cache
    
    Use this before indexing a new project to ensure clean state.
    """
    try:
        logger.info("🗑️  Clearing all databases...")
        start_time = datetime.utcnow()
        
        cleared = {}
        errors = []
        
        # Clear SQLite Graph Database
        try:
            if graph:
                graph.clear()
                cleared["sqlite"] = "success"
                logger.info("✅ SQLite graph database cleared")
        except Exception as e:
            logger.error(f"Failed to clear SQLite graph database: {e}")
            errors.append(f"SQLite: {str(e)}")
            cleared["sqlite"] = "failed"
        
        # Clear Qdrant
        try:
            if vector_store:
                vector_store.clear()
                cleared["qdrant"] = "success"
                logger.info("✅ Qdrant cleared")
        except Exception as e:
            logger.error(f"Failed to clear Qdrant: {e}")
            errors.append(f"Qdrant: {str(e)}")
            cleared["qdrant"] = "failed"
        
        # Clear Redis (if available)
        try:
            from database.redis_client import RedisClientLogger
            redis_client = RedisClientLogger()
            redis_client.flushdb()
            redis_client.close()
            cleared["redis"] = "success"
            logger.info("✅ Redis cleared")
        except Exception as e:
            logger.warning(f"Failed to clear Redis: {e}")
            errors.append(f"Redis: {str(e)}")
            cleared["redis"] = "failed"
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Broadcast completion
        await manager.broadcast({
            "type": "databases_cleared",
            "cleared": cleared,
            "duration": duration
        })
        
        logger.info(f"✅ Databases cleared in {duration:.2f}s")
        
        return {
            "status": "success" if not errors else "partial",
            "cleared": cleared,
            "errors": errors,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"❌ Failed to clear databases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/index/project", response_model=IndexResponse, tags=["Indexing"])
async def index_project(request: IndexRequest):
    """
    Index a Java project.
    
    This endpoint will:
    1. Clear databases (if clear_before=True, which is default)
    2. Scan the project directory
    3. Parse all Java files with Tree-sitter
    4. Build a code relationship graph
    5. Generate semantic embeddings
    6. Store in vector database
    
    Returns detailed indexing statistics.
    """
    if not indexer_agent:
        raise HTTPException(status_code=503, detail="Indexer agent not initialized")
    
    try:
        start_time = datetime.utcnow()
        logger.info(f"📂 Indexing project: {request.project_path}")
        
        # Step 1: Clear databases if requested (default: True)
        if request.clear_before:
            logger.info("🗑️  Clearing databases before indexing...")
            try:
                # Clear SQLite graph database
                if graph:
                    graph.clear()
                    logger.info("✅ SQLite graph database cleared")
                
                # Clear Qdrant
                if vector_store:
                    vector_store.clear()
                    logger.info("✅ Qdrant cleared")
                
                # Clear Redis
                try:
                    from database.redis_client import RedisClientLogger
                    redis_client = RedisClientLogger()
                    redis_client.flushdb()
                    redis_client.close()
                    logger.info("✅ Redis cleared")
                except Exception as e:
                    logger.warning(f"Redis clear failed (non-critical): {e}")
                
                logger.info("✅ All databases cleared successfully")
            except Exception as e:
                logger.error(f"⚠️  Database clearing failed: {e}")
                # Continue with indexing even if clearing fails
        
        # Broadcast start message
        await manager.broadcast({
            "type": "indexing_started",
            "project_path": request.project_path,
            "cleared": request.clear_before
        })
        
        # Create agent state
        state = AgentState()
        state.project_path = request.project_path
        state.project_id = request.project_id or "default"
        
        # Execute indexing
        result = await indexer_agent.execute(state)
        
        # Calculate statistics
        methods_count = 0
        for cls_data in result.parsed_classes.values():
            class_info = cls_data.get("class_info", {})
            methods_count += len(class_info.get("methods", []))
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Determine status
        if result.errors:
            status = "completed_with_errors"
        else:
            status = "success"
        
        response = IndexResponse(
            status=status,
            indexed_files=len(result.indexed_files),
            parsed_classes=len(result.parsed_classes),
            methods_count=methods_count,
            steps=result.steps_completed,
            errors=result.errors,
            project_id=state.project_id,
            duration=duration
        )
        
        # Broadcast completion
        await manager.broadcast({
            "type": "indexing_completed",
            "project_path": request.project_path,
            "stats": response.dict()
        })
        
        logger.info(f"✅ Indexing completed in {duration:.2f}s")
        return response
        
    except Exception as e:
        logger.exception(f"❌ Indexing failed: {e}")
        await manager.broadcast({
            "type": "indexing_failed",
            "project_path": request.project_path,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats", response_model=StatsResponse, tags=["Statistics"])
async def get_stats():
    """Get statistics about indexed projects"""
    try:
        if not graph or not vector_store:
            raise HTTPException(status_code=503, detail="Components not initialized")
        
        # Get methods from graph
        methods = graph.get_all_methods()
        
        # Get vector store info
        vector_info = vector_store.get_collection_info()
        
        return StatsResponse(
            methods_in_graph=len(methods),
            vectors_stored=vector_info.get("points_count", 0),
            collection_status=vector_info.get("status", "unknown")
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate/test", response_model=TestGenerationResponse, tags=["Test Generation"])
async def generate_test(request: TestGenerationRequest):
    """
    Generate unit test for a specific method using RAG + Analysis system.
    
    Workflow:
    1. ResearcherAgent: Gather context via Markov walks + vector search (RAG)
    2. AnalystAgent: Perform deep code analysis (complexity, dependencies, edge cases)
    3. GeneratorAgent: Generate test code using LLM with rich context + analysis
    4. CriticAgent: Evaluate quality and suggest improvements
    
    Returns generated test code with quality score and suggestions.
    """
    if not all([researcher_agent, analyst_agent, generator_agent, critic_agent]):
        raise HTTPException(
            status_code=503, 
            detail="Test generation agents not initialized. Make sure API started successfully."
        )
    
    try:
        start_time = datetime.utcnow()
        logger.info(f"🧪 Generating test for method: {request.target_method}")
        
        # Broadcast start message
        await manager.broadcast({
            "type": "test_generation_started",
            "method": request.target_method,
            "class": request.class_name
        })
        
        # Step 1: Create initial state
        state = AgentState()
        state.target_method = request.target_method
        state.project_id = request.project_id
        
        # Add optional metadata
        if request.class_name:
            state.metadata["class_name"] = request.class_name
        if request.file_path:
            state.metadata["file_path"] = request.file_path
        
        # Step 2: Research context (RAG phase)
        logger.info("📚 Step 1/4: Researching context with RAG (Markov walks + vector search)...")
        state = await researcher_agent.execute(state)
        
        if state.errors and not state.method_context:
            error_detail = f"Method '{request.target_method}' not found or context gathering failed"
            if state.errors:
                error_detail += f": {'; '.join(state.errors[:3])}"
            raise HTTPException(status_code=404, detail=error_detail)
        
        logger.info(f"✅ Found {len(state.method_context.get('ranked_methods', []))} relevant methods")
        
        await manager.broadcast({
            "type": "test_generation_progress",
            "step": "research_completed",
            "method": request.target_method,
            "context_items": len(state.method_context.get("ranked_methods", []))
        })
        
        # Step 3: Deep code analysis
        logger.info("🧠 Step 2/4: Performing deep code analysis...")
        logger.info("🔍 DEBUG: About to check analyst_agent availability...")
        
        # Debug: Check if analyst_agent is available
        if analyst_agent is None:
            logger.error("❌ CRITICAL: analyst_agent is None! Skipping analysis step.")
            logger.error("   This indicates a startup initialization problem.")
        else:
            logger.info(f"✅ analyst_agent is available: {type(analyst_agent).__name__}")
            logger.info(f"   Agent name: {analyst_agent.name}")
            logger.info(f"   Agent role: {analyst_agent.role}")
        
        # Debug: Check state before analysis
        logger.info(f"📊 State before analysis:")
        logger.info(f"   • Method context: {len(state.method_context.get('ranked_methods', []))} methods")
        logger.info(f"   • Dependencies: {len(state.dependencies.get('methods', []))} methods, {len(state.dependencies.get('fields', []))} fields")
        logger.info(f"   • Errors: {len(state.errors)} errors")
        
        try:
            logger.info("🔄 Calling analyst_agent.execute(state)...")
            state = await analyst_agent.execute(state)
            logger.info("✅ analyst_agent.execute() completed successfully")
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR in analyst_agent.execute(): {str(e)}")
            logger.error(f"   Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            # Continue with workflow even if analysis fails
            state.errors.append(f"Analysis failed: {str(e)}")
        
        if state.errors:
            logger.warning(f"⚠️ Analysis completed with errors: {state.errors}")
        
        # Log analysis results
        if state.complexity_analysis:
            complexity = state.complexity_analysis
            logger.info(f"✅ Analysis completed: {complexity['complexity_level']} complexity, {len(state.edge_case_analysis.get('edge_cases', []))} edge cases")
        else:
            logger.warning("⚠️ No complexity_analysis found in state after analyst_agent execution")
        
        await manager.broadcast({
            "type": "test_generation_progress",
            "step": "analysis_completed",
            "method": request.target_method,
            "complexity_level": state.complexity_analysis.get('complexity_level') if state.complexity_analysis else 'unknown'
        })
        
        # Step 4: Generate test code
        logger.info("✨ Step 3/4: Generating test code with LLM...")
        state = await generator_agent.execute(state)
        
        if not state.test_code:
            raise HTTPException(
                status_code=500,
                detail="Test generation failed - no code produced. Check logs for details."
            )
        
        logger.info(f"✅ Generated {len(state.test_code)} characters of test code")
        
        # Extract source code for coverage measurement
        if state.method_context and state.method_context.get('ranked_methods'):
            target_method_info = state.method_context['ranked_methods'][0]  # First is the target
            if target_method_info and 'source_code' in target_method_info:
                state.source_code = target_method_info['source_code']
                logger.info(f"✅ Extracted source code for coverage measurement")
        
        await manager.broadcast({
            "type": "test_generation_progress",
            "step": "generation_completed",
            "method": request.target_method,
            "code_length": len(state.test_code)
        })
        
        # Step 5: Measure real coverage (if Java/Maven available)
        logger.info("📊 Step 4/4: Measuring real code coverage...")
        
        # TEMPORARILY DISABLED: Coverage measurement causes compilation hangs
        # TODO: Re-enable after fixing dependency issues
        logger.info("⚠️  Coverage measurement temporarily disabled to avoid compilation hangs")
        state.real_coverage_measured = False
        
        # Original code (disabled):
        # if coverage_agent:
        #     try:
        #         state = await coverage_agent.execute(state)
        #         if state.real_coverage_measured:
        #             logger.info("✅ Real coverage measured successfully")
        #         else:
        #             logger.info("⚠️  Coverage measurement not available (Java/Maven not found)")
        #     except Exception as e:
        #         logger.warning(f"Coverage measurement failed: {e}")
        #         logger.info("Continuing with static analysis only...")
        # else:
        #     logger.info("⚠️  CoverageAgent not available")
        
        # Step 6: Critique and evaluate
        logger.info("🔍 Step 5/5: Evaluating test quality...")
        state = await critic_agent.execute(state)
        
        logger.info(f"✅ Quality score: {state.quality_score:.1f}/100")
        
        # Step 7: Iterative improvement if quality is low
        MIN_ACCEPTABLE_SCORE = 70
        MAX_ITERATIONS = 2
        iteration = 0
        
        while state.quality_score < MIN_ACCEPTABLE_SCORE and iteration < MAX_ITERATIONS:
            iteration += 1
            logger.info(f"⚠️  Quality below {MIN_ACCEPTABLE_SCORE}, attempting improvement (iteration {iteration}/{MAX_ITERATIONS})...")
            logger.info(f"   Issues found: {len(state.issues)}")
            
            # Add improvement feedback to context
            improvement_context = f"\nPREVIOUS ATTEMPT HAD ISSUES:\n"
            for issue in state.issues[:5]:  # Top 5 issues
                improvement_context += f"- {issue}\n"
            improvement_context += f"\nSuggestions:\n"
            for suggestion in state.suggestions[:3]:  # Top 3 suggestions
                improvement_context += f"- {suggestion}\n"
            improvement_context += f"\nPlease fix these issues and regenerate a better test."
            
            # Add to state metadata
            state.metadata["improvement_feedback"] = improvement_context
            state.metadata["previous_score"] = state.quality_score
            
            # Clear previous test
            state.test_code = None
            state.issues = []
            state.suggestions = []
            
            # Re-analyze and regenerate
            logger.info("   🔄 Re-analyzing and regenerating with feedback...")
            # Re-run analysis to get fresh insights
            state = await analyst_agent.execute(state)
            state = await generator_agent.execute(state)
            
            if not state.test_code:
                logger.warning("   ❌ Regeneration failed, using previous attempt")
                break
            
            # Re-evaluate
            state = await critic_agent.execute(state)
            logger.info(f"   ✅ New quality score: {state.quality_score:.1f}/100 (was: {state.metadata.get('previous_score', 0):.1f})")
            
            if state.quality_score >= MIN_ACCEPTABLE_SCORE:
                logger.info(f"   🎉 Quality improved to acceptable level!")
                break
        
        if iteration > 0:
            logger.info(f"📊 Iterative improvement completed: {iteration} iterations, final score: {state.quality_score:.1f}/100")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        response = TestGenerationResponse(
            status="success",
            test_code=state.test_code,
            quality_score=state.quality_score,
            suggestions=state.suggestions,
            method_name=request.target_method,
            duration=duration,
            coverage_metrics=state.coverage_metrics,
            real_coverage_measured=state.real_coverage_measured
        )
        
        # Broadcast completion
        await manager.broadcast({
            "type": "test_generation_completed",
            "method": request.target_method,
            "quality_score": state.quality_score,
            "duration": duration
        })
        
        logger.info(f"✅ Test generated successfully in {duration:.2f}s (quality: {state.quality_score:.1f}/100)")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Test generation failed: {e}")
        await manager.broadcast({
            "type": "test_generation_failed",
            "method": request.target_method,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"Test generation failed: {str(e)}")

@app.post("/api/compile/test", response_model=TestCompilationResponse, tags=["Test Compilation"])
async def compile_test(request: TestCompilationRequest):
    """
    Compile Java test code.
    
    This endpoint compiles the provided Java test code and returns compilation results
    including errors, warnings, and generated class files.
    
    Args:
        request: TestCompilationRequest with test code and optional parameters
        
    Returns:
        TestCompilationResponse with compilation results
    """
    if not test_compiler:
        raise HTTPException(
            status_code=503, 
            detail="Test compiler not initialized. Make sure API started successfully."
        )
    
    try:
        logger.info("🔨 Compiling Java test code...")
        logger.info(f"  • Test code length: {len(request.test_code)} characters")
        logger.info(f"  • Additional source files: {len(request.source_files or [])}")
        logger.info(f"  • Additional classpath entries: {len(request.additional_classpath or [])}")
        
        # Compile the test
        result = test_compiler.compile_test(
            test_code=request.test_code,
            source_files=request.source_files,
            additional_classpath=request.additional_classpath
        )
        
        # Create response
        response = TestCompilationResponse(
            status="success" if result['success'] else "error",
            success=result['success'],
            errors=result['errors'],
            warnings=result['warnings'],
            compiled_files=result['compiled_files'],
            classpath=result['classpath'],
            compilation_time=result['compilation_time'],
            return_code=result['return_code'],
            stdout=result['stdout'],
            stderr=result['stderr']
        )
        
        logger.info(f"✅ Compilation completed: {'success' if result['success'] else 'failed'}")
        logger.info(f"  • Errors: {len(result['errors'])}")
        logger.info(f"  • Warnings: {len(result['warnings'])}")
        logger.info(f"  • Compiled files: {len(result['compiled_files'])}")
        logger.info(f"  • Time: {result['compilation_time']:.2f}s")
        
        return response
        
    except Exception as e:
        logger.exception(f"❌ Test compilation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test compilation failed: {str(e)}")

@app.get("/api/compile/environment", tags=["Test Compilation"])
async def get_compilation_environment():
    """
    Get Java compilation environment status.
    
    Returns information about Java installation, javac compiler, and JUnit dependencies.
    """
    if not test_compiler:
        raise HTTPException(
            status_code=503, 
            detail="Test compiler not initialized. Make sure API started successfully."
        )
    
    try:
        env_status = test_compiler.check_java_environment()
        return {
            "status": "success",
            "environment": env_status
        }
    except Exception as e:
        logger.exception(f"❌ Failed to check compilation environment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check environment: {str(e)}")

@app.get("/api/projects", tags=["Projects"])
async def list_projects():
    """List all indexed projects"""
    # TODO: Implement project tracking
    return {
        "projects": [],
        "total": 0,
        "message": "Project tracking not yet implemented"
    }

@app.get("/index", tags=["Indexing"])
async def index_project_simple(project_path: str = None, force: bool = False):
    """
    Simple GET endpoint for project indexing.
    
    Usage: GET /index?project_path=/path/to/project&force=true
    """
    if not project_path:
        raise HTTPException(
            status_code=400, 
            detail="project_path parameter is required. Usage: /index?project_path=/path/to/project"
        )
    
    # Create IndexRequest from query parameters
    request = IndexRequest(
        project_path=project_path,
        force=force
    )
    
    # Call the main indexing endpoint
    return await index_project(request)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Clients can subscribe to:
    - Indexing progress
    - Test generation updates
    - System notifications
    """
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Java Unit Test Agent API",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Echo back (for now)
            await websocket.send_json({
                "type": "echo",
                "received": message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Development endpoints
if settings.debug:
    @app.get("/api/debug/config", tags=["Debug"])
    async def debug_config():
        """Get current configuration (debug only)"""
        return {
            "environment": settings.environment,
            "debug": settings.debug,
            "llm_model": settings.llm.openai_model,
            "embedding_model": settings.llm.embedding_model,
            "ports": {
                "api": settings.api.python_api_port,
                "memgraph": settings.database.memgraph_port,
                "qdrant": settings.database.qdrant_port,
                "redis": settings.database.redis_port
            }
        }

# Run server
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=settings.api.python_api_port,
        reload=settings.debug,
        log_level="info"
    )

