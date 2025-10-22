"""
CoverageAgent - Measures real code coverage using JaCoCo.

Responsibilities:
- Compile generated tests
- Run tests with coverage measurement
- Parse coverage reports
- Provide real coverage metrics

Pattern: Real Code Coverage Measurement (4.7)
"""

import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import shutil
import re

from agents.base import BaseJavaAgent, AgentState
from logger import get_logger

logger = get_logger(__name__)


class CoverageAgent(BaseJavaAgent):
    """
    Agent responsible for measuring real code coverage.
    
    Workflow:
    1. Create temporary project structure
    2. Compile source code and tests
    3. Run tests with JaCoCo
    4. Parse coverage report
    5. Return real coverage metrics
    """
    
    def __init__(self):
        """Initialize CoverageAgent"""
        super().__init__(
            name="CoverageAgent",
            role="Real code coverage measurement",
            tools=[],
            temperature=0.1  # Low temperature for objective measurement
        )
        
        # Java and Maven paths (will be detected)
        self.java_home = self._detect_java_home()
        self.maven_home = self._detect_maven_home()
        
    def _detect_java_home(self) -> Optional[str]:
        """Detect Java installation"""
        try:
            result = subprocess.run(['java', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Try to get JAVA_HOME from environment
                java_home = os.environ.get('JAVA_HOME')
                if java_home and os.path.exists(java_home):
                    return java_home
                
                # Try common locations
                common_paths = [
                    '/usr/lib/jvm/default-java',
                    '/Library/Java/JavaVirtualMachines/*/Contents/Home',
                    'C:\\Program Files\\Java\\*',
                ]
                for path_pattern in common_paths:
                    import glob
                    matches = glob.glob(path_pattern)
                    if matches:
                        return matches[0]
        except Exception as e:
            logger.warning(f"Could not detect Java: {e}")
        return None
    
    def _detect_maven_home(self) -> Optional[str]:
        """Detect Maven installation"""
        try:
            result = subprocess.run(['mvn', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Try to get MAVEN_HOME from environment
                maven_home = os.environ.get('MAVEN_HOME')
                if maven_home and os.path.exists(maven_home):
                    return maven_home
                
                # Try common locations
                common_paths = [
                    '/usr/local/apache-maven',
                    '/opt/apache-maven',
                    'C:\\apache-maven',
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        return path
        except Exception as e:
            logger.warning(f"Could not detect Maven: {e}")
        return None
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute coverage measurement workflow.
        
        Args:
            state: Current agent state with test_code and source_code
        
        Returns:
            Updated state with real coverage metrics
        """
        logger.info("="*80)
        logger.info(f"[{self.name}] 📊 STARTING REAL COVERAGE MEASUREMENT")
        logger.info("="*80)
        
        try:
            if not state.test_code:
                error_msg = "No test code to measure coverage for"
                logger.error(f"  ❌ {error_msg}")
                self.log_error(error_msg, state)
                return state
            
            if not state.source_code:
                error_msg = "No source code to measure coverage against"
                logger.error(f"  ❌ {error_msg}")
                self.log_error(error_msg, state)
                return state
            
            logger.info(f"  📝 Measuring coverage for:")
            logger.info(f"    • Source code length: {len(state.source_code)} chars")
            logger.info(f"    • Test code length: {len(state.test_code)} chars")
            logger.info("")
            
            # Create temporary project
            logger.info(f"  🏗️  Creating temporary project...")
            temp_dir = self._create_temp_project(state)
            logger.info(f"    ✅ Project created at: {temp_dir}")
            logger.info("")
            
            # Compile and run tests with coverage
            logger.info(f"  🔨 Compiling and running tests with JaCoCo...")
            coverage_result = await self._run_coverage_measurement(temp_dir)
            logger.info("")
            
            # Parse coverage report
            logger.info(f"  📊 Parsing coverage report...")
            coverage_metrics = self._parse_coverage_report(temp_dir)
            
            if coverage_metrics:
                logger.info(f"    ✅ Coverage measured successfully:")
                logger.info(f"    • Line coverage: {coverage_metrics.get('line_coverage', 0):.1f}%")
                logger.info(f"    • Branch coverage: {coverage_metrics.get('branch_coverage', 0):.1f}%")
                logger.info(f"    • Method coverage: {coverage_metrics.get('method_coverage', 0):.1f}%")
                logger.info(f"    • Class coverage: {coverage_metrics.get('class_coverage', 0):.1f}%")
            else:
                logger.warning(f"    ⚠️  Could not parse coverage report")
            
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"  🧹 Cleaned up temporary directory")
            
            # Update state
            state.coverage_metrics = coverage_metrics
            state.real_coverage_measured = coverage_metrics is not None
            
            if coverage_metrics:
                self.log_step(f"Coverage measured: {coverage_metrics.get('line_coverage', 0):.1f}% line coverage", state)
            else:
                self.log_step("Coverage measurement failed - using fallback", state)
            
            logger.info("="*80)
            logger.info(f"[{self.name}] ✅ COVERAGE MEASUREMENT COMPLETED")
            logger.info("="*80)
            
            return state
            
        except Exception as e:
            error_msg = f"Coverage measurement failed: {str(e)}"
            logger.exception(f"[{self.name}] {error_msg}")
            self.log_error(error_msg, state)
            return state
    
    def _create_temp_project(self, state: AgentState) -> str:
        """Create temporary Maven project for coverage measurement"""
        temp_dir = tempfile.mkdtemp(prefix="coverage_test_")
        
        # Create Maven project structure
        src_dir = Path(temp_dir) / "src" / "main" / "java"
        test_dir = Path(temp_dir) / "src" / "test" / "java"
        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract package and class info from source code
        package_name, class_name = self._extract_class_info(state.source_code)
        
        # Create package directories
        if package_name:
            src_package_dir = src_dir / package_name.replace('.', '/')
            test_package_dir = test_dir / package_name.replace('.', '/')
            src_package_dir.mkdir(parents=True, exist_ok=True)
            test_package_dir.mkdir(parents=True, exist_ok=True)
            
            # Write source file
            source_file = src_package_dir / f"{class_name}.java"
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(state.source_code)
            
            # Write test file
            test_file = test_package_dir / f"{class_name}Test.java"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(state.test_code)
        else:
            # No package, write directly
            source_file = src_dir / f"{class_name}.java"
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(state.source_code)
            
            test_file = test_dir / f"{class_name}Test.java"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(state.test_code)
        
        # Create pom.xml
        self._create_pom_xml(temp_dir, package_name)
        
        return temp_dir
    
    def _extract_class_info(self, source_code: str) -> Tuple[str, str]:
        """Extract package and class name from source code"""
        package_name = ""
        class_name = "TestClass"
        
        # Extract package
        package_match = re.search(r'package\s+([\w.]+);', source_code)
        if package_match:
            package_name = package_match.group(1)
        
        # Extract class name
        class_match = re.search(r'(?:public\s+)?class\s+(\w+)', source_code)
        if class_match:
            class_name = class_match.group(1)
        
        return package_name, class_name
    
    def _create_pom_xml(self, temp_dir: str, package_name: str) -> None:
        """Create Maven pom.xml with JaCoCo plugin"""
        pom_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>coverage-test</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <junit.version>5.9.2</junit.version>
        <jacoco.version>0.8.8</jacoco.version>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>${{junit.version}}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.mockito</groupId>
            <artifactId>mockito-core</artifactId>
            <version>4.11.0</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.mockito</groupId>
            <artifactId>mockito-junit-jupiter</artifactId>
            <version>4.11.0</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>11</source>
                    <target>11</target>
                </configuration>
            </plugin>
            
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.0.0</version>
                <configuration>
                    <includes>
                        <include>**/*Test.java</include>
                    </includes>
                </configuration>
            </plugin>
            
            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>${{jacoco.version}}</version>
                <executions>
                    <execution>
                        <goals>
                            <goal>prepare-agent</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>report</id>
                        <phase>test</phase>
                        <goals>
                            <goal>report</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>"""
        
        pom_file = Path(temp_dir) / "pom.xml"
        with open(pom_file, 'w', encoding='utf-8') as f:
            f.write(pom_content)
    
    async def _run_coverage_measurement(self, temp_dir: str) -> bool:
        """Run Maven with JaCoCo to measure coverage"""
        try:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            # Run Maven test with JaCoCo
            cmd = ["mvn", "clean", "test", "jacoco:report"]
            
            logger.info(f"    Running: {' '.join(cmd)}")
            logger.info(f"    Working directory: {temp_dir}")
            
            # Set environment variables
            env = os.environ.copy()
            if self.java_home:
                env['JAVA_HOME'] = self.java_home
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env=env
            )
            
            if result.returncode == 0:
                logger.info(f"    ✅ Maven test completed successfully")
                return True
            else:
                logger.error(f"    ❌ Maven test failed:")
                logger.error(f"       Return code: {result.returncode}")
                logger.error(f"       STDOUT: {result.stdout}")
                logger.error(f"       STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"    ❌ Maven test timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"    ❌ Error running Maven: {e}")
            return False
        finally:
            os.chdir(original_cwd)
    
    def _parse_coverage_report(self, temp_dir: str) -> Optional[Dict[str, float]]:
        """Parse JaCoCo coverage report"""
        try:
            # Look for JaCoCo report
            jacoco_report = Path(temp_dir) / "target" / "site" / "jacoco" / "jacoco.xml"
            
            if not jacoco_report.exists():
                logger.warning(f"    ⚠️  JaCoCo report not found at: {jacoco_report}")
                return None
            
            # Parse XML report
            tree = ET.parse(jacoco_report)
            root = tree.getroot()
            
            # Extract coverage metrics
            coverage_data = {}
            
            # Parse counter elements
            for counter in root.findall('.//counter'):
                counter_type = counter.get('type')
                covered = int(counter.get('covered', 0))
                missed = int(counter.get('missed', 0))
                total = covered + missed
                
                if total > 0:
                    percentage = (covered / total) * 100
                    
                    if counter_type == 'LINE':
                        coverage_data['line_coverage'] = percentage
                    elif counter_type == 'BRANCH':
                        coverage_data['branch_coverage'] = percentage
                    elif counter_type == 'METHOD':
                        coverage_data['method_coverage'] = percentage
                    elif counter_type == 'CLASS':
                        coverage_data['class_coverage'] = percentage
            
            return coverage_data
            
        except Exception as e:
            logger.error(f"    ❌ Error parsing coverage report: {e}")
            return None
    
    def get_system_prompt(self) -> str:
        """Override to provide specialized system prompt"""
        return """You are a code coverage measurement specialist focused on providing accurate, real-world coverage metrics.

Your primary responsibilities:
1. Compile source code and tests correctly
2. Run tests with proper coverage instrumentation
3. Parse coverage reports accurately
4. Provide detailed coverage metrics

Always ensure:
- Proper Maven project structure
- Correct Java compilation
- Accurate JaCoCo configuration
- Reliable coverage measurement

Focus on precision and reliability in coverage measurement."""
