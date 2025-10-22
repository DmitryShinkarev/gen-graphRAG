"""
AnalystAgent - Performs deep code analysis for test generation.

Responsibilities:
- Analyze method complexity and patterns
- Identify edge cases and potential issues
- Recommend test strategies
- Provide performance insights
- Generate test recommendations

Pattern: Code Analysis & Intelligence (4.3)
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import ast
import json
from collections import defaultdict, Counter

from agents.base import BaseJavaAgent, AgentState
from logger import get_logger

logger = get_logger(__name__)


class AnalystAgent(BaseJavaAgent):
    """
    Agent responsible for deep code analysis.
    
    Workflow:
    1. Analyze method complexity
    2. Analyze dependencies and their criticality
    3. Detect edge cases and potential issues
    4. Analyze performance implications
    5. Generate test recommendations
    """
    
    def __init__(self):
        """Initialize AnalystAgent"""
        super().__init__(
            name="AnalystAgent",
            role="Deep code analysis and test strategy recommendations",
            tools=[],
            temperature=0.2  # Low temperature for analytical tasks
        )
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute deep code analysis workflow.
        
        Args:
            state: Current agent state with method_context and dependencies
        
        Returns:
            Updated state with analysis results and recommendations
        """
        logger.info("="*80)
        logger.info(f"[{self.name}] 🧠 STARTING DEEP CODE ANALYSIS")
        logger.info("="*80)
        
        # Debug logging
        logger.info(f"[{self.name}] 🔍 DEBUG: Method execute() called")
        logger.info(f"[{self.name}] 🔍 DEBUG: State type: {type(state)}")
        logger.info(f"[{self.name}] 🔍 DEBUG: State has method_context: {hasattr(state, 'method_context')}")
        logger.info(f"[{self.name}] 🔍 DEBUG: State has dependencies: {hasattr(state, 'dependencies')}")
        if hasattr(state, 'method_context') and state.method_context:
            logger.info(f"[{self.name}] 🔍 DEBUG: Method context keys: {list(state.method_context.keys())}")
        logger.info("="*80)
        
        try:
            # Get target method info
            method_info = self._extract_method_info(state)
            
            if not method_info:
                error_msg = "No method information available for analysis"
                logger.error(f"  ❌ {error_msg}")
                self.log_error(error_msg, state)
                return state
            
            method_name = method_info.get('name', 'unknown')
            source_code = method_info.get('source_code', '')
            class_name = method_info.get('class_name', 'UnknownClass')
            
            logger.info(f"  📝 Analyzing method: {method_name}")
            logger.info(f"  📦 Class: {class_name}")
            logger.info(f"  📏 Code length: {len(source_code)} characters")
            logger.info("")
            
            self.log_step(f"Analyzing method: {method_name}", state)
            
            # 1. Complexity Analysis
            logger.info(f"  🔍 Step 1/5: Complexity Analysis")
            complexity_analysis = await self._analyze_complexity(source_code, method_info)
            logger.info(f"    ✅ Cyclomatic complexity: {complexity_analysis['cyclomatic_complexity']}")
            logger.info(f"    ✅ Complexity level: {complexity_analysis['complexity_level']}")
            logger.info(f"    ✅ Branch count: {complexity_analysis['branch_count']}")
            logger.info("")
            
            self.log_step("Completed complexity analysis", state)
            
            # 2. Dependency Analysis
            logger.info(f"  🔍 Step 2/5: Dependency Analysis")
            dependency_analysis = await self._analyze_dependencies(source_code, state)
            logger.info(f"    ✅ External dependencies: {len(dependency_analysis['external_deps'])}")
            logger.info(f"    ✅ Critical dependencies: {len(dependency_analysis['critical_deps'])}")
            logger.info(f"    ✅ Mocking recommendations: {len(dependency_analysis['mock_recommendations'])}")
            logger.info("")
            
            self.log_step("Completed dependency analysis", state)
            
            # 3. Edge Case Detection
            logger.info(f"  🔍 Step 3/5: Edge Case Detection")
            edge_case_analysis = await self._detect_edge_cases(source_code, method_info)
            logger.info(f"    ✅ Edge cases found: {len(edge_case_analysis['edge_cases'])}")
            logger.info(f"    ✅ Exception scenarios: {len(edge_case_analysis['exception_scenarios'])}")
            logger.info(f"    ✅ Boundary conditions: {len(edge_case_analysis['boundary_conditions'])}")
            logger.info("")
            
            self.log_step("Completed edge case detection", state)
            
            # 4. Performance Analysis
            logger.info(f"  🔍 Step 4/5: Performance Analysis")
            performance_analysis = await self._analyze_performance(source_code, method_info)
            logger.info(f"    ✅ Performance level: {performance_analysis['performance_level']}")
            logger.info(f"    ✅ Resource concerns: {len(performance_analysis['resource_concerns'])}")
            logger.info(f"    ✅ Async operations: {performance_analysis['has_async_operations']}")
            logger.info("")
            
            self.log_step("Completed performance analysis", state)
            
            # 5. Generate Test Recommendations
            logger.info(f"  🔍 Step 5/5: Test Strategy Recommendations")
            test_recommendations = await self._generate_test_recommendations(
                complexity_analysis, dependency_analysis, edge_case_analysis, performance_analysis
            )
            logger.info(f"    ✅ Recommended test count: {test_recommendations['recommended_test_count']}")
            logger.info(f"    ✅ Test priorities: {len(test_recommendations['test_priorities'])}")
            logger.info(f"    ✅ Special considerations: {len(test_recommendations['special_considerations'])}")
            logger.info("")
            
            self.log_step("Completed test recommendations", state)
            
            # Update state with analysis results
            state.complexity_analysis = complexity_analysis
            state.dependency_analysis = dependency_analysis
            state.edge_case_analysis = edge_case_analysis
            state.performance_analysis = performance_analysis
            state.test_recommendations = test_recommendations
            
            # Log summary
            logger.info("="*80)
            logger.info(f"[{self.name}] ✅ ANALYSIS COMPLETED")
            logger.info("="*80)
            logger.info(f"  📊 Analysis Summary:")
            logger.info(f"    • Complexity: {complexity_analysis['complexity_level']} ({complexity_analysis['cyclomatic_complexity']} CC)")
            logger.info(f"    • Dependencies: {len(dependency_analysis['external_deps'])} external, {len(dependency_analysis['critical_deps'])} critical")
            logger.info(f"    • Edge Cases: {len(edge_case_analysis['edge_cases'])} identified")
            logger.info(f"    • Performance: {performance_analysis['performance_level']}")
            logger.info(f"    • Recommended Tests: {test_recommendations['recommended_test_count']}")
            logger.info("")
            logger.info(f"  💡 Key Recommendations:")
            for i, rec in enumerate(test_recommendations['test_priorities'][:3], 1):
                logger.info(f"    {i}. {rec}")
            logger.info("="*80)
            logger.info("")
            
            # Debug: Log final state
            logger.info(f"[{self.name}] 🔍 DEBUG: Final state analysis results:")
            logger.info(f"  • complexity_analysis: {'✅' if state.complexity_analysis else '❌'}")
            logger.info(f"  • dependency_analysis: {'✅' if state.dependency_analysis else '❌'}")
            logger.info(f"  • edge_case_analysis: {'✅' if state.edge_case_analysis else '❌'}")
            logger.info(f"  • performance_analysis: {'✅' if state.performance_analysis else '❌'}")
            logger.info(f"  • test_recommendations: {'✅' if state.test_recommendations else '❌'}")
            
            # Log hybrid approach statistics
            self.log_hybrid_stats()
            
            return state
            
        except Exception as e:
            error_msg = f"Code analysis failed: {str(e)}"
            logger.exception(f"[{self.name}] {error_msg}")
            self.log_error(error_msg, state)
            return state
    
    def _extract_method_info(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """Extract method information from state"""
        # Try to get from method_context
        if state.method_context and state.method_context.get("ranked_methods"):
            ranked = state.method_context["ranked_methods"]
            if ranked:
                return ranked[0].get("data", {})
        
        # Try to get from parsed_classes
        if state.parsed_classes:
            for class_data in state.parsed_classes.values():
                class_info = class_data.get("class_info", {})
                methods = class_info.get("methods", [])
                if methods:
                    return methods[0]
        
        return None
    
    async def _analyze_complexity(self, source_code: str, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze method complexity using hybrid approach (regex + LLM).
        
        Returns:
            Dict with complexity analysis results
        """
        # Determine if code is complex enough for LLM analysis
        if self._should_use_llm_analysis(source_code, method_info):
            logger.info(f"    🤖 Using LLM for complex code analysis...")
            result = await self._analyze_complexity_with_llm(source_code, method_info)
            self.update_hybrid_stats('llm')
            return result
        else:
            logger.info(f"    ⚡ Using fast regex analysis for simple code...")
            result = await self._analyze_complexity_regex(source_code, method_info)
            self.update_hybrid_stats('regex')
            return result
    
    def _should_use_llm_analysis(self, source_code: str, method_info: Dict[str, Any]) -> bool:
        """
        Determine if code is complex enough to warrant LLM analysis.
        
        Returns:
            True if LLM analysis should be used, False for regex
        """
        # Quick regex-based complexity check
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(source_code)
        branch_count = self._count_branches(source_code)
        max_nesting_depth = self._calculate_nesting_depth(source_code)
        
        # Use LLM if:
        # 1. High cyclomatic complexity (>10)
        # 2. Many branches (>7)
        # 3. Deep nesting (>4)
        # 4. Contains complex patterns
        # 5. Long method (>50 lines)
        
        use_llm = (
            cyclomatic_complexity > 10 or
            branch_count > 7 or
            max_nesting_depth > 4 or
            len(source_code.split('\n')) > 50 or
            self._has_complex_patterns(source_code)
        )
        
        lines_count = len(source_code.split('\n'))
        logger.info(f"    🔍 Complexity check: CC={cyclomatic_complexity}, branches={branch_count}, nesting={max_nesting_depth}, lines={lines_count}")
        logger.info(f"    🎯 Analysis method: {'LLM' if use_llm else 'Regex'}")
        
        return use_llm
    
    def _has_complex_patterns(self, source_code: str) -> bool:
        """Check if code contains complex patterns that need LLM analysis"""
        complex_patterns = [
            r'@\w+',  # Annotations
            r'Stream\.',  # Stream API
            r'Optional\.',  # Optional
            r'CompletableFuture',  # Async
            r'BigDecimal',  # Complex math
            r'Reflection',  # Reflection
            r'Pattern\.',  # Regex patterns
            r'\.map\(',  # Functional programming
            r'\.filter\(',  # Functional programming
            r'\.reduce\(',  # Functional programming
        ]
        
        for pattern in complex_patterns:
            if re.search(pattern, source_code):
                return True
        return False
    
    async def _analyze_complexity_regex(self, source_code: str, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast regex-based complexity analysis for simple code.
        
        Returns:
            Dict with complexity analysis results
        """
        logger.info(f"    🔢 Calculating cyclomatic complexity (regex)...")
        
        # Calculate cyclomatic complexity
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(source_code)
        
        # Count branches
        branch_count = self._count_branches(source_code)
        
        # Analyze nesting depth
        max_nesting_depth = self._calculate_nesting_depth(source_code)
        
        # Determine complexity level
        complexity_level = self._determine_complexity_level(cyclomatic_complexity, branch_count, max_nesting_depth)
        
        # Identify complexity patterns
        complexity_patterns = self._identify_complexity_patterns(source_code)
        
        return {
            "cyclomatic_complexity": cyclomatic_complexity,
            "branch_count": branch_count,
            "max_nesting_depth": max_nesting_depth,
            "complexity_level": complexity_level,
            "complexity_patterns": complexity_patterns,
            "analysis_method": "regex",
            "analysis_timestamp": self._get_timestamp()
        }
    
    async def _analyze_complexity_with_llm(self, source_code: str, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM-based complexity analysis for complex code.
        
        Returns:
            Dict with detailed complexity analysis results
        """
        logger.info(f"    🤖 Performing deep LLM complexity analysis...")
        
        method_name = method_info.get('name', 'unknown')
        class_name = method_info.get('class_name', 'UnknownClass')
        
        # Build prompt for LLM analysis
        prompt = f"""Analyze the complexity of this Java method and provide detailed insights for test generation.

**Method:** {class_name}.{method_name}

**Source Code:**
```java
{source_code}
```

Please provide a detailed complexity analysis in JSON format with the following structure:

{{
    "cyclomatic_complexity": <number>,
    "branch_count": <number>,
    "max_nesting_depth": <number>,
    "complexity_level": "<low|medium|high|very_high>",
    "complexity_patterns": [
        "<pattern1>",
        "<pattern2>"
    ],
    "cognitive_complexity": <number>,
    "business_logic_complexity": "<low|medium|high>",
    "architectural_concerns": [
        "<concern1>",
        "<concern2>"
    ],
    "testability_assessment": "<easy|moderate|difficult>",
    "recommended_test_strategy": "<brief strategy description>",
    "critical_test_scenarios": [
        {{
            "scenario": "<description>",
            "priority": "<high|medium|low>",
            "reason": "<why this scenario is important>"
        }}
    ]
}}

Focus on:
1. Actual cognitive complexity (not just syntactic)
2. Business logic complexity
3. Architectural patterns and concerns
4. Testability challenges
5. Critical scenarios that MUST be tested
6. Specific edge cases and boundary conditions

Provide concrete, actionable insights for test generation."""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert Java code analyst specializing in complexity analysis and test strategy recommendations. Provide detailed, actionable insights in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self.call_llm(messages, max_tokens=1500)
            
            # Parse LLM response
            try:
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                    
                    # Merge with basic regex analysis for consistency
                    basic_analysis = await self._analyze_complexity_regex(source_code, method_info)
                    
                    # Combine results
                    result = {
                        **basic_analysis,
                        **analysis_data,
                        "analysis_method": "llm",
                        "llm_insights": True
                    }
                    
                    logger.info(f"    ✅ LLM analysis completed: {result.get('complexity_level', 'unknown')} complexity")
                    return result
                else:
                    logger.warning("    ⚠️ Could not parse LLM response as JSON, falling back to regex")
                    return await self._analyze_complexity_regex(source_code, method_info)
                    
            except json.JSONDecodeError as e:
                logger.warning(f"    ⚠️ JSON parsing failed: {e}, falling back to regex")
                return await self._analyze_complexity_regex(source_code, method_info)
                
        except Exception as e:
            logger.error(f"    ❌ LLM analysis failed: {e}, falling back to regex")
            return await self._analyze_complexity_regex(source_code, method_info)
    
    def _calculate_cyclomatic_complexity(self, source_code: str) -> int:
        """Calculate cyclomatic complexity for Java code"""
        # Base complexity is 1
        complexity = 1
        
        # Count decision points
        decision_patterns = [
            r'\bif\s*\(',           # if statements
            r'\bwhile\s*\(',        # while loops
            r'\bfor\s*\(',          # for loops
            r'\bswitch\s*\(',       # switch statements
            r'\bcatch\s*\(',        # catch blocks
            r'\bcase\s+',           # case statements
            r'\belse\s+if\s*\(',    # else-if statements
            r'\?\s*.*\s*:',         # ternary operators
        ]
        
        for pattern in decision_patterns:
            matches = re.findall(pattern, source_code, re.IGNORECASE)
            complexity += len(matches)
        
        # Subtract else statements (they don't add complexity)
        else_count = len(re.findall(r'\belse\s*{', source_code, re.IGNORECASE))
        complexity -= else_count
        
        return max(1, complexity)  # Minimum complexity is 1
    
    def _count_branches(self, source_code: str) -> int:
        """Count the number of branches in the code"""
        branch_patterns = [
            r'\bif\s*\(',           # if statements
            r'\belse\s+if\s*\(',    # else-if statements
            r'\bwhile\s*\(',        # while loops
            r'\bfor\s*\(',          # for loops
            r'\bswitch\s*\(',       # switch statements
            r'\bcatch\s*\(',        # catch blocks
        ]
        
        total_branches = 0
        for pattern in branch_patterns:
            matches = re.findall(pattern, source_code, re.IGNORECASE)
            total_branches += len(matches)
        
        return total_branches
    
    def _calculate_nesting_depth(self, source_code: str) -> int:
        """Calculate maximum nesting depth"""
        max_depth = 0
        current_depth = 0
        
        for char in source_code:
            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth = max(0, current_depth - 1)
        
        return max_depth
    
    def _determine_complexity_level(self, cyclomatic_complexity: int, branch_count: int, nesting_depth: int) -> str:
        """Determine overall complexity level"""
        if cyclomatic_complexity <= 5 and branch_count <= 3 and nesting_depth <= 2:
            return "Low"
        elif cyclomatic_complexity <= 10 and branch_count <= 7 and nesting_depth <= 4:
            return "Medium"
        elif cyclomatic_complexity <= 20 and branch_count <= 15 and nesting_depth <= 6:
            return "High"
        else:
            return "Very High"
    
    def _identify_complexity_patterns(self, source_code: str) -> List[str]:
        """Identify specific complexity patterns"""
        patterns = []
        
        # Long method detection
        lines = source_code.split('\n')
        if len(lines) > 20:
            patterns.append("Long method (>20 lines)")
        
        # Deep nesting
        if self._calculate_nesting_depth(source_code) > 4:
            patterns.append("Deep nesting (>4 levels)")
        
        # Multiple return statements
        return_count = len(re.findall(r'\breturn\s+', source_code))
        if return_count > 3:
            patterns.append("Multiple return statements")
        
        # Complex boolean expressions
        complex_booleans = re.findall(r'\([^)]*(&&|\|\|)[^)]*\)', source_code)
        if len(complex_booleans) > 2:
            patterns.append("Complex boolean expressions")
        
        return patterns
    
    async def _analyze_dependencies(self, source_code: str, state: AgentState) -> Dict[str, Any]:
        """
        Analyze method dependencies and their criticality.
        
        Returns:
            Dict with dependency analysis results
        """
        logger.info(f"    🔗 Analyzing dependencies...")
        
        # Get dependencies from state
        dependencies = state.dependencies or {}
        dependent_methods = dependencies.get("methods", [])
        used_fields = dependencies.get("fields", [])
        
        # Analyze external dependencies
        external_deps = self._identify_external_dependencies(source_code)
        
        # Analyze critical dependencies
        critical_deps = self._identify_critical_dependencies(dependent_methods, external_deps)
        
        # Generate mocking recommendations
        mock_recommendations = self._generate_mocking_recommendations(dependent_methods, external_deps)
        
        # Analyze dependency patterns
        dependency_patterns = self._analyze_dependency_patterns(source_code, dependent_methods)
        
        return {
            "external_deps": external_deps,
            "critical_deps": critical_deps,
            "mock_recommendations": mock_recommendations,
            "dependency_patterns": dependency_patterns,
            "dependent_methods_count": len(dependent_methods),
            "used_fields_count": len(used_fields),
            "analysis_timestamp": self._get_timestamp()
        }
    
    def _identify_external_dependencies(self, source_code: str) -> List[Dict[str, Any]]:
        """Identify external dependencies in the code"""
        external_deps = []
        
        # Enhanced external dependency patterns with more specific detection
        external_patterns = {
            'database': [r'\.save\(', r'\.findBy', r'\.delete\(', r'Repository', r'EntityManager', r'JpaRepository', r'CrudRepository', r'@Transactional', r'@Entity'],
            'network': [r'\.get\(', r'\.post\(', r'\.put\(', r'\.delete\(', r'HttpClient', r'RestTemplate', r'WebClient', r'OkHttp', r'ApacheHttp'],
            'file_system': [r'Files\.', r'File\.', r'\.read\(', r'\.write\(', r'Path\.', r'InputStream', r'OutputStream', r'BufferedReader', r'BufferedWriter'],
            'logging': [r'Logger', r'\.log\(', r'LogManager', r'LoggerFactory', r'@Slf4j', r'@Log4j2'],
            'time': [r'System\.currentTimeMillis', r'LocalDateTime', r'Instant\.', r'ZonedDateTime', r'Clock\.', r'Date\.'],
            'random': [r'Random', r'Math\.random', r'ThreadLocalRandom', r'SecureRandom'],
            'system': [r'System\.', r'Runtime\.', r'ProcessBuilder', r'Process\.'],
            # Enhanced system and environment dependencies
            'environment': [r'System\.getenv\(', r'System\.getProperty\(', r'System\.setProperty\(', r'@Value\s*\(\s*"\$\{', r'@ConfigurationProperties'],
            'object_creation': [r'new\s+[A-Z]\w*\(', r'\.newInstance\(', r'Class\.forName\(', r'BeanUtils\.', r'ObjectMapper\.'],
            'reflection': [r'\.getClass\(', r'\.getMethod\(', r'\.invoke\(', r'Field\.', r'Constructor\.', r'Method\.'],
            'io_operations': [r'\.read\(', r'\.write\(', r'\.flush\(', r'\.close\(', r'\.available\(', r'\.skip\('],
            # NEW: Additional specific dependency categories
            'security': [r'SecurityContext', r'Authentication', r'Principal', r'@PreAuthorize', r'@Secured', r'BCrypt', r'JWT'],
            'validation': [r'@Valid', r'@NotNull', r'@NotEmpty', r'@Size', r'@Pattern', r'Validator\.', r'ConstraintViolation'],
            'serialization': [r'ObjectMapper', r'Gson', r'Jackson', r'@JsonIgnore', r'@JsonProperty', r'Serializable'],
            'caching': [r'@Cacheable', r'@CacheEvict', r'@CachePut', r'CacheManager', r'RedisTemplate', r'@EnableCaching'],
            'messaging': [r'@RabbitListener', r'@KafkaListener', r'@JmsListener', r'MessageProducer', r'MessageConsumer'],
            'scheduling': [r'@Scheduled', r'@EnableScheduling', r'TaskScheduler', r'CronExpression'],
            'configuration': [r'@Configuration', r'@Bean', r'@Component', r'@Service', r'@Repository', r'@Controller'],
            'testing': [r'@MockBean', r'@SpyBean', r'@TestConfiguration', r'@MockitoSettings'],
            'metrics': [r'@Timed', r'@Counted', r'MeterRegistry', r'Counter\.', r'Timer\.', r'Gauge\.'],
            'actuator': [r'@Actuator', r'HealthIndicator', r'@Endpoint', r'@ReadOperation'],
            # NEW: Spring Boot specific patterns
            'spring_boot': [r'@SpringBootApplication', r'@RestController', r'@Controller', r'@Service', r'@Repository', r'@Component', r'@Autowired', r'@Value', r'@Configuration', r'@Bean', r'@Primary', r'@Qualifier', r'@Profile', r'@ConditionalOn', r'@EnableAutoConfiguration', r'@EnableWebMvc', r'@EnableJpaRepositories', r'@EnableTransactionManagement'],
            'spring_web': [r'@RequestMapping', r'@GetMapping', r'@PostMapping', r'@PutMapping', r'@DeleteMapping', r'@PatchMapping', r'@PathVariable', r'@RequestParam', r'@RequestBody', r'@ResponseBody', r'@ResponseStatus', r'@ExceptionHandler', r'@Valid', r'@ModelAttribute', r'@SessionAttribute', r'@CookieValue', r'@RequestHeader', r'@CrossOrigin'],
            'spring_security': [r'@EnableWebSecurity', r'@EnableGlobalMethodSecurity', r'@PreAuthorize', r'@PostAuthorize', r'@Secured', r'@RolesAllowed', r'@PermitAll', r'@DenyAll', r'SecurityContextHolder', r'Authentication', r'Principal', r'GrantedAuthority', r'UserDetails', r'UserDetailsService', r'PasswordEncoder', r'BCryptPasswordEncoder'],
            'spring_data': [r'@Repository', r'JpaRepository', r'CrudRepository', r'PagingAndSortingRepository', r'@Query', r'@Modifying', r'@Transactional', r'@Entity', r'@Table', r'@Id', r'@GeneratedValue', r'@Column', r'@OneToMany', r'@ManyToOne', r'@ManyToMany', r'@OneToOne', r'@JoinColumn', r'@JoinTable'],
            'spring_batch': [r'@EnableBatchProcessing', r'@Job', r'@Step', r'@ItemReader', r'@ItemProcessor', r'@ItemWriter', r'@JobParameters', r'@StepScope', r'@JobScope', r'JobLauncher', r'JobRepository', r'StepBuilderFactory', r'JobBuilderFactory'],
            'spring_cloud': [r'@EnableEurekaClient', r'@EnableDiscoveryClient', r'@EnableFeignClients', r'@EnableHystrix', r'@EnableCircuitBreaker', r'@EnableZuulProxy', r'@EnableConfigServer', r'@LoadBalanced', r'@HystrixCommand', r'@FeignClient', r'@RibbonClient'],
            'spring_kafka': [r'@EnableKafka', r'@KafkaListener', r'@KafkaHandler', r'@SendTo', r'@Header', r'@Payload', r'KafkaTemplate', r'ProducerFactory', r'ConsumerFactory', r'@KafkaTopic'],
            'spring_amqp': [r'@EnableRabbit', r'@RabbitListener', r'@RabbitHandler', r'@SendTo', r'@Header', r'@Payload', r'RabbitTemplate', r'@Queue', r'@Exchange', r'@Binding'],
            # NEW: Hibernate/JPA specific patterns
            'hibernate': [r'@Entity', r'@Table', r'@Id', r'@GeneratedValue', r'@Column', r'@OneToMany', r'@ManyToOne', r'@ManyToMany', r'@OneToOne', r'@JoinColumn', r'@JoinTable', r'@Embedded', r'@Embeddable', r'@Enumerated', r'@Temporal', r'@Lob', r'@Transient', r'@Version', r'@Cache', r'@Cacheable', r'@CacheEvict', r'@CachePut'],
            'hibernate_advanced': [r'@NamedQuery', r'@NamedQueries', r'@NamedNativeQuery', r'@SqlResultSetMapping', r'@EntityResult', r'@FieldResult', r'@ConstructorResult', r'@Formula', r'@Where', r'@WhereJoinTable', r'@Filter', r'@FilterDef', r'@FilterJoinTable', r'@Any', r'@AnyMetaDef', r'@MetaValue', r'@Type', r'@TypeDef', r'@TypeDefs'],
            # NEW: JPA Query patterns
            'jpa_queries': [r'findBy', r'findAllBy', r'countBy', r'deleteBy', r'existsBy', r'@Query', r'@Modifying', r'@Param', r'@Procedure', r'@NamedStoredProcedureQuery', r'@StoredProcedureParameter', r'CriteriaBuilder', r'CriteriaQuery', r'Predicate', r'Root', r'Join', r'Subquery'],
            # NEW: Testing frameworks
            'spring_test': [r'@SpringBootTest', r'@WebMvcTest', r'@DataJpaTest', r'@JsonTest', r'@RestClientTest', r'@MockBean', r'@SpyBean', r'@TestConfiguration', r'@TestPropertySource', r'@ActiveProfiles', r'@DirtiesContext', r'@Transactional', r'@Rollback', r'@Commit', r'@Sql', r'@SqlGroup', r'@SqlConfig', r'TestRestTemplate', r'MockMvc', r'@AutoConfigureTestDatabase', r'@AutoConfigureTestEntityManager'],
            'junit5_spring': [r'@ExtendWith\(SpringExtension\.class\)', r'@SpringJUnitConfig', r'@SpringJUnitWebConfig', r'@TestPropertySource', r'@ActiveProfiles', r'@DirtiesContext', r'@Transactional', r'@Rollback', r'@Commit', r'@Sql', r'@SqlGroup', r'@SqlConfig', r'@MockBean', r'@SpyBean', r'@TestConfiguration'],
            # NEW: Microservices patterns
            'microservices': [r'@EnableEurekaClient', r'@EnableDiscoveryClient', r'@EnableFeignClients', r'@EnableHystrix', r'@EnableCircuitBreaker', r'@EnableZuulProxy', r'@EnableConfigServer', r'@LoadBalanced', r'@HystrixCommand', r'@FeignClient', r'@RibbonClient', r'@EnableAdminServer', r'@EnableTurbine', r'@EnableSleuth', r'@EnableZipkinServer'],
            # NEW: Database patterns
            'database_advanced': [r'@Transactional', r'@Rollback', r'@Commit', r'@Sql', r'@SqlGroup', r'@SqlConfig', r'@DataSource', r'@PersistenceContext', r'@PersistenceUnit', r'@EntityManager', r'@EntityManagerFactory', r'@Query', r'@Modifying', r'@Param', r'@Procedure', r'@NamedStoredProcedureQuery', r'@StoredProcedureParameter'],
            # NEW: Validation patterns
            'validation_advanced': [r'@Valid', r'@Validated', r'@NotNull', r'@NotEmpty', r'@NotBlank', r'@Size', r'@Min', r'@Max', r'@DecimalMin', r'@DecimalMax', r'@Digits', r'@Pattern', r'@Email', r'@URL', r'@AssertTrue', r'@AssertFalse', r'@Future', r'@Past', r'@PastOrPresent', r'@FutureOrPresent', r'@Positive', r'@PositiveOrZero', r'@Negative', r'@NegativeOrZero', r'@Range', r'@Length', r'@SafeHtml', r'@ScriptAssert'],
            # NEW: AOP patterns
            'spring_aop': [r'@Aspect', r'@Pointcut', r'@Before', r'@After', r'@AfterReturning', r'@AfterThrowing', r'@Around', r'@EnableAspectJAutoProxy', r'@Order', r'@DeclareParents', r'@DeclareMixin', r'@DeclareAnnotation', r'@DeclarePrecedence', r'@DeclareWarning', r'@DeclareError'],
            # NEW: Event patterns
            'spring_events': [r'@EventListener', r'@Async', r'@EnableAsync', r'@EnableScheduling', r'@Scheduled', r'@EnableCaching', r'@Cacheable', r'@CacheEvict', r'@CachePut', r'@Caching', r'@CacheConfig', r'ApplicationEventPublisher', r'ApplicationEvent', r'ApplicationListener'],
            # NEW: Configuration patterns
            'spring_config': [r'@Configuration', r'@ConfigurationProperties', r'@EnableConfigurationProperties', r'@ConditionalOnProperty', r'@ConditionalOnClass', r'@ConditionalOnMissingClass', r'@ConditionalOnBean', r'@ConditionalOnMissingBean', r'@ConditionalOnWebApplication', r'@ConditionalOnNotWebApplication', r'@ConditionalOnResource', r'@ConditionalOnExpression', r'@ConditionalOnJava', r'@ConditionalOnCloudPlatform', r'@ConditionalOnSingleCandidate', r'@ConditionalOnWarDeployment'],
        }
        
        for category, patterns in external_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, source_code, re.IGNORECASE)
                if matches:
                    # Determine criticality based on category
                    if category in ['database', 'network', 'environment', 'object_creation', 'security', 'file_system', 'io_operations']:
                        criticality = 'high'
                    elif category in ['reflection', 'validation', 'serialization', 'caching', 'messaging']:
                        criticality = 'high'
                    elif category in ['scheduling', 'configuration', 'metrics', 'actuator']:
                        criticality = 'medium'
                    # NEW: Spring Boot and framework specific criticality
                    elif category in ['spring_boot', 'spring_web', 'spring_security', 'spring_data', 'hibernate', 'hibernate_advanced', 'jpa_queries']:
                        criticality = 'high'  # Spring components often have external dependencies
                    elif category in ['spring_batch', 'spring_cloud', 'spring_kafka', 'spring_amqp', 'microservices']:
                        criticality = 'high'  # These often involve external systems
                    elif category in ['spring_test', 'junit5_spring', 'database_advanced', 'validation_advanced']:
                        criticality = 'medium'  # Testing and validation frameworks
                    elif category in ['spring_aop', 'spring_events', 'spring_config']:
                        criticality = 'medium'  # AOP and configuration are usually internal
                    else:
                        criticality = 'medium'
                    
                    external_deps.append({
                        'category': category,
                        'pattern': pattern,
                        'matches': matches,
                        'criticality': criticality,
                        'requires_mocking': True  # All external dependencies should be mocked
                    })
        
        # Additional specific checks for common problematic patterns
        specific_checks = [
            # System environment variables
            (r'System\.getenv\s*\(', 'environment', 'System.getenv() calls must be mocked for predictable tests'),
            # Object creation with new keyword
            (r'new\s+[A-Z]\w*\s*\(', 'object_creation', 'Object creation should be mocked for better test isolation'),
            # Method calls on external objects
            (r'[a-zA-Z_]\w*\.\w+\s*\(', 'method_calls', 'External method calls should be mocked'),
            # Static method calls
            (r'[A-Z]\w*\.\w+\s*\(', 'static_calls', 'Static method calls should be mocked when possible'),
        ]
        
        for pattern, category, reason in specific_checks:
            matches = re.findall(pattern, source_code)
            if matches:
                external_deps.append({
                    'category': category,
                    'pattern': pattern,
                    'matches': matches,
                    'criticality': 'high',
                    'requires_mocking': True,
                    'reason': reason
                    })
        
        return external_deps
    
    def _identify_critical_dependencies(self, dependent_methods: List[Dict], external_deps: List[Dict]) -> List[Dict[str, Any]]:
        """Identify critical dependencies that need special attention"""
        critical_deps = []
        
        for method in dependent_methods:
            method_name = method.get('name', '')
            
            # Check for critical patterns
            if any(pattern in method_name.lower() for pattern in ['save', 'delete', 'update', 'create']):
                critical_deps.append({
                    'method': method,
                    'reason': 'Data modification operation',
                    'criticality': 'high'
                })
            elif any(pattern in method_name.lower() for pattern in ['validate', 'check', 'verify']):
                critical_deps.append({
                    'method': method,
                    'reason': 'Validation operation',
                    'criticality': 'medium'
                })
        
        # Add external dependencies as critical
        for dep in external_deps:
            if dep['criticality'] == 'high':
                critical_deps.append({
                    'dependency': dep,
                    'reason': f"External {dep['category']} dependency",
                    'criticality': 'high'
                })
        
        return critical_deps
    
    def _generate_mocking_recommendations(self, dependent_methods: List[Dict], external_deps: List[Dict]) -> List[Dict[str, Any]]:
        """Generate recommendations for mocking dependencies"""
        recommendations = []
        
        # Enhanced recommendations for ALL external dependencies
        for dep in external_deps:
            if dep.get('requires_mocking', False):
                recommendations.append({
                    'target': dep['category'],
                    'recommendation': f"CRITICAL: Mock {dep['category']} operations for isolated testing",
                    'priority': 'high' if dep['criticality'] == 'high' else 'medium',
                    'examples': self._get_mocking_examples(dep['category']),
                    'reason': dep.get('reason', f"External {dep['category']} dependency requires mocking"),
                    'mandatory': True  # Mark as mandatory for high-criticality dependencies
                })
        
        # Special handling for environment and system dependencies
        environment_deps = [dep for dep in external_deps if dep['category'] == 'environment']
        if environment_deps:
            recommendations.append({
                'target': 'System.getenv()',
                'recommendation': 'CRITICAL: Mock System.getenv() calls for predictable test behavior',
                    'priority': 'high',
                'examples': ['@Mock System', 'when(System.getenv()).thenReturn("test_value")'],
                'reason': 'System environment variables must be mocked for consistent test results',
                'mandatory': True
            })
        
        # Special handling for object creation
        object_creation_deps = [dep for dep in external_deps if dep['category'] == 'object_creation']
        if object_creation_deps:
            recommendations.append({
                'target': 'Object Creation',
                'recommendation': 'CRITICAL: Mock object creation for better test isolation',
                'priority': 'high',
                'examples': ['@Mock ClassName', 'when(mockObject.method()).thenReturn(value)'],
                'reason': 'Object creation with new keyword should be mocked for test isolation',
                'mandatory': True
                })
        
        # Recommend mocking for data modification methods
        for method in dependent_methods:
            method_name = method.get('name', '')
            if any(pattern in method_name.lower() for pattern in ['save', 'delete', 'update', 'create']):
                recommendations.append({
                    'target': method_name,
                    'recommendation': f"Mock {method_name} to avoid side effects",
                    'priority': 'high',
                    'examples': ['@Mock', 'when().thenReturn()', 'verify()'],
                    'mandatory': True
                })
        
        return recommendations
    
    def _get_mocking_examples(self, category: str) -> List[str]:
        """Get mocking examples for different categories"""
        examples = {
            'database': ['@Mock Repository', 'when(repository.save()).thenReturn()', 'verify(repository).delete()'],
            'network': ['@Mock RestTemplate', 'when(restTemplate.getForObject()).thenReturn()', 'verify(restTemplate).postForObject()'],
            'file_system': ['@Mock Files', 'when(Files.readAllLines()).thenReturn()', 'verify(Files).write()'],
            'logging': ['@Mock Logger', 'when(logger.isDebugEnabled()).thenReturn(true)'],
            'time': ['@Mock Clock', 'when(clock.instant()).thenReturn(fixedInstant)'],
            'random': ['@Mock Random', 'when(random.nextInt()).thenReturn(fixedValue)'],
            # Enhanced examples for new categories
            'environment': ['@Mock System', 'when(System.getenv("VAR")).thenReturn("test_value")', 'verify(System).getProperty("key")'],
            'object_creation': ['@Mock ClassName', 'when(mockObject.method()).thenReturn(value)', 'verify(mockObject).method()'],
            'reflection': ['@Mock Class', 'when(clazz.getMethod()).thenReturn(method)', 'verify(clazz).newInstance()'],
            'io_operations': ['@Mock InputStream', 'when(inputStream.read()).thenReturn(data)', 'verify(inputStream).close()'],
            'method_calls': ['@Mock Object', 'when(mockObject.method()).thenReturn(result)', 'verify(mockObject).method()'],
            'static_calls': ['@Mock ClassName', 'when(ClassName.staticMethod()).thenReturn(value)', 'verify(ClassName).staticMethod()'],
            # NEW: Additional specific mocking examples
            'security': ['@Mock SecurityContext', 'when(securityContext.getAuthentication()).thenReturn(mockAuth)', 'verify(authentication).getPrincipal()'],
            'validation': ['@Mock Validator', 'when(validator.validate()).thenReturn(violations)', 'verify(validator).validate()'],
            'serialization': ['@Mock ObjectMapper', 'when(objectMapper.writeValueAsString()).thenReturn(json)', 'verify(objectMapper).readValue()'],
            'caching': ['@Mock CacheManager', 'when(cacheManager.getCache()).thenReturn(mockCache)', 'verify(cache).put()'],
            'messaging': ['@Mock MessageProducer', 'when(producer.send()).thenReturn(future)', 'verify(producer).send()'],
            'scheduling': ['@Mock TaskScheduler', 'when(scheduler.schedule()).thenReturn(scheduledFuture)', 'verify(scheduler).schedule()'],
            'configuration': ['@MockBean ConfigurationClass', 'when(configBean.getProperty()).thenReturn(value)', 'verify(configBean).getProperty()'],
            'testing': ['@MockBean TestClass', 'when(testBean.method()).thenReturn(result)', 'verify(testBean).method()'],
            'metrics': ['@Mock MeterRegistry', 'when(registry.counter()).thenReturn(mockCounter)', 'verify(counter).increment()'],
            'actuator': ['@Mock HealthIndicator', 'when(healthIndicator.health()).thenReturn(health)', 'verify(healthIndicator).health()'],
            # NEW: Spring Boot specific examples
            'spring_boot': ['@MockBean ServiceClass', 'when(serviceBean.method()).thenReturn(result)', 'verify(serviceBean).method()'],
            'spring_web': ['@MockBean RestController', 'when(controller.method()).thenReturn(response)', 'verify(controller).method()'],
            'spring_security': ['@MockBean SecurityConfig', 'when(securityConfig.authenticationManager()).thenReturn(mockAuthManager)', 'verify(securityConfig).authenticationManager()'],
            'spring_data': ['@MockBean Repository', 'when(repository.findById(any())).thenReturn(Optional.of(entity))', 'verify(repository).save(any())'],
            'spring_batch': ['@MockBean JobLauncher', 'when(jobLauncher.run(any(Job.class), any(JobParameters.class))).thenReturn(jobExecution)', 'verify(jobLauncher).run(any(), any())'],
            'spring_cloud': ['@MockBean FeignClient', 'when(feignClient.call(any())).thenReturn(response)', 'verify(feignClient).call(any())'],
            'spring_kafka': ['@MockBean KafkaTemplate', 'when(kafkaTemplate.send(anyString(), any())).thenReturn(future)', 'verify(kafkaTemplate).send(anyString(), any())'],
            'spring_amqp': ['@MockBean RabbitTemplate', 'when(rabbitTemplate.convertAndSend(anyString(), any())).thenReturn(null)', 'verify(rabbitTemplate).convertAndSend(anyString(), any())'],
            # NEW: Hibernate/JPA specific examples
            'hibernate': ['@MockBean EntityManager', 'when(entityManager.find(any(Class.class), any())).thenReturn(entity)', 'verify(entityManager).persist(any())'],
            'hibernate_advanced': ['@MockBean SessionFactory', 'when(sessionFactory.openSession()).thenReturn(mockSession)', 'verify(sessionFactory).openSession()'],
            'jpa_queries': ['@MockBean CriteriaBuilder', 'when(criteriaBuilder.createQuery()).thenReturn(mockQuery)', 'verify(criteriaBuilder).createQuery()'],
            # NEW: Testing frameworks
            'spring_test': ['@MockBean TestService', 'when(testService.method()).thenReturn(result)', 'verify(testService).method()'],
            'junit5_spring': ['@ExtendWith(SpringExtension.class)', '@MockBean TestComponent', 'when(testComponent.method()).thenReturn(value)', 'verify(testComponent).method()'],
            # NEW: Microservices
            'microservices': ['@MockBean DiscoveryClient', 'when(discoveryClient.getInstances(anyString())).thenReturn(instances)', 'verify(discoveryClient).getInstances(anyString())'],
            # NEW: Database advanced
            'database_advanced': ['@MockBean DataSource', 'when(dataSource.getConnection()).thenReturn(mockConnection)', 'verify(dataSource).getConnection()'],
            # NEW: Validation advanced
            'validation_advanced': ['@MockBean Validator', 'when(validator.validate(any())).thenReturn(violations)', 'verify(validator).validate(any())'],
            # NEW: AOP
            'spring_aop': ['@MockBean Aspect', 'when(aspect.advice(any())).thenReturn(result)', 'verify(aspect).advice(any())'],
            # NEW: Events
            'spring_events': ['@MockBean ApplicationEventPublisher', 'when(eventPublisher.publishEvent(any())).thenReturn(null)', 'verify(eventPublisher).publishEvent(any())'],
            # NEW: Configuration
            'spring_config': ['@MockBean ConfigurationClass', 'when(configClass.getProperty()).thenReturn(value)', 'verify(configClass).getProperty()'],
        }
        return examples.get(category, ['@Mock', 'when().thenReturn()', 'verify()'])
    
    def _analyze_dependency_patterns(self, source_code: str, dependent_methods: List[Dict]) -> List[str]:
        """Analyze patterns in dependency usage"""
        patterns = []
        
        # Check for dependency injection patterns
        if '@Autowired' in source_code or '@Inject' in source_code:
            patterns.append("Dependency injection pattern detected")
        
        # Check for factory patterns
        if 'Factory' in source_code or 'Builder' in source_code:
            patterns.append("Factory/Builder pattern detected")
        
        # Check for service layer patterns
        if 'Service' in source_code:
            patterns.append("Service layer pattern detected")
        
        # Check for repository patterns
        if 'Repository' in source_code:
            patterns.append("Repository pattern detected")
        
        return patterns
    
    async def _detect_edge_cases(self, source_code: str, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential edge cases using hybrid approach (regex + LLM).
        
        Returns:
            Dict with edge case analysis results
        """
        # Use the same complexity check to determine analysis method
        if self._should_use_llm_analysis(source_code, method_info):
            logger.info(f"    🤖 Using LLM for edge case detection...")
            result = await self._detect_edge_cases_with_llm(source_code, method_info)
            self.update_hybrid_stats('llm')
            return result
        else:
            logger.info(f"    ⚡ Using fast regex for edge case detection...")
            result = await self._detect_edge_cases_regex(source_code, method_info)
            self.update_hybrid_stats('regex')
            return result
    
    async def _detect_edge_cases_regex(self, source_code: str, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast regex-based edge case detection for simple code.
        
        Returns:
            Dict with edge case analysis results
        """
        logger.info(f"    🎯 Detecting edge cases (regex)...")
        
        # Detect edge cases
        edge_cases = self._identify_edge_cases(source_code, method_info)
        
        # Detect exception scenarios
        exception_scenarios = self._identify_exception_scenarios(source_code)
        
        # Detect boundary conditions
        boundary_conditions = self._identify_boundary_conditions(source_code, method_info)
        
        # Detect null safety issues
        null_safety_issues = self._detect_null_safety_issues(source_code)
        
        return {
            "edge_cases": edge_cases,
            "exception_scenarios": exception_scenarios,
            "boundary_conditions": boundary_conditions,
            "null_safety_issues": null_safety_issues,
            "analysis_method": "regex",
            "analysis_timestamp": self._get_timestamp()
        }
    
    async def _detect_edge_cases_with_llm(self, source_code: str, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM-based edge case detection for complex code.
        
        Returns:
            Dict with detailed edge case analysis results
        """
        logger.info(f"    🤖 Performing deep LLM edge case analysis...")
        
        method_name = method_info.get('name', 'unknown')
        class_name = method_info.get('class_name', 'UnknownClass')
        
        # Build prompt for LLM analysis
        prompt = f"""Analyze this Java method and identify ALL possible edge cases, exception scenarios, and boundary conditions for comprehensive test coverage.

**Method:** {class_name}.{method_name}

**Source Code:**
```java
{source_code}
```

Please provide a comprehensive edge case analysis in JSON format with the following structure:

{{
    "edge_cases": [
        {{
            "type": "<edge_case_type>",
            "description": "<detailed description>",
            "test_suggestion": "<specific test approach>",
            "priority": "<high|medium|low>",
            "business_impact": "<description of business impact>",
            "test_data": "<specific test data to use>"
        }}
    ],
    "exception_scenarios": [
        {{
            "exception_type": "<Exception class or scenario>",
            "description": "<when this exception occurs>",
            "test_suggestion": "<how to test this scenario>",
            "priority": "<high|medium|low>",
            "trigger_condition": "<specific condition that triggers this>"
        }}
    ],
    "boundary_conditions": [
        {{
            "boundary_type": "<type of boundary>",
            "description": "<description of the boundary>",
            "test_suggestion": "<how to test boundary conditions>",
            "priority": "<high|medium|low>",
            "critical_values": ["<list of critical boundary values>"]
        }}
    ],
    "null_safety_issues": [
        {{
            "parameter": "<parameter or variable name>",
            "issue": "<description of null safety concern>",
            "test_suggestion": "<how to test null scenarios>",
            "priority": "<high|medium|low>"
        }}
    ],
    "complex_scenarios": [
        {{
            "scenario": "<complex test scenario>",
            "description": "<why this scenario is important>",
            "test_approach": "<detailed testing approach>",
            "priority": "<high|medium|low>"
        }}
    ],
    "business_logic_edge_cases": [
        {{
            "case": "<business-specific edge case>",
            "description": "<business context and importance>",
            "test_strategy": "<how to test this business scenario>",
            "priority": "<high|medium|low>"
        }}
    ]
}}

Focus on:
1. **ALL possible input combinations** that could cause issues
2. **Business logic edge cases** specific to the domain
3. **Resource constraints** (memory, time, disk space)
4. **Concurrency issues** if applicable
5. **Data validation edge cases**
6. **Integration points** and external dependencies
7. **Performance boundaries** and limits
8. **Security considerations** and injection points

Be thorough and identify edge cases that a simple regex analysis would miss. Provide specific, actionable test scenarios."""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert Java testing specialist with deep knowledge of edge cases, boundary conditions, and exception scenarios. Provide comprehensive, actionable test scenarios in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self.call_llm(messages, max_tokens=2000)
            
            # Parse LLM response
            try:
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                    
                    # Merge with basic regex analysis for consistency
                    basic_analysis = await self._detect_edge_cases_regex(source_code, method_info)
                    
                    # Combine results
                    result = {
                        **basic_analysis,
                        **analysis_data,
                        "analysis_method": "llm",
                        "llm_insights": True
                    }
                    
                    total_edge_cases = (
                        len(result.get('edge_cases', [])) +
                        len(result.get('exception_scenarios', [])) +
                        len(result.get('boundary_conditions', [])) +
                        len(result.get('complex_scenarios', [])) +
                        len(result.get('business_logic_edge_cases', []))
                    )
                    
                    logger.info(f"    ✅ LLM edge case analysis completed: {total_edge_cases} total scenarios identified")
                    return result
                else:
                    logger.warning("    ⚠️ Could not parse LLM response as JSON, falling back to regex")
                    return await self._detect_edge_cases_regex(source_code, method_info)
                    
            except json.JSONDecodeError as e:
                logger.warning(f"    ⚠️ JSON parsing failed: {e}, falling back to regex")
                return await self._detect_edge_cases_regex(source_code, method_info)
                
        except Exception as e:
            logger.error(f"    ❌ LLM edge case analysis failed: {e}, falling back to regex")
            return await self._detect_edge_cases_regex(source_code, method_info)
    
    def _identify_edge_cases(self, source_code: str, method_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify potential edge cases"""
        edge_cases = []
        
        # Check for null handling
        if 'null' in source_code.lower():
            edge_cases.append({
                'type': 'null_input',
                'description': 'Method handles null inputs',
                'test_suggestion': 'Test with null parameters',
                'priority': 'high'
            })
        
        # Check for empty collection handling
        if any(pattern in source_code.lower() for pattern in ['empty', 'isEmpty()', 'size() == 0']):
            edge_cases.append({
                'type': 'empty_collection',
                'description': 'Method handles empty collections',
                'test_suggestion': 'Test with empty lists/arrays',
                'priority': 'medium'
            })
        
        # Check for zero/numeric edge cases
        if any(pattern in source_code for pattern in ['== 0', '> 0', '< 0', '<= 0', '>= 0']):
            edge_cases.append({
                'type': 'numeric_boundary',
                'description': 'Method has numeric boundary conditions',
                'test_suggestion': 'Test with zero, negative, and boundary values',
                'priority': 'medium'
            })
        
        # Check for string edge cases
        if any(pattern in source_code for pattern in ['String', 'length()', 'substring']):
            edge_cases.append({
                'type': 'string_edge_cases',
                'description': 'Method processes strings',
                'test_suggestion': 'Test with empty strings, whitespace, and special characters',
                'priority': 'medium'
            })
        
        return edge_cases
    
    def _identify_exception_scenarios(self, source_code: str) -> List[Dict[str, Any]]:
        """Identify potential exception scenarios"""
        exception_scenarios = []
        
        # Check for exception throwing
        if 'throw new' in source_code or 'throws' in source_code:
            exception_scenarios.append({
                'type': 'explicit_exceptions',
                'description': 'Method explicitly throws exceptions',
                'test_suggestion': 'Test exception scenarios with assertThrows',
                'priority': 'high'
            })
        
        # Check for division operations
        if '/' in source_code and not source_code.count('/') == source_code.count('//'):
            exception_scenarios.append({
                'type': 'division_by_zero',
                'description': 'Method performs division operations',
                'test_suggestion': 'Test division by zero scenarios',
                'priority': 'high'
            })
        
        # Check for array access
        if '[' in source_code and ']' in source_code:
            exception_scenarios.append({
                'type': 'array_index_out_of_bounds',
                'description': 'Method accesses arrays',
                'test_suggestion': 'Test array bounds scenarios',
                'priority': 'medium'
            })
        
        return exception_scenarios
    
    def _identify_boundary_conditions(self, source_code: str, method_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify boundary conditions"""
        boundary_conditions = []
        
        # Check for MAX/MIN values
        if any(pattern in source_code for pattern in ['MAX_VALUE', 'MIN_VALUE', 'Integer.MAX', 'Long.MAX']):
            boundary_conditions.append({
                'type': 'max_min_values',
                'description': 'Method uses MAX/MIN constants',
                'test_suggestion': 'Test with Integer.MAX_VALUE, Integer.MIN_VALUE',
                'priority': 'high'
            })
        
        # Check for loop conditions
        if any(pattern in source_code for pattern in ['for(', 'while(', 'do {']):
            boundary_conditions.append({
                'type': 'loop_boundaries',
                'description': 'Method contains loops',
                'test_suggestion': 'Test with empty iterations and single iterations',
                'priority': 'medium'
            })
        
        return boundary_conditions
    
    def _detect_null_safety_issues(self, source_code: str) -> List[Dict[str, Any]]:
        """Detect potential null safety issues"""
        null_safety_issues = []
        
        # Check for direct field access without null checks
        field_access_pattern = r'\w+\.\w+(?!\s*[!=]=)'
        field_accesses = re.findall(field_access_pattern, source_code)
        
        for access in field_accesses:
            if not any(null_check in source_code for null_check in [f'{access.split(".")[0]} != null', f'{access.split(".")[0]} == null']):
                null_safety_issues.append({
                    'type': 'potential_null_pointer',
                    'description': f'Direct access to {access} without null check',
                    'test_suggestion': f'Test with null {access.split(".")[0]}',
                    'priority': 'high'
                })
        
        return null_safety_issues
    
    async def _analyze_performance(self, source_code: str, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze performance implications of the method.
        
        Returns:
            Dict with performance analysis results
        """
        logger.info(f"    ⚡ Analyzing performance...")
        
        # Analyze performance patterns
        performance_patterns = self._identify_performance_patterns(source_code)
        
        # Check for resource concerns
        resource_concerns = self._identify_resource_concerns(source_code)
        
        # Check for async operations
        has_async_operations = self._detect_async_operations(source_code)
        
        # Determine performance level
        performance_level = self._determine_performance_level(performance_patterns, resource_concerns)
        
        return {
            "performance_patterns": performance_patterns,
            "resource_concerns": resource_concerns,
            "has_async_operations": has_async_operations,
            "performance_level": performance_level,
            "analysis_timestamp": self._get_timestamp()
        }
    
    def _identify_performance_patterns(self, source_code: str) -> List[str]:
        """Identify performance-related patterns"""
        patterns = []
        
        # Check for loops
        if 'for(' in source_code or 'while(' in source_code:
            patterns.append("Contains loops")
            
            # Check for nested loops
            nested_loops = source_code.count('for(') + source_code.count('while(')
            if nested_loops > 1:
                patterns.append("Contains nested loops (O(n²) potential)")
        
        # Check for collections operations
        if any(pattern in source_code for pattern in ['stream()', 'forEach', 'map(', 'filter(']):
            patterns.append("Uses Stream API")
        
        # Check for recursive calls
        method_name = self._extract_method_name(source_code)
        if method_name and method_name in source_code:
            patterns.append("Potential recursion")
        
        return patterns
    
    def _identify_resource_concerns(self, source_code: str) -> List[Dict[str, Any]]:
        """Identify potential resource concerns"""
        concerns = []
        
        # Check for file operations
        if any(pattern in source_code for pattern in ['File', 'Files.', 'InputStream', 'OutputStream']):
            concerns.append({
                'type': 'file_operations',
                'description': 'File I/O operations detected',
                'impact': 'medium',
                'recommendation': 'Ensure proper resource cleanup in tests'
            })
        
        # Check for database operations
        if any(pattern in source_code for pattern in ['Repository', 'EntityManager', 'save(', 'findBy']):
            concerns.append({
                'type': 'database_operations',
                'description': 'Database operations detected',
                'impact': 'high',
                'recommendation': 'Use in-memory database or mocks for tests'
            })
        
        # Check for network operations
        if any(pattern in source_code for pattern in ['HttpClient', 'RestTemplate', 'WebClient']):
            concerns.append({
                'type': 'network_operations',
                'description': 'Network operations detected',
                'impact': 'high',
                'recommendation': 'Mock network calls for isolated testing'
            })
        
        return concerns
    
    def _detect_async_operations(self, source_code: str) -> bool:
        """Detect if method has async operations"""
        async_patterns = [
            'CompletableFuture',
            'Future',
            '@Async',
            'async',
            'await',
            'thenApply',
            'thenAccept'
        ]
        
        return any(pattern in source_code for pattern in async_patterns)
    
    def _determine_performance_level(self, patterns: List[str], concerns: List[Dict]) -> str:
        """Determine overall performance level"""
        if len(concerns) > 2 or 'O(n²) potential' in patterns:
            return "High Impact"
        elif len(concerns) > 0 or len(patterns) > 2:
            return "Medium Impact"
        else:
            return "Low Impact"
    
    def _extract_method_name(self, source_code: str) -> Optional[str]:
        """Extract method name from source code"""
        method_match = re.search(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(', source_code)
        return method_match.group(1) if method_match else None
    
    async def _generate_test_recommendations(
        self,
        complexity_analysis: Dict[str, Any],
        dependency_analysis: Dict[str, Any],
        edge_case_analysis: Dict[str, Any],
        performance_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive test recommendations based on all analyses.
        
        Returns:
            Dict with test recommendations
        """
        logger.info(f"    💡 Generating test recommendations...")
        
        # Calculate recommended test count
        recommended_test_count = self._calculate_recommended_test_count(
            complexity_analysis, edge_case_analysis
        )
        
        # Generate test priorities
        test_priorities = self._generate_test_priorities(
            complexity_analysis, dependency_analysis, edge_case_analysis, performance_analysis
        )
        
        # Generate special considerations
        special_considerations = self._generate_special_considerations(
            complexity_analysis, dependency_analysis, performance_analysis
        )
        
        # Generate test strategy
        test_strategy = self._generate_test_strategy(
            complexity_analysis, dependency_analysis, edge_case_analysis
        )
        
        return {
            "recommended_test_count": recommended_test_count,
            "test_priorities": test_priorities,
            "special_considerations": special_considerations,
            "test_strategy": test_strategy,
            "analysis_timestamp": self._get_timestamp()
        }
    
    def _calculate_recommended_test_count(
        self,
        complexity_analysis: Dict[str, Any],
        edge_case_analysis: Dict[str, Any]
    ) -> int:
        """Calculate recommended number of test methods"""
        base_tests = 3  # Happy path, edge case, exception
        
        # Add tests based on complexity
        complexity = complexity_analysis['cyclomatic_complexity']
        if complexity > 10:
            base_tests += 3
        elif complexity > 5:
            base_tests += 2
        else:
            base_tests += 1
        
        # Add tests based on edge cases
        edge_cases_count = len(edge_case_analysis['edge_cases'])
        base_tests += min(edge_cases_count, 5)  # Cap at 5 additional tests
        
        return min(base_tests, 15)  # Cap at 15 tests total
    
    def _generate_test_priorities(
        self,
        complexity_analysis: Dict[str, Any],
        dependency_analysis: Dict[str, Any],
        edge_case_analysis: Dict[str, Any],
        performance_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate prioritized test recommendations"""
        priorities = []
        
        # High priority based on complexity
        if complexity_analysis['complexity_level'] in ['High', 'Very High']:
            priorities.append("Focus on comprehensive branch coverage due to high complexity")
        
        # High priority based on dependencies
        if len(dependency_analysis['critical_deps']) > 0:
            priorities.append("Mock all critical dependencies for isolated testing")
        
        # High priority based on edge cases
        if len(edge_case_analysis['edge_cases']) > 3:
            priorities.append("Prioritize edge case testing - multiple edge cases detected")
        
        # Medium priority based on performance
        if performance_analysis['performance_level'] != 'Low Impact':
            priorities.append("Include performance-related test scenarios")
        
        # General priorities
        priorities.extend([
            "Always test happy path scenario first",
            "Include at least one exception test case",
            "Test with boundary values and edge cases",
            "Verify all assertions have descriptive messages"
        ])
        
        return priorities
    
    def _generate_special_considerations(
        self,
        complexity_analysis: Dict[str, Any],
        dependency_analysis: Dict[str, Any],
        performance_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate special testing considerations"""
        considerations = []
        
        # Complexity considerations
        if complexity_analysis['complexity_level'] == 'Very High':
            considerations.append("Consider refactoring before adding more tests - complexity is very high")
        
        # Dependency considerations
        if len(dependency_analysis['external_deps']) > 0:
            considerations.append("External dependencies detected - ensure proper mocking strategy")
        
        # Performance considerations
        if performance_analysis['has_async_operations']:
            considerations.append("Async operations detected - consider testing with CompletableFuture")
        
        if len(performance_analysis['resource_concerns']) > 0:
            considerations.append("Resource-intensive operations detected - test resource cleanup")
        
        return considerations
    
    def _generate_test_strategy(
        self,
        complexity_analysis: Dict[str, Any],
        dependency_analysis: Dict[str, Any],
        edge_case_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate overall test strategy"""
        strategy = {
            "approach": "comprehensive",
            "focus_areas": [],
            "testing_patterns": ["Arrange-Act-Assert"],
            "tools_recommended": ["JUnit 5", "Mockito"]
        }
        
        # Determine approach based on complexity
        if complexity_analysis['complexity_level'] in ['High', 'Very High']:
            strategy["approach"] = "branch-focused"
            strategy["focus_areas"].append("Complete branch coverage")
        
        # Add focus areas based on analysis
        if len(dependency_analysis['critical_deps']) > 0:
            strategy["focus_areas"].append("Dependency mocking")
        
        if len(edge_case_analysis['edge_cases']) > 0:
            strategy["focus_areas"].append("Edge case validation")
        
        # Add testing patterns based on dependencies
        if any(dep['category'] == 'database' for dep in dependency_analysis['external_deps']):
            strategy["testing_patterns"].append("Database transaction testing")
        
        if any(dep['category'] == 'network' for dep in dependency_analysis['external_deps']):
            strategy["testing_patterns"].append("HTTP client mocking")
        
        return strategy
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_system_prompt(self) -> str:
        """Override to provide specialized system prompt"""
        return """You are an expert code analysis AI specialized in deep analysis of Java methods for test generation.

Your role is to:
1. Analyze code complexity and patterns
2. Identify dependencies and their criticality
3. Detect edge cases and potential issues
4. Assess performance implications
5. Generate comprehensive test recommendations

Provide detailed, actionable analysis that will help generate high-quality unit tests."""
