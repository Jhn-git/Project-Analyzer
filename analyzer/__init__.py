"""
Project Analyzer - Advanced Architectural Health Monitoring

A comprehensive tool that analyzes project structure, detects architectural patterns,
and provides AI-powered insights for code quality improvement.
"""

__version__ = "1.0.0"
__author__ = "Project Analyzer Team"

from .main import main
from .architectural_analysis import ArchitecturalSniffer
from .dependency_analysis import DependencyGraph, ImportParser
from .file_classifier import FileClassifier
from .workspace_resolver import WorkspaceResolver
from .pattern_analysis import PatternAnalyzer
from .git_analysis import GitAnalyzer
from .config import *
from .decorators import cache_result
from .smell_factory import create_smell

__all__ = [
    'main',
    'ArchitecturalSniffer',
    'DependencyGraph',
    'ImportParser',
    'FileClassifier',
    'WorkspaceResolver',
    'PatternAnalyzer',
    'GitAnalyzer',
    'cache_result',
    'create_smell'
]
