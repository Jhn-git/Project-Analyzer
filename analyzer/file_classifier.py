"""
file_classifier.py

This module provides the FileClassifier class for classifying files based on their
purpose or type within a project, such as source code, test files, documentation, etc.
It is designed to be a missing dependency that GitAnalyzer needs.
"""

import os
import fnmatch
from typing import List, Dict, Any
from .config import DEFAULT_CONFIG

class FileClassifier:
    """
    Classifies files based on their type or purpose within a project.

    This classifier helps in categorizing files (e.g., source code, tests, docs)
    which can be crucial for various analysis tasks, such as determining
    code churn in specific areas or identifying stale tests.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the FileClassifier with configuration settings.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration settings,
                                     including patterns for different file types.
                                     Expected keys might include 'source_patterns',
                                     'test_patterns', 'doc_patterns', etc.
        """
        self.config = config
        self.source_patterns = config.get("source_file_patterns", DEFAULT_CONFIG["source_file_patterns"])
        self.test_patterns = config.get("test_file_patterns", DEFAULT_CONFIG["test_file_patterns"])
        self.documentation_patterns = config.get("documentation_file_patterns", DEFAULT_CONFIG["documentation_file_patterns"])
        self.config_patterns = config.get("config_file_patterns", DEFAULT_CONFIG["config_file_patterns"])
        self.ignore_patterns = config.get("ignore_file_patterns", DEFAULT_CONFIG["ignore_file_patterns"])
        self.project_lifecycle_patterns = config.get("project_lifecycle_patterns", DEFAULT_CONFIG["project_lifecycle_patterns"])

    def classify_file(self, file_path: str) -> List[str]:
        """
        Classifies a given file path into one or more categories.

        Args:
            file_path (str): The absolute or relative path to the file.

        Returns:
            List[str]: A list of categories the file belongs to (e.g., ['source', 'python', 'backend']).
                       Returns an empty list if no classification matches.
        """
        classifications = []
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[1].lower()

        # Check ignore patterns first
        if self._matches_pattern(file_path, self.ignore_patterns):
            return []  # Ignore this file

        # More specific classifications first
        if self._matches_pattern(file_path, self.project_lifecycle_patterns):
            classifications.append("project_lifecycle")
        if self._matches_pattern(file_path, self.documentation_patterns):
            classifications.append("documentation")
        if self._matches_pattern(file_path, self.config_patterns):
            classifications.append("config")
        if self._matches_pattern(file_path, self.test_patterns):
            classifications.append("test")
        if self._matches_pattern(file_path, self.source_patterns):
            classifications.append("source")

        # Basic language classification based on extension
        # Also classify as 'source' if it's a recognized programming language
        if file_extension == ".py":
            classifications.append("python")
            if "source" not in classifications and "test" not in classifications:
                classifications.append("source")
        elif file_extension in [".js", ".ts", ".jsx", ".tsx"]:
            classifications.append("javascript_typescript")
            if "source" not in classifications and "test" not in classifications:
                classifications.append("source")
        elif file_extension in [".java", ".jar"]:
            classifications.append("java")
            if "source" not in classifications and "test" not in classifications:
                classifications.append("source")
        elif file_extension in [".c", ".cpp", ".h", ".hpp"]:
            classifications.append("c_cpp")
            if "source" not in classifications and "test" not in classifications:
                classifications.append("source")
        elif file_extension == ".cs":
            classifications.append("csharp")
            if "source" not in classifications and "test" not in classifications:
                classifications.append("source")
        elif file_extension == ".go":
            classifications.append("go")
            if "source" not in classifications and "test" not in classifications:
                classifications.append("source")
        elif file_extension == ".rb":
            classifications.append("ruby")
            if "source" not in classifications and "test" not in classifications:
                classifications.append("source")
        elif file_extension == ".php":
            classifications.append("php")
            if "source" not in classifications and "test" not in classifications:
                classifications.append("source")
        elif file_extension in [".html", ".htm", ".css", ".scss", ".less"]:
            classifications.append("web_frontend")
        elif file_extension in [".json", ".yaml", ".yml", ".xml"]:
            classifications.append("data_config")


        # Deduplicate and return
        return sorted(list(set(classifications)))

    def _matches_pattern(self, file_path: str, patterns: List[str]) -> bool:
        """
        Checks if a file path matches any of the given glob patterns.

        Args:
            file_path (str): The path to the file.
            patterns (List[str]): A list of glob patterns to match against.

        Returns:
            bool: True if the file path matches any pattern, False otherwise.
        """
        file_name = os.path.basename(file_path)

        for pattern in patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True
        return False
