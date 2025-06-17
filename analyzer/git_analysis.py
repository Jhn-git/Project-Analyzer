#
# Pseudocode for updated analyzer/git_analysis.py
#

from pathlib import Path
import time
from datetime import datetime, timedelta
import sys
from typing import List, Dict, Any

# Optional dependency
try:
    import git
    HAS_GIT = True
except ImportError:
    HAS_GIT = False

# Project-specific imports
from .file_classifier import FileClassifier
from .config import get_configured_source_dirs, DEFAULT_CONFIG
from .decorators import cache_result
from .smell_factory import create_smell

class GitAnalyzer:
    """
    Handles all Git-based analysis, such as code churn, stale logic, and stale tests.
    Relies on a FileClassifier instance for all file-type checks.
    """
    # --- TDD ANCHOR: Test initialization and Git repository detection ---
    def __init__(self, project_root: Path, config: dict, file_classifier: FileClassifier):
        """
        Initializes the Git analyzer.
        
        Args:
            project_root: The root directory of the project.
            config: The project's configuration dictionary.
            file_classifier: An initialized instance of the FileClassifier.
        """
        self.project_root = project_root
        self.config = config
        self.file_classifier = file_classifier # Dependency is injected
        self.repo = self._get_repo()

    def _get_repo(self):
        """Initializes the Git repository object, returns None if not found."""
        if not HAS_GIT:
            print("Warning: GitPython not found. Git-based checks will be skipped.", file=sys.stderr)
            return None
        try:
            return git.Repo(self.project_root)
        except git.exc.InvalidGitRepositoryError:
            print("Warning: Not a valid Git repository. Git-based checks will be skipped.", file=sys.stderr)
            return None

    def has_git_repo(self) -> bool:
        """Checks if a valid Git repository is available."""
        return self.repo is not None

    # --- TDD ANCHOR: Test stale logic with old, new, and untracked files ---
    @cache_result(expiry_seconds=86400)
    def check_stale_logic(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Checks for source files that have not been modified in a long time.

        Args:
            file_paths (List[Path]): A list of file paths to check.

        Returns:
            List[Dict[str, Any]]: A list of detected 'STALE_LOGIC' smells.
        """
        if not self.has_git_repo():
            return []

        smells = []
        threshold_days = self.config.get('stale_logic_threshold_days', DEFAULT_CONFIG['stale_logic_threshold_days'])
        cutoff_date = datetime.now() - timedelta(days=threshold_days)

        for file_path in file_paths:
            classifications = self.file_classifier.classify_file(str(file_path))
            if "source" in classifications:
                try:
                    # Get the last commit date for the file
                    last_commit = next(self.repo.iter_commits(paths=str(file_path), max_count=1))
                    last_commit_date = last_commit.committed_datetime.astimezone()

                    if last_commit_date < cutoff_date:
                        smells.append(create_smell(
                            smell_type='STALE_LOGIC',
                            file_path=str(file_path),
                            message=f"Source file has not been modified in {threshold_days} days.",
                            severity='Low',
                            category='Git Analysis'
                        ))
                except (StopIteration, git.exc.GitCommandError):
                    # File might be untracked or no commits exist for it
                    continue

        return smells

    @cache_result(expiry_seconds=86400)
    def check_high_churn(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Checks for source files with a high number of commits in a recent period.

        Args:
            file_paths (List[Path]): A list of file paths to check.

        Returns:
            List[Dict[str, Any]]: A list of detected 'HIGH_CHURN' smells.
        """
        if not self.has_git_repo():
            return []

        smells = []
        days = self.config.get('high_churn_days', DEFAULT_CONFIG['high_churn_days'])
        threshold_commits = self.config.get('high_churn_threshold', DEFAULT_CONFIG['high_churn_threshold'])
        since_date = datetime.now() - timedelta(days=days)

        for file_path in file_paths:
            classifications = self.file_classifier.classify_file(str(file_path))
            if "source" in classifications:
                try:
                    commits = list(self.repo.iter_commits(paths=str(file_path), since=since_date))
                    if len(commits) >= threshold_commits:
                        smells.append(create_smell(
                            smell_type='HIGH_CHURN',
                            file_path=str(file_path),
                            message=f"High churn: {len(commits)} commits in the last {days} days.",
                            severity='Medium',
                            category='Git Analysis'
                        ))
                except git.exc.GitCommandError:
                    continue

        return smells

    @cache_result(expiry_seconds=86400)
    def check_stale_tests(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Checks if a source file has been modified more recently than its corresponding test.

        Args:
            file_paths (List[Path]): A list of file paths to check.

        Returns:
            List[Dict[str, Any]]: A list of detected 'STALE_TESTS' smells.
        """
        if not self.has_git_repo():
            return []

        smells = []
        all_files_str_set = {str(p) for p in file_paths}

        for file_path in file_paths:
            classifications = self.file_classifier.classify_file(str(file_path))
            if "source" in classifications:
                # Attempt to find a corresponding test file
                test_file_candidates = self._find_corresponding_test_candidates(file_path, all_files_str_set)

                for test_file in test_file_candidates:
                    try:
                        source_commit_time = next(self.repo.iter_commits(paths=str(file_path), max_count=1)).committed_datetime
                        test_commit_time = next(self.repo.iter_commits(paths=str(test_file), max_count=1)).committed_datetime

                        if source_commit_time > test_commit_time:
                            smells.append(create_smell(
                                smell_type='STALE_TESTS',
                                file_path=str(file_path),
                                message=f"Source file ({file_path.name}) modified more recently than its test file ({Path(test_file).name}).",
                                severity='Medium',
                                category='Git Analysis'
                            ))
                            break # Found a stale test, no need to check other candidates
                    except (StopIteration, git.exc.GitCommandError):
                        continue # One of the files is not tracked or no commits
        
        return smells

    def _find_corresponding_test_candidates(self, source_file: Path, all_files_str_set: set[str]) -> List[str]:
        """
        Finds potential corresponding test file paths for a given source file.
        This is a heuristic and can be expanded based on project conventions.

        Args:
            source_file (Path): The path to the source file.
            all_files_str_set (set[str]): A set of all project files as strings for quick lookup.

        Returns:
            List[str]: A list of potential test file paths.
        """
        candidates = []
        source_name = source_file.stem # file name without extension
        source_dir = source_file.parent

        # Common test file naming conventions
        # e.g., my_module.py -> test_my_module.py, my_module.py -> my_module_test.py
        test_prefixes = ["test_", ""]
        test_suffixes = ["_test", ""]
        test_exts = [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go"] # Common test extensions

        # Check in the same directory
        for prefix in test_prefixes:
            for suffix in test_suffixes:
                for ext in test_exts:
                    candidate_name = f"{prefix}{source_name}{suffix}{ext}"
                    candidate_path = source_dir / candidate_name
                    if str(candidate_path) in all_files_str_set and "test" in self.file_classifier.classify_file(str(candidate_path)):
                        candidates.append(str(candidate_path))

        # Check in a 'tests' or '__tests__' subdirectory
        # This assumes a structure like `src/module.py` and `tests/test_module.py`
        for test_dir_name in ["test", "tests", "__tests__"]:
            parts = list(source_file.parts)
            try:
                # Find the 'source' part of the path (e.g., 'src', 'app')
                # This is a heuristic, and might need refinement based on actual project structure
                source_root_index = -1
                for i, part in enumerate(parts):
                    if part in self.config.get("source_dirs", ["src", "app", "main"]):
                        source_root_index = i
                        break

                if source_root_index != -1:
                    # Construct path to parallel test directory
                    # e.g., /project/src/module/file.py -> /project/tests/module/test_file.py
                    relative_to_source_root = Path(*parts[source_root_index+1:])
                    test_base_dir = Path(*parts[:source_root_index]) / test_dir_name
                    
                    for prefix in test_prefixes:
                        for suffix in test_suffixes:
                            for ext in test_exts:
                                candidate_name = f"{prefix}{relative_to_source_root.stem}{suffix}{ext}"
                                candidate_path = test_base_dir / relative_to_source_root.parent / candidate_name
                                if str(candidate_path) in all_files_str_set and "test" in self.file_classifier.classify_file(str(candidate_path)):
                                    candidates.append(str(candidate_path))
            except Exception:
                # Handle cases where path manipulation fails
                pass

        return list(set(candidates)) # Remove duplicates
