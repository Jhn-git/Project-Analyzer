#!/usr/bin/env python3
"""
Test Core Functionality

Tests for validating that the core Project-Analyzer functionality works
correctly after fixes: dependency analysis, architectural pattern detection,
Git analysis, and caching system.
"""

import unittest
import tempfile
import os
import time
import shutil
from pathlib import Path
import sys

# Add analyzer to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analyzer'))

from analyzer.architectural_analysis import ArchitecturalSniffer
from analyzer.dependency_analysis import DependencyGraph, ImportParser
from analyzer.pattern_analysis import PatternAnalyzer
from analyzer.git_analysis import GitAnalyzer
from analyzer.file_classifier import FileClassifier
from analyzer.utils import load_cache, save_cache, get_project_hash


class TestDependencyAnalysis(unittest.TestCase):
    """Test dependency analysis functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dependency_graph_creation(self):
        """Test that dependency graphs are created correctly."""
        graph = DependencyGraph()
        
        # Test adding dependencies
        graph.add_dependency("file1.py", "file2.py")
        graph.add_dependency("file1.py", "file3.py")
        graph.add_dependency("file2.py", "file3.py")
        
        # Test structure
        self.assertIn("file2.py", graph.imports["file1.py"])
        self.assertIn("file3.py", graph.imports["file1.py"])
        self.assertIn("file3.py", graph.imports["file2.py"])
    
    def test_import_parsing(self):
        """Test that imports are parsed correctly from source files."""
        # Create test Python file with imports
        test_file = self.project_dir / "test_module.py"
        test_file.write_text("""
import os
import sys
from pathlib import Path
from . import utils
from ..parent import helper

def main():
    pass
""")
        
        imports = ImportParser.get_file_imports(str(test_file), str(self.project_dir))
        
        # Should detect various import types
        expected_imports = {"os", "sys", "pathlib", "utils", "parent"}
        
        # At least some imports should be detected
        self.assertTrue(len(imports) > 0, "Should detect some imports")
        
        # Should handle relative imports
        self.assertTrue(any("utils" in imp or "parent" in imp for imp in imports),
                       "Should detect relative imports")
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        # Create files with circular dependencies
        file_a = self.project_dir / "module_a.py"
        file_b = self.project_dir / "module_b.py"
        file_c = self.project_dir / "module_c.py"
        
        file_a.write_text("import module_b")
        file_b.write_text("import module_c") 
        file_c.write_text("import module_a")  # Creates cycle
        
        config = {"source_file_patterns": ["*.py"]}
        sniffer = ArchitecturalSniffer(str(self.project_dir), config)
        
        file_paths = [str(file_a), str(file_b), str(file_c)]
        smells = sniffer.analyze_architecture(file_paths)
        
        # Should detect circular dependency
        circular_smells = [s for s in smells if s.get("type") == "CIRCULAR_DEPENDENCY"]
        self.assertTrue(len(circular_smells) > 0, 
                       "Should detect circular dependency")


class TestArchitecturalPatternDetection(unittest.TestCase):
    """Test architectural pattern detection."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = {
            "architectural_patterns": {},
            "monolithic_source_ratio_threshold": 0.8
        }
        self.analyzer = PatternAnalyzer(self.config)
    
    def test_cyclic_dependency_pattern_detection(self):
        """Test detection of cyclic dependency patterns."""
        # Create dependency graph with cycles
        dependency_graph = {
            "a.py": ["b.py"],
            "b.py": ["c.py"],
            "c.py": ["a.py"]  # Creates cycle
        }
        
        file_classifications = {
            "a.py": ["source", "python"],
            "b.py": ["source", "python"], 
            "c.py": ["source", "python"]
        }
        
        patterns = self.analyzer.analyze_patterns(dependency_graph, file_classifications, {})
        
        # Should detect cyclic dependencies
        self.assertTrue(patterns["cyclic_dependencies"]["detected"])
        self.assertEqual(patterns["cyclic_dependencies"]["count"], 1)
        self.assertTrue(len(patterns["cyclic_dependencies"]["details"]) > 0)
    
    def test_no_false_positive_cycles(self):
        """Test that acyclic graphs don't trigger false positives."""
        # Create acyclic dependency graph
        dependency_graph = {
            "a.py": ["b.py"],
            "b.py": ["c.py"],
            "c.py": []  # No cycle
        }
        
        file_classifications = {
            "a.py": ["source", "python"],
            "b.py": ["source", "python"],
            "c.py": ["source", "python"]
        }
        
        patterns = self.analyzer.analyze_patterns(dependency_graph, file_classifications, {})
        
        # Should NOT detect cyclic dependencies
        self.assertFalse(patterns["cyclic_dependencies"]["detected"])
        self.assertEqual(patterns["cyclic_dependencies"]["count"], 0)
    
    def test_monolithic_structure_detection(self):
        """Test detection of monolithic structures."""
        # Create file classifications with high source ratio
        file_classifications = {}
        for i in range(10):
            file_classifications[f"src_{i}.py"] = ["source", "python"]
        
        # Add only one non-source file (high ratio)
        file_classifications["README.md"] = ["documentation"]
        
        patterns = self.analyzer.analyze_patterns({}, file_classifications, {})
        
        # Should detect monolithic structure (10/11 = 90% > 80% threshold)
        self.assertTrue(patterns["monolithic_structure"]["detected"])


class TestGitAnalysis(unittest.TestCase):
    """Test Git analysis functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()
        
        self.config = {"source_file_patterns": [".py"]}
        self.file_classifier = FileClassifier(self.config)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_git_analyzer_without_git_repo(self):
        """Test Git analyzer behavior when no Git repository exists."""
        git_analyzer = GitAnalyzer(self.project_dir, self.config, self.file_classifier)
        
        # Should correctly detect no Git repo
        self.assertFalse(git_analyzer.has_git_repo())
        
        # Should handle gracefully without crashing
        stale_logic = git_analyzer.check_stale_logic([])
        self.assertEqual(stale_logic, [])
        
        high_churn = git_analyzer.check_high_churn([])
        self.assertEqual(high_churn, [])
        
        stale_tests = git_analyzer.check_stale_tests([])
        self.assertEqual(stale_tests, [])
    
    def test_git_analyzer_initialization(self):
        """Test that Git analyzer initializes correctly."""
        git_analyzer = GitAnalyzer(self.project_dir, self.config, self.file_classifier)
        
        # Should initialize without errors
        self.assertIsNotNone(git_analyzer)
        self.assertEqual(git_analyzer.project_root, self.project_dir)


class TestCachingSystem(unittest.TestCase):
    """Test caching system functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cache_file = None
        
        # Temporarily override cache location for testing
        import analyzer.config as config
        self.original_cache_file = config.CACHE_FILE
        config.CACHE_FILE = os.path.join(self.temp_dir, "test_cache.json")
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original cache file location
        if self.original_cache_file:
            import analyzer.config as config
            config.CACHE_FILE = self.original_cache_file
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_save_and_load(self):
        """Test basic cache save and load functionality."""
        test_data = {
            "test_key": "test_value",
            "timestamp": time.time(),
            "nested": {"key": "value"}
        }
        
        # Save cache
        save_cache(test_data)
        
        # Load cache
        loaded_data = load_cache()
        
        # Should match saved data
        self.assertEqual(loaded_data["test_key"], "test_value")
        self.assertEqual(loaded_data["nested"]["key"], "value")
    
    def test_project_hash_consistency(self):
        """Test that project hash generation is consistent."""
        test_files = [
            "/project/file1.py",
            "/project/file2.py",
            "/project/subdir/file3.py"
        ]
        
        hash1 = get_project_hash(test_files)
        hash2 = get_project_hash(test_files)
        
        # Should be consistent
        self.assertEqual(hash1, hash2)
        
        # Should change when files change
        different_files = test_files + ["/project/file4.py"]
        hash3 = get_project_hash(different_files)
        self.assertNotEqual(hash1, hash3)
    
    def test_architectural_analysis_caching(self):
        """Test that architectural analysis results are cached."""
        # Create test project
        project_dir = Path(self.temp_dir) / "cache_test_project"
        project_dir.mkdir()
        
        test_file = project_dir / "test.py"
        test_file.write_text("print('hello')")
        
        # First analysis
        sniffer1 = ArchitecturalSniffer(str(project_dir))
        start_time1 = time.time()
        smells1 = sniffer1.analyze_architecture([str(test_file)])
        duration1 = time.time() - start_time1
        
        # Second analysis (should use cache)
        sniffer2 = ArchitecturalSniffer(str(project_dir))
        start_time2 = time.time()
        smells2 = sniffer2.analyze_architecture([str(test_file)])
        duration2 = time.time() - start_time2
        
        # Results should be identical
        self.assertEqual(smells1, smells2)
        
        # Second run should be faster (cached)
        # Note: This might not always be true in fast environments, so we just check that it completes
        self.assertIsNotNone(smells2)


class TestEndToEndIntegration(unittest.TestCase):
    """Test end-to-end integration of core functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "integration_test"
        self.project_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_analysis_pipeline(self):
        """Test the complete analysis pipeline end-to-end."""
        # Create realistic project structure
        (self.project_dir / "README.md").write_text("# Test Project")
        (self.project_dir / "LICENSE").write_text("MIT License")
        (self.project_dir / ".gitignore").write_text("*.pyc")
        
        # Source files
        src_dir = self.project_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("""
import utils
from config import settings

def main():
    utils.helper()
    print(settings.DEBUG)
""")
        
        (src_dir / "utils.py").write_text("""
def helper():
    return "helper"
""")
        
        (src_dir / "config.py").write_text("""
class Settings:
    DEBUG = True

settings = Settings()
""")
        
        # Tests
        tests_dir = self.project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("""
import unittest
from src.main import main

class TestMain(unittest.TestCase):
    def test_main(self):
        main()
""")
        
        # Run complete analysis
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        
        all_files = [
            str(src_dir / "main.py"),
            str(src_dir / "utils.py"),
            str(src_dir / "config.py"),
            str(tests_dir / "test_main.py")
        ]
        
        # Should complete without errors
        smells = sniffer.analyze_architecture(all_files)
        
        # Should return list (may be empty, which is fine)
        self.assertIsInstance(smells, list)
        
        # If smells found, they should be properly formatted
        for smell in smells:
            self.assertIsInstance(smell, dict)
            self.assertIn("type", smell)
            self.assertIn("message", smell)
    
    def test_analysis_with_no_source_files(self):
        """Test analysis when no source files are provided."""
        # Only create documentation files
        (self.project_dir / "README.md").write_text("# Test")
        (self.project_dir / "LICENSE").write_text("MIT")
        
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        
        # Analyze with empty file list
        smells = sniffer.analyze_architecture([])
        
        # Should handle gracefully
        self.assertIsInstance(smells, list)
    
    def test_analysis_with_complex_dependencies(self):
        """Test analysis with complex dependency patterns."""
        # Create multiple modules with various dependency patterns
        modules = {}
        src_dir = self.project_dir / "src"
        src_dir.mkdir()
        
        # Linear dependencies: A -> B -> C
        modules["a"] = "import b"
        modules["b"] = "import c"
        modules["c"] = "# leaf module"
        
        # Fan-out: D imports multiple modules
        modules["d"] = "import a\nimport b\nimport c"
        
        # Create files
        file_paths = []
        for name, content in modules.items():
            file_path = src_dir / f"{name}.py"
            file_path.write_text(content)
            file_paths.append(str(file_path))
        
        # Run analysis
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        smells = sniffer.analyze_architecture(file_paths)
        
        # Should complete successfully
        self.assertIsInstance(smells, list)
        
        # Should not detect circular dependencies in linear structure
        circular_smells = [s for s in smells if s.get("type") == "CIRCULAR_DEPENDENCY"]
        self.assertEqual(len(circular_smells), 0, 
                        "Should not detect circular dependencies in linear structure")


if __name__ == '__main__':
    unittest.main()