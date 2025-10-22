"""
GeneratorAgent - Generates unit tests using LLM.

Responsibilities:
- Analyze target method
- Create test cases with LLM
- Generate mocks for dependencies
- Format and validate generated code

Pattern: Prompt Engineering (4.2)
"""

from typing import List, Dict, Any, Optional
import json
import re
import os

from agents.base import BaseJavaAgent, AgentState
from logger import get_logger

logger = get_logger(__name__)


class GeneratorAgent(BaseJavaAgent):
    """
    Agent responsible for generating unit tests.
    
    Workflow:
    1. Analyze method signature and context
    2. Generate test cases using LLM
    3. Create mocks for dependencies
    4. Format code properly
    5. Add necessary imports
    """
    
    def __init__(self, test_framework: str = "junit5", graph=None):
        """
        Initialize GeneratorAgent.
        
        Args:
            test_framework: Test framework to use (junit5, junit4, testng)
            graph: CodeGraph instance for accessing class data
        """
        super().__init__(
            name="GeneratorAgent",
            role="Unit test code generation",
            tools=[],
            temperature=0.7  # Higher temperature for creative test generation
        )
        
        self.graph = graph
        
        self.test_framework = test_framework
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute test generation workflow.
        
        Args:
            state: Current agent state with method_context
        
        Returns:
            Updated state with generated test code
        """
        logger.info("="*80)
        logger.info(f"[{self.name}] ✨ STARTING TEST CODE GENERATION")
        logger.info("="*80)
        
        try:
            # Get target method info
            method_info = self._extract_method_info(state)
            
            if not method_info:
                error_msg = "No method information available for generation"
                logger.error(f"  ❌ {error_msg}")
                self.log_error(error_msg, state)
                return state
            
            logger.info(f"  📝 Target method: {method_info.get('name', 'unknown')}")
            logger.info(f"  📦 Class: {method_info.get('class_name', 'unknown')}")
            logger.info(f"  🔢 Complexity: {method_info.get('complexity', 'N/A')}")
            logger.info("")
            
            self.log_step(f"Analyzing method: {method_info['name']}", state)
            
            # Count context methods
            context_methods = state.method_context.get('ranked_methods', [])
            logger.info(f"  📚 Using RAG context:")
            logger.info(f"    • Total methods in context: {len(context_methods)}")
            logger.info(f"    • Dependencies: {len(state.dependencies.get('methods', []))}")
            logger.info(f"    • Similar methods: {len(state.similar_methods)}")
            logger.info("")
            
            # Log analysis results if available
            if state.complexity_analysis:
                complexity = state.complexity_analysis
                logger.info(f"  🧠 Using analysis results:")
                logger.info(f"    • Complexity: {complexity['complexity_level']} (CC: {complexity['cyclomatic_complexity']})")
                logger.info(f"    • Branches: {complexity['branch_count']}")
                if complexity.get('complexity_patterns'):
                    logger.info(f"    • Patterns: {', '.join(complexity['complexity_patterns'][:2])}")
                logger.info("")
            
            if state.edge_case_analysis:
                edge_cases = state.edge_case_analysis
                logger.info(f"  🎯 Edge case analysis:")
                logger.info(f"    • Edge cases: {len(edge_cases['edge_cases'])}")
                logger.info(f"    • Exceptions: {len(edge_cases['exception_scenarios'])}")
                logger.info(f"    • Boundaries: {len(edge_cases['boundary_conditions'])}")
                logger.info("")
            
            if state.test_recommendations:
                test_recs = state.test_recommendations
                logger.info(f"  💡 Test recommendations:")
                logger.info(f"    • Recommended tests: {test_recs['recommended_test_count']}")
                if test_recs.get('test_priorities'):
                    logger.info(f"    • Priority: {test_recs['test_priorities'][0]}")
                logger.info("")
            
            # Build prompt
            logger.info(f"  🏗️  Building generation prompt...")
            prompt = self._build_generation_prompt(method_info, state)
            prompt_length = len(prompt)
            logger.info(f"    ✅ Prompt built ({prompt_length} chars)")
            logger.info(f"       Context includes: signature, source code, dependencies, similar examples")
            if state.complexity_analysis or state.edge_case_analysis:
                logger.info(f"       Analysis includes: complexity, edge cases, test recommendations")
            logger.info("")
            
            self.log_step("Built generation prompt", state)
            
            # Generate test with LLM
            logger.info(f"  🤖 Calling LLM ({self.llm_model})...")
            logger.info(f"     Temperature: {self.temperature}")
            logger.info(f"     Framework: {self.test_framework}")
            test_code = await self._generate_test_code(prompt)
            logger.info(f"    ✅ LLM returned {len(test_code)} characters")
            logger.info("")
            
            self.log_step("Generated test code", state)
            
            # Extract and format code
            logger.info(f"  🔧 Formatting and extracting code...")
            formatted_code = self._extract_and_format_code(test_code)
            logger.info(f"    ✅ Formatted code: {len(formatted_code)} characters")
            logger.info(f"    ✅ Test methods: {formatted_code.count('@Test')}")
            logger.info("")
            
            # Update state
            state.test_code = formatted_code
            # Get full class source code for coverage measurement
            state.source_code = await self._get_full_class_source(method_info, state)
            state.generated_tests.append({
                "method": method_info['name'],
                "code": formatted_code,
                "framework": self.test_framework
            })
            
            logger.info("="*80)
            logger.info(f"[{self.name}] ✅ TEST GENERATION COMPLETED")
            logger.info(f"  • Generated {formatted_code.count('@Test')} test methods")
            logger.info(f"  • Code length: {len(formatted_code)} characters")
            logger.info(f"  • Framework: {self.test_framework}")
            logger.info("="*80)
            logger.info("")
            
            return state
            
        except Exception as e:
            error_msg = f"Test generation failed: {str(e)}"
            logger.exception(f"[{self.name}] {error_msg}")
            self.log_error(error_msg, state)
            return state
    
    async def _get_full_class_source(self, method_info: Dict[str, Any], state: AgentState) -> str:
        """Get full class source code with all dependencies"""
        try:
            # Get main class source code
            main_class_source = await self._get_main_class_source(method_info)
            if not main_class_source:
                return method_info.get("source_code", "")
            
            # Analyze dependencies
            dependencies = await self._analyze_dependencies(main_class_source, method_info)
            logger.info(f"  📦 Found {len(dependencies)} dependencies")
            
            # Collect all dependency source codes
            dependency_sources = []
            for dep_name, dep_info in dependencies.items():
                dep_source = await self._get_dependency_source(dep_name, dep_info)
                if dep_source:
                    dependency_sources.append(dep_source)
                    logger.info(f"  ✅ Added dependency: {dep_name}")
                else:
                    logger.warning(f"  ⚠️  Could not find dependency: {dep_name}")
            
            # Combine main class with dependencies
            if dependency_sources:
                combined_source = "\n\n".join(dependency_sources + [main_class_source])
                logger.info(f"  📄 Combined source with dependencies: {len(combined_source)} chars")
                return combined_source
            else:
                logger.info(f"  📄 Using main class source only: {len(main_class_source)} chars")
                return main_class_source
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to get full class source with dependencies: {e}")
            # Return method source as fallback
            return method_info.get("source_code", "")
    
    async def _get_main_class_source(self, method_info: Dict[str, Any]) -> str:
        """Get main class source code"""
        try:
            # Priority 1: Read full source from file_path (most reliable)
            file_path = method_info.get("file_path")
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    full_source = f.read()
                    logger.info(f"  📄 Read {len(full_source)} chars from file: {file_path}")
                    return full_source
            
            # Priority 2: Try to get from class_id in graph (may not have full source)
            class_id = method_info.get("class_id")
            if class_id:
                # Get full class from graph
                class_data = self.graph.get_class_by_id(class_id)
                if class_data and class_data.get("source_code"):
                    logger.info(f"  📄 Read {len(class_data['source_code'])} chars from graph")
                    return class_data["source_code"]
                else:
                    logger.warning(f"  ⚠️  Class data found but no source_code field")
            
            logger.warning(f"  ⚠️  Could not find source code for method")
            return ""
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to get main class source: {e}")
            return ""
    
    async def _analyze_dependencies(self, source_code: str, method_info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Analyze source code to find dependencies"""
        dependencies = {}
        
        try:
            # Extract class name from source code
            class_name = self._extract_class_name(source_code)
            if not class_name:
                return dependencies
            
            # Find all class references in the source code
            class_refs = self._find_class_references(source_code, class_name)
            logger.info(f"  🔍 Found {len(class_refs)} class references in {class_name}")
            
            # For each reference, try to find the class in the graph
            for ref in class_refs:
                if ref not in dependencies:
                    dep_info = await self._find_class_in_graph(ref, method_info)
                    if dep_info:
                        dependencies[ref] = dep_info
            
            return dependencies
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to analyze dependencies: {e}")
            return dependencies
    
    def _extract_class_name(self, source_code: str) -> Optional[str]:
        """Extract class name from source code"""
        try:
            import re
            # Look for class declaration
            match = re.search(r'public\s+class\s+(\w+)', source_code)
            if match:
                return match.group(1)
            
            # Look for any class declaration
            match = re.search(r'class\s+(\w+)', source_code)
            if match:
                return match.group(1)
            
            return None
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to extract class name: {e}")
            return None
    
    def _find_class_references(self, source_code: str, exclude_class: str) -> List[str]:
        """Find all class references in source code"""
        try:
            import re
            class_refs = set()
            
            # Find new ClassName() patterns
            new_pattern = r'new\s+(\w+)\s*\('
            matches = re.findall(new_pattern, source_code)
            for match in matches:
                if match != exclude_class and not self._is_java_builtin(match):
                    class_refs.add(match)
            
            # Find ClassName variable declarations
            var_pattern = r'(\w+)\s+\w+\s*=\s*new\s+(\w+)\s*\('
            matches = re.findall(var_pattern, source_code)
            for match in matches:
                if len(match) >= 2 and match[1] != exclude_class and not self._is_java_builtin(match[1]):
                    class_refs.add(match[1])
            
            # Find method parameter types
            param_pattern = r'(\w+)\s+\w+\s*[,\)]'
            matches = re.findall(param_pattern, source_code)
            for match in matches:
                if match != exclude_class and not self._is_java_builtin(match):
                    class_refs.add(match)
            
            return list(class_refs)
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to find class references: {e}")
            return []
    
    def _is_java_builtin(self, class_name: str) -> bool:
        """Check if class name is a Java builtin"""
        java_builtins = {
            'String', 'Integer', 'Double', 'Float', 'Long', 'Boolean', 'Character',
            'Object', 'Exception', 'RuntimeException', 'IllegalArgumentException',
            'NullPointerException', 'IndexOutOfBoundsException', 'System', 'Math',
            'ArrayList', 'HashMap', 'HashSet', 'List', 'Map', 'Set', 'Collection',
            'Iterator', 'Comparable', 'Serializable', 'Cloneable', 'Runnable',
            'Thread', 'Date', 'Calendar', 'SimpleDateFormat', 'Scanner', 'BufferedReader',
            'File', 'FileReader', 'FileWriter', 'PrintWriter', 'IOException',
            'FileNotFoundException', 'NumberFormatException', 'ArrayIndexOutOfBoundsException',
            'ClassCastException', 'IllegalStateException', 'UnsupportedOperationException',
            'ConcurrentModificationException', 'NoSuchElementException', 'InputMismatchException'
        }
        return class_name in java_builtins
    
    async def _find_class_in_graph(self, class_name: str, method_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find class in the graph by name"""
        try:
            if not self.graph:
                logger.warning(f"  ⚠️  Graph is None for class {class_name}")
                return None
            
            # Try to find class by name in the graph
            if hasattr(self.graph, 'get_class_by_name'):
                result = self.graph.get_class_by_name(class_name)
                if result:
                    logger.info(f"  ✅ Found class {class_name} via get_class_by_name")
                    return result
                else:
                    logger.warning(f"  ⚠️  get_class_by_name returned None for {class_name}")
            
            # Fallback: search in all classes
            if hasattr(self.graph, 'get_all_classes'):
                all_classes = self.graph.get_all_classes()
                logger.info(f"  🔍 Searching in {len(all_classes)} classes for {class_name}")
                for class_data in all_classes:
                    if class_data.get('name') == class_name:
                        logger.info(f"  ✅ Found class {class_name} via get_all_classes")
                        return class_data
                logger.warning(f"  ⚠️  Class {class_name} not found in {len(all_classes)} classes")
            
            logger.warning(f"  ⚠️  Class {class_name} not found in graph")
            return None
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to find class {class_name} in graph: {e}")
            return None
    
    async def _get_dependency_source(self, class_name: str, dep_info: Dict[str, Any]) -> Optional[str]:
        """Get source code for a dependency"""
        try:
            # Priority 1: Try to get from file_path (most reliable)
            file_path = dep_info.get("file_path")
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    full_source = f.read()
                    logger.info(f"  📄 Read dependency {class_name}: {len(full_source)} chars from file")
                    return full_source
            
            # Priority 2: Try to get from graph data (may not have full source)
            if dep_info.get("source_code"):
                logger.info(f"  📄 Read dependency {class_name}: {len(dep_info['source_code'])} chars from graph")
                return dep_info["source_code"]
            
            logger.warning(f"  ⚠️  No source found for dependency {class_name}")
            return None
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to get dependency source for {class_name}: {e}")
            return None
    
    def _extract_method_info(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """Extract method information from state"""
        # Try to get from method_context
        if state.method_context and state.method_context.get("ranked_methods"):
            # First method should be the target
            ranked = state.method_context["ranked_methods"]
            if ranked:
                return ranked[0].get("data", {})
        
        # Try to get from parsed_classes
        if state.parsed_classes:
            for class_data in state.parsed_classes.values():
                class_info = class_data.get("class_info", {})
                methods = class_info.get("methods", [])
                if methods:
                    return methods[0]  # Return first method for testing
        
        return None
    
    def _build_generation_prompt(
        self,
        method_info: Dict[str, Any],
        state: AgentState
    ) -> str:
        """Build prompt for LLM test generation"""
        
        # Extract method details
        method_name = method_info.get("name", "unknown")
        signature = method_info.get("full_signature", method_info.get("signature", ""))
        source_code = method_info.get("source_code", "")
        
        # Use class_name from state.metadata if available (user-specified), otherwise from method_info
        class_name = state.metadata.get("class_name") if state.metadata else None
        if not class_name:
            class_name = method_info.get("class_name", "UnknownClass")
        
        # Log which class name is being used
        logger.info(f"  🎯 Using class name: '{class_name}' (from {'metadata' if state.metadata and state.metadata.get('class_name') else 'method_info'})")
        
        complexity = method_info.get("complexity", 0)
        
        # Get dependencies
        dependencies = state.dependencies or {}
        dependent_methods = dependencies.get("methods", [])
        used_fields = dependencies.get("fields", [])
        
        # Build prompt
        prompt = f"""Generate comprehensive JUnit 5 unit tests for the following Java method.

## Target Method

**Class:** {class_name}
**Method:** {method_name}
**Signature:** {signature}
**Complexity:** {complexity}

**Source Code:**
```java
{source_code}
```

## Code Analysis Results

"""
        
        # Add analysis results if available
        if state.complexity_analysis:
            complexity_analysis = state.complexity_analysis
            prompt += f"**Complexity Analysis:**\n"
            prompt += f"- Cyclomatic Complexity: {complexity_analysis['cyclomatic_complexity']}\n"
            prompt += f"- Complexity Level: {complexity_analysis['complexity_level']}\n"
            prompt += f"- Branch Count: {complexity_analysis['branch_count']}\n"
            if complexity_analysis.get('complexity_patterns'):
                prompt += f"- Patterns: {', '.join(complexity_analysis['complexity_patterns'])}\n"
            prompt += "\n"
        
        if state.dependency_analysis:
            dep_analysis = state.dependency_analysis
            prompt += f"**Dependency Analysis:**\n"
            prompt += f"- External Dependencies: {len(dep_analysis['external_deps'])}\n"
            prompt += f"- Critical Dependencies: {len(dep_analysis['critical_deps'])}\n"
            if dep_analysis.get('mock_recommendations'):
                prompt += f"- Mocking Recommendations: {len(dep_analysis['mock_recommendations'])}\n"
            prompt += "\n"
        
        if state.edge_case_analysis:
            edge_analysis = state.edge_case_analysis
            prompt += f"**Edge Case Analysis:**\n"
            prompt += f"- Edge Cases Identified: {len(edge_analysis['edge_cases'])}\n"
            prompt += f"- Exception Scenarios: {len(edge_analysis['exception_scenarios'])}\n"
            prompt += f"- Boundary Conditions: {len(edge_analysis['boundary_conditions'])}\n"
            prompt += "\n"
        
        if state.test_recommendations:
            test_recs = state.test_recommendations
            prompt += f"**Test Recommendations:**\n"
            prompt += f"- Recommended Test Count: {test_recs['recommended_test_count']}\n"
            if test_recs.get('test_priorities'):
                prompt += f"- Priority Focus: {test_recs['test_priorities'][0] if test_recs['test_priorities'] else 'Standard coverage'}\n"
            prompt += "\n"

        prompt += """## Context

"""
        
        # Add dependencies info
        if dependent_methods:
            prompt += "**Called Methods:**\n"
            for method in dependent_methods[:5]:
                m_name = method.get("name", "unknown")
                m_sig = method.get("signature", "")
                prompt += f"- {m_name}: {m_sig}\n"
            prompt += "\n"
        
        if used_fields:
            prompt += "**Used Fields:**\n"
            for field in used_fields[:5]:
                f_name = field.get("name", "unknown")
                f_type = field.get("type", "")
                prompt += f"- {f_type} {f_name}\n"
            prompt += "\n"
        
        # Add improvement feedback if this is a regeneration
        if state.metadata and "improvement_feedback" in state.metadata:
            feedback = state.metadata["improvement_feedback"]
            previous_score = state.metadata.get("previous_score", 0)
            prompt += f"## IMPORTANT: Quality Improvement Required\n\n"
            prompt += f"Previous test scored only {previous_score}/100. Please address these issues:\n\n"
            prompt += feedback
            prompt += "\n\n"
        
        # Add similar methods from vector search (for reference)
        if state.similar_methods:
            prompt += "**Similar Methods (for reference):**\n\n"
            for i, similar in enumerate(state.similar_methods[:3], 1):  # Top 3
                payload = similar.get("payload", {})
                s_name = payload.get("method_name", "unknown")
                s_class = payload.get("class_name", "unknown")
                s_signature = payload.get("signature", "")
                s_code = payload.get("source_code", "")
                
                prompt += f"{i}. `{s_class}.{s_name}`\n"
                if s_signature:
                    prompt += f"   Signature: `{s_signature}`\n"
                if s_code and len(s_code) > 0:
                    # Truncate long code
                    code_snippet = s_code if len(s_code) < 300 else s_code[:300] + "..."
                    prompt += f"   Code:\n```java\n{code_snippet}\n```\n"
                prompt += "\n"
        
        # Add auto-generated mock template if dependencies exist
        auto_mock_template = self._generate_auto_mocks(state)
        if auto_mock_template:
            prompt += "**Auto-Generated Mock Template (USE THIS PATTERN):**\n\n"
            prompt += "```java\n"
            prompt += auto_mock_template
            prompt += "```\n\n"
        
        # Add detailed test requirements based on analysis
        prompt += """
## Test Requirements

Generate a complete test class with:

1. **Test Class Name:** `{class_name}Test`
2. **Test Framework:** JUnit 5
3. **Mocking Strategy:** Mockito for dependencies

"""
        
        # Add specific requirements based on analysis
        if state.test_recommendations:
            test_recs = state.test_recommendations
            prompt += f"4. **Test Count:** Generate approximately {test_recs['recommended_test_count']} test methods\n"
            
            if test_recs.get('test_priorities'):
                prompt += "5. **Test Priorities:**\n"
                for i, priority in enumerate(test_recs['test_priorities'][:5], 1):
                    prompt += f"   - {i}. {priority}\n"
                prompt += "\n"
            
            if test_recs.get('special_considerations'):
                prompt += "6. **Special Considerations:**\n"
                for consideration in test_recs['special_considerations'][:3]:
                    prompt += f"   - {consideration}\n"
                prompt += "\n"
        
        # Add edge case requirements if available
        if state.edge_case_analysis:
            edge_analysis = state.edge_case_analysis
            prompt += "7. **Specific Edge Cases to Test:**\n"
            for edge_case in edge_analysis['edge_cases'][:5]:
                prompt += f"   - {edge_case['description']}: {edge_case['test_suggestion']}\n"
            prompt += "\n"
            
            if edge_analysis['exception_scenarios']:
                prompt += "8. **Exception Scenarios:**\n"
                for exc_scenario in edge_analysis['exception_scenarios'][:3]:
                    prompt += f"   - {exc_scenario['description']}: {exc_scenario['test_suggestion']}\n"
                prompt += "\n"
        
        # Add dependency mocking requirements
        if state.dependency_analysis and state.dependency_analysis.get('mock_recommendations'):
            prompt += "9. **CRITICAL: Required Mocking (MANDATORY):**\n"
            for mock_rec in state.dependency_analysis['mock_recommendations'][:5]:  # Show more recommendations
                priority = mock_rec.get('priority', 'medium')
                mandatory = mock_rec.get('mandatory', False)
                reason = mock_rec.get('reason', '')
                
                if mandatory:
                    prompt += f"   - 🚨 MANDATORY: {mock_rec['recommendation']}\n"
                    if reason:
                        prompt += f"     Reason: {reason}\n"
                    if mock_rec.get('examples'):
                        prompt += f"     Examples: {', '.join(mock_rec['examples'][:2])}\n"
                else:
                    prompt += f"   - {mock_rec['recommendation']}\n"
            prompt += "\n"

        # Add special section for methods with external dependencies
        has_external_deps = False
        if state.dependency_analysis and state.dependency_analysis.get('external_deps'):
            external_deps = state.dependency_analysis['external_deps']
            has_external_deps = len(external_deps) > 0
            
            if has_external_deps:
                prompt += "10. **🚨 CRITICAL: This method has external dependencies that MUST be mocked:**\n"
                for dep in external_deps[:3]:  # Show top 3 dependencies
                    category = dep.get('category', 'unknown')
                    criticality = dep.get('criticality', 'medium')
                    matches = dep.get('matches', [])
                    
                    prompt += f"   - {category.upper()} dependency (Criticality: {criticality})\n"
                    if matches:
                        prompt += f"     Found: {', '.join(matches[:2])}\n"
                prompt += "   ⚠️  FAILURE TO MOCK THESE DEPENDENCIES WILL RESULT IN 0/15 MOCKING SCORE\n\n"

        prompt += """11. **Coverage Requirements:**
    - Happy path test (normal case)
    - Edge cases (null inputs, empty collections, boundary values)
    - Exception scenarios
    - Complex logic branches (based on complexity analysis)

12. **🚨 CRITICAL: Mocking Requirements (MANDATORY - NO EXCEPTIONS):**
    
    **MANDATORY IMPORTS:**
    ```java
    import static org.mockito.Mockito.*;
    import org.mockito.Mock;
    import org.mockito.MockedStatic;
    import org.mockito.junit.jupiter.MockitoExtension;
    import org.junit.jupiter.api.extension.ExtendWith;
    ```
    
    **MANDATORY MOCKING PATTERNS:**
    - ALWAYS use Mockito for external dependencies - THIS IS MANDATORY
    - Use `@Mock` annotations for mock fields
    - Use `mock(ClassName.class)` for mock creation
    - Use `when(mock.method()).thenReturn(value)` for mock setup
    - Use `verify(mock).method()` for verification
    - Mock ANY external classes, services, or dependencies
    
    **SPECIFIC MOCKING REQUIREMENTS:**
    - 🚨 System.getenv() calls - MANDATORY for predictable tests
      ```java
      try (MockedStatic<System> mockedSystem = mockStatic(System.class)) {
          mockedSystem.when(() -> System.getenv("VAR")).thenReturn("test_value");
      }
      ```
    - 🚨 Object creation with 'new' keyword - MANDATORY for test isolation
      ```java
      @Mock private ClassName mockObject;
      when(mockObject.method()).thenReturn(expectedValue);
      ```
    - 🚨 Static method calls - MANDATORY when possible
      ```java
      try (MockedStatic<StaticClass> mockedStatic = mockStatic(StaticClass.class)) {
          mockedStatic.when(() -> StaticClass.staticMethod()).thenReturn(value);
      }
      ```
    - 🚨 Database operations - MANDATORY for isolation
      ```java
      @Mock private Repository mockRepository;
      when(mockRepository.save(any())).thenReturn(savedEntity);
      ```
    - 🚨 Network calls - MANDATORY for isolation
      ```java
      @Mock private RestTemplate mockRestTemplate;
      when(mockRestTemplate.getForObject(anyString(), any())).thenReturn(response);
      ```
    - 🚨 File operations - MANDATORY for isolation
      ```java
      try (MockedStatic<Files> mockedFiles = mockStatic(Files.class)) {
          mockedFiles.when(() -> Files.readAllLines(any())).thenReturn(lines);
      }
      ```
    
    **MOCKING SETUP PATTERN:**
    ```java
    @ExtendWith(MockitoExtension.class)
    class TestClass {
        @Mock private Dependency mockDependency;
        
        @BeforeEach
        void setUp() {
            // Setup mock behaviors
            when(mockDependency.method()).thenReturn(expectedValue);
        }
    }
    ```
    
    ⚠️  FAILURE TO MOCK EXTERNAL DEPENDENCIES WILL RESULT IN 0/15 MOCKING SCORE

13. **Best Practices:**
    - Use `@Test` annotations
    - Clear test method names (should_ExpectedBehavior_When_Condition)
    - Arrange-Act-Assert pattern
    - Meaningful assertions with messages
    - Mock external dependencies (REQUIRED)
    - Clean test data setup

14. **Code Quality:**
    - Add all necessary imports (including Mockito)
    - Include class-level setup (`@BeforeEach` if needed)
    - Add helpful comments
    - Follow Java naming conventions

## Output Format

Provide ONLY the complete Java test class code. No explanations, just the code.

```java
// Your test class here
```
"""
        
        return prompt.replace("{class_name}", class_name)
    
    async def _generate_test_code(self, prompt: str) -> str:
        """Generate test code using LLM"""
        logger.info(f"[{self.name}] Calling LLM for test generation")
        
        messages = [
            {
                "role": "system",
                "content": self.get_system_prompt()
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = await self.call_llm(messages, max_tokens=2000)
        return response
    
    def _extract_and_format_code(self, llm_response: str) -> str:
        """Extract code from LLM response and format it"""
        # Try to extract code from markdown code blocks
        code_pattern = r"```java\s*(.*?)\s*```"
        matches = re.findall(code_pattern, llm_response, re.DOTALL)
        
        if matches:
            code = matches[0]
        else:
            # No code blocks, assume entire response is code
            code = llm_response
        
        # Clean up
        code = code.strip()
        
        # Ensure proper formatting
        code = self._ensure_imports(code)
        
        return code
    
    def _ensure_imports(self, code: str) -> str:
        """Ensure all necessary imports are present"""
        imports = []
        
        # JUnit 5 imports
        if "@Test" in code or "@BeforeEach" in code or "@AfterEach" in code:
            if "import org.junit.jupiter.api" not in code:
                imports.append("import org.junit.jupiter.api.Test;")
                if "@BeforeEach" in code:
                    imports.append("import org.junit.jupiter.api.BeforeEach;")
                if "@AfterEach" in code:
                    imports.append("import org.junit.jupiter.api.AfterEach;")
        
        # Mockito imports
        if "@Mock" in code or "mock(" in code.lower():
            if "import org.mockito" not in code:
                imports.append("import org.mockito.Mock;")
                imports.append("import org.mockito.Mockito;")
                if "@InjectMocks" in code:
                    imports.append("import org.mockito.InjectMocks;")
        
        # Assertions
        if "assert" in code.lower():
            if "import static org.junit.jupiter.api.Assertions" not in code:
                imports.append("import static org.junit.jupiter.api.Assertions.*;")
        
        # Add imports if not present
        if imports and "package " in code:
            # Find package declaration
            package_end = code.find(";", code.find("package ")) + 1
            import_block = "\n".join(imports)
            code = code[:package_end] + "\n\n" + import_block + "\n" + code[package_end:]
        elif imports:
            # No package, add imports at the beginning
            import_block = "\n".join(imports)
            code = import_block + "\n\n" + code
        
        return code
    
    def get_system_prompt(self) -> str:
        """Override to provide specialized system prompt"""
        return """You are an expert Java test generation AI specialized in creating high-quality, production-ready unit tests.

CRITICAL REQUIREMENTS (must include ALL):

1. PACKAGE & IMPORTS:
   - Always start with: package com.example.test;
   - Import all JUnit 5 annotations: @Test, @BeforeEach, @DisplayName
   - Import assertions: import static org.junit.jupiter.api.Assertions.*;
   - Import Mockito if needed: @Mock, @InjectMocks, when(), verify()

2. TEST CLASS STRUCTURE:
   - Class name: [ClassName]Test (e.g., CalculatorTest)
   - Use @BeforeEach for setup
   - Initialize objects properly

3. TEST METHODS (generate 5-8 tests):
   - ✅ Happy path test (normal case)
   - ✅ Edge cases: null, empty, zero, negative, max/min values
   - ✅ Boundary conditions: Integer.MAX_VALUE, Integer.MIN_VALUE
   - ✅ Exception testing: use assertThrows for expected exceptions
   - ✅ Multiple scenarios per edge case

4. TEST METHOD NAMING:
   - Use: shouldDoSomethingWhenCondition
   - Examples: shouldReturnZeroWhenInputIsNull, shouldThrowExceptionWhenDivideByZero
   - Add @DisplayName("Human readable description")

5. ARRANGE-ACT-ASSERT:
   - Always include comments: // Arrange, // Act, // Assert
   - Clear separation of test phases

6. ASSERTIONS:
   - ALWAYS add descriptive messages: assertEquals(expected, actual, "message")
   - Use specific assertions: assertNotNull, assertTrue, assertFalse, assertThrows
   - Multiple assertions per test when appropriate

7. CODE QUALITY:
   - Proper indentation (4 spaces)
   - No duplicate code
   - Clean, readable
   - Professional comments

EXAMPLE OUTPUT STRUCTURE:
```java
package com.example.test;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {
    
    private Calculator calculator;
    
    @BeforeEach
    void setUp() {
        calculator = new Calculator();
    }
    
    @Test
    @DisplayName("Should return sum when adding two positive numbers")
    void shouldReturnSumWhenAddingTwoPositiveNumbers() {
        // Arrange
        int a = 5;
        int b = 3;
        
        // Act
        int result = calculator.add(a, b);
        
        // Assert
        assertEquals(8, result, "5 + 3 should equal 8");
    }
    
    @Test
    @DisplayName("Should handle zero correctly")
    void shouldHandleZeroCorrectly() {
        // Arrange & Act & Assert
        assertEquals(0, calculator.add(0, 0), "0 + 0 should equal 0");
        assertEquals(5, calculator.add(5, 0), "5 + 0 should equal 5");
        assertEquals(5, calculator.add(0, 5), "0 + 5 should equal 5");
    }
    
    @Test
    @DisplayName("Should handle negative numbers")
    void shouldHandleNegativeNumbers() {
        // Act & Assert
        assertEquals(-8, calculator.add(-5, -3), "-5 + -3 should equal -8");
        assertEquals(2, calculator.add(5, -3), "5 + -3 should equal 2");
    }
    
    @Test
    @DisplayName("Should handle maximum integer values without overflow")
    void shouldHandleMaximumIntegerValues() {
        // Arrange
        int nearMax = Integer.MAX_VALUE - 1;
        
        // Act
        int result = calculator.add(nearMax, 1);
        
        // Assert
        assertEquals(Integer.MAX_VALUE, result, "Should handle near-max values");
    }
}
```

OUTPUT ONLY THE COMPLETE TEST CLASS. No explanations, no markdown formatting, just pure Java code.
"""

    def _generate_auto_mocks(self, state: AgentState) -> str:
        """
        Automatically generate mock setup code based on dependency analysis.
        Enhanced with intelligent mock generation for complex scenarios.
        
        Returns:
            String containing mock setup code
        """
        if not state.dependency_analysis:
            return ""
        
        mock_code = ""
        external_deps = state.dependency_analysis.get('external_deps', [])
        mock_recommendations = state.dependency_analysis.get('mock_recommendations', [])
        
        if not external_deps and not mock_recommendations:
            return ""
        
        # NEW: Enhanced analysis for complex scenarios
        method_info = state.method_info
        source_code = method_info.get('source_code', '') if method_info else ''
        
        # Analyze method signature for parameter types
        method_signature = method_info.get('signature', '') if method_info else ''
        parameter_types = self._extract_parameter_types(method_signature)
        
        # Analyze return type
        return_type = method_info.get('return_type', 'void') if method_info else 'void'
        
        # Analyze method complexity
        complexity_score = self._calculate_method_complexity(source_code)
        
        # Determine mock strategy based on complexity
        mock_strategy = self._determine_mock_strategy(complexity_score, external_deps)
        
        # Generate imports
        mock_code += "    // Auto-generated mock imports\n"
        mock_code += "    import static org.mockito.Mockito.*;\n"
        mock_code += "    import org.mockito.Mock;\n"
        mock_code += "    import org.mockito.MockedStatic;\n"
        mock_code += "    import org.mockito.junit.jupiter.MockitoExtension;\n"
        mock_code += "    import org.junit.jupiter.api.extension.ExtendWith;\n\n"
        
        # Generate class-level annotations based on strategy
        if mock_strategy == 'comprehensive':
            mock_code += "    @ExtendWith(MockitoExtension.class)\n"
            mock_code += "    @SpringBootTest\n"  # For comprehensive Spring testing
            mock_code += "    @TestPropertySource(properties = {\n"
            mock_code += "        \"spring.datasource.url=jdbc:h2:mem:testdb\",\n"
            mock_code += "        \"spring.jpa.hibernate.ddl-auto=create-drop\"\n"
            mock_code += "    })\n"
        elif mock_strategy == 'moderate':
            mock_code += "    @ExtendWith(MockitoExtension.class)\n"
            mock_code += "    @MockitoSettings(strictness = Strictness.LENIENT)\n"
        else:
            mock_code += "    @ExtendWith(MockitoExtension.class)\n"
        
        mock_code += "    class AutoMockedTest {\n\n"
        
        # Generate mock fields based on external dependencies
        mock_fields = set()
        for dep in external_deps:
            category = dep.get('category', '')
            matches = dep.get('matches', [])
            
            if category == 'database':
                mock_fields.add('@Mock private Repository mockRepository;')
                mock_fields.add('@Mock private EntityManager mockEntityManager;')
            elif category == 'network':
                mock_fields.add('@Mock private RestTemplate mockRestTemplate;')
                mock_fields.add('@Mock private HttpClient mockHttpClient;')
            elif category == 'file_system':
                mock_fields.add('@Mock private File mockFile;')
                mock_fields.add('@Mock private InputStream mockInputStream;')
            elif category == 'environment':
                mock_fields.add('// System.getenv() will be mocked with MockedStatic')
            elif category == 'object_creation':
                # Extract class names from matches
                for match in matches:
                    if 'new ' in match:
                        class_name = match.split('new ')[1].split('(')[0].strip()
                        if class_name and class_name[0].isupper():
                            mock_fields.add(f'@Mock private {class_name} mock{class_name};')
            elif category == 'security':
                mock_fields.add('@Mock private SecurityContext mockSecurityContext;')
                mock_fields.add('@Mock private Authentication mockAuthentication;')
            elif category == 'validation':
                mock_fields.add('@Mock private Validator mockValidator;')
            elif category == 'serialization':
                mock_fields.add('@Mock private ObjectMapper mockObjectMapper;')
            elif category == 'caching':
                mock_fields.add('@Mock private CacheManager mockCacheManager;')
            elif category == 'messaging':
                mock_fields.add('@Mock private MessageProducer mockMessageProducer;')
            elif category == 'scheduling':
                mock_fields.add('@Mock private TaskScheduler mockTaskScheduler;')
            elif category == 'metrics':
                mock_fields.add('@Mock private MeterRegistry mockMeterRegistry;')
            # NEW: Spring Boot specific mock fields
            elif category == 'spring_boot':
                mock_fields.add('@MockBean private ServiceClass mockService;')
                mock_fields.add('@MockBean private ComponentClass mockComponent;')
            elif category == 'spring_web':
                mock_fields.add('@MockBean private RestController mockController;')
                mock_fields.add('@MockBean private WebMvcConfigurer mockConfigurer;')
            elif category == 'spring_security':
                mock_fields.add('@MockBean private SecurityConfig mockSecurityConfig;')
                mock_fields.add('@MockBean private AuthenticationManager mockAuthManager;')
            elif category == 'spring_data':
                mock_fields.add('@MockBean private Repository mockRepository;')
                mock_fields.add('@MockBean private EntityManager mockEntityManager;')
            elif category == 'spring_batch':
                mock_fields.add('@MockBean private JobLauncher mockJobLauncher;')
                mock_fields.add('@MockBean private JobRepository mockJobRepository;')
            elif category == 'spring_cloud':
                mock_fields.add('@MockBean private FeignClient mockFeignClient;')
                mock_fields.add('@MockBean private DiscoveryClient mockDiscoveryClient;')
            elif category == 'spring_kafka':
                mock_fields.add('@MockBean private KafkaTemplate mockKafkaTemplate;')
                mock_fields.add('@MockBean private ProducerFactory mockProducerFactory;')
            elif category == 'spring_amqp':
                mock_fields.add('@MockBean private RabbitTemplate mockRabbitTemplate;')
                mock_fields.add('@MockBean private ConnectionFactory mockConnectionFactory;')
            elif category == 'hibernate':
                mock_fields.add('@MockBean private SessionFactory mockSessionFactory;')
                mock_fields.add('@MockBean private Session mockSession;')
            elif category == 'hibernate_advanced':
                mock_fields.add('@MockBean private CriteriaBuilder mockCriteriaBuilder;')
                mock_fields.add('@MockBean private CriteriaQuery mockCriteriaQuery;')
            elif category == 'jpa_queries':
                mock_fields.add('@MockBean private Query mockQuery;')
                mock_fields.add('@MockBean private TypedQuery mockTypedQuery;')
            elif category == 'spring_test':
                mock_fields.add('@MockBean private TestService mockTestService;')
                mock_fields.add('@MockBean private TestComponent mockTestComponent;')
            elif category == 'junit5_spring':
                mock_fields.add('@ExtendWith(SpringExtension.class)')
                mock_fields.add('@MockBean private TestComponent mockTestComponent;')
            elif category == 'microservices':
                mock_fields.add('@MockBean private ServiceRegistry mockServiceRegistry;')
                mock_fields.add('@MockBean private LoadBalancer mockLoadBalancer;')
            elif category == 'database_advanced':
                mock_fields.add('@MockBean private DataSource mockDataSource;')
                mock_fields.add('@MockBean private Connection mockConnection;')
            elif category == 'validation_advanced':
                mock_fields.add('@MockBean private Validator mockValidator;')
                mock_fields.add('@MockBean private ConstraintValidator mockConstraintValidator;')
            elif category == 'spring_aop':
                mock_fields.add('@MockBean private Aspect mockAspect;')
                mock_fields.add('@MockBean private Advisor mockAdvisor;')
            elif category == 'spring_events':
                mock_fields.add('@MockBean private ApplicationEventPublisher mockEventPublisher;')
                mock_fields.add('@MockBean private ApplicationListener mockEventListener;')
            elif category == 'spring_config':
                mock_fields.add('@MockBean private ConfigurationClass mockConfiguration;')
                mock_fields.add('@MockBean private PropertySource mockPropertySource;')
        
        # Add mock fields
        if mock_fields:
            mock_code += "        // Auto-generated mock fields\n"
            for field in sorted(mock_fields):
                mock_code += f"        {field}\n"
            mock_code += "\n"
        
        # Generate setUp method based on strategy
        mock_code += "        @BeforeEach\n"
        mock_code += "        void setUp() {\n"
        
        if mock_strategy == 'comprehensive':
            mock_code += "            // Comprehensive mock setup for complex method\n"
            mock_code += "            // Initialize all mocks with realistic behavior\n"
        elif mock_strategy == 'moderate':
            mock_code += "            // Moderate mock setup for medium complexity\n"
            mock_code += "            // Focus on critical dependencies\n"
        elif mock_strategy == 'focused':
            mock_code += "            // Focused mock setup for many dependencies\n"
            mock_code += "            // Mock only external dependencies\n"
        else:
            mock_code += "            // Minimal mock setup for simple method\n"
            mock_code += "            // Basic mock configuration\n"
        
        # Add specific mock setups based on dependencies and strategy
        for dep in external_deps:
            category = dep.get('category', '')
            criticality = dep.get('criticality', 'medium')
            
            # Skip low-priority dependencies for minimal strategy
            if mock_strategy == 'minimal' and criticality == 'low':
                continue
            
            # Generate comprehensive mocks for high complexity
            if mock_strategy == 'comprehensive':
                if category == 'database':
                    mock_code += "            when(mockRepository.save(any())).thenReturn(mockEntity);\n"
                    mock_code += "            when(mockRepository.findById(any())).thenReturn(Optional.of(mockEntity));\n"
                    mock_code += "            when(mockRepository.findAll()).thenReturn(Arrays.asList(mockEntity));\n"
                    mock_code += "            when(mockRepository.deleteById(any())).thenReturn(null);\n"
                    mock_code += "            when(mockRepository.count()).thenReturn(1L);\n"
            elif category == 'network':
                mock_code += "            when(mockRestTemplate.getForObject(anyString(), any())).thenReturn(mockResponse);\n"
                mock_code += "            when(mockRestTemplate.postForObject(anyString(), any(), any())).thenReturn(mockResponse);\n"
                mock_code += "            when(mockRestTemplate.put(anyString(), any())).thenReturn(null);\n"
                mock_code += "            when(mockRestTemplate.delete(anyString())).thenReturn(null);\n"
            elif category == 'file_system':
                mock_code += "            when(mockFile.exists()).thenReturn(true);\n"
                mock_code += "            when(mockFile.canRead()).thenReturn(true);\n"
                mock_code += "            when(mockFile.canWrite()).thenReturn(true);\n"
                mock_code += "            when(mockFile.length()).thenReturn(1024L);\n"
            elif category == 'security':
                mock_code += "            when(mockSecurityContext.getAuthentication()).thenReturn(mockAuthentication);\n"
                mock_code += "            when(mockAuthentication.getPrincipal()).thenReturn(mockPrincipal);\n"
                mock_code += "            when(mockAuthentication.getAuthorities()).thenReturn(mockAuthorities);\n"
                mock_code += "            when(mockAuthentication.isAuthenticated()).thenReturn(true);\n"
            
            # Generate moderate mocks for medium complexity
            elif mock_strategy == 'moderate':
                if category in ['database', 'network', 'file_system', 'security']:
                    mock_code += f"            when(mock{category.title()}.method()).thenReturn(mockResult);\n"
            
            # Generate focused mocks for many dependencies
            elif mock_strategy == 'focused':
                if criticality == 'high':
                    mock_code += f"            when(mock{category.title()}.criticalMethod()).thenReturn(mockResult);\n"
            
            # Generate minimal mocks for simple methods
            else:  # minimal
                if criticality == 'high':
                    mock_code += f"            when(mock{category.title()}.method()).thenReturn(mockResult);\n"
            
            # NEW: Spring Boot specific mock setups (outside the strategy blocks)
            if category == 'spring_boot':
                mock_code += "            when(mockService.method()).thenReturn(mockResult);\n"
                mock_code += "            when(mockComponent.getProperty()).thenReturn(mockValue);\n"
            elif category == 'spring_web':
                mock_code += "            when(mockController.handleRequest(any())).thenReturn(mockResponse);\n"
                mock_code += "            when(mockConfigurer.configure(any())).thenReturn(null);\n"
            elif category == 'spring_security':
                mock_code += "            when(mockSecurityConfig.authenticationManager()).thenReturn(mockAuthManager);\n"
                mock_code += "            when(mockAuthManager.authenticate(any())).thenReturn(mockAuthentication);\n"
            elif category == 'spring_data':
                mock_code += "            when(mockRepository.findById(any())).thenReturn(Optional.of(mockEntity));\n"
                mock_code += "            when(mockRepository.save(any())).thenReturn(mockEntity);\n"
            elif category == 'spring_batch':
                mock_code += "            when(mockJobLauncher.run(any(Job.class), any(JobParameters.class))).thenReturn(mockJobExecution);\n"
                mock_code += "            when(mockJobRepository.createJobExecution(anyString(), any(JobParameters.class))).thenReturn(mockJobExecution);\n"
            elif category == 'spring_cloud':
                mock_code += "            when(mockFeignClient.call(any())).thenReturn(mockResponse);\n"
                mock_code += "            when(mockDiscoveryClient.getInstances(anyString())).thenReturn(mockInstances);\n"
            elif category == 'spring_kafka':
                mock_code += "            when(mockKafkaTemplate.send(anyString(), any())).thenReturn(mockFuture);\n"
                mock_code += "            when(mockProducerFactory.createProducer()).thenReturn(mockProducer);\n"
            elif category == 'spring_amqp':
                mock_code += "            when(mockRabbitTemplate.convertAndSend(anyString(), any())).thenReturn(null);\n"
                mock_code += "            when(mockConnectionFactory.createConnection()).thenReturn(mockConnection);\n"
            elif category == 'hibernate':
                mock_code += "            when(mockSessionFactory.openSession()).thenReturn(mockSession);\n"
                mock_code += "            when(mockSession.save(any())).thenReturn(mockId);\n"
            elif category == 'hibernate_advanced':
                mock_code += "            when(mockCriteriaBuilder.createQuery()).thenReturn(mockCriteriaQuery);\n"
                mock_code += "            when(mockCriteriaQuery.from(any(Class.class))).thenReturn(mockRoot);\n"
            elif category == 'jpa_queries':
                mock_code += "            when(mockQuery.getResultList()).thenReturn(mockResultList);\n"
                mock_code += "            when(mockTypedQuery.getSingleResult()).thenReturn(mockResult);\n"
            elif category == 'spring_test':
                mock_code += "            when(mockTestService.method()).thenReturn(mockResult);\n"
                mock_code += "            when(mockTestComponent.getProperty()).thenReturn(mockValue);\n"
            elif category == 'junit5_spring':
                mock_code += "            when(mockTestComponent.method()).thenReturn(mockResult);\n"
            elif category == 'microservices':
                mock_code += "            when(mockServiceRegistry.getService(anyString())).thenReturn(mockServiceInstance);\n"
                mock_code += "            when(mockLoadBalancer.choose(anyString())).thenReturn(mockServiceInstance);\n"
            elif category == 'database_advanced':
                mock_code += "            when(mockDataSource.getConnection()).thenReturn(mockConnection);\n"
                mock_code += "            when(mockConnection.prepareStatement(anyString())).thenReturn(mockPreparedStatement);\n"
            elif category == 'validation_advanced':
                mock_code += "            when(mockValidator.validate(any())).thenReturn(mockViolations);\n"
                mock_code += "            when(mockConstraintValidator.isValid(any(), any())).thenReturn(true);\n"
            elif category == 'spring_aop':
                mock_code += "            when(mockAspect.advice(any())).thenReturn(mockResult);\n"
                mock_code += "            when(mockAdvisor.getAdvice()).thenReturn(mockAdvice);\n"
            elif category == 'spring_events':
                mock_code += "            when(mockEventPublisher.publishEvent(any())).thenReturn(null);\n"
                mock_code += "            when(mockEventListener.onApplicationEvent(any())).thenReturn(null);\n"
            elif category == 'spring_config':
                mock_code += "            when(mockConfiguration.getProperty(anyString())).thenReturn(mockValue);\n"
                mock_code += "            when(mockPropertySource.getProperty(anyString())).thenReturn(mockValue);\n"
        
        mock_code += "        }\n\n"
        
        # Generate helper methods for static mocking
        static_mocks_needed = any(dep.get('category') in ['environment', 'file_system', 'system'] for dep in external_deps)
        if static_mocks_needed:
            mock_code += "        // Helper methods for static mocking\n"
            mock_code += "        private void mockSystemEnvironment() {\n"
            mock_code += "            try (MockedStatic<System> mockedSystem = mockStatic(System.class)) {\n"
            mock_code += "                mockedSystem.when(() -> System.getenv(\"TEST_VAR\")).thenReturn(\"test_value\");\n"
            mock_code += "                mockedSystem.when(() -> System.getProperty(\"test.property\")).thenReturn(\"test_value\");\n"
            mock_code += "            }\n"
            mock_code += "        }\n\n"
            
            mock_code += "        private void mockFileOperations() {\n"
            mock_code += "            try (MockedStatic<Files> mockedFiles = mockStatic(Files.class)) {\n"
            mock_code += "                mockedFiles.when(() -> Files.readAllLines(any())).thenReturn(Arrays.asList(\"line1\", \"line2\"));\n"
            mock_code += "                mockedFiles.when(() -> Files.write(any(), any())).thenReturn(mockPath);\n"
            mock_code += "            }\n"
            mock_code += "        }\n\n"
        
        mock_code += "    }\n"
        
        return mock_code
    
    def _extract_parameter_types(self, method_signature: str) -> List[str]:
        """Extract parameter types from method signature"""
        import re
        if not method_signature:
            return []
        
        # Simple regex to extract parameter types
        param_pattern = r'(\w+(?:<[^>]*>)?)\s+\w+'
        matches = re.findall(param_pattern, method_signature)
        return matches
    
    def _calculate_method_complexity(self, source_code: str) -> int:
        """Calculate method complexity score"""
        if not source_code:
            return 0
        
        complexity = 0
        
        # Count control structures
        complexity += source_code.count('if')
        complexity += source_code.count('for')
        complexity += source_code.count('while')
        complexity += source_code.count('switch')
        complexity += source_code.count('catch')
        complexity += source_code.count('try')
        
        # Count method calls
        complexity += source_code.count('(') - source_code.count(')')
        
        # Count nested blocks
        complexity += source_code.count('{') - source_code.count('}')
        
        return complexity
    
    def _determine_mock_strategy(self, complexity_score: int, external_deps: List[Dict]) -> str:
        """Determine mock strategy based on complexity and dependencies"""
        if complexity_score > 20:
            return 'comprehensive'  # High complexity - need comprehensive mocking
        elif complexity_score > 10:
            return 'moderate'       # Medium complexity - moderate mocking
        elif len(external_deps) > 5:
            return 'focused'        # Many dependencies - focused mocking
        else:
            return 'minimal'        # Low complexity - minimal mocking


if __name__ == "__main__":
    # Test the GeneratorAgent
    import asyncio
    
    async def test_generator():
        agent = GeneratorAgent(test_framework="junit5")
        
        # Create test state with method info
        state = AgentState()
        state.method_context = {
            "ranked_methods": [{
                "data": {
                    "name": "calculateTotal",
                    "full_signature": "public double calculateTotal(List<Item> items)",
                    "source_code": """
                    public double calculateTotal(List<Item> items) {
                        if (items == null || items.isEmpty()) {
                            return 0.0;
                        }
                        return items.stream()
                            .mapToDouble(Item::getPrice)
                            .sum();
                    }
                    """,
                    "class_name": "ShoppingCart",
                    "complexity": 3
                }
            }]
        }
        
        state.dependencies = {
            "methods": [],
            "fields": []
        }
        
        print("Testing GeneratorAgent...")
        print("="*60)
        
        # Execute
        result_state = await agent.execute(state)
        
        if result_state.test_code:
            print("\n✅ Generated Test Code:\n")
            print(result_state.test_code)
        else:
            print("\n❌ Test generation failed")
            for error in result_state.errors:
                print(f"Error: {error}")
    
    asyncio.run(test_generator())

