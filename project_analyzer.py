#!/usr/bin/env python3
"""
Project Analyzer - Advanced Architectural Health Monitoring

A comprehensive tool that analyzes project structure, detects architectural patterns,
and provides AI-powered insights for code quality improvement.

Features:
- File structure analysis with intelligent filtering
- Architectural boundary violation detection
- Dependency graph analysis and circular dependency detection
- Test coverage analysis (Jest support)
- AI-powered code review and summarization
- Multiple output formats (console, markdown, JSON, HTML)
"""

import os
import sys
import fnmatch
import re
import collections
import json
import subprocess
import hashlib
import ast
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
import threading
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Optional dependencies
try:
    import git
    HAS_GIT = True
except ImportError:
    HAS_GIT = False

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# ANSI escape sequences for colored output
RESET = "\033[0m"
GREY = "\033[90m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"

# File analysis thresholds
FILE_WARNING_THRESHOLD = 400
FILE_DANGER_THRESHOLD = 550
DIR_WARNING_THRESHOLD = 5000
DIR_DANGER_THRESHOLD = 10000

# File type classifications
SCRIPT_EXTS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.sh', '.bat', '.ps1', '.rb', '.php', 
    '.pl', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.cs', '.m', '.swift', 
    '.kt', '.dart'
}

DATA_EXTS = {
    '.json', '.csv', '.yml', '.yaml', '.xml', '.txt', '.md', '.ini', '.conf', '.log'
}

# Default exclusions
EXCLUDED_DIRS = {
    "node_modules", ".git", ".vscode", ".idea", "dist", "coverage", 
    "venv", ".venv", "__pycache__", "build", "target"
}

SOURCE_CODE_DIRS = {"src", "app", "main"}

# Architectural smell indicators
ARCHITECTURAL_SMELLS = {
    'BOUNDARY_VIOLATION': '🏛️ ARCHITECTURE',
    'ENTANGLEMENT': '🔗 ENTANGLEMENT', 
    'BLAST_RADIUS': '💥 BLAST RADIUS',
    'CIRCULAR_DEPENDENCY': '🔄 CIRCULAR DEPENDENCY',
    'GHOST_FILE': '👻 GHOST FILE',
    'STALE_TESTS': '👀 STALE TESTS',
    'STALE_LOGIC': '🕰️ STALE LOGIC',
    'HIGH_CHURN': '🔥 HIGH CHURN'
}

# Global paths
PROJECT_ROOT = os.getcwd()
CACHE_FILE = os.path.join(PROJECT_ROOT, "cache", ".analyzer-cache.json")
CONFIG_FILE = os.path.join(PROJECT_ROOT, ".analyzer-config.json")
_cache_lock = threading.Lock()

# AI schemas
CODE_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "positive_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "A list of 2-3 things that are well-designed in the code."
        },
        "refactoring_suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "smell": {"type": "string"},
                    "explanation": {"type": "string"},
                    "suggestion": {"type": "string"}
                },
                "required": ["smell", "explanation", "suggestion"]
            }
        }
    },
    "required": ["positive_points", "refactoring_suggestions"]
}

CODE_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "A 2-3 sentence summary of the file's primary responsibility."
        }
    },
    "required": ["summary"]
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_file_size(file_path):
    """Get file size in bytes, handling errors gracefully."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def count_lines(file_path):
    """Count lines in a text file, handling errors gracefully."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, IOError):
        return 0

def remove_ansi_colors(text):
    """Remove ANSI color codes from text."""
    if not text:
        return ""
    return re.sub(r"\033\[[0-9;]*m", "", text)

def is_binary_file(file_path):
    """Check if a file is binary."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(2048)
            if not chunk:
                return False
            text_characters = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)))
            nontext = chunk.translate(None, text_characters)
            return b'\0' in chunk or float(len(nontext)) / len(chunk) > 0.3
    except (OSError, IOError):
        return True

# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

def load_config():
    """Load configuration from .analyzer-config.json if it exists."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_configured_source_dirs(config):
    """Get configured source directories."""
    return set(config.get("source_dirs", ["src", "app", "main"]))

def get_configured_excluded_dirs(config):
    """Get configured excluded directories."""
    return set(config.get("exclude_dirs", [
        "node_modules", ".git", ".vscode", ".idea", "dist", "coverage", 
        "venv", ".venv", "__pycache__"
    ]))

def get_configured_exclude_patterns(config):
    """Get configured exclusion patterns."""
    return set(config.get("exclude_patterns", []))

def get_configured_llm_review_file_count(config):
    """Get number of files to review with LLM."""
    return int(config.get("llm_review_file_count", 3))

def get_configured_untestable_patterns(config):
    """Get configured untestable file patterns."""
    return set(config.get("untestable_patterns", []))

def get_configured_utility_patterns(config):
    """Get configured utility file patterns."""
    return set(config.get("utility_patterns", []))

# =============================================================================
# FILE FILTERING AND GITIGNORE HANDLING
# =============================================================================

def parse_gitignore(directory, config=None):
    """Parse .gitignore file and return ignore patterns."""
    gitignore_path = Path(directory) / ".gitignore"
    ignore_patterns = set()
    
    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ignore_patterns.add(line)
        except (OSError, IOError):
            pass
    
    if config:
        ignore_patterns.update(get_configured_exclude_patterns(config))
    
    return ignore_patterns

def should_ignore(path_str: str, gitignore_patterns: set, base_dir: str, config=None) -> bool:
    """Check if a file or directory should be ignored."""
    try:
        relative_path = Path(path_str).relative_to(base_dir)
    except ValueError:
        return True
    
    excluded_dirs = get_configured_excluded_dirs(config) if config else EXCLUDED_DIRS
    if any(part in excluded_dirs for part in relative_path.parts):
        return True
    
    for pattern in gitignore_patterns:
        if fnmatch.fnmatch(str(relative_path), pattern) or fnmatch.fnmatch(relative_path.name, pattern):
            return True
    
    return False

# =============================================================================
# CACHING SYSTEM
# =============================================================================

def load_cache():
    """Load analysis cache from disk."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(cache):
    """Save analysis cache to disk."""
    with _cache_lock:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass

def get_file_md5(file_path):
    """Get MD5 hash of a file for cache invalidation."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None

def get_project_hash(file_paths):
    """Generate a hash representing the current state of all project files."""
    file_hashes = []
    for file_path in sorted(file_paths):
        try:
            mtime = os.path.getmtime(file_path)
            size = os.path.getsize(file_path)
            file_hashes.append(f"{file_path}:{mtime}:{size}")
        except (OSError, IOError):
            continue
    
    combined = '|'.join(file_hashes)
    return hashlib.md5(combined.encode()).hexdigest()

def load_cached_dependency_graph(project_hash):
    """Load cached dependency graph if it exists and is valid."""
    cache = load_cache()
    cache_key = f"dependency_graph:{project_hash}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        try:
            graph = DependencyGraph()
            # Reconstruct the graph from cached data
            for from_file, to_files in cached_data.get('imports', {}).items():
                for to_file in to_files:
                    graph.add_dependency(from_file, to_file)
            return graph
        except Exception:
            return None
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
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
                
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.imports[node]:
                dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for file in self.all_files:
            if file not in visited:
                dfs(file, [])
        
        return cycles

class ImportParser:
    """Parses import statements from different programming languages."""
    
    @staticmethod
    def parse_python_imports(file_path, project_root):
        """Parse Python import statements using AST and regex fallback."""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Try AST parsing first
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
        except (SyntaxError, UnicodeDecodeError, Exception):
            # Fallback to regex parsing
            imports.update(ImportParser._parse_python_imports_regex(file_path))
        
        return imports
    
    @staticmethod
    def _parse_python_imports_regex(file_path):
        """Fallback regex-based Python import parsing."""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('import '):
                        module = line[7:].split()[0].split('.')[0]
                        imports.add(module)
                    elif line.startswith('from ') and ' import ' in line:
                        module = line[5:].split(' import ')[0].split('.')[0]
                        imports.add(module)
        except Exception:
            pass
        return imports
    
    @staticmethod
    def parse_javascript_imports(file_path, project_root):
        """Parse JavaScript/TypeScript import statements."""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Match various import patterns
            import_patterns = [
                r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',  # import ... from 'module'
                r'import\s+[\'"]([^\'"]+)[\'"]',                # import 'module'
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',    # require('module')
                r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',     # dynamic import('module')
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Focus on relative imports and local modules
                    if match.startswith('./') or match.startswith('../') or not match.startswith('@'):
                        imports.add(match)
        except Exception:
            pass
        
        return imports
    
    @staticmethod
    def get_file_imports(file_path, project_root):
        """Get imports for any supported file type."""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.py':
            return ImportParser.parse_python_imports(file_path, project_root)
        elif ext in {'.js', '.ts', '.tsx', '.jsx'}:
            return ImportParser.parse_javascript_imports(file_path, project_root)
        else:
            return set()

# =============================================================================
# ARCHITECTURAL PATTERN ANALYSIS
# =============================================================================

class ArchitecturalSniffer:
    """Main class for architectural pattern detection and analysis."""
    
    def __init__(self, project_root, config=None):
        self.project_root = project_root
        self.config = config or {}
        self.dependency_graph = DependencyGraph()
        self.smells = []
        
    def analyze_architecture(self, file_paths):
        """Run all architectural analyses."""
        print(f"{GREY}Building dependency graph...{RESET}")
        self._build_dependency_graph(file_paths)
        
        print(f"{GREY}Checking architectural patterns...{RESET}")
        self._check_boundary_violations()
        self._check_feature_entanglement()
        self._check_blast_radius()
        self._check_circular_dependencies()
        self._check_ghost_files(file_paths)
        self._check_stale_logic(file_paths)
        self._check_high_churn(file_paths)
        self._check_stale_tests(file_paths)
        
        return self.smells
    
    def _build_dependency_graph(self, file_paths):
        """Build the dependency graph for all files."""
        for file_path in file_paths:
            if Path(file_path).suffix.lower() in SCRIPT_EXTS:
                imports = ImportParser.get_file_imports(file_path, self.project_root)
                
                for import_name in imports:
                    resolved_path = self._resolve_import_path(import_name, file_path)
                    if resolved_path and resolved_path in file_paths:
                        self.dependency_graph.add_dependency(file_path, resolved_path)
    
    def _resolve_import_path(self, import_name, from_file):
        """Resolve an import name to an actual file path with enhanced config support."""
        from_dir = Path(from_file).parent
        
        # Handle relative imports
        if import_name.startswith('./') or import_name.startswith('../'):
            resolved = (from_dir / import_name).resolve()
            for ext in ['.py', '.js', '.ts', '.tsx', '.jsx']:
                candidate = resolved.parent / (resolved.name + ext)
                if candidate.exists():
                    return str(candidate)
        
        # Check for TypeScript/JavaScript config files for path aliases
        config_paths = self._get_config_path_aliases()
        if config_paths:
            for alias, real_path in config_paths.items():
                if import_name.startswith(alias):
                    relative_import = import_name[len(alias):].lstrip('/')
                    resolved_path = Path(self.project_root) / real_path / relative_import
                    for ext in ['.py', '.js', '.ts', '.tsx', '.jsx']:
                        candidate = resolved_path.parent / (resolved_path.name + ext)
                        if candidate.exists():
                            return str(candidate)
        
        # Handle absolute imports within project
        project_path = Path(self.project_root)
        for potential_file in project_path.rglob(f"{import_name}.*"):
            if potential_file.suffix in SCRIPT_EXTS:
                return str(potential_file)
        
        return None
    
    def _get_config_path_aliases(self):
        """Extract path aliases from tsconfig.json or jsconfig.json."""
        config_paths = {}
        
        # Check for TypeScript config
        for config_file in ['tsconfig.json', 'jsconfig.json']:
            config_path = Path(self.project_root) / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    compiler_options = config_data.get('compilerOptions', {})
                    base_url = compiler_options.get('baseUrl', '.')
                    paths = compiler_options.get('paths', {})
                    
                    for alias, path_list in paths.items():
                        if path_list and isinstance(path_list, list):
                            # Remove wildcard and map to actual path
                            clean_alias = alias.replace('/*', '')
                            clean_path = path_list[0].replace('/*', '')
                            full_path = Path(base_url) / clean_path
                            config_paths[clean_alias] = str(full_path)
                            
                except (json.JSONDecodeError, IOError):
                    continue
                    
        return config_paths
    
    def _check_boundary_violations(self):
        """Check for architectural boundary violations."""
        rules = self.config.get('architecture_rules', [])
        
        for rule in rules:
            layer_name = rule.get('layer')
            layer_path = rule.get('path')
            cannot_be_imported_by = set(rule.get('cannot_be_imported_by', []))
            
            layer_files = [f for f in self.dependency_graph.all_files if layer_path in f]
            
            for layer_file in layer_files:
                for importing_file in self.dependency_graph.imported_by[layer_file]:
                    for forbidden_layer in cannot_be_imported_by:
                        forbidden_path = self._get_layer_path(forbidden_layer)
                        if forbidden_path and forbidden_path in importing_file:
                            self.smells.append({
                                'type': 'BOUNDARY_VIOLATION',
                                'severity': 'high',
                                'file': importing_file,
                                'target': layer_file,
                                'message': f"'{Path(importing_file).name}' is importing from '{Path(layer_file).name}'. {forbidden_layer.title()} layer must not depend on {layer_name} layer."
                            })
    
    def _get_layer_path(self, layer_name):
        """Get the path pattern for a layer name."""
        rules = self.config.get('architecture_rules', [])
        for rule in rules:
            if rule.get('layer') == layer_name:
                return rule.get('path')
        return None
    
    def _check_feature_entanglement(self):
        """Check for feature modules importing from unrelated features."""
        features_path = self.config.get('features_path', 'src/features/')
        features = defaultdict(list)
        
        for file_path in self.dependency_graph.all_files:
            if features_path in file_path:
                path_parts = Path(file_path).parts
                features_dir = features_path.replace('/', '')
                if features_dir in path_parts:
                    feature_idx = list(path_parts).index(features_dir)
                    if feature_idx + 1 < len(path_parts):
                        feature_name = path_parts[feature_idx + 1]
                        features[feature_name].append(file_path)
        
        # Check for cross-feature dependencies
        for feature_name, feature_files in features.items():
            for file_path in feature_files:
                for imported_file in self.dependency_graph.imports[file_path]:
                    for other_feature, other_files in features.items():
                        if other_feature != feature_name and imported_file in other_files:
                            self.smells.append({
                                'type': 'ENTANGLEMENT',
                            'severity': 'medium',
                            'file': file_path,
                            'target': imported_file,
                            'message': f"The '{feature_name}' feature is directly importing from the '{other_feature}' feature. Consider extracting shared logic into a common module."
                        })

    def _check_blast_radius(self):
        """Check for files with high import counts (blast radius)."""
        blast_threshold = self.config.get('blast_radius_threshold', 10)
        utility_patterns = get_configured_utility_patterns(self.config) if self.config else set()
        
        for file_path in self.dependency_graph.all_files:
            import_count = self.dependency_graph.get_import_count(file_path)
            if import_count >= blast_threshold:
                # Check if this is a utility file with expected high blast radius
                is_utility = any(self._matches_pattern(file_path, pattern) for pattern in utility_patterns)
                
                if is_utility:
                    # Lower severity for utility files - informational
                    self.smells.append({
                        'type': 'BLAST_RADIUS',
                        'severity': 'low',
                        'file': file_path,
                        'count': import_count,
                        'message': f"ℹ️  Utility '{Path(file_path).name}' is imported by {import_count} modules (as expected)."
                    })
                else:
                    # High severity for core business logic files
                    severity = 'high' if import_count >= blast_threshold * 2 else 'medium'
                    self.smells.append({
                        'type': 'BLAST_RADIUS',
                        'severity': severity,
                        'file': file_path,
                        'count': import_count,
                        'message': f"Core file '{Path(file_path).name}' is imported by {import_count} modules. Changes are high-risk."
                    })
    
    def _check_circular_dependencies(self):
        """Check for circular dependencies."""
        cycles = self.dependency_graph.find_circular_dependencies()
        
        for cycle in cycles:
            if len(cycle) > 1:  # Ignore self-cycles
                cycle_str = ' → '.join([Path(f).name for f in cycle])
                self.smells.append({
                    'type': 'CIRCULAR_DEPENDENCY',
                    'severity': 'high',
                    'files': cycle,
                    'message': f"Circular dependency detected: {cycle_str}. Break the dependency loop."                })

    def _check_ghost_files(self, file_paths):
        """Check for source files with no corresponding test files."""
        test_patterns = self.config.get('test_patterns', [
            '**/test_*.py', '**/tests/*.py', '**/*_test.py',
            '**/*.test.js', '**/*.spec.js', '**/tests/*.js'
        ])
        
        # Get untestable patterns from config
        untestable_patterns = get_configured_untestable_patterns(self.config) if self.config else set()
        source_dirs = get_configured_source_dirs(self.config) if self.config else SOURCE_CODE_DIRS
        
        test_files = set()
        for pattern in test_patterns:
            for file_path in file_paths:
                if self._matches_pattern(file_path, pattern):
                    test_files.add(file_path)
        
        for file_path in file_paths:
            if (Path(file_path).suffix.lower() in SCRIPT_EXTS and 
                self._is_source_file(file_path)):
                
                # Check if file matches untestable patterns
                is_untestable = any(self._matches_pattern(file_path, pattern) for pattern in untestable_patterns)
                if is_untestable:
                    continue
                
                # Focus primarily on files within configured source directories
                is_in_source_dir = any(source_dir in file_path for source_dir in source_dirs)
                if not is_in_source_dir:
                    continue
                
                if not self._has_corresponding_test(file_path, test_files):
                    self.smells.append({
                        'type': 'GHOST_FILE',
                        'severity': 'medium',
                        'file': file_path,
                        'message': f"'{Path(file_path).name}' has no corresponding test file."                    })

    def _check_stale_logic(self, file_paths):
        """Check for files that haven't been touched in over a year."""
        if not HAS_GIT or not self._has_git_repo():
            return
        
        stale_threshold_days = self.config.get('stale_logic_threshold_days', 365)
        cutoff_date = datetime.now() - timedelta(days=stale_threshold_days)
        source_dirs = get_configured_source_dirs(self.config) if self.config else SOURCE_CODE_DIRS
        
        try:
            repo = git.Repo(self.project_root)
            
            for file_path in file_paths:
                if (Path(file_path).suffix.lower() in SCRIPT_EXTS and 
                    self._is_source_file(file_path)):
                    
                    # Focus on files within source directories
                    is_in_source_dir = any(source_dir in file_path for source_dir in source_dirs)
                    if not is_in_source_dir:
                        continue
                    
                    try:
                        commits = list(repo.iter_commits(paths=file_path, max_count=1))
                        if commits:
                            last_modified = commits[0].committed_datetime.replace(tzinfo=None)
                            
                            if last_modified < cutoff_date:
                                self.smells.append({
                                    'type': 'STALE_LOGIC',
                                    'severity': 'medium',
                                    'file': file_path,
                                    'last_modified': last_modified.strftime('%Y-%m-%d'),
                                    'message': f"'{Path(file_path).name}' hasn't been modified since {last_modified.strftime('%Y-%m-%d')}. Consider reviewing for outdated business rules."
                                })
                    except Exception:
                        continue
        except Exception:
            pass

    def _check_high_churn(self, file_paths):
        """Check for files with high commit frequency indicating potential instability."""
        if not HAS_GIT or not self._has_git_repo():
            return
        
        churn_threshold = self.config.get('high_churn_threshold', 10)
        churn_days = self.config.get('high_churn_days', 30)
        since_date = datetime.now() - timedelta(days=churn_days)
        source_dirs = get_configured_source_dirs(self.config) if self.config else SOURCE_CODE_DIRS
        
        try:
            repo = git.Repo(self.project_root)
            
            for file_path in file_paths:
                if (Path(file_path).suffix.lower() in SCRIPT_EXTS and 
                    self._is_source_file(file_path)):
                    
                    # Focus on files within source directories
                    is_in_source_dir = any(source_dir in file_path for source_dir in source_dirs)
                    if not is_in_source_dir:
                        continue
                    
                    try:
                        commits = list(repo.iter_commits(paths=file_path, since=since_date))
                        commit_count = len(commits)
                        
                        if commit_count >= churn_threshold:
                            self.smells.append({
                                'type': 'HIGH_CHURN',
                                'severity': 'medium',
                                'file': file_path,
                                'commit_count': commit_count,
                                'message': f"'{Path(file_path).name}' has {commit_count} commits in the last {churn_days} days. High activity may indicate instability."
                            })
                    except Exception:
                        continue
        except Exception:
            pass

    def _check_stale_tests(self, file_paths):
        """Check for source files changed recently but tests not updated."""
        if not HAS_GIT or not self._has_git_repo():
            return
        
        stale_threshold_days = self.config.get('stale_test_threshold_days', 30)
        cutoff_date = datetime.now() - timedelta(days=stale_threshold_days)
        
        try:
            repo = git.Repo(self.project_root)
            
            for file_path in file_paths:
                if (Path(file_path).suffix.lower() in SCRIPT_EXTS and 
                    self._is_source_file(file_path)):
                    try:
                        commits = list(repo.iter_commits(paths=file_path, max_count=1))
                        if commits:
                            source_last_modified = commits[0].committed_datetime.replace(tzinfo=None)
                            
                            test_file = self._find_test_file(file_path, file_paths)
                            if test_file:
                                test_commits = list(repo.iter_commits(paths=test_file, max_count=1))
                                if test_commits:
                                    test_last_modified = test_commits[0].committed_datetime.replace(tzinfo=None)
                                    
                                    if (source_last_modified > cutoff_date and 
                                        test_last_modified < cutoff_date):
                                        self.smells.append({
                                            'type': 'STALE_TESTS',
                                            'severity': 'medium',
                                            'file': file_path,
                                            'test_file': test_file,
                                            'message': f"'{Path(file_path).name}' was changed recently, but its tests haven't been updated in {stale_threshold_days}+ days."
                                        })
                    except Exception:
                        continue
        except Exception:
            pass
    
    def _has_git_repo(self):
        """Check if project has a git repository."""
        if not HAS_GIT:
            return False
        try:
            git.Repo(self.project_root)
            return True
        except:
            return False
    
    def _is_source_file(self, file_path):
        """Check if file is a source file (not test, config, etc.)."""
        test_indicators = ['test', 'spec', '__tests__', 'tests']
        path_lower = file_path.lower()
        return not any(indicator in path_lower for indicator in test_indicators)
    
    def _has_corresponding_test(self, source_file, test_files):
        """Check if source file has a corresponding test file."""
        source_name = Path(source_file).stem
        
        for test_file in test_files:
            test_name = Path(test_file).stem
            if (f"test_{source_name}" in test_name or 
                f"{source_name}_test" in test_name or
                f"{source_name}.test" in test_name or
                f"{source_name}.spec" in test_name):
                return True
        return False
    
    def _find_test_file(self, source_file, all_files):
        """Find the corresponding test file for a source file."""
        source_name = Path(source_file).stem
        
        for file_path in all_files:
            if self._is_test_file(file_path):
                test_name = Path(file_path).stem
                if (f"test_{source_name}" in test_name or 
                    f"{source_name}_test" in test_name or
                    f"{source_name}.test" in test_name or
                    f"{source_name}.spec" in test_name):
                    return file_path
        return None
    
    def _is_test_file(self, file_path):
        """Check if file is a test file."""
        test_indicators = ['test', 'spec', '__tests__', 'tests']
        path_lower = file_path.lower()
        return any(indicator in path_lower for indicator in test_indicators)
    
    def _matches_pattern(self, file_path, pattern):
        """Check if file path matches a glob pattern."""
        return fnmatch.fnmatch(file_path, pattern)

# =============================================================================
# TEST COVERAGE ANALYSIS
# =============================================================================

def is_jest_project(directory):
    """Check if project uses Jest for testing."""
    package_json_path = os.path.join(directory, "package.json")
    if not os.path.exists(package_json_path):
        return False
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        return "jest" in deps or "jest" in dev_deps or "jest" in data
    except (json.JSONDecodeError, IOError):
        return False

def run_jest_coverage(directory):
    """Run Jest coverage analysis."""
    print(f"\n{BOLD}--- Jest Coverage Analysis ---{RESET}")
    print(f"{YELLOW}Running 'npm test' to generate coverage report...{RESET}")
    
    try:
        subprocess.run([
            "npm", "test"
        ], cwd=directory, check=True, capture_output=True, text=True)
        print(f"{GREEN}✔ Test run completed successfully.{RESET}")
    except FileNotFoundError:
        print(f"{RED}✖ Error: 'npm' command not found. Is Node.js installed?{RESET}")
        return None
    except subprocess.CalledProcessError:
        print(f"{RED}✖ Error: 'npm test' failed. See test output for details.{RESET}")
        return None
    
    coverage_file = os.path.join(directory, "coverage", "coverage-summary.json")
    if not os.path.exists(coverage_file):
        print(f"{RED}✖ Analysis Error: 'coverage/coverage-summary.json' not found.{RESET}")
        print(f"{YELLOW}  Hint: Ensure your jest.config.js has 'json-summary' in coverageReport.{RESET}")
        return None
    
    with open(coverage_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_coverage = data.get("total", {})
    lines_pct = total_coverage.get("lines", {}).get("pct", 0)
    color = GREEN if lines_pct >= 70 else YELLOW if lines_pct >= 50 else RED
    
    return f"  Overall Line Coverage: {color}{lines_pct:.2f}%{RESET}\n{GREY}------------------------------------{RESET}"

# =============================================================================
# AI-POWERED ANALYSIS
# =============================================================================

def configure_gemini():
    """Configure the Gemini client with API key."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(f"{RED}✖ Error: GOOGLE_API_KEY not found in environment variables or .env file.{RESET}")
        return None
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"{RED}✖ Error configuring Gemini client: {e}{RESET}")
        return None

def call_llm(prompt_messages, json_schema=None):
    """Call the Google Gemini API with optional JSON schema enforcement."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Convert OpenAI-style messages to Gemini format
        system_prompt = ""
        user_prompt = ""
        for msg in prompt_messages:
            if msg['role'] == 'system':
                system_prompt += msg['content'] + "\n\n"
            elif msg['role'] == 'user':
                user_prompt += msg['content']
        
        full_prompt = system_prompt + user_prompt
        
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 20,
        }
        
        if json_schema:
            generation_config["response_mime_type"] = "application/json"
            full_prompt += "\n\nIMPORTANT: Your entire response MUST be a single JSON object matching this schema:\n" + json.dumps(json_schema)
        
        response = model.generate_content(full_prompt, generation_config=generation_config)
        return response.text
        
    except Exception as e:
        return f'{{"error": "Error calling Google Gemini API: {str(e)}"}}'

def find_all_source_dirs(root_path, source_dirs, ignore_patterns, base_dir, config=None):
    """Recursively find all directories matching source directory names."""
    matches = []
    for dirpath, dirnames, _ in os.walk(root_path):
        # Remove ignored directories in-place
        dirnames[:] = [d for d in dirnames if not should_ignore(
            os.path.join(dirpath, d), ignore_patterns, base_dir, config)]
        for d in dirnames:
            if d in source_dirs:
                matches.append(Path(dirpath) / d)
    return matches

def find_top_script_files(directory, ignore_patterns, base_dir, count=3, config=None):
    """Find the top script files for analysis based on various criteria."""
    source_dirs = get_configured_source_dirs(config)
    all_source_dirs = find_all_source_dirs(directory, source_dirs, ignore_patterns, base_dir, config)
    
    # Store the top file found for each source directory
    top_files_per_dir = {str(path): (0, 0, None) for path in all_source_dirs}
    
    if not all_source_dirs:
        print(f"{YELLOW}Warning: No source directories found. Analyzing project root as fallback.{RESET}")
        return []
    
    now = time.time()
    for search_path in all_source_dirs:
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if not should_ignore(
                os.path.join(root, d), ignore_patterns, base_dir, config)]
            
            for name in files:
                file_path = os.path.join(root, name)
                if should_ignore(file_path, ignore_patterns, base_dir, config):
                    continue
                
                ext = Path(name).suffix
                if ext in SCRIPT_EXTS:
                    line_count = count_lines(file_path)
                    
                    # Scoring logic
                    rel_path = str(Path(file_path).relative_to(directory))
                    score = 0
                    
                    if any(part in source_dirs for part in Path(rel_path).parts): 
                        score += 30
                    if any(part in {"test", "tests", "docs", "archived"} for part in Path(rel_path).parts): 
                        score -= 20
                    
                    try:
                        if now - os.path.getmtime(file_path) < 7*24*3600: 
                            score += 15
                    except Exception: 
                        pass
                    
                    score += min(line_count // 10, 10)
                    
                    # Check if this is the new top file for its source directory
                    current_top_score = top_files_per_dir[str(search_path)][0]
                    if score > current_top_score:
                        top_files_per_dir[str(search_path)] = (score, line_count, file_path)
    
    # Collect results
    final_files = []
    for _, line_count, file_path in top_files_per_dir.values():
        if file_path:
            final_files.append((line_count, file_path))
    
    final_files.sort(key=lambda item: item[0], reverse=True)
    return final_files

def run_llm_analysis_on_top_files(directory, system_prompt, output_label, schema=None, config=None):
    """Run LLM analysis on top files in the project."""
    print(f"\n{BOLD}--- LLM-Powered {output_label} ---{RESET}")
    
    base_dir = directory
    ignore_patterns = parse_gitignore(base_dir, config)
    top_files = find_top_script_files(
        directory, ignore_patterns, base_dir, 
        count=get_configured_llm_review_file_count(config), config=config
    )
    
    if not top_files:
        print(f"{GREY}No script files found to analyze.{RESET}")
        return
    
    cache = load_cache()
    cache_updated = False
    project_context = config.get("project_context", "This file is part of a software project.")
    
    for idx, (line_count, file_path) in enumerate(top_files, 1):
        print(f"\n{BOLD}File {idx}: {os.path.relpath(file_path, directory)} ({line_count} lines){RESET}")
        
        file_hash = get_file_md5(file_path)
        cache_key = f"{file_path}|{file_hash}|{output_label}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"{GREY}  -> Using cached {output_label} result.{RESET}")
            response_str = cached_result
        else:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read(4000)  # Limit to avoid token limits
            except Exception as e:
                print(f"{RED}Could not read file: {e}{RESET}")
                continue
            
            user_prompt = (
                f"Please analyze the following file.\n\n"
                f"**File Path:** `{os.path.relpath(file_path, directory)}`\n\n"
                f"**Project Context:** {project_context}\n\n"
                f"**File Content:**\n\n```{Path(file_path).suffix[1:] or 'txt'}\n{code}\n```"
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            print(f"{GREY}  -> Sending to LLM for {output_label}. This may take a few minutes...{RESET}")
            response_str = call_llm(messages, json_schema=schema)
            cache[cache_key] = response_str
            cache_updated = True
        
        # Parse and display results
        try:
            # Try to extract JSON from markdown code blocks
            cleaned_json_str = response_str
            match = re.search(r'```(?:json)?\s*({.*})\s*```', response_str, re.DOTALL)
            if match:
                cleaned_json_str = match.group(1)
            
            response_data = json.loads(cleaned_json_str)
            
            if 'error' in response_data:
                print(f"{RED}{response_data['error']}{RESET}")
                continue
            
            print(f"{YELLOW}{output_label}:{RESET}")
            if output_label == "Review":
                print(f"  {GREEN}Positive Points:{RESET}")
                for point in response_data.get("positive_points", []):
                    print(f"    - {point}")
                print(f"  {YELLOW}Refactoring Suggestions:{RESET}")
                for sugg in response_data.get("refactoring_suggestions", []):
                    print(f"    - {BOLD}Smell:{RESET} {sugg['smell']}")
                    print(f"      {BOLD}Explanation:{RESET} {sugg['explanation']}")
                    print(f"      {BOLD}Suggestion:{RESET} {sugg['suggestion']}")
            elif output_label == "Summary":
                print(f"  {GREEN}Summary:{RESET} {response_data.get('summary', '')}")
                
        except json.JSONDecodeError:
            print(f"{RED}✖ Failed to parse LLM response as JSON.{RESET}")
            print(f"{GREY}--- Raw LLM Output ---{RESET}")
            print(response_str)
            print(f"{GREY}------------------------{RESET}")
    
    if cache_updated:
        save_cache(cache)

def run_llm_summarization(directory, config=None):
    """Run LLM-powered code summarization."""
    system_prompt = (
        "You are a senior software architect. Your task is to summarize the following code file in 2-3 sentences. "
        "Focus on its primary responsibility, its main inputs, and its key outputs or side effects. "
        "Respond ONLY with a JSON object matching the provided schema."
    )
    run_llm_analysis_on_top_files(directory, system_prompt, "Summary", CODE_SUMMARY_SCHEMA, config=config)

def run_llm_code_review(directory, config=None):
    """Run LLM-powered code review."""
    system_prompt = (
        "You are a code review expert specializing in clean code principles. Analyze the following code. "
        "Identify potential code smells such as long functions, high cyclomatic complexity, tight coupling, or poor naming. "
        "For each smell, provide a brief explanation and a suggestion for refactoring. "
        "If there are no obvious smells, say 'Code looks clean.' "
        "Respond ONLY with a JSON object matching the provided schema."
    )
    run_llm_analysis_on_top_files(directory, system_prompt, "Review", CODE_REVIEW_SCHEMA, config=config)

# =============================================================================
# ARCHITECTURAL ANALYSIS RUNNER
# =============================================================================

def run_architectural_analysis(directory, config=None, file_data=None):
    """Run comprehensive architectural analysis with optional pre-collected file data."""
    print(f"\n{BOLD}--- Architectural Health Analysis ---{RESET}")
    
    if file_data is None:
        # Collect files if not provided
        file_data = collect_all_project_files(directory, config=config)
    
    file_paths = file_data['script_files']  # Focus on script files for architectural analysis
    
    # Check for cached dependency graph
    project_hash = get_project_hash(file_paths)
    cached_graph = load_cached_dependency_graph(project_hash)
    
    if cached_graph:
        print(f"{GREY}Using cached dependency graph...{RESET}")
        sniffer = ArchitecturalSniffer(directory, config)
        sniffer.dependency_graph = cached_graph
    else:
        print(f"{GREY}Building dependency graph...{RESET}")
        sniffer = ArchitecturalSniffer(directory, config)
        sniffer._build_dependency_graph(file_paths)        # Cache the newly built graph
        save_dependency_graph_cache(sniffer.dependency_graph, project_hash)
    
    print(f"{GREY}Checking architectural patterns...{RESET}")
    sniffer._check_boundary_violations()
    sniffer._check_feature_entanglement()
    sniffer._check_blast_radius()
    sniffer._check_circular_dependencies()
    sniffer._check_ghost_files(file_data['all_files'])
    sniffer._check_stale_logic(file_data['all_files'])
    sniffer._check_high_churn(file_data['all_files'])
    sniffer._check_stale_tests(file_data['all_files'])
    
    smells = sniffer.smells
    
    if not smells:
        print(f"{GREEN}✅ No architectural issues detected! Your codebase follows good design principles.{RESET}")
        return []
    
    # Group and display smells by type
    smell_groups = defaultdict(list)
    for smell in smells:
        smell_groups[smell['type']].append(smell)
    
    for smell_type, smell_list in smell_groups.items():
        emoji_type = ARCHITECTURAL_SMELLS.get(smell_type, '⚠️  ISSUE')
        print(f"\n{RED}{emoji_type}:{RESET}")
        
        for smell in smell_list:
            severity_color = RED if smell['severity'] == 'high' else YELLOW
            print(f"  {severity_color}• {smell['message']}{RESET}")
    
    print(f"\n{GREY}Found {len(smells)} architectural issues across {len(smell_groups)} categories.{RESET}")
    return smells

def get_file_structure_from_data(directory, file_data, markdown=False, json_output=False, coverage_data=None):
    """Generate file structure analysis using pre-collected file data."""
    lines = []
    directory_totals = {}
    file_stats = []
    duplicate_files = collections.defaultdict(list)
    ext_counts = collections.Counter()
    errors = []
    
    stats = {
        "total_files": 0,
        "script_files": 0,
        "data_files": 0,
        "binary_files": 0,
        "total_lines": 0,
        "script_lines": 0,
        "data_lines": 0,
        "other_lines": 0,
    }
    
    # Build file tree structure from collected data
    def build_tree_from_files(files, base_path):
        tree = {}
        for file_path in files:
            try:
                rel_path = Path(file_path).relative_to(base_path)
                parts = rel_path.parts
                current_level = tree
                
                # Build nested structure
                for i, part in enumerate(parts[:-1]):
                    if part not in current_level:
                        current_level[part] = {}
                    current_level = current_level[part]
                
                # Add file
                if len(parts) > 0:
                    filename = parts[-1]
                    current_level[filename] = file_path
            except ValueError:
                continue  # Skip files outside base path
        return tree
    
    def render_tree(tree, prefix="", path_so_far=""):
        items = sorted(tree.items())
        dirs = [(k, v) for k, v in items if isinstance(v, dict)]
        files = [(k, v) for k, v in items if not isinstance(v, dict)]
        
        # Render directories first
        for i, (name, subtree) in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1) and len(files) == 0
            pointer = "└── " if is_last_dir else "├── "
            lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET}")
            
            extension = "    " if is_last_dir else "│   "
            render_tree(subtree, prefix + extension, os.path.join(path_so_far, name))
        
        # Render files
        for i, (name, file_path) in enumerate(files):
            is_last = (i == len(files) - 1)
            pointer = "└── " if is_last else "├── "
            
            stats["total_files"] += 1
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            ext_counts[ext] += 1
            
            duplicate_files[name].append(os.path.join(path_so_far, name))
            
            if is_binary_file(file_path):
                stats["binary_files"] += 1
                lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} {GREY}(binary file){RESET}")
                file_stats.append({
                    "path": os.path.join(path_so_far, name),
                    "lines": 0,
                    "type": "binary",
                    "size": get_file_size(file_path)
                })
            else:
                line_count = count_lines(file_path)
                stats["total_lines"] += line_count
                
                if ext in SCRIPT_EXTS:
                    stats["script_files"] += 1
                    stats["script_lines"] += line_count
                    file_type = "script"
                    
                    if line_count >= FILE_DANGER_THRESHOLD:
                        line_color = RED
                        warning = " (!!! TOO LARGE !!!)"
                    elif line_count >= FILE_WARNING_THRESHOLD:
                        line_color = YELLOW
                        warning = " (! approaching limit !)"
                    else:
                        line_color = RESET
                        warning = ""
                    lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} {line_color}({line_count} lines){warning}{RESET}")
                elif ext in DATA_EXTS:
                    stats["data_files"] += 1
                    stats["data_lines"] += line_count
                    file_type = "data"
                    lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} ({line_count} lines)")
                else:
                    stats["other_lines"] += line_count
                    file_type = "other"
                    lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} ({line_count} lines)")
                
                file_stats.append({
                    "path": os.path.join(path_so_far, name),
                    "lines": line_count,
                    "type": file_type,
                    "size": get_file_size(file_path)
                })
    
    # Start rendering
    lines.append(f"{os.path.basename(directory)}/")
    tree = build_tree_from_files(file_data['all_files'], directory)
    render_tree(tree)
    
    # Add coverage data if available
    if coverage_data:
        lines.append(f"\n{BOLD}--- Jest Test Coverage ---{RESET}")
        lines.append(coverage_data)
    
    # Format output based on requested format
    if markdown:
        md = []
        md.append("## File Tree\n")
        md.append("```")
        md.append(remove_ansi_colors("\n".join(lines)))
        md.append("```")
        if coverage_data:
            md.append("\n## Test Coverage\n")
            md.append(f"```\n{remove_ansi_colors(coverage_data)}\n```")
        return "\n".join(md)
    elif json_output:
        if coverage_data:
            stats['coverage_report'] = remove_ansi_colors(coverage_data)
        return json.dumps({"stats": stats}, indent=2)
    else:
        return "\n".join(lines)

# =============================================================================
# MAIN FILE STRUCTURE ANALYSIS
# =============================================================================

def get_file_structure(directory, ignore_patterns=None, markdown=False, json_output=False, coverage_data=None):
    """Generate file structure analysis with various output formats."""
    if ignore_patterns is None:
        ignore_patterns = parse_gitignore(directory)
    
    lines = []
    directory_totals = {}
    file_stats = []
    base_dir = directory
    duplicate_files = collections.defaultdict(list)
    ext_counts = collections.Counter()
    top_level_files = set()
    errors = []
    
    stats = {
        "total_files": 0,
        "script_files": 0,
        "data_files": 0,
        "binary_files": 0,
        "total_lines": 0,
        "script_lines": 0,
        "data_lines": 0,
        "other_lines": 0,
    }
    
    def walk_dir(path, prefix="", depth=0):
        dirs, files = [], []
        dir_total_lines = 0
        rel_path = os.path.relpath(path, directory)
        if rel_path == ".":
            rel_path = os.path.basename(directory)
        
        # Collect top-level files
        if depth == 0:
            try:
                for entry in sorted(os.listdir(path)):
                    entry_path = os.path.join(path, entry)
                    if os.path.isfile(entry_path):
                        top_level_files.add(entry)
            except (OSError, IOError):
                pass
        
        # Process directory contents
        try:
            for entry in sorted(os.listdir(path)):
                entry_path = os.path.join(path, entry)
                if should_ignore(entry_path, ignore_patterns, base_dir):
                    continue
                if os.path.isdir(entry_path):
                    dirs.append(entry)
                else:
                    files.append(entry)
        except PermissionError:
            lines.append(f"{prefix}├── {RED}Permission denied{RESET}")
            errors.append({"path": path, "error": "Permission denied"})
            return 0
        except (OSError, IOError) as e:
            lines.append(f"{prefix}├── Error: {str(e)}")
            errors.append({"path": path, "error": str(e)})
            return 0
        
        # Process directories
        pointers = ["├── "] * (len(dirs) - 1) + ["└── "] if dirs else []
        for pointer, name in zip(pointers, dirs):
            full_path = os.path.join(path, name)
            subdir_rel_path = os.path.join(rel_path, name) if rel_path != "." else name
            
            try:
                if not os.listdir(full_path):
                    lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET} {GREY}(Empty){RESET}")
                    subdir_lines = 0
                else:
                    lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET}")
                    extension = "│   " if pointer == "├── " else "    "
                    subdir_lines = walk_dir(full_path, prefix + extension, depth+1)
                
                if subdir_lines > 0:
                    directory_totals[subdir_rel_path] = subdir_lines
                dir_total_lines += subdir_lines
                
            except PermissionError:
                lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET} {GREY}(Permission denied){RESET}")
            except (OSError, IOError) as e:
                lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET} {GREY}(Error: {str(e)}){RESET}")
        
        # Process files
        for name in files:
            file_path = os.path.join(path, name)
            stats["total_files"] += 1
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            ext_counts[ext] += 1
            file_size = get_file_size(file_path)
            
            duplicate_files[name].append(os.path.join(rel_path, name))
            
            is_binary = is_binary_file(file_path)
            
            if is_binary:
                stats["binary_files"] += 1
                file_stats.append({
                    "path": os.path.join(rel_path, name), 
                    "lines": 0, 
                    "type": "binary", 
                    "size": file_size
                })
                continue
            
            line_count = count_lines(file_path)
            dir_total_lines += line_count
            stats["total_lines"] += line_count
            
            if ext in SCRIPT_EXTS:
                stats["script_files"] += 1
                stats["script_lines"] += line_count
                file_type = "script"
            elif ext in DATA_EXTS:
                stats["data_files"] += 1
                stats["data_lines"] += line_count
                file_type = "data"
            else:
                stats["other_lines"] += line_count
                file_type = "other"
            
            file_stats.append({
                "path": os.path.join(rel_path, name),
                "lines": line_count,
                "type": file_type,
                "size": file_size
            })
          # Display files with appropriate formatting
        pointers = ["├── "] * (len(files) - 1) + ["└── "] if files else []
        for pointer, name in zip(pointers, files):
            file_path = os.path.join(path, name)
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            
            if is_binary_file(file_path):
                lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} {GREY}(binary file){RESET}")
            else:
                line_count = count_lines(file_path)
                if ext in SCRIPT_EXTS:
                    if line_count >= FILE_DANGER_THRESHOLD:
                        line_color = RED
                        warning = " (!!! TOO LARGE !!!)"  # Yes, this will hilariously flag itself 😄
                    elif line_count >= FILE_WARNING_THRESHOLD:
                        line_color = YELLOW
                        warning = " (! approaching limit !)"
                    else:
                        line_color = RESET
                        warning = ""
                    lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} {line_color}({line_count} lines){warning}{RESET}")
                else:
                    lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} ({line_count} lines)")
        
        return dir_total_lines
    
    # Start the analysis
    lines.append(f"{os.path.basename(directory)}/")
    walk_dir(directory)
    
    # Add coverage data if available
    if coverage_data:
        lines.append(f"\n{BOLD}--- Jest Test Coverage ---{RESET}")
        lines.append(coverage_data)
    
    # Format output based on requested format
    if markdown:
        md = []
        md.append("## File Tree\n")
        md.append("```")
        md.append(remove_ansi_colors("\n".join(lines)))
        md.append("```")
        if coverage_data:
            md.append("\n## Test Coverage\n")
            md.append(f"```\n{remove_ansi_colors(coverage_data)}\n```")
        return "\n".join(md)
    elif json_output:
        if coverage_data:
            stats['coverage_report'] = remove_ansi_colors(coverage_data)
        return json.dumps({"stats": stats}, indent=2)
    else:
        return "\n".join(lines)

# =============================================================================
# HTML REPORT GENERATION
# =============================================================================

def generate_html_report(directory, text_output, config, coverage_report):
    """Generate an HTML report of the analysis."""
    try:
        from jinja2 import Template
    except ImportError:
        print(f"{RED}Jinja2 is required for HTML report generation. Install with 'pip install jinja2'.{RESET}")
        return
    
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Project Analyzer Report</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f8f8f8; color: #222; }
            .container { max-width: 900px; margin: 2em auto; background: #fff; padding: 2em; border-radius: 8px; box-shadow: 0 2px 8px #0001; }
            h1 { color: #2d5be3; }
            pre { background: #f4f4f4; padding: 1em; border-radius: 6px; overflow-x: auto; }
            .section { margin-bottom: 2em; }
            .coverage { background: #e8f5e9; padding: 1em; border-radius: 6px; }
            .timestamp { color: #888; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Project Analyzer Report</h1>
            <div class="timestamp">Generated: {{ timestamp }}</div>
            <div class="section">
                <h2>File Tree & Stats</h2>
                <pre>{{ file_tree }}</pre>
            </div>
            {% if coverage %}
            <div class="section coverage">
                <h2>Test Coverage</h2>
                <pre>{{ coverage }}</pre>
            </div>
            {% endif %}
            {% if config %}
            <div class="section">
                <h2>Analyzer Config</h2>
                <pre>{{ config }}</pre>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    
    template = Template(html_template)
    html = template.render(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        file_tree=remove_ansi_colors(text_output),
        coverage=remove_ansi_colors(coverage_report) if coverage_report else None,
        config=json.dumps(config, indent=2) if config else None
    )
    
    out_path = os.path.join(directory, "analyzer-report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{GREEN}HTML report generated at: {out_path}{RESET}")

# =============================================================================
# CENTRALIZED FILE COLLECTION
# =============================================================================

def collect_all_project_files(directory, ignore_patterns=None, config=None):
    """
    Centralized file collection - walk the filesystem once and return comprehensive data.
    This replaces multiple os.walk() calls throughout the application.
    """
    if ignore_patterns is None:
        ignore_patterns = parse_gitignore(directory, config)
    
    all_files = []
    all_directories = []
    source_directories = set()
    script_files = []
    
    source_dirs = get_configured_source_dirs(config)
    
    for root, dirs, files in os.walk(directory):
        # Remove ignored directories in-place
        dirs[:] = [d for d in dirs if not should_ignore(
            os.path.join(root, d), ignore_patterns, directory, config)]
        
        # Track directories
        for d in dirs:
            dir_path = os.path.join(root, d)
            all_directories.append(dir_path)
            
            # Check if this is a source directory
            if d in source_dirs:
                source_directories.add(dir_path)
        
        # Track files
        for file in files:
            file_path = os.path.join(root, file)
            if not should_ignore(file_path, ignore_patterns, directory, config):
                all_files.append(file_path)
                
                # Track script files separately for efficiency
                ext = Path(file_path).suffix.lower()
                if ext in SCRIPT_EXTS:
                    script_files.append(file_path)
    
    return {
        'all_files': all_files,
        'all_directories': all_directories,
        'source_directories': list(source_directories),
        'script_files': script_files,
        'ignore_patterns': ignore_patterns
    }

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the Project Analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Project Analyzer - Advanced Architectural Health Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python project_analyzer.py                    # Run architectural analysis (default)
  python project_analyzer.py --tree             # Show file tree structure  
  python project_analyzer.py --full             # Run all analyses
  python project_analyzer.py --coverage         # Include test coverage
  python project_analyzer.py --review           # AI-powered code review
  python project_analyzer.py --markdown         # Output as Markdown"""
    )
    parser.add_argument('--tree', action='store_true', 
                       help='Show file tree structure')
    parser.add_argument('--markdown', action='store_true', 
                       help='Output results in Markdown format')
    parser.add_argument('--json', action='store_true', 
                       help='Output results in JSON format')
    parser.add_argument('--coverage', action='store_true', 
                       help='Run test coverage analysis if possible')
    parser.add_argument('--summarize', action='store_true', 
                       help='Use AI to summarize key files')
    parser.add_argument('--review', action='store_true', 
                       help='Use AI to review key files for code smells')
    parser.add_argument('--html-report', action='store_true', 
                       help='Generate an HTML report')
    parser.add_argument('--architecture', action='store_true', 
                       help='Run architectural health analysis (same as default)')
    parser.add_argument('--full', action='store_true', 
                       help='Run all analyses (structure, coverage, architecture)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Configure AI if needed
    if args.summarize or args.review:
        if not configure_gemini():
            sys.exit(1)
    
    directory = PROJECT_ROOT
    
    # Centralized file collection - walk filesystem once
    print(f"{GREY}Collecting project files...{RESET}")
    file_data = collect_all_project_files(directory, config=config)
    
    # Handle AI-only modes
    if args.summarize:
        run_llm_summarization(directory, config=config)
        return
    
    if args.review:
        run_llm_code_review(directory, config=config)
        return
    
    # If no flags are given, run architectural analysis by default (the "alerter" mode)
    if not any([args.tree, args.architecture, args.full, args.coverage, args.markdown, args.json, args.html_report]):
        run_architectural_analysis(directory, config=config, file_data=file_data)
        return
    
    # Handle architectural analysis
    if args.architecture or args.full:
        run_architectural_analysis(directory, config=config, file_data=file_data)
        if args.architecture and not args.full:
            return
    
    # Handle coverage analysis
    coverage_report = None
    if args.coverage or args.full:
        if is_jest_project(directory):
            coverage_report = run_jest_coverage(directory)
        else:
            print(f"{GREY}(No supported test coverage found for this project.){RESET}")
    
    # Generate main structure analysis (only if --tree flag or --full)
    if args.tree or args.full:
        final_output = get_file_structure_from_data(
            directory,
            file_data,
            markdown=args.markdown,
            json_output=args.json,
            coverage_data=coverage_report
        )
        print(final_output)
    
    # Generate HTML report if requested
    if args.html_report:
        try:
            if args.tree or args.full:
                generate_html_report(directory, final_output, config, coverage_report)
            else:
                # Generate a basic report without file tree
                basic_output = f"Architectural Analysis completed for {directory}"
                generate_html_report(directory, basic_output, config, coverage_report)
        except Exception as e:
            print(f"{RED}Failed to generate HTML report: {e}{RESET}")

if __name__ == "__main__":
    main()
