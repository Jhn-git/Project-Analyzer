"""
Configuration constants and settings for Project Analyzer.
"""

import os
import json
import threading
from pathlib import Path

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
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    # WorkspaceResolver settings
    "workspace_markers": [
        ".git", "pyproject.toml", "requirements.txt", "package.json",
        "pom.xml", "build.gradle", "Makefile", ".project", "README.md"
    ],

    # FileClassifier settings
    "source_file_patterns": [
        "*.py", "*.js", "*.ts", "*.java", "*.go", "*.cs", "*.rb", "*.php",
        "*.c", "*.cpp", "*.h", "*.hpp", "*.swift", "*.kt", "*.dart"
    ],
    "test_file_patterns": [
        "test_*.py", "*_test.py", "*.spec.js", "*.test.js",
        "*.spec.ts", "*.test.ts", "*Test.java", "*Tests.cs"
    ],
    "documentation_file_patterns": ["*.md", "*.txt", "README*", "LICENSE*", "CONTRIBUTING*"],
    "config_file_patterns": [
        "*.json", "*.yaml", "*.yml", "*.xml", "*.ini", "*.toml", "*.cfg",
        "config", ".env", "env.*", "settings.py"
    ],
    "ignore_file_patterns": [],
    "project_lifecycle_patterns": [
        ".gitignore", "setup.py", "requirements.txt", "Dockerfile",
        "docker-compose.yml", "package.json", "webpack.config.js"
    ],
    
    # GitAnalyzer settings
    "stale_logic_threshold_days": 365,
    "high_churn_days": 30,
    "high_churn_threshold": 10,
    
    # Main analysis settings
    "source_dirs": ["src", "app", "main"],
    "exclude_dirs": [
        "node_modules", ".git", ".vscode", ".idea", "dist", "coverage",
        "venv", ".venv", "__pycache__", "build", "target"
    ],
    "exclude_patterns": [],
    "llm_review_file_count": 3,
    "untestable_patterns": [],
    "utility_patterns": []
}


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
    return set(config.get("source_dirs", DEFAULT_CONFIG["source_dirs"]))

def get_configured_excluded_dirs(config):
    """Get configured excluded directories."""
    return set(config.get("exclude_dirs", DEFAULT_CONFIG["exclude_dirs"]))

def get_configured_exclude_patterns(config):
    """Get configured exclusion patterns."""
    return set(config.get("exclude_patterns", DEFAULT_CONFIG["exclude_patterns"]))

def get_configured_llm_review_file_count(config):
    """Get number of files to review with LLM."""
    return int(config.get("llm_review_file_count", DEFAULT_CONFIG["llm_review_file_count"]))

def get_configured_untestable_patterns(config):
    """Get configured untestable file patterns."""
    return set(config.get("untestable_patterns", DEFAULT_CONFIG["untestable_patterns"]))

def get_configured_utility_patterns(config):
    """Get configured utility file patterns."""
    return set(config.get("utility_patterns", DEFAULT_CONFIG["utility_patterns"]))
