"""
CoverageAgentGradle - Measures real code coverage using JaCoCo with Gradle.

Responsibilities:
- Compile generated tests with Gradle
- Run tests with coverage measurement using JaCoCo Gradle plugin
- Parse coverage reports
- Provide real coverage metrics

Pattern: Real Code Coverage Measurement with Gradle (4.7)
"""

import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import shutil
import re

from agents.base import BaseJavaAgent, AgentState
from logger import get_logger

logger = get_logger(__name__)


class CoverageAgentGradle(BaseJavaAgent):
    """
    Agent responsible for measuring real code coverage using Gradle + JaCoCo.
    
    Workflow:
    1. Create temporary Gradle project structure
    2. Compile source code and tests
    3. Run tests with JaCoCo Gradle plugin
    4. Parse coverage report
    5. Return real coverage metrics
    """
    
    def __init__(self):
        """Initialize CoverageAgentGradle"""
        super().__init__(
            name="CoverageAgentGradle",
            role="Real code coverage measurement with Gradle",
            tools=[],
            temperature=0.1  # Low temperature for objective measurement
        )
        
        # Java and Gradle paths (will be detected)
        self.java_home = self._detect_java_home()
        self.gradle_home = self._detect_gradle_home()
        
    def _detect_java_home(self) -> Optional[str]:
        """Detect Java installation, preferring newer versions"""
        try:
            result = subprocess.run(['java', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Try to get JAVA_HOME from environment first
                java_home = os.environ.get('JAVA_HOME')
                if java_home and os.path.exists(java_home):
                    return java_home
                
                # Try common locations and prefer newer versions
                common_paths = [
                    '/Library/Java/JavaVirtualMachines/*/Contents/Home',  # macOS
                    '/usr/lib/jvm/default-java',  # Linux
                    'C:\\Program Files\\Java\\*',  # Windows
                ]
                
                all_java_homes = []
                for path_pattern in common_paths:
                    import glob
                    matches = glob.glob(path_pattern)
                    all_java_homes.extend(matches)
                
                if all_java_homes:
                    # Sort by path to prefer newer versions (they typically have higher numbers)
                    # e.g., temurin-23.jdk comes before jdk-11.jdk
                    all_java_homes.sort(reverse=True)
                    return all_java_homes[0]
        except Exception as e:
            logger.warning(f"Could not detect Java: {e}")
        return None
    
    def _detect_gradle_home(self) -> Optional[str]:
        """Detect Gradle installation"""
        try:
            result = subprocess.run(['gradle', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Try to get GRADLE_HOME from environment
                gradle_home = os.environ.get('GRADLE_HOME')
                if gradle_home and os.path.exists(gradle_home):
                    return gradle_home
                
                # Try common locations
                common_paths = [
                    '/usr/local/gradle',
                    '/opt/gradle',
                    'C:\\gradle',
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        return path
        except Exception as e:
            logger.warning(f"Could not detect Gradle: {e}")
        return None
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute coverage measurement workflow with Gradle.
        
        Args:
            state: Current agent state with test_code and source_code
        
        Returns:
            Updated state with real coverage metrics
        """
        logger.info("="*80)
        logger.info(f"[{self.name}] 📊 STARTING REAL COVERAGE MEASUREMENT (GRADLE)")
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
            logger.info(f"    • Java Home: {self.java_home or 'Not found'}")
            logger.info(f"    • Gradle Home: {self.gradle_home or 'Not found'}")
            logger.info("")
            
            # Create temporary Gradle project
            logger.info(f"  🏗️  Creating temporary Gradle project...")
            temp_dir = self._create_temp_gradle_project(state)
            logger.info(f"    ✅ Project created at: {temp_dir}")
            logger.info("")
            
            # Compile and run tests with coverage
            logger.info(f"  🔨 Compiling and running tests with Gradle + JaCoCo...")
            coverage_result = await self._run_gradle_coverage_measurement(temp_dir)
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
    
    def _create_temp_gradle_project(self, state: AgentState) -> str:
        """Create temporary Gradle project for coverage measurement"""
        temp_dir = tempfile.mkdtemp(prefix="gradle_coverage_test_")
        
        # Create Gradle project structure
        src_dir = Path(temp_dir) / "src" / "main" / "java"
        test_dir = Path(temp_dir) / "src" / "test" / "java"
        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse multiple classes from source code
        classes_info = self._extract_multiple_classes(state.source_code)
        
        # Write all source classes
        for class_info in classes_info:
            package_name = class_info['package']
            class_name = class_info['name']
            source_code = class_info['source']
            
            # Create package directories
            if package_name:
                src_package_dir = src_dir / package_name.replace('.', '/')
                src_package_dir.mkdir(parents=True, exist_ok=True)
                
                # Write source file
                source_file = src_package_dir / f"{class_name}.java"
                with open(source_file, 'w', encoding='utf-8') as f:
                    f.write(source_code)
            else:
                # No package, write directly
                source_file = src_dir / f"{class_name}.java"
                with open(source_file, 'w', encoding='utf-8') as f:
                    f.write(source_code)
        
        # Extract main class info for test file
        main_package, main_class = self._extract_class_info(state.source_code)
        
        # Write test file
        if main_package:
            test_package_dir = test_dir / main_package.replace('.', '/')
            test_package_dir.mkdir(parents=True, exist_ok=True)
            
            test_file = test_package_dir / f"{main_class}Test.java"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(state.test_code)
        else:
            test_file = test_dir / f"{main_class}Test.java"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(state.test_code)
        
        # Create build.gradle
        self._create_build_gradle(temp_dir, package_name)
        
        # Create gradle.properties
        self._create_gradle_properties(temp_dir)
        
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
    
    def _extract_multiple_classes(self, source_code: str) -> List[Dict[str, str]]:
        """Extract multiple classes from combined source code"""
        classes_info = []
        
        try:
            # Try to split by our custom separator first
            if '\n\n' in source_code:
                # Use smarter splitting - look for class boundaries
                class_blocks = self._smart_split_classes(source_code)
                logger.info(f"  🔍 Smart split into {len(class_blocks)} blocks")
            else:
                # If no separator, try to parse as single class
                logger.info("  🔍 No \\n\\n separator found, treating as single class")
                package_name, class_name = self._extract_class_info(source_code)
                return [{
                    'package': package_name,
                    'name': class_name,
                    'source': source_code
                }]
            
            valid_classes = 0
            for i, block in enumerate(class_blocks):
                if not block.strip():
                    logger.info(f"  ⚠️  Skipping empty block {i+1}")
                    continue
                
                # Extract package and class info for this block
                package_name, class_name = self._extract_class_info(block)
                
                # More lenient validation - accept most blocks that look like classes
                if self._is_complete_class(block):
                    classes_info.append({
                        'package': package_name,
                        'name': class_name,
                        'source': block.strip()
                    })
                    logger.info(f"  ✅ Extracted class: {class_name} (package: {package_name or 'default'}) - {len(block.strip())} chars")
                    valid_classes += 1
                else:
                    logger.warning(f"  ⚠️  Skipping block {i+1}: {class_name} - validation failed")
            
            # If we didn't extract many classes, be more permissive
            if valid_classes < len(class_blocks) * 0.5:  # If less than 50% were valid
                logger.warning(f"  ⚠️  Only {valid_classes}/{len(class_blocks)} blocks passed validation, being more permissive...")
                classes_info = []  # Reset and try again with more lenient approach
                
                for i, block in enumerate(class_blocks):
                    if not block.strip():
                        continue
                    
                    package_name, class_name = self._extract_class_info(block)
                    
                    # Very lenient check - just need class declaration
                    if re.search(r'class\s+\w+', block):
                        classes_info.append({
                            'package': package_name,
                            'name': class_name,
                            'source': block.strip()
                        })
                        logger.info(f"  ✅ Extracted class (lenient): {class_name} (package: {package_name or 'default'}) - {len(block.strip())} chars")
            
            # If still no valid classes found, treat as single class
            if not classes_info:
                logger.warning("  ⚠️  No valid classes found, treating entire source as single class")
                package_name, class_name = self._extract_class_info(source_code)
                classes_info = [{
                    'package': package_name,
                    'name': class_name,
                    'source': source_code
                }]
            
            logger.info(f"  📦 Total classes extracted: {len(classes_info)}")
            return classes_info
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to extract multiple classes: {e}")
            # Fallback to single class
            package_name, class_name = self._extract_class_info(source_code)
            return [{
                'package': package_name,
                'name': class_name,
                'source': source_code
            }]
    
    def _smart_split_classes(self, source_code: str) -> List[str]:
        """Smart splitting that looks for class boundaries"""
        try:
            # Try simple class-based splitting first
            logger.info("  🔍 Using simple class-based parsing...")
            classes = self._split_by_class_patterns(source_code)
            
            if len(classes) > 1:
                logger.info(f"  ✅ Simple class parsing found {len(classes)} classes")
                return classes
            
            # Fallback to separator-based splitting with improved cleaning
            if '\n\n' in source_code:
                blocks = source_code.split('\n\n')
                logger.info(f"  🔍 Fallback: Found {len(blocks)} blocks using \\n\\n separator")
                
                # Clean up each block to remove duplicate packages/imports
                cleaned_blocks = []
                for i, block in enumerate(blocks):
                    if block.strip():
                        cleaned_block = self._clean_class_block(block)
                        if cleaned_block and self._is_complete_class(cleaned_block):
                            cleaned_blocks.append(cleaned_block)
                            logger.info(f"  ✅ Extracted class block {i+1}: {len(cleaned_block)} chars")
                        else:
                            logger.warning(f"  ⚠️  Skipping block {i+1}: incomplete or invalid")
                
                if len(cleaned_blocks) > 1:
                    logger.info(f"  ✅ Successfully cleaned {len(cleaned_blocks)} class blocks")
                    return cleaned_blocks
                elif len(cleaned_blocks) == 1:
                    logger.info("  ✅ Successfully cleaned 1 class block")
                    return cleaned_blocks
            
            # Last resort: return original source
            logger.info("  🔍 Returning original source as-is")
            return [source_code]
            
        except Exception as e:
            logger.warning(f"  ⚠️  Smart split failed: {e}, falling back to simple split")
            # Fallback to simple split
            return source_code.split('\n\n')
    
    def _split_by_class_patterns(self, source_code: str) -> List[str]:
        """Split source code by finding class patterns and extracting complete classes using brace counting"""
        try:
            # Extract package and imports from the entire source
            lines = source_code.split('\n')
            package_line = None
            import_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                if line_stripped.startswith('package '):
                    package_line = line
                elif line_stripped.startswith('import '):
                    import_lines.append(line)
            
            # Find all class declarations using regex
            class_pattern = r'^\s*(public\s+|abstract\s+|final\s+|static\s+)*class\s+(\w+)'
            class_matches = list(re.finditer(class_pattern, source_code, re.MULTILINE))
            
            logger.info(f"  🔍 Found {len(class_matches)} class declarations using regex")
            
            if len(class_matches) < 2:
                logger.info("  🔍 Only one class found with regex, returning as single class")
                return [source_code]
            
            # Extract complete classes using brace counting
            classes = []
            for i, match in enumerate(class_matches):
                class_name = match.group(2)
                start_pos = match.start()
                
                # Extract complete class by counting braces
                class_content = self._extract_complete_class_by_braces(source_code, start_pos)
                
                if not class_content:
                    logger.warning(f"  ⚠️  Could not extract class {i+1}: {class_name}")
                    continue
                
                # Build complete class with package and imports
                complete_class = []
                if package_line:
                    complete_class.append(package_line)
                complete_class.extend(import_lines)
                if package_line or import_lines:
                    complete_class.append("")
                complete_class.append(class_content)
                
                # Join and clean up
                class_code = '\n'.join(complete_class)
                
                # Validate class completeness
                if self._is_complete_class(class_code):
                    classes.append(class_code)
                    logger.info(f"  ✅ Extracted complete class {i+1}: {class_name} - {len(class_code)} chars (braces balanced)")
                else:
                    logger.warning(f"  ⚠️  Skipping incomplete class {i+1}: {class_name} (braces unbalanced)")
            
            return classes if classes else [source_code]
            
        except Exception as e:
            logger.warning(f"  ⚠️  Class pattern parsing failed: {e}")
            return [source_code]
    
    def _extract_complete_class_by_braces(self, source_code: str, start_pos: int) -> str:
        """Extract complete class starting from position by counting braces"""
        try:
            brace_count = 0
            in_class = False
            in_string = False
            in_char = False
            in_comment = False
            in_multiline_comment = False
            escape_next = False
            
            i = start_pos
            while i < len(source_code):
                char = source_code[i]
                
                # Handle escape sequences
                if escape_next:
                    escape_next = False
                    i += 1
                    continue
                
                if char == '\\':
                    escape_next = True
                    i += 1
                    continue
                
                # Handle comments
                if i + 1 < len(source_code):
                    two_char = source_code[i:i+2]
                    if two_char == '//' and not in_string and not in_char and not in_multiline_comment:
                        in_comment = True
                        i += 2
                        continue
                    elif two_char == '/*' and not in_string and not in_char and not in_comment:
                        in_multiline_comment = True
                        i += 2
                        continue
                    elif two_char == '*/' and in_multiline_comment:
                        in_multiline_comment = False
                        i += 2
                        continue
                
                # Handle end of line comment
                if char == '\n' and in_comment:
                    in_comment = False
                
                # Skip if in comment
                if in_comment or in_multiline_comment:
                    i += 1
                    continue
                
                # Handle strings
                if char == '"' and not in_char:
                    in_string = not in_string
                    i += 1
                    continue
                
                # Handle chars
                if char == "'" and not in_string:
                    in_char = not in_char
                    i += 1
                    continue
                
                # Count braces only if not in string or char
                if not in_string and not in_char:
                    if char == '{':
                        brace_count += 1
                        in_class = True
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and in_class:
                            # Found the end of the class
                            return source_code[start_pos:i+1]
                
                i += 1
            
            # If we reached the end without balanced braces, return what we have
            logger.warning(f"  ⚠️  Reached end of source without balanced braces (count: {brace_count})")
            return source_code[start_pos:]
            
        except Exception as e:
            logger.warning(f"  ⚠️  Error extracting class by braces: {e}")
            return ""
    
    def _split_by_class_boundaries(self, source_code: str) -> List[str]:
        """Split source code by finding class boundaries using improved algorithm"""
        try:
            # First, extract package and imports from the entire source
            lines = source_code.split('\n')
            package_line = None
            import_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                if line_stripped.startswith('package '):
                    package_line = line
                elif line_stripped.startswith('import '):
                    import_lines.append(line)
            
            # Find all class declarations and their positions
            class_positions = []
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if re.match(r'^\s*(public\s+|abstract\s+|final\s+|static\s+)*class\s+\w+', line_stripped):
                    class_positions.append(i)
                    logger.info(f"  🔍 Found class at line {i}: {line_stripped[:50]}...")
            
            logger.info(f"  🔍 Found {len(class_positions)} class declarations at lines: {class_positions}")
            
            if len(class_positions) < 2:
                logger.info("  🔍 Only one class found, returning as single class")
                return [source_code]
            
            # Split into classes based on positions
            classes = []
            for i, class_start in enumerate(class_positions):
                # Determine class end
                if i + 1 < len(class_positions):
                    class_end = class_positions[i + 1]
                else:
                    class_end = len(lines)
                
                # Extract class lines
                class_lines = lines[class_start:class_end]
                
                # Build complete class with package and imports
                complete_class = []
                if package_line:
                    complete_class.append(package_line)
                complete_class.extend(import_lines)
                if package_line or import_lines:
                    complete_class.append("")
                complete_class.extend(class_lines)
                
                # Join and clean up
                class_code = '\n'.join(complete_class)
                
                # Validate class completeness by checking braces
                if self._is_complete_class(class_code):
                    classes.append(class_code)
                    logger.info(f"  ✅ Extracted complete class {i+1}: {len(class_code)} chars")
                else:
                    logger.warning(f"  ⚠️  Skipping incomplete class {i+1}")
            
            return classes if classes else [source_code]
            
        except Exception as e:
            logger.warning(f"  ⚠️  Class-boundary parsing failed: {e}")
            return [source_code]
    
    def _parse_classes_by_braces(self, source_code: str) -> List[str]:
        """Parse classes by analyzing brace structure"""
        try:
            lines = source_code.split('\n')
            classes = []
            current_class = []
            brace_count = 0
            in_class = False
            current_package = None
            current_imports = set()
            
            for line in lines:
                line_stripped = line.strip()
                
                # Track package and imports at the top level
                if not in_class:
                    if line_stripped.startswith('package '):
                        current_package = line_stripped.replace('package ', '').replace(';', '')
                        continue
                    elif line_stripped.startswith('import '):
                        import_stmt = line_stripped.replace('import ', '').replace(';', '')
                        current_imports.add(import_stmt)
                        continue
                
                # Check if this line starts a new class
                if re.match(r'^\s*(public\s+|abstract\s+|final\s+|static\s+)*class\s+\w+', line_stripped):
                    if current_class and in_class:
                        # Save previous class
                        classes.append('\n'.join(current_class))
                    
                    # Start new class
                    current_class = []
                    in_class = True
                    brace_count = 0
                    
                    # Add package and imports if they exist
                    if current_package:
                        current_class.append(f"package {current_package};")
                    for imp in sorted(current_imports):
                        current_class.append(f"import {imp};")
                    if current_package or current_imports:
                        current_class.append("")
                
                if in_class:
                    current_class.append(line)
                    
                    # Count braces to track class boundaries
                    for char in line:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                    
                    # If braces are balanced and we're at the top level, class is complete
                    if brace_count == 0 and in_class:
                        # Only end class if we've seen at least one opening brace
                        if '{' in '\n'.join(current_class):
                            in_class = False
            
            # Add the last class if it exists
            if current_class and in_class:
                classes.append('\n'.join(current_class))
            
            # If we found multiple classes, return them
            if len(classes) > 1:
                logger.info(f"  🔍 Brace-based parsing found {len(classes)} separate classes")
                return classes
            
            # If we found only one class, but it might contain multiple classes,
            # try to split by looking for multiple class declarations
            if len(classes) == 1:
                single_class = classes[0]
                class_matches = list(re.finditer(r'class\s+\w+', single_class))
                
                if len(class_matches) > 1:
                    logger.info(f"  🔍 Single class contains {len(class_matches)} class declarations, splitting...")
                    # Split by class boundaries
                    split_classes = []
                    lines = single_class.split('\n')
                    
                    current_class = []
                    brace_count = 0
                    in_class = False
                    
                    for line in lines:
                        line_stripped = line.strip()
                        
                        # Check if this line starts a new class
                        if re.match(r'^\s*(public\s+|abstract\s+|final\s+|static\s+)*class\s+\w+', line_stripped):
                            if current_class and in_class:
                                # Save previous class
                                split_classes.append('\n'.join(current_class))
                            
                            # Start new class
                            current_class = []
                            in_class = True
                            brace_count = 0
                            
                            # Add package and imports if they exist
                            if current_package:
                                current_class.append(f"package {current_package};")
                            for imp in sorted(current_imports):
                                current_class.append(f"import {imp};")
                            if current_package or current_imports:
                                current_class.append("")
                        
                        if in_class:
                            current_class.append(line)
                            
                            # Count braces to track class boundaries
                            for char in line:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                            
                            # If braces are balanced and we're at the top level, class is complete
                            if brace_count == 0 and in_class:
                                # Only end class if we've seen at least one opening brace
                                if '{' in '\n'.join(current_class):
                                    in_class = False
                    
                    # Add the last class if it exists
                    if current_class and in_class:
                        split_classes.append('\n'.join(current_class))
                    
                    if len(split_classes) > 1:
                        logger.info(f"  ✅ Successfully split into {len(split_classes)} classes")
                        return split_classes
            
            return classes
            
        except Exception as e:
            logger.warning(f"  ⚠️  Brace-based parsing failed: {e}")
            return [source_code]
    
    def _clean_class_block(self, block: str) -> str:
        """Clean a class block by removing duplicate packages/imports and ensuring proper structure"""
        try:
            lines = block.split('\n')
            cleaned_lines = []
            seen_package = False
            seen_imports = set()
            
            for line in lines:
                line_stripped = line.strip()
                
                # Handle package declaration
                if line_stripped.startswith('package '):
                    if not seen_package:
                        cleaned_lines.append(line)
                        seen_package = True
                    # Skip duplicate packages
                
                # Handle imports
                elif line_stripped.startswith('import '):
                    import_stmt = line_stripped.replace('import ', '').replace(';', '')
                    if import_stmt not in seen_imports:
                        cleaned_lines.append(line)
                        seen_imports.add(import_stmt)
                    # Skip duplicate imports
                
                # Everything else
                else:
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to clean class block: {e}")
            return block
    
    def _is_complete_class(self, class_code: str) -> bool:
        """Check if the code block looks like a complete Java class"""
        try:
            # Basic checks for completeness
            if not class_code.strip():
                return False
            
            # Must have class declaration
            if not re.search(r'class\s+\w+', class_code):
                return False
            
            # Check for balanced braces - this is the most important check
            brace_count = 0
            for char in class_code:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
            
            # For a complete class, braces must be perfectly balanced
            if brace_count != 0:
                logger.warning(f"  ⚠️  Unbalanced braces: {brace_count}")
                return False
            
            # Check that class has a reasonable minimum size
            if len(class_code.strip()) < 50:
                logger.warning(f"  ⚠️  Class too small: {len(class_code)} chars")
                return False
            
            # Check that class ends with closing brace
            if not class_code.strip().endswith('}'):
                logger.warning("  ⚠️  Class doesn't end with closing brace")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"  ⚠️  Class validation error: {e}")
            return False
    
    def _create_build_gradle(self, temp_dir: str, package_name: str) -> None:
        """Create build.gradle with JaCoCo plugin"""
        build_gradle_content = f"""plugins {{
    id 'java'
    id 'jacoco'
}}

group = 'com.example'
version = '1.0-SNAPSHOT'

java {{
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}}

repositories {{
    mavenCentral()
}}

dependencies {{
    testImplementation 'org.junit.jupiter:junit-jupiter:5.9.2'
    testImplementation 'org.mockito:mockito-core:4.11.0'
    testImplementation 'org.mockito:mockito-junit-jupiter:4.11.0'
}}

test {{
    useJUnitPlatform()
    finalizedBy jacocoTestReport
}}

jacocoTestReport {{
    dependsOn test
    reports {{
        xml.required = true
        html.required = true
        csv.required = false
    }}
}}

jacocoTestCoverageVerification {{
    violationRules {{
        rule {{
            limit {{
                minimum = 0.50
            }}
        }}
    }}
}}"""
        
        build_gradle_file = Path(temp_dir) / "build.gradle"
        with open(build_gradle_file, 'w', encoding='utf-8') as f:
            f.write(build_gradle_content)
    
    def _create_gradle_properties(self, temp_dir: str) -> None:
        """Create gradle.properties"""
        gradle_properties_content = """org.gradle.jvmargs=-Xmx2048m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8
org.gradle.parallel=true
org.gradle.caching=true
org.gradle.daemon=true
"""
        
        gradle_properties_file = Path(temp_dir) / "gradle.properties"
        with open(gradle_properties_file, 'w', encoding='utf-8') as f:
            f.write(gradle_properties_content)
    
    async def _run_gradle_coverage_measurement(self, temp_dir: str) -> bool:
        """Run Gradle with JaCoCo to measure coverage"""
        try:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            # Run Gradle test with JaCoCo (with more verbose output)
            cmd = ["gradle", "clean", "test", "jacocoTestReport", "--info"]
            
            logger.info(f"    Running: {' '.join(cmd)}")
            logger.info(f"    Working directory: {temp_dir}")
            
            # Set environment variables
            env = os.environ.copy()
            if self.java_home:
                env['JAVA_HOME'] = self.java_home
            if self.gradle_home:
                env['GRADLE_HOME'] = self.gradle_home
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env=env
            )
            
            if result.returncode == 0:
                logger.info(f"    ✅ Gradle test completed successfully")
                return True
            else:
                logger.error(f"    ❌ Gradle test failed:")
                logger.error(f"       Return code: {result.returncode}")
                logger.error(f"       STDOUT: {result.stdout}")
                logger.error(f"       STDERR: {result.stderr}")
                # Log the last few lines of output for debugging
                if result.stdout:
                    stdout_lines = result.stdout.strip().split('\n')
                    logger.error(f"       Last STDOUT lines:")
                    for line in stdout_lines[-5:]:
                        logger.error(f"         {line}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"    ❌ Gradle test timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"    ❌ Error running Gradle: {e}")
            return False
        finally:
            os.chdir(original_cwd)
    
    def _parse_coverage_report(self, temp_dir: str) -> Optional[Dict[str, float]]:
        """Parse JaCoCo coverage report from Gradle"""
        try:
            # Look for JaCoCo report (Gradle puts it in build/reports/jacoco/test/jacocoTestReport.xml)
            jacoco_report = Path(temp_dir) / "build" / "reports" / "jacoco" / "test" / "jacocoTestReport.xml"
            
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
        return """You are a code coverage measurement specialist focused on providing accurate, real-world coverage metrics using Gradle.

Your primary responsibilities:
1. Compile source code and tests correctly with Gradle
2. Run tests with proper JaCoCo instrumentation
3. Parse coverage reports accurately
4. Provide detailed coverage metrics

Always ensure:
- Proper Gradle project structure
- Correct Java compilation with Gradle
- Accurate JaCoCo Gradle plugin configuration
- Reliable coverage measurement

Focus on precision and reliability in coverage measurement with modern Gradle build system."""
