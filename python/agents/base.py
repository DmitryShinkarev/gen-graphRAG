"""
Base agent class extending agent-patterns BaseAgent.
Provides common functionality for all Java test generation agents.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import sys
from pathlib import Path
from openai import AsyncOpenAI

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import get_settings
from logger import get_logger

# Langfuse integration for LLM tracing
try:
    from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

# LangSmith integration for LLM tracing
try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

logger = get_logger(__name__)
settings = get_settings()


class BaseTool(ABC):
    """Base class for agent tools"""
    
    name: str = "base_tool"
    description: str = "Base tool description"
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool"""
        pass
    
    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"


class AgentState:
    """
    State object passed between agents in workflow.
    Contains all necessary context and intermediate results.
    """
    
    def __init__(self):
        self.project_path: Optional[str] = None
        self.project_id: Optional[str] = None
        self.target_method: Optional[str] = None
        self.target_file: Optional[str] = None
        
        # Indexing results
        self.indexed_files: List[str] = []
        self.parsed_classes: Dict[str, Any] = {}
        self.graph_nodes: Dict[str, Any] = {}
        
        # Research results
        self.method_context: Dict[str, Any] = {}
        self.dependencies: Dict[str, Any] = {}
        self.similar_methods: List[Dict] = []
        
        # Analysis results
        self.complexity_analysis: Optional[Dict[str, Any]] = None
        self.dependency_analysis: Optional[Dict[str, Any]] = None
        self.edge_case_analysis: Optional[Dict[str, Any]] = None
        self.performance_analysis: Optional[Dict[str, Any]] = None
        self.test_recommendations: Optional[Dict[str, Any]] = None
        
        # Generation results
        self.generated_tests: List[Dict] = []
        self.test_code: Optional[str] = None
        self.source_code: Optional[str] = None
        
        # Coverage results
        self.coverage_metrics: Optional[Dict[str, float]] = None
        self.real_coverage_measured: bool = False
        
        # Critique results
        self.quality_score: int = 0
        self.issues: List[str] = []
        self.suggestions: List[str] = []
        
        # Additional metadata
        self.metadata: Dict[str, Any] = {}
        
        # Metadata
        self.started_at: datetime = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.errors: List[str] = []
        self.steps_completed: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            "project_path": self.project_path,
            "project_id": self.project_id,
            "target_method": self.target_method,
            "target_file": self.target_file,
            "indexed_files": self.indexed_files,
            "generated_tests": self.generated_tests,
            "quality_score": self.quality_score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "steps_completed": self.steps_completed,
            "errors": self.errors,
            # Analysis results
            "complexity_analysis": self.complexity_analysis,
            "dependency_analysis": self.dependency_analysis,
            "edge_case_analysis": self.edge_case_analysis,
            "performance_analysis": self.performance_analysis,
            "test_recommendations": self.test_recommendations
        }


class BaseJavaAgent(ABC):
    """
    Base agent class for Java test generation system.
    Inspired by agent-patterns library but customized for our use case.
    
    Each agent:
    - Has a specific role and responsibilities
    - Uses tools to interact with the system
    - Can communicate via LLM
    - Logs all actions for observability
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        tools: Optional[List[BaseTool]] = None,
        llm_model: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Initialize agent.
        
        Args:
            name: Agent name
            role: Agent role description
            tools: List of tools available to this agent
            llm_model: LLM model to use
            temperature: LLM temperature
        """
        self.name = name
        self.role = role
        self.tools = tools or []
        self.llm_model = llm_model or settings.llm.openai_model
        self.temperature = temperature
        
        # Initialize OpenAI client with tracing if available
        langfuse_enabled = (
            LANGFUSE_AVAILABLE and 
            settings.monitoring.langfuse_public_key and 
            settings.monitoring.langfuse_secret_key
        )
        
        langsmith_enabled = (
            LANGSMITH_AVAILABLE and 
            settings.monitoring.langchain_tracing_v2 and 
            settings.monitoring.langchain_api_key
        )
        
        if langfuse_enabled and langsmith_enabled:
            logger.warning(f"Both Langfuse and LangSmith are enabled for {name}. Langfuse will take precedence.")
        
        if langfuse_enabled:
            logger.info(f"Initializing {name} with Langfuse tracing enabled")
            # Langfuse wraps OpenAI client - initialization is different
            import os
            os.environ["LANGFUSE_PUBLIC_KEY"] = settings.monitoring.langfuse_public_key
            os.environ["LANGFUSE_SECRET_KEY"] = settings.monitoring.langfuse_secret_key
            os.environ["LANGFUSE_HOST"] = settings.monitoring.langfuse_host
            
            self.llm = LangfuseAsyncOpenAI(
                api_key=settings.llm.openai_api_key
            )
            self.tracing_enabled = "langfuse"
        elif langsmith_enabled:
            logger.info(f"Initializing {name} with LangSmith tracing enabled")
            # LangSmith uses environment variables set in server.py
            import os
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = settings.monitoring.langchain_api_key
            os.environ["LANGCHAIN_PROJECT"] = settings.monitoring.langchain_project
            os.environ["LANGCHAIN_ENDPOINT"] = settings.monitoring.langchain_endpoint
            
            self.llm = AsyncOpenAI(api_key=settings.llm.openai_api_key)
            self.tracing_enabled = "langsmith"
        else:
            if not LANGFUSE_AVAILABLE and not LANGSMITH_AVAILABLE:
                logger.warning("Neither Langfuse nor LangSmith libraries available - tracing disabled")
            elif not langfuse_enabled and not langsmith_enabled:
                logger.warning("No tracing keys configured - tracing disabled")
            self.llm = AsyncOpenAI(api_key=settings.llm.openai_api_key)
            self.tracing_enabled = None
        
        # Tool registry
        self.tool_registry = {tool.name: tool for tool in self.tools}
        
        # Initialize LangSmith client if available
        self.langsmith_client = None
        if LANGSMITH_AVAILABLE and langsmith_enabled:
            try:
                self.langsmith_client = Client()
                logger.debug(f"LangSmith client initialized for {name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LangSmith client for {name}: {e}")
        
        # Hybrid approach statistics
        self.hybrid_stats = {
            'llm_calls': 0,
            'regex_calls': 0,
            'fallback_calls': 0,
            'total_analyses': 0
        }
        
        logger.info(f"Initialized agent: {name} ({role}) with {len(self.tools)} tools")
    
    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute agent's main task.
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state
        """
        pass
    
    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Call LLM with messages.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            response_format: Response format specification
        
        Returns:
            LLM response text
        """
        try:
            logger.debug(f"[{self.name}] Calling LLM with {len(messages)} messages")
            
            kwargs = {
                "model": self.llm_model,
                "messages": messages,
                "temperature": self.temperature,
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            if response_format:
                kwargs["response_format"] = response_format
            
            # Add tracing metadata if available
            if self.tracing_enabled == "langfuse":
                kwargs["name"] = f"{self.name}_llm_call"
                kwargs["metadata"] = {
                    "agent_name": self.name,
                    "agent_role": self.role
                }
                logger.info(f"[{self.name}] Langfuse tracing enabled - adding metadata")
            elif self.tracing_enabled == "langsmith":
                # LangSmith automatically traces when environment variables are set
                # We can add custom metadata via tags
                kwargs["tags"] = [f"agent:{self.name}", f"role:{self.role}"]
            
            response = await self.llm.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            logger.debug(f"[{self.name}] LLM response: {len(content)} chars")
            
            # Log successful Langfuse tracing if enabled
            if self.tracing_enabled == "langfuse":
                logger.info(f"[{self.name}] Langfuse trace sent successfully")
            
            return content
        except Exception as e:
            logger.error(f"[{self.name}] LLM call failed: {e}")
            raise
    
    def create_langsmith_run(
        self,
        name: str,
        inputs: Dict[str, Any],
        run_type: str = "chain"
    ) -> Optional[Any]:
        """
        Create a LangSmith run for manual tracing.
        
        Args:
            name: Run name
            inputs: Input data
            run_type: Type of run (chain, tool, etc.)
        
        Returns:
            LangSmith run object or None if not available
        """
        if self.langsmith_client:
            try:
                run = self.langsmith_client.create_run(
                    name=name,
                    run_type=run_type,
                    inputs=inputs,
                    project_name=settings.monitoring.langchain_project,
                    tags=[f"agent:{self.name}", f"role:{self.role}"]
                )
                logger.debug(f"[{self.name}] Created LangSmith run: {name}")
                return run
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to create LangSmith run: {e}")
        return None
    
    def update_langsmith_run(
        self,
        run_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update a LangSmith run.
        
        Args:
            run_id: Run ID
            outputs: Output data
            status: Run status
            error: Error message
        """
        if self.langsmith_client:
            try:
                self.langsmith_client.update_run(
                    run_id=run_id,
                    outputs=outputs,
                    status=status,
                    error=error
                )
                logger.debug(f"[{self.name}] Updated LangSmith run: {run_id}")
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to update LangSmith run: {e}")
    
    def create_langsmith_feedback(
        self,
        run_id: str,
        key: str,
        value: float,
        comment: Optional[str] = None
    ) -> None:
        """
        Create feedback for a LangSmith run.
        
        Args:
            run_id: Run ID
            key: Feedback key
            value: Feedback value
            comment: Optional comment
        """
        if self.langsmith_client:
            try:
                self.langsmith_client.create_feedback(
                    run_id=run_id,
                    key=key,
                    value=value,
                    comment=comment
                )
                logger.debug(f"[{self.name}] Created LangSmith feedback for run: {run_id}")
            except Exception as e:
                logger.warning(f"[{self.name}] Failed to create LangSmith feedback: {e}")
    
    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Use a tool by name.
        
        Args:
            tool_name: Name of the tool
            **kwargs: Tool arguments
        
        Returns:
            Tool execution result
        """
        if tool_name not in self.tool_registry:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        tool = self.tool_registry[tool_name]
        logger.info(f"[{self.name}] Using tool: {tool_name}")
        
        try:
            result = await tool.execute(**kwargs)
            logger.info(f"[{self.name}] Tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Tool '{tool_name}' failed: {e}")
            raise
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for this agent.
        
        Returns:
            System prompt string
        """
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools
        ])
        
        return f"""You are {self.name}, a specialized agent for Java unit test generation.

Role: {self.role}

Available Tools:
{tools_desc}

Your responsibilities:
1. Analyze the provided Java code carefully
2. Use available tools to gather information
3. Follow best practices for unit testing
4. Generate clear, maintainable test code
5. Explain your reasoning

Always:
- Be precise and accurate
- Use proper Java syntax
- Follow JUnit 5 conventions
- Include necessary imports
- Add helpful comments
"""
    
    def log_step(self, step: str, state: AgentState) -> None:
        """Log a completed step"""
        state.steps_completed.append(f"[{self.name}] {step}")
        logger.info(f"[{self.name}] Step completed: {step}")
    
    def log_error(self, error: str, state: AgentState) -> None:
        """Log an error"""
        state.errors.append(f"[{self.name}] {error}")
        logger.error(f"[{self.name}] Error: {error}")
    
    async def execute_with_retry(
        self,
        state: AgentState,
        max_retries: int = 3
    ) -> AgentState:
        """
        Execute agent with retry logic.
        
        Args:
            state: Agent state
            max_retries: Maximum number of retries
        
        Returns:
            Updated state
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"[{self.name}] Execution attempt {attempt + 1}/{max_retries}")
                result = await self.execute(state)
                return result
            except Exception as e:
                logger.error(f"[{self.name}] Execution failed (attempt {attempt + 1}): {e}")
                
                if attempt == max_retries - 1:
                    self.log_error(f"Max retries reached: {str(e)}", state)
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        return state
    
    def update_hybrid_stats(self, method: str):
        """Update hybrid approach statistics"""
        self.hybrid_stats['total_analyses'] += 1
        if method == 'llm':
            self.hybrid_stats['llm_calls'] += 1
        elif method == 'regex':
            self.hybrid_stats['regex_calls'] += 1
        elif method == 'fallback':
            self.hybrid_stats['fallback_calls'] += 1
        
        logger.debug(f"[{self.name}] Hybrid stats: {self.hybrid_stats}")
    
    def get_hybrid_stats(self) -> Dict[str, int]:
        """Get current hybrid approach statistics"""
        return self.hybrid_stats.copy()
    
    def log_hybrid_stats(self):
        """Log hybrid approach statistics"""
        stats = self.hybrid_stats
        total = stats['total_analyses']
        if total > 0:
            llm_pct = (stats['llm_calls'] / total) * 100
            regex_pct = (stats['regex_calls'] / total) * 100
            fallback_pct = (stats['fallback_calls'] / total) * 100
            
            logger.info(f"[{self.name}] Hybrid approach statistics:")
            logger.info(f"  Total analyses: {total}")
            logger.info(f"  LLM calls: {stats['llm_calls']} ({llm_pct:.1f}%)")
            logger.info(f"  Regex calls: {stats['regex_calls']} ({regex_pct:.1f}%)")
            logger.info(f"  Fallback calls: {stats['fallback_calls']} ({fallback_pct:.1f}%)")
    
    def __repr__(self) -> str:
        return f"<Agent: {self.name} ({self.role})>"


class AgentMetrics:
    """Track agent performance metrics"""
    
    def __init__(self):
        self.executions: int = 0
        self.successes: int = 0
        self.failures: int = 0
        self.total_duration: float = 0.0
        self.llm_calls: int = 0
        self.tool_calls: int = 0
    
    def record_execution(
        self,
        success: bool,
        duration: float,
        llm_calls: int = 0,
        tool_calls: int = 0
    ):
        """Record an execution"""
        self.executions += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        self.total_duration += duration
        self.llm_calls += llm_calls
        self.tool_calls += tool_calls
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            "executions": self.executions,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": self.successes / self.executions if self.executions > 0 else 0,
            "avg_duration": self.total_duration / self.executions if self.executions > 0 else 0,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls
        }


if __name__ == "__main__":
    # Test base agent
    class TestTool(BaseTool):
        name = "test_tool"
        description = "A test tool"
        
        async def execute(self, **kwargs):
            return {"result": "success"}
    
    class TestAgent(BaseJavaAgent):
        async def execute(self, state: AgentState) -> AgentState:
            self.log_step("Test step", state)
            result = await self.use_tool("test_tool")
            print(f"Tool result: {result}")
            return state
    
    # Create agent
    tool = TestTool()
    agent = TestAgent("TestAgent", "Testing role", tools=[tool])
    
    # Test execution
    state = AgentState()
    
    async def test():
        result_state = await agent.execute(state)
        print(f"Steps completed: {result_state.steps_completed}")
    
    asyncio.run(test())
    
    print("\n✅ Base agent test passed!")

