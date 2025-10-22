"""
CriticAgent - Evaluates test quality and suggests improvements.

Responsibilities:
- Analyze generated test code
- Check compilability
- Evaluate coverage and quality
- Score tests (0-100)
- Provide improvement suggestions

Pattern: Evaluation & Guardrails (4.6, 4.5)
"""

from typing import List, Dict, Any, Optional
import re
import json
import subprocess
import tempfile
from pathlib import Path

from agents.base import BaseJavaAgent, AgentState
from logger import get_logger

logger = get_logger(__name__)


class CriticAgent(BaseJavaAgent):
    """
    Agent responsible for evaluating test quality.
    
    Scoring Criteria (0-100):
    - Compilability: 20 points
    - Edge case coverage: 30 points
    - Assertion quality: 20 points
    - Proper mocking: 15 points
    - Code readability: 15 points
    """
    
    # Quality thresholds
    PASSING_SCORE = 70
    EXCELLENT_SCORE = 90
    
    def __init__(self):
        """Initialize CriticAgent"""
        super().__init__(
            name="CriticAgent",
            role="Test quality evaluation and improvement",
            tools=[],
            temperature=0.3  # Lower temperature for objective evaluation
        )
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute test quality evaluation.
        
        Args:
            state: Current agent state with test_code
        
        Returns:
            Updated state with quality_score, issues, suggestions
        """
        logger.info("="*80)
        logger.info(f"[{self.name}] 🔎 STARTING QUALITY EVALUATION")
        logger.info("="*80)
        
        try:
            if not state.test_code:
                error_msg = "No test code to evaluate"
                logger.error(f"  ❌ {error_msg}")
                self.log_error(error_msg, state)
                return state
            
            test_length = len(state.test_code)
            test_count = state.test_code.count("@Test")
            logger.info(f"  📝 Evaluating test code:")
            logger.info(f"    • Code length: {test_length} characters")
            logger.info(f"    • Test methods: {test_count}")
            logger.info("")
            
            # Perform evaluations
            scores = {}
            
            # Determine if test code is complex enough for LLM analysis
            if self._should_use_llm_evaluation(state.test_code, state):
                logger.info(f"  🤖 Using LLM for comprehensive test quality evaluation...")
                scores = await self._evaluate_test_quality_with_llm(state.test_code, state)
                self.update_hybrid_stats('llm')
                # Extract issues from scores
                all_issues = []
                for criterion, score_data in scores.items():
                    if isinstance(score_data, dict) and 'issues' in score_data:
                        all_issues.extend(score_data['issues'])
                state.issues.extend(all_issues)
            else:
                logger.info(f"  ⚡ Using fast regex evaluation for simple tests...")
                scores = await self._evaluate_test_quality_regex(state.test_code, state)
                self.update_hybrid_stats('regex')
                # Extract issues from scores
                all_issues = []
                for criterion, score_data in scores.items():
                    if isinstance(score_data, dict) and 'issues' in score_data:
                        all_issues.extend(score_data['issues'])
                state.issues.extend(all_issues)
            
            # Log scores
            for criterion, score_data in scores.items():
                if isinstance(score_data, dict):
                    score = score_data.get('score', 0)
                    max_score = score_data.get('max_score', 0)
                    issues_count = len(score_data.get('issues', []))
                    
                    # Map criterion names for logging
                    criterion_names = {
                        'compilability': 'Compilability',
                        'coverage': 'Edge Case Coverage', 
                        'assertions': 'Assertion Quality',
                        'mocking': 'Mocking Strategy',
                        'readability': 'Code Readability'
                    }
                    
                    criterion_name = criterion_names.get(criterion, criterion.title())
                    logger.info(f"  🔍 {criterion_name}: {score}/{max_score}")
                    if issues_count > 0:
                        logger.info(f"       Issues: {issues_count}")
                    self.log_step(f"{criterion_name}: {score}/{max_score}", state)
            logger.info("")
            logger.info("")
            
            # Calculate total score
            total_score = 0
            for criterion, score_data in scores.items():
                if isinstance(score_data, dict):
                    total_score += score_data.get('score', 0)
                else:
                    total_score += score_data  # Fallback for simple numeric scores
            state.quality_score = int(total_score)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(scores, state.issues)
            state.suggestions = suggestions
            
            # Log result
            quality_level = self._get_quality_level(total_score)
            quality_emoji = "🌟" if total_score >= 90 else "⭐" if total_score >= 75 else "✨" if total_score >= 60 else "⚠️"
            
            logger.info("="*80)
            logger.info(f"[{self.name}] {quality_emoji} QUALITY EVALUATION COMPLETED")
            logger.info("="*80)
            logger.info(f"  📊 Score Breakdown:")
            # Helper function to get score value
            def get_score_value(criterion: str) -> int:
                score_data = scores.get(criterion, 0)
                if isinstance(score_data, dict):
                    return score_data.get('score', 0)
                return score_data
            
            compilability_score = get_score_value("compilability")
            coverage_score = get_score_value("coverage")
            assertions_score = get_score_value("assertions")
            mocking_score = get_score_value("mocking")
            readability_score = get_score_value("readability")
            
            logger.info(f"    • Compilability:  {compilability_score:2.0f}/20  ({compilability_score/20*100:.0f}%)")
            logger.info(f"    • Coverage:       {coverage_score:2.0f}/30  ({coverage_score/30*100:.0f}%)")
            logger.info(f"    • Assertions:     {assertions_score:2.0f}/20  ({assertions_score/20*100:.0f}%)")
            logger.info(f"    • Mocking:        {mocking_score:2.0f}/15  ({mocking_score/15*100:.0f}%)")
            logger.info(f"    • Readability:    {readability_score:2.0f}/15  ({readability_score/15*100:.0f}%)")
            logger.info(f"  " + "-"*76)
            logger.info(f"  🎯 TOTAL SCORE:     {total_score}/100  ({quality_level})")
            logger.info("")
            logger.info(f"  ⚠️  Issues found: {len(state.issues)}")
            logger.info(f"  💡 Suggestions: {len(suggestions)}")
            
            if suggestions:
                logger.info(f"  📝 Top suggestions:")
                for i, suggestion in enumerate(suggestions[:3], 1):
                    logger.info(f"    {i}. {suggestion}")
            
            logger.info("="*80)
            logger.info("")
            
            # Log hybrid approach statistics
            self.log_hybrid_stats()
            
            self.log_step(f"Final score: {total_score}/100 ({quality_level})", state)
            
            return state
            
        except Exception as e:
            error_msg = f"Test evaluation failed: {str(e)}"
            logger.exception(f"[{self.name}] {error_msg}")
            self.log_error(error_msg, state)
            return state
    
    async def _evaluate_compilability(
        self,
        test_code: str
    ) -> tuple[int, List[str]]:
        """
        Check if test code is likely compilable.
        
        Returns:
            Tuple of (score 0-20, issues list)
        """
        issues = []
        score = 20  # Start with full points
        
        # Check for class declaration
        if not re.search(r"class\s+\w+Test", test_code):
            issues.append("Missing test class declaration")
            score -= 5
        
        # Check for package declaration (WARNING only, don't penalize heavily)
        if "package " not in test_code:
            # Package is optional for simple tests, just log it
            pass  # Don't penalize
        
        # Check for basic imports
        required_imports = ["org.junit"]
        for imp in required_imports:
            if imp not in test_code:
                issues.append(f"Missing import: {imp}")
                score -= 3
        
        # Check for balanced braces
        open_braces = test_code.count("{")
        close_braces = test_code.count("}")
        if open_braces != close_braces:
            issues.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
            score -= 5
        
        # Check for balanced parentheses
        open_parens = test_code.count("(")
        close_parens = test_code.count(")")
        if open_parens != close_parens:
            issues.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
            score -= 3
        
        # Check for syntax errors (basic)
        if ";;" in test_code:
            issues.append("Possible syntax error: double semicolon")
            score -= 2
        
        # Check that all @Test methods have void return type
        test_methods = re.findall(r"@Test\s+(?:public\s+)?(\w+)\s+(\w+)\s*\(", test_code)
        for return_type, method_name in test_methods:
            if return_type != "void":
                issues.append(f"Test method {method_name} should return void, not {return_type}")
                score -= 2
        
        return max(0, score), issues
    
    def _evaluate_coverage(self, test_code: str, state: AgentState = None) -> tuple[int, List[str]]:
        """
        Evaluate test coverage quality using real coverage metrics when available.
        
        Returns:
            Tuple of (score 0-30, issues list)
        """
        issues = []
        score = 0
        
        # If we have real coverage metrics, use them
        if state and hasattr(state, 'coverage_metrics') and state.coverage_metrics:
            real_coverage = state.coverage_metrics.get('line_coverage', 0)
            branch_coverage = state.coverage_metrics.get('branch_coverage', 0)
            
            logger.info(f"    📊 Using REAL coverage metrics:")
            logger.info(f"       • Line coverage: {real_coverage:.1f}%")
            logger.info(f"       • Branch coverage: {branch_coverage:.1f}%")
            
            # Score based on real coverage
            if real_coverage >= 90:
                score = 30
                logger.info(f"       ✅ Excellent coverage: {real_coverage:.1f}%")
            elif real_coverage >= 80:
                score = 25
                logger.info(f"       ✅ Good coverage: {real_coverage:.1f}%")
            elif real_coverage >= 70:
                score = 20
                logger.info(f"       ⚠️  Acceptable coverage: {real_coverage:.1f}%")
            elif real_coverage >= 50:
                score = 15
                logger.info(f"       ⚠️  Low coverage: {real_coverage:.1f}%")
                issues.append(f"Low line coverage: {real_coverage:.1f}%")
            else:
                score = 10
                logger.info(f"       ❌ Very low coverage: {real_coverage:.1f}%")
                issues.append(f"Very low line coverage: {real_coverage:.1f}%")
            
            # Additional penalty for low branch coverage
            if branch_coverage < 50:
                score -= 5
                issues.append(f"Low branch coverage: {branch_coverage:.1f}%")
            
            return min(30, max(0, score)), issues
        
        # Fallback to static analysis if no real coverage
        logger.info(f"    📊 Using STATIC analysis (no real coverage available)")
        
        # Simple but effective test detection - just count @Test annotations
        num_tests = test_code.count("@Test")
        logger.info(f"    🔍 Found {num_tests} @Test annotations")
        
        if num_tests == 0:
            issues.append("No test methods found")
            return 0, issues
        
        # Base score for having tests
        score += min(10, num_tests * 2)  # Up to 10 points for quantity
        
        # Check for edge case tests
        edge_case_keywords = [
            "null", "empty", "zero", "negative", "boundary",
            "edge", "maximum", "minimum", "invalid"
        ]
        
        found_edge_cases = 0
        for keyword in edge_case_keywords:
            if keyword.lower() in test_code.lower():
                found_edge_cases += 1
        
        score += min(10, found_edge_cases * 2)  # Up to 10 points for edge cases
        
        if found_edge_cases == 0:
            issues.append("No edge case tests detected")
        
        # Check for exception testing
        if "assertThrows" in test_code or "expected" in test_code.lower():
            score += 5
        else:
            issues.append("No exception testing found")
        
        # Check for various assertion types
        assertion_types = ["assertEquals", "assertTrue", "assertFalse", "assertNotNull"]
        found_assertions = sum(1 for a in assertion_types if a in test_code)
        score += min(5, found_assertions)
        
        # Add warning about static analysis
        issues.append("Coverage estimated by static analysis - run CoverageAgent for real metrics")
        
        return min(30, score), issues
    
    def _evaluate_assertions(self, test_code: str) -> tuple[int, List[str]]:
        """
        Evaluate assertion quality.
        
        Returns:
            Tuple of (score 0-20, issues list)
        """
        issues = []
        score = 0
        
        # Find all assertions
        assertion_pattern = r"assert\w+\s*\("
        assertions = re.findall(assertion_pattern, test_code)
        
        if not assertions:
            issues.append("No assertions found")
            return 0, issues
        
        # Base score for having assertions
        score += min(10, len(assertions))  # Up to 10 points
        
        # Check for assertion messages
        message_pattern = r'assert\w+\s*\([^)]*,\s*"[^"]*"'
        messages = re.findall(message_pattern, test_code)
        
        if messages:
            message_ratio = len(messages) / len(assertions)
            score += int(5 * message_ratio)  # Up to 5 points
        else:
            issues.append("Assertions lack descriptive messages")
        
        # Check for specific assertion types
        if "assertNotNull" in test_code:
            score += 2
        if "assertThrows" in test_code:
            score += 3
        
        return min(20, score), issues
    
    def _evaluate_mocking(self, test_code: str) -> tuple[int, List[str]]:
        """
        Evaluate mocking strategy with enhanced dependency detection.
        
        Now uses stricter evaluation for external dependencies.
        
        Returns:
            Tuple of (score 0-15, issues list)
        """
        issues = []
        score = 0  # Start with 0 points - must earn them
        
        # Enhanced dependency detection patterns with more categories
        critical_dependency_patterns = {
            'system_env': r'System\.getenv\s*\(',
            'system_props': r'System\.getProperty\s*\(',
            'object_creation': r'new\s+[A-Z]\w*\s*\(',
            'method_calls': r'[a-zA-Z_]\w*\.\w+\s*\(',
            'static_calls': r'[A-Z]\w*\.\w+\s*\(',
            'io_operations': r'\.(read|write|flush|close|available|skip)\s*\(',
            'database': r'(Repository|EntityManager|JpaRepository|CrudRepository|\.save|\.findBy|\.delete|@Transactional|@Entity)',
            'network': r'(HttpClient|RestTemplate|WebClient|OkHttp|ApacheHttp|\.get|\.post|\.put|\.delete)',
            'file_system': r'(Files\.|File\.|Path\.|InputStream|OutputStream|BufferedReader|BufferedWriter)',
            'security': r'(SecurityContext|Authentication|Principal|@PreAuthorize|@Secured|BCrypt|JWT)',
            'validation': r'(@Valid|@NotNull|@NotEmpty|@Size|@Pattern|Validator\.|ConstraintViolation)',
            'serialization': r'(ObjectMapper|Gson|Jackson|@JsonIgnore|@JsonProperty|Serializable)',
            'caching': r'(@Cacheable|@CacheEvict|@CachePut|CacheManager|RedisTemplate|@EnableCaching)',
            'messaging': r'(@RabbitListener|@KafkaListener|@JmsListener|MessageProducer|MessageConsumer)',
            'scheduling': r'(@Scheduled|@EnableScheduling|TaskScheduler|CronExpression)',
            'configuration': r'(@Configuration|@Bean|@Component|@Service|@Repository|@Controller)',
            'testing': r'(@MockBean|@SpyBean|@TestConfiguration|@MockitoSettings)',
            'metrics': r'(@Timed|@Counted|MeterRegistry|Counter\.|Timer\.|Gauge\.)',
            'actuator': r'(@Actuator|HealthIndicator|@Endpoint|@ReadOperation)',
            'logging': r'(Logger|\.log\(|LogManager|LoggerFactory|@Slf4j|@Log4j2)',
            'time': r'(System\.currentTimeMillis|LocalDateTime|Instant\.|ZonedDateTime|Clock\.|Date\.)',
            'random': r'(Random|Math\.random|ThreadLocalRandom|SecureRandom)',
            'reflection': r'(\.getClass\(|\.getMethod\(|\.invoke\(|Field\.|Constructor\.|Method\.)',
            # NEW: Spring Boot specific patterns
            'spring_boot': r'(@SpringBootApplication|@RestController|@Controller|@Service|@Repository|@Component|@Autowired|@Value|@Configuration|@Bean|@Primary|@Qualifier|@Profile|@ConditionalOn|@EnableAutoConfiguration|@EnableWebMvc|@EnableJpaRepositories|@EnableTransactionManagement)',
            'spring_web': r'(@RequestMapping|@GetMapping|@PostMapping|@PutMapping|@DeleteMapping|@PatchMapping|@PathVariable|@RequestParam|@RequestBody|@ResponseBody|@ResponseStatus|@ExceptionHandler|@Valid|@ModelAttribute|@SessionAttribute|@CookieValue|@RequestHeader|@CrossOrigin)',
            'spring_security': r'(@EnableWebSecurity|@EnableGlobalMethodSecurity|@PreAuthorize|@PostAuthorize|@Secured|@RolesAllowed|@PermitAll|@DenyAll|SecurityContextHolder|Authentication|Principal|GrantedAuthority|UserDetails|UserDetailsService|PasswordEncoder|BCryptPasswordEncoder)',
            'spring_data': r'(@Repository|JpaRepository|CrudRepository|PagingAndSortingRepository|@Query|@Modifying|@Transactional|@Entity|@Table|@Id|@GeneratedValue|@Column|@OneToMany|@ManyToOne|@ManyToMany|@OneToOne|@JoinColumn|@JoinTable)',
            'spring_batch': r'(@EnableBatchProcessing|@Job|@Step|@ItemReader|@ItemProcessor|@ItemWriter|@JobParameters|@StepScope|@JobScope|JobLauncher|JobRepository|StepBuilderFactory|JobBuilderFactory)',
            'spring_cloud': r'(@EnableEurekaClient|@EnableDiscoveryClient|@EnableFeignClients|@EnableHystrix|@EnableCircuitBreaker|@EnableZuulProxy|@EnableConfigServer|@LoadBalanced|@HystrixCommand|@FeignClient|@RibbonClient)',
            'spring_kafka': r'(@EnableKafka|@KafkaListener|@KafkaHandler|@SendTo|@Header|@Payload|KafkaTemplate|ProducerFactory|ConsumerFactory|@KafkaTopic)',
            'spring_amqp': r'(@EnableRabbit|@RabbitListener|@RabbitHandler|@SendTo|@Header|@Payload|RabbitTemplate|@Queue|@Exchange|@Binding)',
            # NEW: Hibernate/JPA specific patterns
            'hibernate': r'(@Entity|@Table|@Id|@GeneratedValue|@Column|@OneToMany|@ManyToOne|@ManyToMany|@OneToOne|@JoinColumn|@JoinTable|@Embedded|@Embeddable|@Enumerated|@Temporal|@Lob|@Transient|@Version|@Cache|@Cacheable|@CacheEvict|@CachePut)',
            'hibernate_advanced': r'(@NamedQuery|@NamedQueries|@NamedNativeQuery|@SqlResultSetMapping|@EntityResult|@FieldResult|@ConstructorResult|@Formula|@Where|@WhereJoinTable|@Filter|@FilterDef|@FilterJoinTable|@Any|@AnyMetaDef|@MetaValue|@Type|@TypeDef|@TypeDefs)',
            'jpa_queries': r'(findBy|findAllBy|countBy|deleteBy|existsBy|@Query|@Modifying|@Param|@Procedure|@NamedStoredProcedureQuery|@StoredProcedureParameter|CriteriaBuilder|CriteriaQuery|Predicate|Root|Join|Subquery)',
            # NEW: Testing frameworks
            'spring_test': r'(@SpringBootTest|@WebMvcTest|@DataJpaTest|@JsonTest|@RestClientTest|@MockBean|@SpyBean|@TestConfiguration|@TestPropertySource|@ActiveProfiles|@DirtiesContext|@Transactional|@Rollback|@Commit|@Sql|@SqlGroup|@SqlConfig|TestRestTemplate|MockMvc|@AutoConfigureTestDatabase|@AutoConfigureTestEntityManager)',
            'junit5_spring': r'(@ExtendWith\(SpringExtension\.class\)|@SpringJUnitConfig|@SpringJUnitWebConfig|@TestPropertySource|@ActiveProfiles|@DirtiesContext|@Transactional|@Rollback|@Commit|@Sql|@SqlGroup|@SqlConfig|@MockBean|@SpyBean|@TestConfiguration)',
            # NEW: Microservices patterns
            'microservices': r'(@EnableEurekaClient|@EnableDiscoveryClient|@EnableFeignClients|@EnableHystrix|@EnableCircuitBreaker|@EnableZuulProxy|@EnableConfigServer|@LoadBalanced|@HystrixCommand|@FeignClient|@RibbonClient|@EnableAdminServer|@EnableTurbine|@EnableSleuth|@EnableZipkinServer)',
            # NEW: Database patterns
            'database_advanced': r'(@Transactional|@Rollback|@Commit|@Sql|@SqlGroup|@SqlConfig|@DataSource|@PersistenceContext|@PersistenceUnit|@EntityManager|@EntityManagerFactory|@Query|@Modifying|@Param|@Procedure|@NamedStoredProcedureQuery|@StoredProcedureParameter)',
            # NEW: Validation patterns
            'validation_advanced': r'(@Valid|@Validated|@NotNull|@NotEmpty|@NotBlank|@Size|@Min|@Max|@DecimalMin|@DecimalMax|@Digits|@Pattern|@Email|@URL|@AssertTrue|@AssertFalse|@Future|@Past|@PastOrPresent|@FutureOrPresent|@Positive|@PositiveOrZero|@Negative|@NegativeOrZero|@Range|@Length|@SafeHtml|@ScriptAssert)',
            # NEW: AOP patterns
            'spring_aop': r'(@Aspect|@Pointcut|@Before|@After|@AfterReturning|@AfterThrowing|@Around|@EnableAspectJAutoProxy|@Order|@DeclareParents|@DeclareMixin|@DeclareAnnotation|@DeclarePrecedence|@DeclareWarning|@DeclareError)',
            # NEW: Event patterns
            'spring_events': r'(@EventListener|@Async|@EnableAsync|@EnableScheduling|@Scheduled|@EnableCaching|@Cacheable|@CacheEvict|@CachePut|@Caching|@CacheConfig|ApplicationEventPublisher|ApplicationEvent|ApplicationListener)',
            # NEW: Configuration patterns
            'spring_config': r'(@Configuration|@ConfigurationProperties|@EnableConfigurationProperties|@ConditionalOnProperty|@ConditionalOnClass|@ConditionalOnMissingClass|@ConditionalOnBean|@ConditionalOnMissingBean|@ConditionalOnWebApplication|@ConditionalOnNotWebApplication|@ConditionalOnResource|@ConditionalOnExpression|@ConditionalOnJava|@ConditionalOnCloudPlatform|@ConditionalOnSingleCandidate|@ConditionalOnWarDeployment)',
        }
        
        # Check for critical dependencies that MUST be mocked
        critical_deps_found = []
        for dep_type, pattern in critical_dependency_patterns.items():
            matches = re.findall(pattern, test_code, re.IGNORECASE)
            if matches:
                critical_deps_found.append((dep_type, matches))
        
        # Check if mocking is used
        has_mock_annotation = "@Mock" in test_code
        has_mock_creation = "mock(" in test_code.lower() or "Mockito.mock" in test_code
        has_mockito_import = "import org.mockito" in test_code or "static org.mockito" in test_code
        has_mocking = has_mock_annotation or has_mock_creation or has_mockito_import
        
        if has_mocking:
            score += 5  # Base points for using mocks
            
            # Check for proper mock setup
            if "when(" in test_code and ".thenReturn" in test_code:
                score += 3  # BONUS for proper configuration
            elif has_mock_creation:
                issues.append("Mocks created but not properly configured with when().thenReturn()")
                score -= 2
            
            # Check for mock verification
            if "verify(" in test_code:
                score += 2  # BONUS for verification
            
            # Check for @InjectMocks
            if "@InjectMocks" in test_code:
                score += 1  # BONUS for dependency injection
            
            # Check if critical dependencies are properly mocked
            for dep_type, matches in critical_deps_found:
                if dep_type == 'system_env' and 'System.getenv' in test_code:
                    if not any(mock_pattern in test_code for mock_pattern in ['@Mock System', 'mock(System', 'when(System.getenv', 'MockedStatic<System>']):
                        issues.append("CRITICAL: System.getenv() calls must be mocked for predictable tests")
                        score -= 3
                
                elif dep_type == 'object_creation':
                    # Check if object creation is mocked
                    if not any(mock_pattern in test_code for mock_pattern in ['@Mock', 'mock(', 'when(']):
                        issues.append("CRITICAL: Object creation should be mocked for test isolation")
                        score -= 3
                
                elif dep_type in ['database', 'network', 'file_system', 'security', 'validation', 'serialization']:
                    if not has_mocking:
                        issues.append(f"CRITICAL: {dep_type} operations must be mocked for test isolation")
                        score -= 4
        else:
                        # Check for specific mocking patterns for each category
                        if dep_type == 'database' and not any(pattern in test_code for pattern in ['@Mock Repository', '@Mock EntityManager', 'mockRepository', 'mockEntityManager']):
                            issues.append(f"Consider specific mocking for {dep_type} components")
                            score -= 1
                        elif dep_type == 'network' and not any(pattern in test_code for pattern in ['@Mock RestTemplate', '@Mock HttpClient', 'mockRestTemplate', 'mockHttpClient']):
                            issues.append(f"Consider specific mocking for {dep_type} components")
                            score -= 1
                        elif dep_type == 'security' and not any(pattern in test_code for pattern in ['@Mock SecurityContext', '@Mock Authentication', 'mockSecurityContext', 'mockAuthentication']):
                            issues.append(f"Consider specific mocking for {dep_type} components")
                            score -= 1
                
                elif dep_type in ['caching', 'messaging', 'scheduling', 'metrics', 'actuator']:
                    if not has_mocking:
                        issues.append(f"Consider mocking {dep_type} operations for better test isolation")
                        score -= 2
                
                elif dep_type in ['logging', 'time', 'random', 'reflection']:
                    if not has_mocking:
                        issues.append(f"Consider mocking {dep_type} operations for predictable tests")
                        score -= 1
                # NEW: Spring Boot and framework specific checks
                elif dep_type in ['spring_boot', 'spring_web', 'spring_security', 'spring_data', 'hibernate', 'hibernate_advanced', 'jpa_queries']:
                    if not has_mocking:
                        issues.append(f"CRITICAL: {dep_type} components must be mocked for test isolation")
                        score -= 4
                    else:
                        # Specific checks for Spring components
                        if dep_type == 'spring_boot' and not any(pattern in test_code for pattern in ['@MockBean', '@SpyBean', '@TestConfiguration']):
                            issues.append(f"Consider using Spring Test annotations for {dep_type} components")
                            score -= 1
                        elif dep_type == 'spring_web' and not any(pattern in test_code for pattern in ['@MockBean', '@WebMvcTest', 'MockMvc']):
                            issues.append(f"Consider using @WebMvcTest or MockMvc for {dep_type} testing")
                            score -= 1
                        elif dep_type == 'spring_security' and not any(pattern in test_code for pattern in ['@MockBean', '@WithMockUser', '@WithUserDetails']):
                            issues.append(f"Consider using Spring Security test annotations for {dep_type}")
                            score -= 1
                        elif dep_type in ['spring_data', 'hibernate', 'hibernate_advanced', 'jpa_queries'] and not any(pattern in test_code for pattern in ['@MockBean', '@DataJpaTest', '@TestEntityManager']):
                            issues.append(f"Consider using @DataJpaTest or @MockBean for {dep_type} testing")
                            score -= 1
                elif dep_type in ['spring_batch', 'spring_cloud', 'spring_kafka', 'spring_amqp', 'microservices']:
                    if not has_mocking:
                        issues.append(f"CRITICAL: {dep_type} operations must be mocked for test isolation")
                        score -= 4
                    else:
                        # Specific checks for microservices and messaging
                        if dep_type in ['spring_kafka', 'spring_amqp'] and not any(pattern in test_code for pattern in ['@MockBean', 'EmbeddedKafka', 'EmbeddedRabbit']):
                            issues.append(f"Consider using embedded brokers or @MockBean for {dep_type} testing")
                            score -= 1
                        elif dep_type == 'spring_cloud' and not any(pattern in test_code for pattern in ['@MockBean', '@MockBean', 'WireMock']):
                            issues.append(f"Consider using WireMock or @MockBean for {dep_type} testing")
                            score -= 1
                elif dep_type in ['spring_test', 'junit5_spring', 'database_advanced', 'validation_advanced']:
                    if not has_mocking:
                        issues.append(f"Consider mocking {dep_type} operations for better test isolation")
                        score -= 2
                elif dep_type in ['spring_aop', 'spring_events', 'spring_config']:
                    if not has_mocking:
                        issues.append(f"Consider mocking {dep_type} operations for predictable tests")
                        score -= 1
        else:
            # No mocking detected - check if it's needed
            if critical_deps_found:
                # CRITICAL: External dependencies found but no mocking
                for dep_type, matches in critical_deps_found:
                    if dep_type == 'system_env':
                        issues.append("CRITICAL: System.getenv() calls must be mocked for predictable tests")
                        score -= 5
                    elif dep_type == 'object_creation':
                        issues.append("CRITICAL: Object creation should be mocked for test isolation")
                        score -= 5
                    elif dep_type in ['database', 'network', 'file_system']:
                        issues.append(f"CRITICAL: {dep_type} operations must be mocked for isolated testing")
                        score -= 5
                    else:
                        issues.append(f"Consider using mocks for {dep_type} operations")
                        score -= 2
            else:
                # No critical dependencies - give some points for simple tests
                score += 8
        
        # Additional checks for common mocking issues
        if has_mocking:
            # Check for proper Mockito imports
            if not has_mockito_import:
                issues.append("Missing Mockito imports - add 'import static org.mockito.Mockito.*;'")
                score -= 1
            
            # Check for proper mock initialization
            if has_mock_annotation and '@BeforeEach' not in test_code and 'MockitoAnnotations.openMocks' not in test_code:
                issues.append("Consider using @BeforeEach to initialize mocks with MockitoAnnotations.openMocks(this)")
                score -= 1
            
            # Check for MockitoExtension usage
            if has_mock_annotation and '@ExtendWith(MockitoExtension.class)' not in test_code:
                issues.append("Consider using @ExtendWith(MockitoExtension.class) for automatic mock initialization")
                score -= 1
            
            # Check for proper mock setup patterns
            if 'when(' in test_code and '.thenReturn(' in test_code:
                score += 2  # BONUS for proper mock configuration
            elif 'when(' in test_code and '.thenThrow(' in test_code:
                score += 1  # BONUS for exception testing
            
            # Check for argument matchers usage
            if 'any(' in test_code or 'anyString(' in test_code or 'anyInt(' in test_code:
                score += 1  # BONUS for using argument matchers
            
            # Check for mock verification patterns
            if 'verify(' in test_code:
                score += 1  # BONUS for verification
                if 'times(' in test_code or 'never(' in test_code:
                    score += 1  # BONUS for specific verification
            
            # Check for static mocking
            if 'MockedStatic' in test_code or 'mockStatic(' in test_code:
                score += 2  # BONUS for static mocking (advanced technique)
            
            # Check for spy usage
            if '@Spy' in test_code or 'spy(' in test_code:
                score += 1  # BONUS for spy usage (advanced technique)
            
            # Check for mock reset
            if 'reset(' in test_code:
                score += 1  # BONUS for proper mock cleanup
        
        # Check for comprehensive mocking coverage
        if critical_deps_found and has_mocking:
            mocked_deps = 0
            total_deps = len(critical_deps_found)
            
            for dep_type, matches in critical_deps_found:
                if dep_type == 'system_env' and any(pattern in test_code for pattern in ['MockedStatic<System>', 'when(System.getenv']):
                    mocked_deps += 1
                elif dep_type == 'object_creation' and any(pattern in test_code for pattern in ['@Mock', 'mock(']):
                    mocked_deps += 1
                elif dep_type in ['database', 'network', 'file_system'] and any(pattern in test_code for pattern in ['@Mock', 'mock(']):
                    mocked_deps += 1
                elif dep_type in ['security', 'validation', 'serialization'] and any(pattern in test_code for pattern in ['@Mock', 'mock(']):
                    mocked_deps += 1
            
            if total_deps > 0:
                coverage_ratio = mocked_deps / total_deps
                if coverage_ratio >= 0.8:
                    score += 2  # BONUS for comprehensive mocking
                elif coverage_ratio >= 0.5:
                    score += 1  # BONUS for partial mocking
            else:
                    issues.append(f"Only {mocked_deps}/{total_deps} critical dependencies are mocked")
                    score -= 2
        
        return min(15, max(0, score)), issues  # Min 0, Max 15
    
    def _evaluate_readability(self, test_code: str) -> tuple[int, List[str]]:
        """
        Evaluate code readability.
        
        Returns:
            Tuple of (score 0-15, issues list)
        """
        issues = []
        score = 15  # Start with full points, deduct for issues
        
        # Check test method naming
        test_methods = re.findall(r"@Test\s+(?:public\s+)?void\s+(\w+)", test_code)
        
        good_naming_count = 0
        for method_name in test_methods:
            # Good naming: should_ExpectedBehavior_When_Condition or similar
            if "_" in method_name or "should" in method_name.lower():
                good_naming_count += 1
        
        if test_methods:
            naming_ratio = good_naming_count / len(test_methods)
            if naming_ratio < 0.5:
                issues.append("Test method names could be more descriptive")
                score -= 3
        
        # Check for setup method
        if "@BeforeEach" in test_code or "@Before" in test_code:
            score = min(15, score + 2)  # Bonus for proper setup
        
        # Check for comments
        comment_count = test_code.count("//") + test_code.count("/*")
        if comment_count == 0:
            issues.append("Consider adding comments to explain complex test logic")
            score -= 2
        
        # Check for magic numbers
        magic_numbers = re.findall(r"\b\d{3,}\b", test_code)
        if len(magic_numbers) > 3:
            issues.append("Consider extracting magic numbers to constants")
            score -= 2
        
        # Check for line length (very long lines)
        lines = test_code.split("\n")
        long_lines = [l for l in lines if len(l) > 120]
        if len(long_lines) > 5:
            issues.append("Some lines are too long (>120 characters)")
            score -= 2
        
        return max(0, score), issues
    
    def _generate_suggestions(
        self,
        scores: Dict[str, Any],
        issues: List[str]
    ) -> List[str]:
        """Generate improvement suggestions based on scores and issues"""
        suggestions = []
        
        # Helper function to get score value
        def get_score_value(criterion: str) -> int:
            score_data = scores.get(criterion, 0)
            if isinstance(score_data, dict):
                return score_data.get('score', 0)
            return score_data
        
        # Compilability suggestions
        if get_score_value("compilability") < 20:
            suggestions.append(
                "Fix compilation issues: ensure proper class structure, "
                "imports, and syntax"
            )
        
        # Coverage suggestions
        if get_score_value("coverage") < 20:
            suggestions.append(
                "Increase test coverage: add tests for edge cases, "
                "null inputs, and error scenarios"
            )
        
        # Assertion suggestions
        if get_score_value("assertions") < 15:
            suggestions.append(
                "Improve assertions: add more specific assertions and "
                "include descriptive messages"
            )
        
        # Mocking suggestions
        if get_score_value("mocking") < 10:
            suggestions.append(
                "Consider using mocks: use Mockito to mock external dependencies "
                "for isolated unit tests"
            )
        
        # Readability suggestions
        if get_score_value("readability") < 12:
            suggestions.append(
                "Enhance readability: use descriptive test names, add comments, "
                "and follow naming conventions"
            )
        
        return suggestions
    
    def _should_use_llm_evaluation(self, test_code: str, state: AgentState) -> bool:
        """
        Determine if test code is complex enough to warrant LLM evaluation.
        
        Returns:
            True if LLM evaluation should be used, False for regex
        """
        # Use LLM if:
        # 1. Long test code (>200 lines)
        # 2. Many test methods (>10)
        # 3. Complex test patterns
        # 4. Has analysis results from AnalystAgent (complex original code)
        
        test_lines = len(test_code.split('\n'))
        test_methods = test_code.count('@Test')
        
        # Check for complex test patterns
        complex_patterns = [
            r'@Mock\w+',  # Mocking annotations
            r'@ParameterizedTest',  # Parameterized tests
            r'@TestFactory',  # Test factories
            r'@Nested',  # Nested test classes
            r'Stream\.',  # Stream API in tests
            r'assertThrows',  # Exception testing
            r'@InjectMocks',  # Dependency injection
            r'verify\(',  # Mock verification
            r'when\(',  # Mock stubbing
            r'@ExtendWith',  # Test extensions
        ]
        
        has_complex_patterns = any(re.search(pattern, test_code) for pattern in complex_patterns)
        
        # Check if original code was complex (from AnalystAgent results)
        has_complex_analysis = (
            state.complexity_analysis and 
            state.complexity_analysis.get('complexity_level', 'low') in ['high', 'very_high']
        )
        
        use_llm = (
            test_lines > 200 or
            test_methods > 10 or
            has_complex_patterns or
            has_complex_analysis
        )
        
        logger.info(f"    🔍 Test complexity check: lines={test_lines}, methods={test_methods}, complex_patterns={has_complex_patterns}, complex_analysis={has_complex_analysis}")
        logger.info(f"    🎯 Evaluation method: {'LLM' if use_llm else 'Regex'}")
        
        return use_llm
    
    async def _evaluate_test_quality_regex(self, test_code: str, state: AgentState) -> Dict[str, Dict[str, Any]]:
        """
        Fast regex-based test quality evaluation for simple tests.
        
        Returns:
            Dict with evaluation results for each criterion
        """
        logger.info(f"    ⚡ Performing fast regex test evaluation...")
        
        scores = {}
        
        # 1. Compilability (20 points)
        compile_score, compile_issues = await self._evaluate_compilability(test_code)
        scores['compilability'] = {
            'score': compile_score,
            'max_score': 20,
            'issues': compile_issues,
            'method': 'regex'
        }
        
        # 2. Coverage (30 points)
        coverage_score, coverage_issues = self._evaluate_coverage(test_code, state)
        scores['coverage'] = {
            'score': coverage_score,
            'max_score': 30,
            'issues': coverage_issues,
            'method': 'regex'
        }
        
        # 3. Assertions (20 points)
        assertion_score, assertion_issues = self._evaluate_assertions(test_code)
        scores['assertions'] = {
            'score': assertion_score,
            'max_score': 20,
            'issues': assertion_issues,
            'method': 'regex'
        }
        
        # 4. Mocking (15 points)
        mock_score, mock_issues = self._evaluate_mocking(test_code)
        scores['mocking'] = {
            'score': mock_score,
            'max_score': 15,
            'issues': mock_issues,
            'method': 'regex'
        }
        
        # 5. Readability (15 points)
        readability_score, readability_issues = self._evaluate_readability(test_code)
        scores['readability'] = {
            'score': readability_score,
            'max_score': 15,
            'issues': readability_issues,
            'method': 'regex'
        }
        
        return scores
    
    async def _evaluate_test_quality_with_llm(self, test_code: str, state: AgentState) -> Dict[str, Dict[str, Any]]:
        """
        LLM-based test quality evaluation for complex tests.
        
        Returns:
            Dict with detailed evaluation results for each criterion
        """
        logger.info(f"    🤖 Performing comprehensive LLM test evaluation...")
        
        # Get context from state
        method_name = getattr(state, 'target_method', 'unknown')
        class_name = 'UnknownClass'
        if hasattr(state, 'method_context') and state.method_context:
            method_data = state.method_context.get('ranked_methods', [{}])[0].get('data', {})
            class_name = method_data.get('class_name', 'UnknownClass')
        
        # Build comprehensive prompt for LLM evaluation
        prompt = f"""Evaluate the quality of this Java test code comprehensively. Consider the original method being tested and provide detailed insights.

**Original Method:** {class_name}.{method_name}
**Test Code:**
```java
{test_code}
```

**Original Method Context (if available):**
- Complexity Analysis: {state.complexity_analysis.get('complexity_level', 'unknown') if state.complexity_analysis else 'not available'}
- Edge Cases: {len(state.edge_case_analysis.get('edge_cases', [])) if state.edge_case_analysis else 0} identified
- Dependencies: {len(state.dependencies.get('methods', [])) if state.dependencies else 0} methods

Please provide a comprehensive test quality evaluation in JSON format with the following structure:

{{
    "compilability": {{
        "score": <0-20>,
        "max_score": 20,
        "issues": ["<issue1>", "<issue2>"],
        "analysis": "<detailed analysis>",
        "recommendations": ["<recommendation1>", "<recommendation2>"]
    }},
    "coverage": {{
        "score": <0-30>,
        "max_score": 30,
        "issues": ["<issue1>", "<issue2>"],
        "analysis": "<detailed analysis of test coverage>",
        "missing_scenarios": ["<missing scenario1>", "<missing scenario2>"],
        "coverage_assessment": "<how well does this cover the original method>"
    }},
    "assertions": {{
        "score": <0-20>,
        "max_score": 20,
        "issues": ["<issue1>", "<issue2>"],
        "analysis": "<detailed analysis of assertions>",
        "assertion_quality": "<assessment of assertion quality>",
        "missing_assertions": ["<missing assertion1>", "<missing assertion2>"]
    }},
    "mocking": {{
        "score": <0-15>,
        "max_score": 15,
        "issues": ["<issue1>", "<issue2>"],
        "analysis": "<detailed analysis of mocking strategy>",
        "mocking_assessment": "<how appropriate is the mocking>",
        "improvements": ["<improvement1>", "<improvement2>"]
    }},
    "readability": {{
        "score": <0-15>,
        "max_score": 15,
        "issues": ["<issue1>", "<issue2>"],
        "analysis": "<detailed analysis of code readability>",
        "readability_assessment": "<how readable and maintainable are the tests>",
        "improvements": ["<improvement1>", "<improvement2>"]
    }},
    "overall_assessment": {{
        "total_score": <0-100>,
        "quality_level": "<excellent|good|acceptable|poor>",
        "strengths": ["<strength1>", "<strength2>"],
        "weaknesses": ["<weakness1>", "<weakness2>"],
        "critical_issues": ["<critical issue1>", "<critical issue2>"],
        "test_strategy_assessment": "<how well does the test strategy match the complexity of the original method>",
        "business_value": "<how well do these tests protect business logic>"
    }}
}}

Focus on:
1. **Semantic correctness** - do the tests actually test the right things?
2. **Business logic coverage** - are critical business scenarios covered?
3. **Edge case coverage** - are boundary conditions and edge cases tested?
4. **Test strategy appropriateness** - is the testing approach suitable for the method's complexity?
5. **Maintainability** - will these tests be easy to maintain and understand?
6. **Real-world effectiveness** - would these tests catch real bugs?

Provide specific, actionable feedback for each criterion."""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert Java testing specialist with deep knowledge of test quality, coverage strategies, and testing best practices. Provide comprehensive, actionable test quality evaluation in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self.call_llm(messages, max_tokens=2500)
            
            # Parse LLM response
            try:
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    evaluation_data = json.loads(json_match.group())
                    
                    # Ensure all required criteria are present
                    required_criteria = ['compilability', 'coverage', 'assertions', 'mocking', 'readability']
                    for criterion in required_criteria:
                        if criterion not in evaluation_data:
                            # Fallback to regex evaluation for missing criteria
                            logger.warning(f"    ⚠️ Missing {criterion} in LLM response, using regex fallback")
                            if criterion == 'compilability':
                                score, issues = await self._evaluate_compilability(test_code)
                            elif criterion == 'coverage':
                                score, issues = self._evaluate_coverage(test_code, state)
                            elif criterion == 'assertions':
                                score, issues = self._evaluate_assertions(test_code)
                            elif criterion == 'mocking':
                                score, issues = self._evaluate_mocking(test_code)
                            elif criterion == 'readability':
                                score, issues = self._evaluate_readability(test_code)
                            
                            evaluation_data[criterion] = {
                                'score': score,
                                'max_score': 20 if criterion == 'compilability' else 30 if criterion == 'coverage' else 20 if criterion == 'assertions' else 15,
                                'issues': issues,
                                'method': 'regex_fallback'
                            }
                        else:
                            # Add method indicator
                            evaluation_data[criterion]['method'] = 'llm'
                    
                    logger.info(f"    ✅ LLM test evaluation completed: {evaluation_data.get('overall_assessment', {}).get('total_score', 'unknown')}/100")
                    return evaluation_data
                else:
                    logger.warning("    ⚠️ Could not parse LLM response as JSON, falling back to regex")
                    return await self._evaluate_test_quality_regex(test_code, state)
                    
            except json.JSONDecodeError as e:
                logger.warning(f"    ⚠️ JSON parsing failed: {e}, falling back to regex")
                return await self._evaluate_test_quality_regex(test_code, state)
                
        except Exception as e:
            logger.error(f"    ❌ LLM test evaluation failed: {e}, falling back to regex")
            return await self._evaluate_test_quality_regex(test_code, state)
    
    def _get_quality_level(self, score: int) -> str:
        """Get quality level description"""
        if score >= self.EXCELLENT_SCORE:
            return "Excellent"
        elif score >= self.PASSING_SCORE:
            return "Good"
        elif score >= 50:
            return "Needs Improvement"
        else:
            return "Poor"
    
    async def needs_regeneration(self, state: AgentState) -> bool:
        """Check if test needs to be regenerated"""
        return state.quality_score < self.PASSING_SCORE


if __name__ == "__main__":
    # Test the CriticAgent
    import asyncio
    
    async def test_critic():
        agent = CriticAgent()
        
        # Sample test code
        test_code = """
package com.example.test;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class CalculatorTest {
    
    @Test
    public void testAdd() {
        Calculator calc = new Calculator();
        assertEquals(5, calc.add(2, 3));
    }
    
    @Test
    public void testAddWithNull() {
        Calculator calc = new Calculator();
        assertThrows(IllegalArgumentException.class, () -> {
            calc.add(null, 3);
        });
    }
}
"""
        
        # Create state
        state = AgentState()
        state.test_code = test_code
        
        print("Testing CriticAgent...")
        print("="*60)
        
        # Execute
        result_state = await agent.execute(state)
        
        print(f"\n✅ Quality Score: {result_state.quality_score}/100")
        
        if result_state.issues:
            print("\n⚠️  Issues Found:")
            for issue in result_state.issues:
                print(f"  - {issue}")
        
        if result_state.suggestions:
            print("\n💡 Suggestions:")
            for suggestion in result_state.suggestions:
                print(f"  - {suggestion}")
        
        print("\n"+"="*60)
        print(f"Test {'PASSES' if result_state.quality_score >= agent.PASSING_SCORE else 'NEEDS IMPROVEMENT'}")
    
    asyncio.run(test_critic())

