"""
Utility functions for file operations, caching, and gitignore handling.
"""

import os
import re
import time
import json
import hashlib
import fnmatch
import threading
from pathlib import Path
from collections import defaultdict

from .config import (
    CACHE_FILE, _cache_lock, EXCLUDED_DIRS, 
    get_configured_excluded_dirs, get_configured_exclude_patterns,
    SCRIPT_EXTS
)

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
            chunk = f.read(1024)
            return b'\x00' in chunk
    except (OSError, IOError):
        return True

def read_file_content(file_path: str) -> str:
    """
    Reads the content of a file with robust error handling.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The content of the file, or an empty string if reading fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except (FileNotFoundError, IOError, UnicodeDecodeError):
        return ""

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
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
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
            stat = os.stat(file_path)
            file_hashes.append(f"{file_path}:{stat.st_mtime}:{stat.st_size}")
        except (OSError, IOError):
            file_hashes.append(f"{file_path}:missing")
    
    combined = '|'.join(file_hashes)
    return hashlib.md5(combined.encode()).hexdigest()

def load_cached_dependency_graph(project_hash):
    """Load cached dependency graph if it exists and is valid."""
    from .dependency_analysis import DependencyGraph
    
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

def clear_cache():
    """Clear the analysis cache."""
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print(f"Cache cleared: {CACHE_FILE}")
        else:
            print("No cache file found to clear")
    except Exception as e:
        print(f"Error clearing cache: {e}")

# =============================================================================
# FILE COLLECTION UTILITIES
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
    
    from .config import get_configured_source_dirs
    source_dirs = get_configured_source_dirs(config) if config else {"src", "app", "main"}
    
    for root, dirs, files in os.walk(directory):
        # Remove ignored directories in-place
        dirs[:] = [d for d in dirs if not should_ignore(
            os.path.join(root, d), ignore_patterns, directory, config)]
        
        # Track directories
        for d in dirs:
            dir_path = os.path.join(root, d)
            all_directories.append(dir_path)
            if d in source_dirs:
                source_directories.add(dir_path)
        
        # Track files
        for file in files:
            file_path = os.path.join(root, file)
            if not should_ignore(file_path, ignore_patterns, directory, config):
                all_files.append(file_path)
                
                # Track script files
                if Path(file).suffix.lower() in SCRIPT_EXTS:
                    script_files.append(file_path)
    
    return {
        'all_files': all_files,
        'all_directories': all_directories,
        'source_directories': list(source_directories),
        'script_files': script_files,
        'ignore_patterns': ignore_patterns
    }
