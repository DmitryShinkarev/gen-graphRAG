"""
Universal Java parser that handles both regular Java files and template files with variables.
Supports Groovy templates and ${} variable substitution.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from parser.tree_sitter_parser import JavaParser, ClassInfo, MethodInfo, FieldInfo
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class TemplateVariable:
    """Represents a template variable"""
    name: str
    value: Optional[str] = None
    is_groovy: bool = False  # True if it's a Groovy expression like <% ... %>
    
    def to_string(self) -> str:
        if self.is_groovy:
            return f"<% {self.name} %>"
        else:
            return f"${{{self.name}}}"


class UniversalJavaParser:
    """
    Universal Java parser that can handle:
    1. Regular Java files
    2. Template files with ${} variables
    3. Groovy template files with <% %> expressions
    
    It preprocesses templates to create valid Java code for parsing.
    """
    
    def __init__(self):
        """Initialize the universal parser"""
        self.java_parser = JavaParser()
        self.template_variables = {}  # Cache for template variables
        
        logger.info("Universal Java parser initialized")
    
    def parse_file(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse a Java file (regular or template).
        
        Args:
            file_path: Path to the Java file
        
        Returns:
            ClassInfo or None if parsing failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            return self.parse_source(source_code, file_path)
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            return None
    
    def parse_source(self, source_code: str, file_path: Optional[Path] = None) -> Optional[ClassInfo]:
        """
        Parse Java source code (regular or template).
        
        Args:
            source_code: Java source code as string
            file_path: Optional file path for context
        
        Returns:
            ClassInfo or None if parsing failed
        """
        try:
            # Detect if this is a template file
            is_template = self._is_template_file(source_code)
            
            if is_template:
                logger.info(f"Detected template file, preprocessing...")
                processed_code, variables = self._preprocess_template(source_code)
                
                # Store variables for later use
                if file_path:
                    self.template_variables[str(file_path)] = variables
                
                # Parse the processed code
                class_info = self.java_parser.parse_source(processed_code)
                
                # Post-process to restore template information
                if class_info:
                    class_info = self._post_process_template_class(class_info, variables, source_code)
                
                return class_info
            else:
                # Regular Java file, use standard parser
                return self.java_parser.parse_source(source_code)
                
        except Exception as e:
            logger.error(f"Failed to parse source code: {e}")
            return None
    
    def _is_template_file(self, source_code: str) -> bool:
        """Check if the source code contains template variables"""
        # Check for ${} variables
        if re.search(r'\$\{[^}]+\}', source_code):
            return True
        
        # Check for Groovy expressions <% %>
        if re.search(r'<%.*?%>', source_code, re.DOTALL):
            return True
        
        return False
    
    def _preprocess_template(self, source_code: str) -> Tuple[str, List[TemplateVariable]]:
        """
        Preprocess template code to create valid Java code.
        
        Args:
            source_code: Original template source code
        
        Returns:
            Tuple of (processed_code, variables_found)
        """
        processed_code = source_code
        variables = []
        
        # Process Groovy expressions first (they can contain ${} variables)
        processed_code, groovy_vars = self._process_groovy_expressions(processed_code)
        variables.extend(groovy_vars)
        
        # Process ${} variables
        processed_code, dollar_vars = self._process_dollar_variables(processed_code)
        variables.extend(dollar_vars)
        
        logger.info(f"Preprocessed template: found {len(variables)} variables")
        for var in variables:
            logger.debug(f"  Variable: {var.to_string()}")
        
        return processed_code, variables
    
    def _process_groovy_expressions(self, source_code: str) -> Tuple[str, List[TemplateVariable]]:
        """Process Groovy expressions <% ... %>"""
        variables = []
        processed_code = source_code
        
        # Find all Groovy expressions
        groovy_pattern = r'<%(.*?)%>'
        matches = list(re.finditer(groovy_pattern, source_code, re.DOTALL))
        
        for i, match in enumerate(matches):
            groovy_code = match.group(1).strip()
            placeholder = f"GROOVY_EXPRESSION_{i}"
            
            # Create variable
            var = TemplateVariable(
                name=groovy_code,
                value=placeholder,
                is_groovy=True
            )
            variables.append(var)
            
            # Replace with placeholder
            processed_code = processed_code.replace(match.group(0), placeholder)
        
        return processed_code, variables
    
    def _process_dollar_variables(self, source_code: str) -> Tuple[str, List[TemplateVariable]]:
        """Process ${} variables"""
        variables = []
        processed_code = source_code
        
        # Find all ${} variables
        dollar_pattern = r'\$\{([^}]+)\}'
        matches = list(re.finditer(dollar_pattern, source_code))
        
        for i, match in enumerate(matches):
            var_name = match.group(1).strip()
            placeholder = f"TEMPLATE_VAR_{i}"
            
            # Create variable
            var = TemplateVariable(
                name=var_name,
                value=placeholder,
                is_groovy=False
            )
            variables.append(var)
            
            # Replace with placeholder
            processed_code = processed_code.replace(match.group(0), placeholder)
        
        return processed_code, variables
    
    def _post_process_template_class(
        self, 
        class_info: ClassInfo, 
        variables: List[TemplateVariable], 
        original_source: str
    ) -> ClassInfo:
        """
        Post-process the parsed class to restore template information and extract semantic connections.
        
        Args:
            class_info: Parsed class information
            variables: Template variables found
            original_source: Original template source code
        
        Returns:
            Enhanced class information with template metadata and semantic connections
        """
        # Add template metadata to the class
        class_info.template_variables = variables
        class_info.is_template = True
        class_info.original_source = original_source
        
        # Process methods to restore template information and extract connections
        for method in class_info.methods:
            method.template_variables = self._find_method_template_variables(method, variables)
            method.is_template = len(method.template_variables) > 0
            
            # Extract semantic connections from method
            method.semantic_connections = self._extract_method_semantic_connections(method, original_source)
            method.method_calls = self._extract_method_calls(method, original_source)
            method.field_usage = self._extract_field_usage(method, original_source)
        
        # Process fields to restore template information
        for field in class_info.fields:
            field.template_variables = self._find_field_template_variables(field, variables)
            field.is_template = len(field.template_variables) > 0
        
        # Extract class-level semantic connections
        class_info.semantic_connections = self._extract_class_semantic_connections(class_info, original_source)
        
        return class_info
    
    def _find_method_template_variables(self, method: MethodInfo, variables: List[TemplateVariable]) -> List[TemplateVariable]:
        """Find template variables used in a method"""
        method_vars = []
        
        for var in variables:
            if var.is_groovy:
                # Check if Groovy expression is in method source
                if f"<% {var.name} %>" in method.source_code:
                    method_vars.append(var)
            else:
                # Check if ${} variable is in method source
                if f"${{{var.name}}}" in method.source_code:
                    method_vars.append(var)
        
        return method_vars
    
    def _find_field_template_variables(self, field: FieldInfo, variables: List[TemplateVariable]) -> List[TemplateVariable]:
        """Find template variables used in a field"""
        field_vars = []
        
        if field.initial_value:
            for var in variables:
                if var.is_groovy:
                    if f"<% {var.name} %>" in field.initial_value:
                        field_vars.append(var)
                else:
                    if f"${{{var.name}}}" in field.initial_value:
                        field_vars.append(var)
        
        return field_vars
    
    def get_template_variables(self, file_path: str) -> List[TemplateVariable]:
        """Get template variables for a specific file"""
        return self.template_variables.get(file_path, [])
    
    def generate_template_instance(
        self, 
        class_info: ClassInfo, 
        variable_values: Dict[str, str]
    ) -> str:
        """
        Generate a concrete Java class from a template by substituting variables.
        
        Args:
            class_info: Template class information
            variable_values: Values for template variables
        
        Returns:
            Generated Java source code
        """
        if not hasattr(class_info, 'original_source') or not class_info.original_source:
            logger.warning("No original source available for template generation")
            return ""
        
        generated_code = class_info.original_source
        
        # Substitute variables
        for var in class_info.template_variables:
            if var.name in variable_values:
                if var.is_groovy:
                    # For Groovy expressions, we need to evaluate them
                    # For now, just replace with the value
                    placeholder = f"<% {var.name} %>"
                    generated_code = generated_code.replace(placeholder, variable_values[var.name])
                else:
                    # For ${} variables, simple substitution
                    placeholder = f"${{{var.name}}}"
                    generated_code = generated_code.replace(placeholder, variable_values[var.name])
        
        return generated_code
    
    def _extract_method_semantic_connections(self, method: MethodInfo, original_source: str) -> List[Dict[str, Any]]:
        """Extract semantic connections from method source code"""
        connections = []
        
        if not hasattr(method, 'source_code') or not method.source_code:
            return connections
        
        # Extract method calls from original source (before template processing)
        method_name = method.signature.name if hasattr(method, 'signature') else getattr(method, 'name', '')
        method_start = original_source.find(method_name)
        if method_start == -1:
            return connections
        
        # Find method body in original source
        method_body = self._extract_method_body_from_source(original_source, method_start)
        if not method_body:
            return connections
        
        # Extract various types of connections
        connections.extend(self._extract_import_connections(method_body))
        connections.extend(self._extract_annotation_connections(method_body))
        connections.extend(self._extract_type_connections(method_body))
        
        return connections
    
    def _extract_method_calls(self, method: MethodInfo, original_source: str) -> List[str]:
        """Extract method calls from method source code"""
        method_calls = []
        
        if not hasattr(method, 'source_code') or not method.source_code:
            return method_calls
        
        # Find method body in original source
        method_name = method.signature.name if hasattr(method, 'signature') else getattr(method, 'name', '')
        method_start = original_source.find(method_name)
        if method_start == -1:
            return method_calls
        
        method_body = self._extract_method_body_from_source(original_source, method_start)
        if not method_body:
            return method_calls
        
        # Pattern for method calls: identifier( or identifier.method(
        method_call_pattern = r'(\w+(?:\.\w+)*)\s*\('
        matches = re.findall(method_call_pattern, method_body)
        
        for match in matches:
            # Filter out common keywords and operators
            if match not in ['if', 'for', 'while', 'switch', 'catch', 'new', 'return', 'throw']:
                method_calls.append(match)
        
        return list(set(method_calls))  # Remove duplicates
    
    def _extract_field_usage(self, method: MethodInfo, original_source: str) -> List[str]:
        """Extract field usage from method source code"""
        field_usage = []
        
        if not hasattr(method, 'source_code') or not method.source_code:
            return field_usage
        
        # Find method body in original source
        method_name = method.signature.name if hasattr(method, 'signature') else getattr(method, 'name', '')
        method_start = original_source.find(method_name)
        if method_start == -1:
            return field_usage
        
        method_body = self._extract_method_body_from_source(original_source, method_start)
        if not method_body:
            return field_usage
        
        # Pattern for field access: this.field or just field
        field_pattern = r'(?:this\.)?(\w+)(?=\s*[=;,\)])'
        matches = re.findall(field_pattern, method_body)
        
        for match in matches:
            # Filter out keywords and method calls
            if match not in ['if', 'for', 'while', 'switch', 'catch', 'new', 'return', 'throw', 'true', 'false', 'null']:
                field_usage.append(match)
        
        return list(set(field_usage))  # Remove duplicates
    
    def _extract_class_semantic_connections(self, class_info: ClassInfo, original_source: str) -> List[Dict[str, Any]]:
        """Extract class-level semantic connections"""
        connections = []
        
        # Extract import connections
        connections.extend(self._extract_import_connections(original_source))
        
        # Extract inheritance connections
        if class_info.extends:
            connections.append({
                'type': 'EXTENDS',
                'target': class_info.extends,
                'source': class_info.name
            })
        
        # Extract interface implementations
        for interface in class_info.implements:
            connections.append({
                'type': 'IMPLEMENTS',
                'target': interface,
                'source': class_info.name
            })
        
        return connections
    
    def _extract_import_connections(self, source_code: str) -> List[Dict[str, Any]]:
        """Extract import-based connections"""
        connections = []
        
        # Pattern for import statements
        import_pattern = r'import\s+(?:static\s+)?([^;]+);'
        matches = re.findall(import_pattern, source_code)
        
        for match in matches:
            # Extract class name from import
            class_name = match.split('.')[-1]
            connections.append({
                'type': 'IMPORTS',
                'target': class_name,
                'source': 'import'
            })
        
        return connections
    
    def _extract_annotation_connections(self, source_code: str) -> List[Dict[str, Any]]:
        """Extract annotation-based connections"""
        connections = []
        
        # Pattern for annotations
        annotation_pattern = r'@(\w+(?:\.\w+)*)'
        matches = re.findall(annotation_pattern, source_code)
        
        for match in matches:
            annotation_name = match.split('.')[-1]
            connections.append({
                'type': 'ANNOTATED',
                'target': annotation_name,
                'source': 'annotation'
            })
        
        return connections
    
    def _extract_type_connections(self, source_code: str) -> List[Dict[str, Any]]:
        """Extract type-based connections"""
        connections = []
        
        # Pattern for type declarations and casts
        type_pattern = r'(?:new\s+|cast\s+|instanceof\s+)(\w+(?:\.\w+)*)'
        matches = re.findall(type_pattern, source_code)
        
        for match in matches:
            type_name = match.split('.')[-1]
            connections.append({
                'type': 'USES_TYPE',
                'target': type_name,
                'source': 'type_usage'
            })
        
        return connections
    
    def _extract_method_body_from_source(self, source_code: str, method_start: int) -> str:
        """Extract method body from source code"""
        # Find the opening brace
        brace_start = source_code.find('{', method_start)
        if brace_start == -1:
            return ""
        
        # Count braces to find the closing brace
        brace_count = 0
        brace_end = brace_start
        
        for i in range(brace_start, len(source_code)):
            if source_code[i] == '{':
                brace_count += 1
            elif source_code[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    brace_end = i
                    break
        
        if brace_count != 0:
            return ""
        
        return source_code[brace_start:brace_end + 1]


if __name__ == "__main__":
    # Test the universal parser
    test_template = """
    package ${packageName};
    
    import static org.junit.Assert.*;
    
    public class ${testClassName} {
        private final ${productionClassName} production = new ${productionClassName}("value");
    
    <% testMethodCount.times { %>
        @org.junit.Test
        public void test${it}() {
            assertEquals(production.getProperty(), "value");
        }
    <% } %>
    }
    """
    
    parser = UniversalJavaParser()
    class_info = parser.parse_source(test_template)
    
    if class_info:
        print(f"\n✅ Parsed template class: {class_info.package}.{class_info.name}")
        print(f"📦 Template variables: {len(class_info.template_variables)}")
        print(f"📋 Fields: {len(class_info.fields)}")
        print(f"🔧 Methods: {len(class_info.methods)}")
        
        for var in class_info.template_variables:
            print(f"  Variable: {var.to_string()}")
        
        # Test generation
        variable_values = {
            "packageName": "com.example.test",
            "testClassName": "MyTest",
            "productionClassName": "MyProduction",
            "testMethodCount.times { }": "3"  # This would need proper Groovy evaluation
        }
        
        generated = parser.generate_template_instance(class_info, variable_values)
        print(f"\n📝 Generated code length: {len(generated)} characters")
    else:
        print("❌ Failed to parse template")
