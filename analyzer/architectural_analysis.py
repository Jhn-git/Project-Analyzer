#
# Pseudocode for refactored analyzer/architectural_analysis.py
#

from pathlib import Path
import time
import os
from typing import List, Dict, Any, Optional

# --- Main project dependencies ---
from .dependency_analysis import DependencyGraph, ImportParser, load_cached_dependency_graph, save_dependency_graph_cache
from .utils import load_cache, save_cache, get_project_hash
from .config import get_configured_source_dirs, SCRIPT_EXTS, load_config

# --- New/Refactored module imports ---
from .file_classifier import FileClassifier
from .workspace_resolver import WorkspaceResolver
from .pattern_analysis import PatternAnalyzer
from .git_analysis import GitAnalyzer
from .smell_factory import create_smell

# Keep backward compatibility
class ArchitecturalSniffer:
    """
    Orchestrates the architectural analysis of a project.
    Delegates specific tasks like file classification, dependency resolution,
    and pattern detection to specialized modules.
    """
    CACHE_EXPIRY_SECONDS = 3600  # 1 hour

    def __init__(self, project_root: str, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the ArchitecturalSniffer.

        Args:
            project_root (str): The project root path.
            config (Optional[Dict[str, Any]]): Configuration dictionary. If None,
                                                it will be loaded from default config.
        """
        self.project_root = Path(project_root)
        self.config = config if config is not None else load_config()
        self.smells = []

        # Initialize core resolvers and classifiers
        self.file_classifier = FileClassifier(self.config)
        self.workspace_resolver = WorkspaceResolver(self.config.get("workspace_markers"))

        # Ensure resolver knows about project root
        self.workspace_resolver.find_project_root(str(self.project_root))

        # These are initialized later, as they depend on the dependency graph or other context
        self.dependency_graph: Optional[DependencyGraph] = None
        self.pattern_analyzer: Optional[PatternAnalyzer] = None
        self.git_analyzer: Optional[GitAnalyzer] = None

    def analyze_architecture(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Public API to run all architectural analyses.
        This method preserves the original public signature and caching behavior.

        Args:
            file_paths (List[str]): A list of file paths (absolute or relative to project root)
                                    to include in the analysis.

        Returns:
            List[Dict[str, Any]]: A list of detected architectural smells.
        """
        # Ensure all file_paths are absolute and within the project root
        absolute_file_paths = []
        for p in file_paths:
            if Path(p).is_absolute():
                abs_p = Path(p)
            else:
                # Use the resolver to get a consistent absolute path
                resolved_p = self.workspace_resolver.get_absolute_path(p)
                if not resolved_p:
                    print(f"Warning: Could not resolve path for {p}. Skipping.")
                    continue
                abs_p = Path(resolved_p)

            if not self.workspace_resolver.is_path_in_project(str(abs_p)):
                print(f"Warning: File {p} is not within the detected project root {self.project_root}. Skipping.")
                continue
            absolute_file_paths.append(abs_p)

        project_hash = get_project_hash([str(p) for p in absolute_file_paths])
        cache_key = f"architectural_analysis:{project_hash}"

        # 1. Check cache first
        cache = load_cache()
        cached_result = cache.get(cache_key)
        if cached_result and (time.time() - cached_result.get('timestamp', 0) < self.CACHE_EXPIRY_SECONDS):
            print("Using cached architectural analysis.")
            self.smells = cached_result['smells']
            return self.smells

        # 2. Build dependency graph
        self.dependency_graph = self._build_dependency_graph(absolute_file_paths)

        # 3. Initialize analyzers that require the graph
        # Note: PatternAnalyzer now takes dependency_graph, file_classifier, and config
        self.pattern_analyzer = PatternAnalyzer(self.config)
        self.git_analyzer = GitAnalyzer(self.project_root, self.config, self.file_classifier)

        # 4. Run all analysis checks by delegating to specialists
        # Prepare inputs for pattern analysis
        file_classifications = {
            str(p): self.file_classifier.classify_file(str(p))
            for p in absolute_file_paths
        }
        # Dummy code_metrics for now, will be populated by other analyzers or future integrations
        code_metrics = {}

        pattern_smells = self.pattern_analyzer.analyze_patterns(
            self.dependency_graph.imports, # Pass the imports dictionary
            file_classifications,
            code_metrics
        )

        # Convert pattern_smells (dict) into a list of smell objects/dicts if needed for consistency
        # For now, let's assume analyze_patterns returns a dict of patterns, not "smells" directly.
        # We need to adapt this to the expected output format of analyze_architecture.
        # For simplicity, let's convert identified patterns into smell-like dicts.
        converted_pattern_smells = self._convert_patterns_to_smells(pattern_smells)


        git_smells = []
        if self.git_analyzer.has_git_repo():
            git_smells.extend(self.git_analyzer.check_stale_logic(absolute_file_paths))
            git_smells.extend(self.git_analyzer.check_high_churn(absolute_file_paths))
            git_smells.extend(self.git_analyzer.check_stale_tests(absolute_file_paths))

        self.smells = converted_pattern_smells + git_smells

        # 5. Cache the new results
        cache[cache_key] = {'smells': self.smells, 'timestamp': time.time()}
        save_cache(cache)
        print("Architectural analysis cached for future runs.")

        return self.smells

    def _convert_patterns_to_smells(self, patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Converts detected architectural patterns into a list of architectural "smell" dictionaries.
        This provides a consistent output format for `analyze_architecture`.
        """
        smells_list = []
        for pattern_name, details in patterns.items():
            if not details.get("detected"):
                continue

            smell_type = pattern_name.upper().replace(" ", "_")
            
            if pattern_name == "cyclic_dependencies" and details.get("details"):
                for cycle in details["details"]:
                    # Format the cycle path to be more readable
                    path_str = " -> ".join([os.path.basename(p) for p in cycle])
                    smells_list.append(create_smell(
                        smell_type="CIRCULAR_DEPENDENCY",
                        file_path=cycle[0],
                        message=f"Circular dependency detected: {path_str}",
                        severity="High",
                        category="Architectural Smell"
                    ))
            elif pattern_name == "unclassified_files" and details.get("details"):
                 for file_path in details["details"]:
                    smells_list.append(create_smell(
                        smell_type="UNCLASSIFIED_FILE",
                        file_path=file_path,
                        message=f"File is unclassified: {os.path.basename(file_path)}",
                        severity="Low",
                        category="Project Structure"
                    ))
            else:
                smell_description = f"Detected {pattern_name}."
                if "details" in details:
                    smell_description += f" Details: {details['details']}"
                elif "count" in details:
                    smell_description += f" Count: {details['count']}"
                
                smells_list.append(create_smell(
                    smell_type=smell_type,
                    file_path="N/A",
                    message=smell_description,
                    severity="Medium",
                    category="Architectural Pattern"
                ))
        return smells_list

    def _build_dependency_graph(self, file_paths: List[Path]) -> DependencyGraph:
        """
        Builds the dependency graph using the file classifier and workspace resolver.
        Includes caching logic for the graph itself.
        """
        graph = DependencyGraph()
        project_hash = get_project_hash([str(p) for p in file_paths])

        cached_graph = load_cached_dependency_graph(project_hash)
        if cached_graph:
            print("Using cached dependency graph.")
            return cached_graph

        print("Building dependency graph...")
        all_project_files_set = {str(p) for p in file_paths} # Convert to string for set lookups

        source_dirs = get_configured_source_dirs(self.config)
        for file_path in file_paths:
            # Use FileClassifier to determine if it's a source file
            classifications = self.file_classifier.classify_file(str(file_path))
            if "source" in classifications:
                # ImportParser needs the project root for absolute imports and path resolution
                imports = ImportParser.get_file_imports(str(file_path), str(self.project_root))
                for import_name in imports:
                    # Delegate import resolution to a helper, using WorkspaceResolver
                    resolved_path = self.workspace_resolver.resolve_import(
                        import_name,
                        file_path,
                        source_dirs,
                        SCRIPT_EXTS
                    )
                    if resolved_path and str(resolved_path) in all_project_files_set:
                        graph.add_dependency(file_path, resolved_path)

        save_dependency_graph_cache(graph, project_hash)
        print("Dependency graph cached.")
        return graph