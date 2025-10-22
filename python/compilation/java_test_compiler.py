"""
Java Test Compiler for compiling generated unit tests.

This module provides functionality to compile Java test files and check for compilation errors.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from logger import get_logger

logger = get_logger(__name__)


class JavaTestCompiler:
    """
    Compiler for Java test files.
    
    Handles:
    - Creating temporary compilation environment
    - Managing classpath with JUnit dependencies
    - Compiling test files
    - Collecting compilation errors and warnings
    """
    
    def __init__(self, java_home: Optional[str] = None):
        """
        Initialize Java test compiler.
        
        Args:
            java_home: Path to Java installation (auto-detected if None)
        """
        self.java_home = java_home or self._detect_java_home()
        self.javac_path = self._find_javac()
        self.temp_dir = None
        
        logger.info(f"JavaTestCompiler initialized:")
        logger.info(f"  • Java Home: {self.java_home}")
        logger.info(f"  • Javac Path: {self.javac_path}")
    
    def _detect_java_home(self) -> Optional[str]:
        """Detect Java installation path."""
        try:
            # Try JAVA_HOME environment variable
            java_home = os.environ.get('JAVA_HOME')
            if java_home and os.path.exists(java_home):
                return java_home
            
            # Try to find java executable
            result = subprocess.run(['which', 'java'], capture_output=True, text=True)
            if result.returncode == 0:
                java_path = result.stdout.strip()
                # Navigate up to find JAVA_HOME
                java_dir = Path(java_path).parent.parent
                if (java_dir / 'bin' / 'javac').exists():
                    return str(java_dir)
            
            logger.warning("Java installation not found")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to detect Java installation: {e}")
            return None
    
    def _find_javac(self) -> Optional[str]:
        """Find javac compiler executable."""
        if not self.java_home:
            return None
        
        javac_path = Path(self.java_home) / 'bin' / 'javac'
        if javac_path.exists():
            return str(javac_path)
        
        # Try system PATH
        try:
            result = subprocess.run(['which', 'javac'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        logger.warning("javac compiler not found")
        return None
    
    def _create_temp_environment(self) -> str:
        """Create temporary directory for compilation."""
        self.temp_dir = tempfile.mkdtemp(prefix='java_test_compiler_')
        logger.info(f"Created temporary compilation directory: {self.temp_dir}")
        return self.temp_dir
    
    def _cleanup_temp_environment(self):
        """Clean up temporary directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            self.temp_dir = None
    
    def _get_junit_classpath(self) -> List[str]:
        """Get classpath with JUnit and Mockito dependencies."""
        classpath = []
        
        # Add current directory
        if self.temp_dir:
            classpath.append(self.temp_dir)
        
        # Try to find JUnit and Mockito JAR files in common locations
        dependency_locations = [
            # Maven local repository
            Path.home() / '.m2' / 'repository' / 'org' / 'junit' / 'jupiter',
            Path.home() / '.m2' / 'repository' / 'org' / 'junit' / 'platform',
            Path.home() / '.m2' / 'repository' / 'org' / 'mockito',
            Path.home() / '.m2' / 'repository' / 'net' / 'bytebuddy',
            Path.home() / '.m2' / 'repository' / 'org' / 'objenesis',
            # Gradle cache
            Path.home() / '.gradle' / 'caches' / 'modules-2' / 'files-2.1' / 'org.junit.jupiter',
            Path.home() / '.gradle' / 'caches' / 'modules-2' / 'files-2.1' / 'org.mockito',
            # System-wide locations
            Path('/usr/share/java'),
            Path('/opt/java/lib'),
        ]
        
        # Dependencies to look for
        dependencies = ['junit', 'mockito', 'bytebuddy', 'objenesis']
        
        for location in dependency_locations:
            if location.exists():
                # Find JAR files for all dependencies
                for jar_file in location.rglob('*.jar'):
                    jar_name = jar_file.name.lower()
                    if any(dep in jar_name for dep in dependencies):
                        classpath.append(str(jar_file))
                        logger.debug(f"Added dependency JAR to classpath: {jar_file}")
        
        # Check if we found the essential dependencies
        has_junit = any('junit' in cp.lower() for cp in classpath)
        has_mockito = any('mockito' in cp.lower() for cp in classpath)
        
        if not has_junit:
            logger.warning("JUnit dependencies not found in classpath - compilation may fail")
        if not has_mockito:
            logger.warning("Mockito dependencies not found in classpath - mocking features may not work")
        
        return classpath
    
    def _write_test_file(self, test_code: str, class_name: str) -> str:
        """Write test code to temporary file."""
        if not self.temp_dir:
            raise RuntimeError("Temporary directory not created")
        
        # Extract package from test code
        package = self._extract_package(test_code)
        
        # Create package directory structure
        if package:
            package_dir = self.temp_dir
            for part in package.split('.'):
                package_dir = os.path.join(package_dir, part)
            os.makedirs(package_dir, exist_ok=True)
            file_path = os.path.join(package_dir, f"{class_name}.java")
        else:
            file_path = os.path.join(self.temp_dir, f"{class_name}.java")
        
        # Write test code
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        logger.info(f"Written test file: {file_path}")
        return file_path
    
    def _extract_package(self, java_code: str) -> str:
        """Extract package declaration from Java code."""
        lines = java_code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('package '):
                # Extract package name
                package = line[8:].rstrip(';').strip()
                return package
        return ""
    
    def _extract_class_name(self, java_code: str) -> str:
        """Extract class name from Java code."""
        lines = java_code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('class ') and '{' in line:
                # Extract class name
                class_part = line.split('class ')[1].split('{')[0].strip()
                class_name = class_part.split()[0]  # Take first word (class name)
                return class_name
        return "TestClass"
    
    def compile_test(
        self, 
        test_code: str, 
        source_files: Optional[List[str]] = None,
        additional_classpath: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compile Java test code.
        
        Args:
            test_code: Java test code to compile
            source_files: List of source file paths to include
            additional_classpath: Additional classpath entries
            
        Returns:
            Dictionary with compilation results:
            {
                'success': bool,
                'errors': List[str],
                'warnings': List[str],
                'compiled_files': List[str],
                'classpath': List[str],
                'compilation_time': float
            }
        """
        if not self.javac_path:
            return {
                'success': False,
                'errors': ['javac compiler not found'],
                'warnings': [],
                'compiled_files': [],
                'classpath': [],
                'compilation_time': 0.0
            }
        
        start_time = os.times().elapsed
        
        try:
            # Create temporary environment
            self._create_temp_environment()
            
            # Extract class name and write test file
            class_name = self._extract_class_name(test_code)
            test_file = self._write_test_file(test_code, class_name)
            
            # Prepare source files
            source_files = source_files or []
            all_source_files = [test_file] + source_files
            
            # Build classpath
            classpath = self._get_junit_classpath()
            if additional_classpath:
                classpath.extend(additional_classpath)
            
            # Prepare javac command
            cmd = [self.javac_path]
            
            # Add classpath
            if classpath:
                cmd.extend(['-cp', ':'.join(classpath)])
            
            # Add source files
            cmd.extend(all_source_files)
            
            logger.info(f"Compiling with command: {' '.join(cmd)}")
            logger.info(f"Classpath: {classpath}")
            
            # Run compilation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.temp_dir,
                timeout=30  # 30 second timeout
            )
            
            compilation_time = os.times().elapsed - start_time
            
            # Parse results
            errors = []
            warnings = []
            
            if result.stderr:
                # Parse javac output
                for line in result.stderr.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    if 'error:' in line.lower():
                        errors.append(line)
                    elif 'warning:' in line.lower():
                        warnings.append(line)
                    else:
                        # Treat unknown output as warnings
                        warnings.append(line)
            
            # Find compiled class files
            compiled_files = []
            if result.returncode == 0:
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        if file.endswith('.class'):
                            compiled_files.append(os.path.join(root, file))
            
            success = result.returncode == 0 and not errors
            
            logger.info(f"Compilation {'succeeded' if success else 'failed'}")
            logger.info(f"  • Errors: {len(errors)}")
            logger.info(f"  • Warnings: {len(warnings)}")
            logger.info(f"  • Compiled files: {len(compiled_files)}")
            logger.info(f"  • Time: {compilation_time:.2f}s")
            
            return {
                'success': success,
                'errors': errors,
                'warnings': warnings,
                'compiled_files': compiled_files,
                'classpath': classpath,
                'compilation_time': compilation_time,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Compilation timed out after 30 seconds")
            return {
                'success': False,
                'errors': ['Compilation timed out after 30 seconds'],
                'warnings': [],
                'compiled_files': [],
                'classpath': [],
                'compilation_time': 30.0
            }
        except Exception as e:
            logger.error(f"Compilation failed with exception: {e}")
            return {
                'success': False,
                'errors': [f'Compilation exception: {str(e)}'],
                'warnings': [],
                'compiled_files': [],
                'classpath': [],
                'compilation_time': 0.0
            }
        finally:
            # Clean up temporary environment
            self._cleanup_temp_environment()
    
    def check_java_environment(self) -> Dict[str, Any]:
        """
        Check Java environment and dependencies.
        
        Returns:
            Dictionary with environment status
        """
        status = {
            'java_available': False,
            'javac_available': False,
            'java_version': None,
            'javac_version': None,
            'java_home': self.java_home,
            'junit_available': False,
            'junit_version': None
        }
        
        # Check Java
        try:
            result = subprocess.run(['java', '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                status['java_available'] = True
                # Parse version from stderr
                version_line = result.stderr.split('\n')[0]
                status['java_version'] = version_line
        except Exception:
            pass
        
        # Check javac
        if self.javac_path:
            try:
                result = subprocess.run([self.javac_path, '-version'], capture_output=True, text=True)
                if result.returncode == 0:
                    status['javac_available'] = True
                    status['javac_version'] = result.stderr.strip()
            except Exception:
                pass
        
        # Check JUnit and Mockito availability
        classpath = self._get_junit_classpath()
        if any('junit' in cp.lower() for cp in classpath):
            status['junit_available'] = True
            # Try to extract version from JAR path
            for cp in classpath:
                if 'junit' in cp.lower():
                    # Look for version in path
                    parts = cp.split('/')
                    for part in parts:
                        if part.replace('.', '').isdigit() and len(part) > 2:
                            status['junit_version'] = part
                            break
                    break
        
        # Check Mockito availability
        if any('mockito' in cp.lower() for cp in classpath):
            status['mockito_available'] = True
            # Try to extract version from JAR path
            for cp in classpath:
                if 'mockito' in cp.lower():
                    # Look for version in path
                    parts = cp.split('/')
                    for part in parts:
                        if part.replace('.', '').isdigit() and len(part) > 2:
                            status['mockito_version'] = part
                            break
                    break
        else:
            status['mockito_available'] = False
        
        return status


def test_compiler():
    """Test the Java test compiler."""
    compiler = JavaTestCompiler()
    
    # Check environment
    env_status = compiler.check_java_environment()
    print("Java Environment Status:")
    for key, value in env_status.items():
        print(f"  {key}: {value}")
    
    # Test compilation with sample code
    sample_test = '''
package com.example.test;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class SampleTest {
    @Test
    void testBasic() {
        assertTrue(true);
    }
}
'''
    
    result = compiler.compile_test(sample_test)
    print("\nCompilation Result:")
    print(f"  Success: {result['success']}")
    print(f"  Errors: {result['errors']}")
    print(f"  Warnings: {result['warnings']}")
    print(f"  Time: {result['compilation_time']:.2f}s")


if __name__ == "__main__":
    test_compiler()
