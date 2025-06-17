"""
workspace_resolver.py

This module provides the WorkspaceResolver class for identifying the project root
and resolving file paths within a given workspace. This is crucial for analyses
that need to operate relative to a consistent project base directory.
"""

import os
from typing import Optional, List
from pathlib import Path
from .config import DEFAULT_CONFIG

class WorkspaceResolver:
    """
    Identifies the project root and resolves file paths within a workspace.

    This class helps in establishing a consistent base directory for all file
    operations and analyses, ensuring that relative paths are correctly handled.
    """

    def __init__(self, markers: Optional[List[str]] = None):
        """
        Initializes the WorkspaceResolver with optional project root markers.

        Args:
            markers (Optional[List[str]]): A list of filenames or directory names
                                           that indicate a project root (e.g., ['.git', 'pyproject.toml']).
                                           If None, a default set of common markers will be used.
        """
        self.project_root: Optional[str] = None
        self.markers = markers if markers is not None else DEFAULT_CONFIG["workspace_markers"]

    def find_project_root(self, start_path: str) -> Optional[str]:
        """
        Traverses up the directory tree from `start_path` to find the project root.

        The project root is identified by the presence of any of the configured markers.

        Args:
            start_path (str): The starting directory from which to search upwards.

        Returns:
            Optional[str]: The absolute path to the project root if found, otherwise None.
        """
        current_path = os.path.abspath(start_path)
        while True:
            for marker in self.markers:
                if os.path.exists(os.path.join(current_path, marker)):
                    self.project_root = current_path
                    return self.project_root
            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:  # Reached the filesystem root
                break
            current_path = parent_path
        self.project_root = None
        return None

    def resolve_path(self, relative_path: str) -> Optional[str]:
        """
        Resolves a relative path to an absolute path within the detected project root.

        Requires `find_project_root` to have been called successfully.

        Args:
            relative_path (str): The path relative to the project root.

        Returns:
            Optional[str]: The absolute path if the project root is known, otherwise None.
        """
        if self.project_root:
            return os.path.join(self.project_root, relative_path)
        return None

    def get_project_root(self) -> Optional[str]:
        """
        Returns the currently identified project root.

        Returns:
            Optional[str]: The absolute path to the project root, or None if not found yet.
        """
        return self.project_root

    def is_path_in_project(self, file_path: str) -> bool:
        """
        Checks if a given file path is located within the identified project root.

        Args:
            file_path (str): The absolute or relative path to check.

        Returns:
            bool: True if the path is within the project root, False otherwise.
        """
        if not self.project_root:
            return False
        abs_file_path = os.path.abspath(file_path)
        return abs_file_path.startswith(self.project_root)

    def get_relative_path(self, file_path: str) -> Optional[str]:
        """
        Returns the path of a file relative to the project root.

        Args:
            file_path (str): The absolute path of the file.

        Returns:
            Optional[str]: The path relative to the project root, or None if the
                           file is not within the project root or root is not set.
        """
        if not self.project_root:
            return None
        abs_file_path = os.path.abspath(file_path)
        try:
            return os.path.relpath(abs_file_path, self.project_root)
        except ValueError:
            return None # Path is not within the project root

    def resolve_import(self, import_name: str, from_file: Path, source_dirs: List[str], script_exts: List[str]) -> Optional[Path]:
        """
        Resolves an import name to a file path, orchestrating workspace and alias lookups.
        """
        if not self.project_root:
            return None

        # 1. Handle relative imports
        if import_name.startswith('.'):
            # Resolve relative path using from_file's parent
            try:
                # The number of dots indicates the level of parent directory
                level = 0
                for char in import_name:
                    if char == '.':
                        level += 1
                    else:
                        break
                
                # The actual import path starts after the dots
                import_path_part = import_name[level:]
                
                base_path = from_file.parent
                for _ in range(level -1):
                    base_path = base_path.parent

                # Combine base path with the import path part
                if import_path_part:
                     # e.g. from .. import module
                    module_path = Path(import_path_part.replace('.', os.sep))
                    relative_resolved = (base_path / module_path).resolve()
                else:
                    # e.g. from ..
                    relative_resolved = base_path.resolve()

                # Check for file with common script extensions or __init__.py
                for ext in script_exts:
                    if relative_resolved.with_suffix(ext).is_file():
                        return relative_resolved.with_suffix(ext)
                if (relative_resolved / "__init__.py").is_file():
                    return (relative_resolved / "__init__.py")

            except Exception:
                return None # Path resolution failed
            return None

        # 2. Try absolute imports from configured source roots
        module_path = Path(import_name.replace('.', os.sep))

        for source_dir in source_dirs:
            potential_path = (Path(self.project_root) / source_dir / module_path)
            for ext in script_exts:
                if potential_path.with_suffix(ext).is_file():
                    return potential_path.with_suffix(ext)
            # Check for package imports (e.g., `import my_package` where my_package is a directory)
            if (potential_path / "__init__.py").is_file():
                return (potential_path / "__init__.py")

        return None
