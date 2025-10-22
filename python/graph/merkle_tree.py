"""
Merkle Tree implementation for efficient change detection in Java projects.
Builds a hash tree of the project structure to quickly identify modified files.
"""

import hashlib
from pathlib import Path
from typing import Optional, List, Set, Dict
from dataclasses import dataclass, field
import pathspec
from datetime import datetime

from logger import get_logger

logger = get_logger(__name__)


@dataclass
class MerkleNode:
    """Node in the Merkle tree representing a file or directory"""
    
    path: Path
    hash: str
    is_file: bool
    size: int = 0
    modified_time: Optional[datetime] = None
    children: List['MerkleNode'] = field(default_factory=list)
    
    def __repr__(self) -> str:
        node_type = "FILE" if self.is_file else "DIR"
        return f"MerkleNode({node_type}: {self.path.name}, hash={self.hash[:8]}...)"
    
    def to_dict(self) -> Dict:
        """Convert node to dictionary representation"""
        return {
            "path": str(self.path),
            "hash": self.hash,
            "is_file": self.is_file,
            "size": self.size,
            "modified_time": self.modified_time.isoformat() if self.modified_time else None,
            "children": [child.to_dict() for child in self.children]
        }


class MerkleTree:
    """
    Merkle Tree for tracking project file changes.
    
    Features:
    - Efficient change detection
    - Respects .gitignore patterns
    - Supports incremental updates
    - Hash-based file comparison
    """
    
    def __init__(self, root_path: Path, gitignore_patterns: Optional[List[str]] = None):
        """
        Initialize Merkle Tree.
        
        Args:
            root_path: Root directory of the project
            gitignore_patterns: List of gitignore patterns to exclude
        """
        self.root_path = Path(root_path).resolve()
        self.root_node: Optional[MerkleNode] = None
        
        # Setup gitignore patterns
        self.spec = None
        if gitignore_patterns:
            self.spec = pathspec.PathSpec.from_lines('gitwildmatch', gitignore_patterns)
        
        # Default ignore patterns
        self.default_ignores = {
            '.git', '.svn', '.hg',
            '__pycache__', '.pytest_cache', '.mypy_cache',
            'node_modules', 'venv', 'env', '.env',
            '.idea', '.vscode',
            '*.pyc', '*.pyo', '*.class',
            '.DS_Store', 'Thumbs.db'
        }
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored"""
        # Check default ignores
        if path.name in self.default_ignores:
            return True
        
        # Check patterns
        if path.suffix in {'.pyc', '.pyo', '.class'}:
            return True
        
        # Check gitignore spec
        if self.spec:
            relative_path = path.relative_to(self.root_path)
            if self.spec.match_file(str(relative_path)):
                return True
        
        return False
    
    def _hash_file(self, file_path: Path) -> str:
        """
        Compute SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
        
        Returns:
            Hex digest of the file hash
        """
        sha256 = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                # Read file in chunks for memory efficiency
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            # Return hash of empty content
            return hashlib.sha256(b'').hexdigest()
    
    def _hash_children(self, children: List[MerkleNode]) -> str:
        """
        Compute hash from children node hashes.
        
        Args:
            children: List of child nodes
        
        Returns:
            Combined hash of all children
        """
        sha256 = hashlib.sha256()
        
        # Sort children by name for deterministic hashing
        sorted_children = sorted(children, key=lambda n: n.path.name)
        
        for child in sorted_children:
            sha256.update(child.hash.encode('utf-8'))
            sha256.update(child.path.name.encode('utf-8'))
        
        return sha256.hexdigest()
    
    def _build_node(self, path: Path) -> Optional[MerkleNode]:
        """
        Recursively build a Merkle node for a path.
        
        Args:
            path: Path to build node for
        
        Returns:
            MerkleNode or None if path should be ignored
        """
        if self._should_ignore(path):
            return None
        
        # File node
        if path.is_file():
            try:
                stat = path.stat()
                file_hash = self._hash_file(path)
                
                return MerkleNode(
                    path=path,
                    hash=file_hash,
                    is_file=True,
                    size=stat.st_size,
                    modified_time=datetime.fromtimestamp(stat.st_mtime)
                )
            except Exception as e:
                logger.warning(f"Failed to process file {path}: {e}")
                return None
        
        # Directory node
        elif path.is_dir():
            children = []
            
            try:
                for child_path in path.iterdir():
                    child_node = self._build_node(child_path)
                    if child_node:
                        children.append(child_node)
            except PermissionError:
                logger.warning(f"Permission denied: {path}")
                return None
            
            # Compute hash from children
            dir_hash = self._hash_children(children) if children else hashlib.sha256(b'').hexdigest()
            
            return MerkleNode(
                path=path,
                hash=dir_hash,
                is_file=False,
                children=children
            )
        
        return None
    
    def build(self) -> MerkleNode:
        """
        Build the complete Merkle tree.
        
        Returns:
            Root node of the Merkle tree
        """
        logger.info(f"Building Merkle tree for: {self.root_path}")
        
        start_time = datetime.now()
        self.root_node = self._build_node(self.root_path)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if self.root_node:
            file_count = self._count_files(self.root_node)
            logger.info(f"Merkle tree built: {file_count} files in {elapsed:.2f}s")
        else:
            logger.warning("Failed to build Merkle tree")
        
        return self.root_node
    
    def _count_files(self, node: MerkleNode) -> int:
        """Count total files in tree"""
        if node.is_file:
            return 1
        return sum(self._count_files(child) for child in node.children)
    
    def get_changed_files(
        self,
        other_tree: 'MerkleTree',
        only_java: bool = True
    ) -> Set[Path]:
        """
        Compare with another Merkle tree to find changed files.
        
        Args:
            other_tree: Another MerkleTree to compare with
            only_java: If True, only return .java files
        
        Returns:
            Set of paths that have changed
        """
        if not self.root_node or not other_tree.root_node:
            logger.warning("Cannot compare: one or both trees are empty")
            return set()
        
        changed = set()
        self._compare_nodes(self.root_node, other_tree.root_node, changed)
        
        if only_java:
            changed = {p for p in changed if p.suffix == '.java'}
        
        logger.info(f"Found {len(changed)} changed files")
        return changed
    
    def _compare_nodes(
        self,
        node1: MerkleNode,
        node2: MerkleNode,
        changed: Set[Path]
    ) -> None:
        """Recursively compare two nodes"""
        # Different hashes = changed
        if node1.hash != node2.hash:
            if node1.is_file:
                changed.add(node1.path)
                return
            
            # Compare children
            children1_dict = {child.path.name: child for child in node1.children}
            children2_dict = {child.path.name: child for child in node2.children}
            
            # Find new and modified files
            for name, child1 in children1_dict.items():
                if name not in children2_dict:
                    # New file/directory
                    if child1.is_file:
                        changed.add(child1.path)
                else:
                    # Recursively compare
                    self._compare_nodes(child1, children2_dict[name], changed)
    
    def get_all_files(self, extensions: Optional[Set[str]] = None) -> List[Path]:
        """
        Get all files in the tree.
        
        Args:
            extensions: Optional set of file extensions to filter (e.g., {'.java'})
        
        Returns:
            List of file paths
        """
        if not self.root_node:
            return []
        
        files = []
        self._collect_files(self.root_node, files, extensions)
        return files
    
    def _collect_files(
        self,
        node: MerkleNode,
        files: List[Path],
        extensions: Optional[Set[str]]
    ) -> None:
        """Recursively collect files"""
        if node.is_file:
            if extensions is None or node.path.suffix in extensions:
                files.append(node.path)
        else:
            for child in node.children:
                self._collect_files(child, files, extensions)


def load_gitignore(project_path: Path) -> List[str]:
    """
    Load .gitignore patterns from project.
    
    Args:
        project_path: Root path of the project
    
    Returns:
        List of gitignore patterns
    """
    gitignore_path = project_path / '.gitignore'
    patterns = []
    
    if gitignore_path.exists():
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
            logger.info(f"Loaded {len(patterns)} patterns from .gitignore")
        except Exception as e:
            logger.warning(f"Failed to load .gitignore: {e}")
    
    return patterns


if __name__ == "__main__":
    # Test the Merkle tree
    import sys
    
    if len(sys.argv) > 1:
        test_path = Path(sys.argv[1])
    else:
        test_path = Path.cwd()
    
    print(f"Building Merkle tree for: {test_path}")
    
    # Load gitignore
    patterns = load_gitignore(test_path)
    
    # Build tree
    tree = MerkleTree(test_path, patterns)
    root = tree.build()
    
    if root:
        print(f"\n✅ Root hash: {root.hash}")
        
        # Get Java files
        java_files = tree.get_all_files({'.java'})
        print(f"\n📁 Found {len(java_files)} Java files:")
        for f in java_files[:10]:  # Show first 10
            print(f"  - {f.relative_to(test_path)}")
        
        if len(java_files) > 10:
            print(f"  ... and {len(java_files) - 10} more")

