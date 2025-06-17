"""
Dependency analysis for building and analyzing file dependency relationships.
"""

import os
import re
import json
import time
from pathlib import Path
from collections import defaultdict, deque

from .utils import read_file_content, load_cache, save_cache

# =============================================================================
# DEPENDENCY ANALYSIS CLASSES
# =============================================================================

class DependencyGraph:
    """Builds and analyzes dependency relationships between files."""
    
    def __init__(self):
        self.imports = defaultdict(set)  # file -> set of files it imports
        self.imported_by = defaultdict(set)  # file -> set of files that import it
        self.all_files = set()
        
    def add_dependency(self, from_file, to_file):
        """Add a dependency relationship."""
        self.imports[from_file].add(to_file)
        self.imported_by[to_file].add(from_file)
        self.all_files.add(from_file)
        self.all_files.add(to_file)
    
    def get_import_count(self, file_path):
        """Get number of files that import this file."""
        return len(self.imported_by[file_path])
    
    def find_circular_dependencies(self):
        """Find circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle - extract the cycle path
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.imports[node]:
                dfs(neighbor, path)
            
            path.pop()
            rec_stack.remove(node)
        
        for file in self.all_files:
            if file not in visited:
                dfs(file, [])
        
        return cycles

class ImportParser:
    """Parses import statements from different programming languages."""
    
    @staticmethod
    def parse_python_imports(file_path, project_root):
        """Parse Python import statements."""
        imports = set()
        content = read_file_content(file_path)
        if not content:
            return []

        # Handle different Python import patterns
        patterns = [
            r'^\s*from\s+([^\s]+)\s+import',  # from module import
            r'^\s*import\s+([^\s,]+)',        # import module
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            imports.update(matches)
            
        return list(imports)
    
    @staticmethod
    def parse_javascript_imports(file_path, project_root):
        """Parse JavaScript/TypeScript import statements."""
        imports = set()
        content = read_file_content(file_path)
        if not content:
            return []

        # Handle different JS/TS import patterns
        patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',  # import from
            r'import\s+[\'"]([^\'"]+)[\'"]',               # import
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',   # require
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            imports.update(matches)
            
        return list(imports)
    
    @staticmethod
    def get_file_imports(file_path, project_root):
        """Get imports for a file based on its extension."""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.py':
            return ImportParser.parse_python_imports(file_path, project_root)
        elif ext in {'.js', '.jsx', '.ts', '.tsx'}:
            return ImportParser.parse_javascript_imports(file_path, project_root)
        else:
            return []

def find_all_source_dirs(root_path, source_dirs, ignore_patterns, base_dir, config=None):
    """Recursively find all directories matching source directory names."""
    from .utils import should_ignore
    
    matches = []
    for dirpath, dirnames, _ in os.walk(root_path):
        # Remove ignored directories in-place
        dirnames[:] = [d for d in dirnames if not should_ignore(
            os.path.join(dirpath, d), ignore_patterns, base_dir, config)]
        for d in dirnames:
            if d in source_dirs:
                matches.append(os.path.join(dirpath, d))
    return matches

def load_cached_dependency_graph(project_hash):
    """Load cached dependency graph if it exists and is valid."""
    cache = load_cache()
    cache_key = f"dependency_graph:{project_hash}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        try:
            # Check if cache is recent (less than 1 hour old)
            if time.time() - cached_data.get('timestamp', 0) < 3600:
                # Reconstruct DependencyGraph object from cached data
                graph = DependencyGraph()
                imports_data = cached_data.get('imports', {})
                for from_file, to_files in imports_data.items():
                    for to_file in to_files:
                        graph.add_dependency(from_file, to_file)
                return graph
        except Exception:
            pass
    return None

def save_dependency_graph_cache(dependency_graph, project_hash):
    """Save dependency graph to cache."""
    cache = load_cache()
    cache_key = f"dependency_graph:{project_hash}"
    
    # Convert graph to serializable format
    cache_data = {
        'imports': {k: list(v) for k, v in dependency_graph.imports.items()},
        'timestamp': time.time()
    }
    
    cache[cache_key] = cache_data
    save_cache(cache)
