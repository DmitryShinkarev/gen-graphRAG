"""
Java code parser using Tree-sitter for accurate AST analysis.
Extracts classes, methods, fields, imports, and calculates complexity metrics.
"""

from pathlib import Path
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
import sys
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser, Node, Tree, Query

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class MethodSignature:
    """Represents a method signature"""
    name: str
    return_type: str
    parameters: List[Dict[str, str]]  # [{name, type}]
    modifiers: List[str]
    annotations: List[str]
    
    def to_string(self) -> str:
        """Convert to human-readable string"""
        params = ", ".join(f"{p['type']} {p['name']}" for p in self.parameters)
        modifiers_str = " ".join(self.modifiers) if self.modifiers else ""
        return f"{modifiers_str} {self.return_type} {self.name}({params})"


@dataclass
class MethodInfo:
    """Complete information about a method"""
    signature: MethodSignature
    source_code: str
    start_line: int
    end_line: int
    complexity: int
    loc: int  # Lines of code
    class_name: str
    package: str
    javadoc: Optional[str] = None
    calls: List[str] = field(default_factory=list)  # Called methods
    used_fields: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.signature.name,
            "full_signature": self.signature.to_string(),
            "return_type": self.signature.return_type,
            "parameters": self.signature.parameters,
            "modifiers": self.signature.modifiers,
            "annotations": self.signature.annotations,
            "source_code": self.source_code,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "complexity": self.complexity,
            "loc": self.loc,
            "class_name": self.class_name,
            "package": self.package,
            "javadoc": self.javadoc,
            "calls": self.calls,
            "used_fields": self.used_fields
        }


@dataclass
class FieldInfo:
    """Information about a class field"""
    name: str
    type: str
    modifiers: List[str]
    initial_value: Optional[str] = None
    annotations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.type,
            "modifiers": self.modifiers,
            "initial_value": self.initial_value,
            "annotations": self.annotations
        }


@dataclass
class ClassInfo:
    """Information about a Java class"""
    name: str
    package: str
    modifiers: List[str]
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    fields: List[FieldInfo] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    javadoc: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "package": self.package,
            "modifiers": self.modifiers,
            "extends": self.extends,
            "implements": self.implements,
            "fields": [f.to_dict() for f in self.fields],
            "methods": [m.to_dict() for m in self.methods],
            "imports": self.imports,
            "annotations": self.annotations,
            "javadoc": self.javadoc
        }


class JavaParser:
    """
    Java code parser using Tree-sitter.
    
    Features:
    - Accurate AST-based parsing
    - Extracts classes, methods, fields
    - Calculates cyclomatic complexity
    - Identifies dependencies and method calls
    """
    
    def __init__(self):
        """Initialize the Java parser"""
        # Load Java language
        self.java_language = Language(tsjava.language())
        self.parser = Parser(self.java_language)
        
        logger.info("Java parser initialized with Tree-sitter")
    
    def parse_file(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse a Java source file.
        
        Args:
            file_path: Path to the Java file
        
        Returns:
            ClassInfo or None if parsing failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            return self.parse_source(source_code)
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            return None
    
    def parse_source(self, source_code: str) -> Optional[ClassInfo]:
        """
        Parse Java source code.
        
        Args:
            source_code: Java source code as string
        
        Returns:
            ClassInfo or None if parsing failed
        """
        try:
            # Parse the code
            tree = self.parser.parse(bytes(source_code, "utf-8"))
            root_node = tree.root_node
            
            # Extract package
            package = self._extract_package(root_node, source_code)
            
            # Extract imports
            imports = self._extract_imports(root_node, source_code)
            
            # Extract class information
            class_node = self._find_class_node(root_node)
            if not class_node:
                logger.warning(f"No class declaration found in source code (length: {len(source_code)})")
                logger.debug(f"Root node type: {root_node.type}, children: {len(root_node.children)}")
                return None
            
            class_info = self._parse_class(class_node, source_code, package, imports)
            return class_info
            
        except Exception as e:
            logger.error(f"Failed to parse source code: {e}")
            return None
    
    def _node_text(self, node: Node, source: str) -> str:
        """Extract text from a node"""
        return source[node.start_byte:node.end_byte]
    
    def _extract_package(self, root: Node, source: str) -> str:
        """Extract package name"""
        def find_package(node: Node) -> Optional[str]:
            if node.type == 'package_declaration':
                for child in node.children:
                    if child.type == 'scoped_identifier':
                        return source[child.start_byte:child.end_byte]
            for child in node.children:
                result = find_package(child)
                if result:
                    return result
            return None
        
        return find_package(root) or ""
    
    def _extract_imports(self, root: Node, source: str) -> List[str]:
        """Extract import statements"""
        imports = []
        
        def traverse(node):
            if node.type == 'import_declaration':
                import_text = self._node_text(node, source)
                if import_text.startswith('import '):
                    imports.append(import_text)
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return imports
    
    def _find_class_node(self, root: Node) -> Optional[Node]:
        """Find the main class declaration node"""
        def traverse(node):
            if node.type == 'class_declaration':
                return node
            for child in node.children:
                result = traverse(child)
                if result:
                    return result
            return None
        
        return traverse(root)
    
    def _parse_class(
        self,
        class_node: Node,
        source: str,
        package: str,
        imports: List[str]
    ) -> ClassInfo:
        """Parse class declaration"""
        # Class name
        name_node = class_node.child_by_field_name("name")
        class_name = self._node_text(name_node, source) if name_node else "Unknown"
        
        # Modifiers
        modifiers = self._extract_modifiers(class_node, source)
        
        # Annotations
        annotations = self._extract_annotations(class_node, source)
        
        # Superclass
        superclass_node = class_node.child_by_field_name("superclass")
        extends = self._node_text(superclass_node, source) if superclass_node else None
        
        # Interfaces
        interfaces_node = class_node.child_by_field_name("interfaces")
        implements = []
        if interfaces_node:
            for child in interfaces_node.children:
                if child.type == "type_identifier":
                    implements.append(self._node_text(child, source))
        
        # Class body
        body_node = class_node.child_by_field_name("body")
        if not body_node:
            return ClassInfo(
                name=class_name,
                package=package,
                modifiers=modifiers,
                extends=extends,
                implements=implements,
                imports=imports,
                annotations=annotations
            )
        
        # Extract fields and methods
        fields = []
        methods = []
        
        for child in body_node.children:
            if child.type == "field_declaration":
                field_info = self._parse_field(child, source)
                if field_info:
                    fields.append(field_info)
            
            elif child.type == "method_declaration":
                method_info = self._parse_method(child, source, class_name, package)
                if method_info:
                    methods.append(method_info)
            
            elif child.type == "constructor_declaration":
                method_info = self._parse_method(child, source, class_name, package)
                if method_info:
                    methods.append(method_info)
        
        return ClassInfo(
            name=class_name,
            package=package,
            modifiers=modifiers,
            extends=extends,
            implements=implements,
            fields=fields,
            methods=methods,
            imports=imports,
            annotations=annotations
        )
    
    def _extract_modifiers(self, node: Node, source: str) -> List[str]:
        """Extract modifiers (public, private, static, etc.)"""
        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type != "marker_annotation" and modifier.type != "annotation":
                        modifiers.append(self._node_text(modifier, source))
        return modifiers
    
    def _extract_annotations(self, node: Node, source: str) -> List[str]:
        """Extract annotations"""
        annotations = []
        for child in node.children:
            if child.type in ("marker_annotation", "annotation"):
                annotations.append(self._node_text(child, source))
            elif child.type == "modifiers":
                for modifier in child.children:
                    if modifier.type in ("marker_annotation", "annotation"):
                        annotations.append(self._node_text(modifier, source))
        return annotations
    
    def _parse_field(self, field_node: Node, source: str) -> Optional[FieldInfo]:
        """Parse field declaration"""
        try:
            # Type
            type_node = field_node.child_by_field_name("type")
            field_type = self._node_text(type_node, source) if type_node else "Unknown"
            
            # Declarator (contains name and initial value)
            declarator = None
            for child in field_node.children:
                if child.type == "variable_declarator":
                    declarator = child
                    break
            
            if not declarator:
                return None
            
            # Name
            name_node = declarator.child_by_field_name("name")
            field_name = self._node_text(name_node, source) if name_node else "Unknown"
            
            # Initial value
            value_node = declarator.child_by_field_name("value")
            initial_value = self._node_text(value_node, source) if value_node else None
            
            # Modifiers and annotations
            modifiers = self._extract_modifiers(field_node, source)
            annotations = self._extract_annotations(field_node, source)
            
            return FieldInfo(
                name=field_name,
                type=field_type,
                modifiers=modifiers,
                initial_value=initial_value,
                annotations=annotations
            )
        except Exception as e:
            logger.warning(f"Failed to parse field: {e}")
            return None
    
    def _parse_method(
        self,
        method_node: Node,
        source: str,
        class_name: str,
        package: str
    ) -> Optional[MethodInfo]:
        """Parse method declaration or constructor"""
        try:
            # Method name
            name_node = method_node.child_by_field_name("name")
            method_name = self._node_text(name_node, source) if name_node else "Unknown"
            
            # Return type - constructors don't have return type
            if method_node.type == "constructor_declaration":
                return_type = "constructor"
            else:
                type_node = method_node.child_by_field_name("type")
                return_type = self._node_text(type_node, source) if type_node else "void"
            
            # Parameters
            parameters = self._parse_parameters(method_node, source)
            
            # Modifiers and annotations
            modifiers = self._extract_modifiers(method_node, source)
            annotations = self._extract_annotations(method_node, source)
            
            # Method signature
            signature = MethodSignature(
                name=method_name,
                return_type=return_type,
                parameters=parameters,
                modifiers=modifiers,
                annotations=annotations
            )
            
            # Method body
            body_node = method_node.child_by_field_name("body")
            if not body_node:
                # Abstract method
                return MethodInfo(
                    signature=signature,
                    source_code="",
                    start_line=method_node.start_point[0] + 1,
                    end_line=method_node.end_point[0] + 1,
                    complexity=0,
                    loc=0,
                    class_name=class_name,
                    package=package
                )
            
            # Source code
            method_source = self._node_text(method_node, source)
            start_line = method_node.start_point[0] + 1
            end_line = method_node.end_point[0] + 1
            loc = end_line - start_line + 1
            
            # Calculate complexity
            complexity = self._calculate_complexity(body_node)
            
            # Extract method calls
            calls = self._extract_method_calls(body_node, source)
            
            # Extract field usage
            used_fields = self._extract_field_usage(body_node, source)
            
            return MethodInfo(
                signature=signature,
                source_code=method_source,
                start_line=start_line,
                end_line=end_line,
                complexity=complexity,
                loc=loc,
                class_name=class_name,
                package=package,
                calls=calls,
                used_fields=used_fields
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse method: {e}")
            return None
    
    def _parse_parameters(self, method_node: Node, source: str) -> List[Dict[str, str]]:
        """Parse method parameters"""
        parameters = []
        params_node = method_node.child_by_field_name("parameters")
        
        if not params_node:
            return parameters
        
        for child in params_node.children:
            if child.type == "formal_parameter":
                type_node = child.child_by_field_name("type")
                name_node = child.child_by_field_name("name")
                
                if type_node and name_node:
                    parameters.append({
                        "type": self._node_text(type_node, source),
                        "name": self._node_text(name_node, source)
                    })
        
        return parameters
    
    def _calculate_complexity(self, body_node: Node) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        # Decision points
        decision_nodes = {
            "if_statement", "while_statement", "for_statement",
            "do_statement", "switch_expression", "catch_clause",
            "conditional_expression", "||", "&&"
        }
        
        def count_decisions(node: Node) -> int:
            count = 1 if node.type in decision_nodes else 0
            for child in node.children:
                count += count_decisions(child)
            return count
        
        complexity += count_decisions(body_node)
        return complexity
    
    def _extract_method_calls(self, body_node: Node, source: str) -> List[str]:
        """Extract method calls from method body"""
        calls = []
        
        def find_calls(node: Node):
            if node.type == "method_invocation":
                name_node = node.child_by_field_name("name")
                if name_node:
                    calls.append(self._node_text(name_node, source))
            
            for child in node.children:
                find_calls(child)
        
        find_calls(body_node)
        return calls
    
    def _extract_field_usage(self, body_node: Node, source: str) -> List[str]:
        """Extract field references from method body"""
        fields = []
        
        def find_fields(node: Node):
            if node.type == "field_access":
                field_node = node.child_by_field_name("field")
                if field_node:
                    fields.append(self._node_text(field_node, source))
            
            for child in node.children:
                find_fields(child)
        
        find_fields(body_node)
        return fields


if __name__ == "__main__":
    # Test the parser
    test_code = """
    package com.example.test;
    
    import java.util.List;
    import java.util.ArrayList;
    
    /**
     * Sample class for testing
     */
    public class Calculator {
        private int counter = 0;
        
        /**
         * Adds two numbers
         */
        public int add(int a, int b) {
            counter++;
            if (a < 0 || b < 0) {
                throw new IllegalArgumentException("Negative numbers");
            }
            return a + b;
        }
        
        public void complexMethod(List<String> items) {
            for (String item : items) {
                if (item != null) {
                    System.out.println(item);
                } else {
                    System.err.println("Null item");
                }
            }
        }
    }
    """
    
    parser = JavaParser()
    class_info = parser.parse_source(test_code)
    
    if class_info:
        print(f"\n✅ Parsed class: {class_info.package}.{class_info.name}")
        print(f"📦 Imports: {len(class_info.imports)}")
        print(f"📋 Fields: {len(class_info.fields)}")
        print(f"🔧 Methods: {len(class_info.methods)}")
        
        for method in class_info.methods:
            print(f"\n  Method: {method.signature.name}")
            print(f"    Signature: {method.signature.to_string()}")
            print(f"    Complexity: {method.complexity}")
            print(f"    LOC: {method.loc}")
            print(f"    Calls: {method.calls}")

