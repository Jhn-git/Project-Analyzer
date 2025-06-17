"""
pattern_analysis.py

This module provides the PatternAnalyzer class, responsible for detecting
common architectural patterns and anti-patterns within a codebase.
It leverages insights from dependency analysis, file classification, and other
metrics to identify structural characteristics of the project.
"""

import os
from typing import Dict, Any, List, Optional

class PatternAnalyzer:
    """
    Analyzes a codebase to detect architectural patterns and anti-patterns.

    This class works with various inputs like dependency graphs, file classifications,
    and potentially code metrics to identify common architectural styles
    (e.g., layered, microservices) or problematic structures (e.g., cyclic dependencies).
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the PatternAnalyzer with configuration settings.

        Args:
            config (Dict[str, Any]): A dictionary containing configuration settings
                                     relevant to pattern detection, such as thresholds
                                     or definitions of certain patterns.
        """
        self.config = config
        self.patterns = config.get("architectural_patterns", {})

    def analyze_patterns(
        self,
        dependency_graph,
        file_classifications: Dict[str, List[str]],
        code_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Performs a comprehensive analysis to detect architectural patterns.

        Args:
            dependency_graph (Dict[str, List[str]]): A graph representing file dependencies,
                                                      where keys are file paths and values
                                                      are lists of files they depend on.
            file_classifications (Dict[str, List[str]]): A mapping of file paths to their
                                                          classified types (e.g., 'source', 'test').
            code_metrics (Dict[str, Any]): A dictionary containing various code metrics
                                            (e.g., cyclomatic complexity, lines of code per file).

        Returns:
            Dict[str, Any]: A dictionary containing the detected patterns and their details.
                            Example: {"layered_architecture": {"detected": True, "layers": [...]},
                                      "cyclic_dependencies": {"count": 5, "details": [...]}}
        """
        detected_patterns = {}
        
        # Convert defaultdict to regular dict for processing
        graph_dict = {}
        if hasattr(dependency_graph, 'items'):
            # It's a defaultdict or dict-like object
            for key, value in dependency_graph.items():
                if hasattr(value, '__iter__') and not isinstance(value, str):
                    graph_dict[key] = list(value)
                else:
                    graph_dict[key] = [value] if value else []
        else:
            graph_dict = dependency_graph

        # Example: Detect cyclic dependencies
        cycles = self._detect_cyclic_dependencies(graph_dict)
        if cycles:
            detected_patterns["cyclic_dependencies"] = {
                "detected": True,
                "count": len(cycles),
                "details": cycles
            }
        else:
            detected_patterns["cyclic_dependencies"] = {"detected": False, "count": 0}

        # Example: Detect common patterns like "God Object" or "Monolithic"
        # This would require more sophisticated logic based on code_metrics and classifications
        # For demonstration, let's assume some simple checks
        if self._is_monolithic(code_metrics, file_classifications):
            detected_patterns["monolithic_structure"] = {"detected": True}
        else:
            detected_patterns["monolithic_structure"] = {"detected": False}

        # Unclassified files check is removed as the new classifier should be more robust.
        # If issues persist, we can add a check for files with no classification
        # and ignore common types like images, binaries, etc.

        return detected_patterns

    def _detect_cyclic_dependencies(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """
        Detects cyclic dependencies in a directed graph using DFS.
        Uses proper cycle detection that finds strongly connected components.

        Args:
            graph (Dict[str, List[str]]): The dependency graph.

        Returns:
            List[List[str]]: A list of detected cycles, where each cycle is a list of nodes.
        """
        visited = set()
        recursion_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in recursion_stack:
                # Found a back edge - extract the cycle
                cycle_start_idx = path.index(node)
                cycle = path[cycle_start_idx:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
                
            visited.add(node)
            recursion_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path[:])  # Pass a copy of the path
            
            recursion_stack.remove(node)
            path.pop()
        
        # Only start DFS from unvisited nodes to avoid duplicates
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        # Remove duplicate cycles by normalizing them
        unique_cycles = []
        seen_cycles = set()
        
        for cycle in cycles:
            if len(cycle) <= 1:
                continue
                
            # Normalize cycle by finding the lexicographically smallest rotation
            min_rotation = min(cycle[i:] + cycle[:i] for i in range(len(cycle) - 1))
            cycle_key = tuple(min_rotation[:-1])  # Remove duplicate last element
            
            if cycle_key not in seen_cycles:
                unique_cycles.append(cycle[:-1])  # Remove duplicate last element
                seen_cycles.add(cycle_key)
        
        return unique_cycles

    def _is_monolithic(self, code_metrics: Dict[str, Any], file_classifications: Dict[str, List[str]]) -> bool:
        """
        Heuristic to determine if the project exhibits monolithic characteristics.
        This is a simplified example.

        Args:
            code_metrics (Dict[str, Any]): Code metrics.
            file_classifications (Dict[str, List[str]]): File classifications.

        Returns:
            bool: True if monolithic characteristics are detected.
        """
        total_files = len(file_classifications)
        if total_files == 0:
            return False

        # Example heuristic: a high percentage of source files and few distinct "service" indicators
        source_files = [f for f, c in file_classifications.items() if "source" in c]
        if len(source_files) / total_files > self.config.get("monolithic_source_ratio_threshold", 0.8):
            # Further checks could involve module coupling, depth of inheritance, etc.
            return True
        return False

    def _find_unclassified_files(self, file_classifications: Dict[str, List[str]]) -> List[str]:
        """
        Identifies files that have no classification, ignoring common non-source files.

        Args:
            file_classifications (Dict[str, List[str]]): A mapping of file paths to their
                                                          classified types.

        Returns:
            List[str]: A list of file paths that are unclassified and potentially problematic.
        """
        unclassified = []
        known_non_code_exts = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.tar', '.gz'}
        for file_path, classifications in file_classifications.items():
            if not classifications:
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in known_non_code_exts:
                    unclassified.append(file_path)
        return unclassified
