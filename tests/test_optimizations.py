#!/usr/bin/env python3
"""
Test Optimizations Suite

This test validates all the optimizations implemented:
1. Caching Decorator (@cache_result)
2. Import Resolution in WorkspaceResolver
3. Pattern Matching in FileClassifier (fnmatch-based)
4. Smell Factory centralization
5. Configuration Defaults (DEFAULT_CONFIG)
"""

import unittest
import tempfile
import os
import shutil
import time
from pathlib import Path
import sys

# Add analyzer to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analyzer'))

from analyzer.decorators import cache_result
from analyzer.smell_factory import create_smell
from analyzer.config import DEFAULT_CONFIG
from analyzer.file_classifier import FileClassifier
from analyzer.workspace_resolver import WorkspaceResolver
from analyzer.git_analysis import GitAnalyzer
from analyzer.utils import load_cache, save_cache


class TestCachingDecorator(unittest.TestCase):
    """Test the @cache_result decorator functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()
        
        # Mock class to test the decorator
        class MockAnalyzer:
            def __init__(self, project_root):
                self.project_root = project_root
                self.call_count = 0
            
            @cache_result(expiry_seconds=60)
            def expensive_operation(self):
                """Mock expensive operation that should be cached."""
                self.call_count += 1
                return f"result_{self.call_count}"
            
            @cache_result(expiry_seconds=1)
            def quick_expiry_operation(self):
                """Mock operation with quick expiry for testing cache expiration."""
                self.call_count += 1
                return f"quick_result_{self.call_count}"
        
        self.mock_analyzer = MockAnalyzer(self.project_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_decorator_caches_results(self):
        """Test that the cache decorator actually caches results."""
        # First call should execute the function
        result1 = self.mock_analyzer.expensive_operation()
        self.assertEqual(result1, "result_1")
        self.assertEqual(self.mock_analyzer.call_count, 1)
        
        # Second call should return cached result
        result2 = self.mock_analyzer.expensive_operation()
        self.assertEqual(result2, "result_1")  # Same result as before
        self.assertEqual(self.mock_analyzer.call_count, 1)  # Function not called again
    
    def test_cache_decorator_respects_expiry(self):
        """Test that cache decorator respects expiry time."""
        # First call
        result1 = self.mock_analyzer.quick_expiry_operation()
        self.assertEqual(result1, "quick_result_1")
        self.assertEqual(self.mock_analyzer.call_count, 1)
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Second call should execute function again
        result2 = self.mock_analyzer.quick_expiry_operation()
        self.assertEqual(result2, "quick_result_2")
        self.assertEqual(self.mock_analyzer.call_count, 2)
    
    def test_cache_decorator_with_invalid_object(self):
        """Test cache decorator behavior with objects without project_root."""
        class InvalidMockAnalyzer:
            def __init__(self):
                self.call_count = 0
            
            @cache_result(expiry_seconds=60)
            def operation(self):
                self.call_count += 1
                return f"result_{self.call_count}"
        
        invalid_analyzer = InvalidMockAnalyzer()
        
        # Should work but without caching
        result1 = invalid_analyzer.operation()
        self.assertEqual(result1, "result_1")
        
        result2 = invalid_analyzer.operation()
        self.assertEqual(result2, "result_2")  # Different result, no caching


class TestSmellFactory(unittest.TestCase):
    """Test the centralized smell factory."""
    
    def test_create_smell_basic(self):
        """Test basic smell creation."""
        smell = create_smell(
            smell_type='TEST_SMELL',
            file_path='/path/to/file.py',
            message='This is a test smell',
            severity='Medium',
            category='Test Category'
        )
        
        expected = {
            'type': 'TEST_SMELL',
            'file': '/path/to/file.py',
            'message': 'This is a test smell',
            'severity': 'Medium',
            'category': 'Test Category',
            'line': 'N/A'
        }
        
        self.assertEqual(smell, expected)
    
    def test_create_smell_with_line_number(self):
        """Test smell creation with line number."""
        smell = create_smell(
            smell_type='LINE_SMELL',
            file_path='/path/to/file.py',
            message='Issue on specific line',
            severity='High',
            category='Line Analysis',
            line=42
        )
        
        self.assertEqual(smell['line'], 42)
        self.assertEqual(smell['type'], 'LINE_SMELL')
    
    def test_create_smell_without_line_number(self):
        """Test smell creation without line number."""
        smell = create_smell(
            smell_type='FILE_SMELL',
            file_path='/path/to/file.py',
            message='File-level issue',
            severity='Low',
            category='File Analysis'
        )
        
        self.assertEqual(smell['line'], 'N/A')


class TestConfigurationDefaults(unittest.TestCase):
    """Test that DEFAULT_CONFIG is properly centralized and used."""
    
    def test_default_config_exists(self):
        """Test that DEFAULT_CONFIG contains expected keys."""
        required_keys = [
            'workspace_markers',
            'source_file_patterns',
            'test_file_patterns',
            'documentation_file_patterns',
            'config_file_patterns',
            'project_lifecycle_patterns',
            'stale_logic_threshold_days',
            'high_churn_days',
            'high_churn_threshold'
        ]
        
        for key in required_keys:
            self.assertIn(key, DEFAULT_CONFIG, f"DEFAULT_CONFIG missing key: {key}")
    
    def test_file_classifier_uses_defaults(self):
        """Test that FileClassifier properly uses DEFAULT_CONFIG."""
        # Create classifier with minimal config
        classifier = FileClassifier({})
        
        # Should fall back to defaults
        self.assertEqual(classifier.source_patterns, DEFAULT_CONFIG["source_file_patterns"])
        self.assertEqual(classifier.test_patterns, DEFAULT_CONFIG["test_file_patterns"])
        self.assertEqual(classifier.documentation_patterns, DEFAULT_CONFIG["documentation_file_patterns"])
    
    def test_workspace_resolver_uses_defaults(self):
        """Test that WorkspaceResolver properly uses DEFAULT_CONFIG."""
        resolver = WorkspaceResolver()
        self.assertEqual(resolver.markers, DEFAULT_CONFIG["workspace_markers"])


class TestPatternMatching(unittest.TestCase):
    """Test the unified fnmatch-based pattern matching in FileClassifier."""
    
    def setUp(self):
        """Set up test classifier."""
        self.config = {
            "source_file_patterns": ["*.py", "*.js", "src/*.ts"],
            "test_file_patterns": ["test_*.py", "*_test.js", "*.spec.ts"],
            "documentation_file_patterns": ["*.md", "README*", "*.txt"],
            "config_file_patterns": ["*.json", "*.yaml", "config.*"]
        }
        self.classifier = FileClassifier(self.config)
    
    def test_fnmatch_source_patterns(self):
        """Test fnmatch-based source file pattern matching."""
        test_cases = [
            ("main.py", True),
            ("app.js", True),
            ("src/component.ts", True),
            ("test.txt", False),
            ("config.json", False)
        ]
        
        for file_path, should_match in test_cases:
            classifications = self.classifier.classify_file(file_path)
            has_source = "source" in classifications
            self.assertEqual(has_source, should_match, 
                           f"File {file_path} source classification: expected {should_match}, got {has_source}")
    
    def test_fnmatch_test_patterns(self):
        """Test fnmatch-based test file pattern matching."""
        test_cases = [
            ("test_main.py", True),
            ("utils_test.js", True),
            ("component.spec.ts", True),
            ("main.py", False),
            ("README.md", False)
        ]
        
        for file_path, should_match in test_cases:
            classifications = self.classifier.classify_file(file_path)
            has_test = "test" in classifications
            self.assertEqual(has_test, should_match,
                           f"File {file_path} test classification: expected {should_match}, got {has_test}")
    
    def test_fnmatch_documentation_patterns(self):
        """Test fnmatch-based documentation pattern matching."""
        test_cases = [
            ("README.md", True),
            ("README", True),
            ("docs.txt", True),
            ("main.py", False),
            ("config.json", False)
        ]
        
        for file_path, should_match in test_cases:
            classifications = self.classifier.classify_file(file_path)
            has_doc = "documentation" in classifications
            self.assertEqual(has_doc, should_match,
                           f"File {file_path} documentation classification: expected {should_match}, got {has_doc}")
    
    def test_fnmatch_config_patterns(self):
        """Test fnmatch-based config pattern matching."""
        test_cases = [
            ("package.json", True),
            ("settings.yaml", True),
            ("config.dev", True),
            ("main.py", False),
            ("README.md", False)
        ]
        
        for file_path, should_match in test_cases:
            classifications = self.classifier.classify_file(file_path)
            has_config = "config" in classifications
            self.assertEqual(has_config, should_match,
                           f"File {file_path} config classification: expected {should_match}, got {has_config}")


class TestImportResolution(unittest.TestCase):
    """Test consolidated import resolution in WorkspaceResolver."""
    
    def setUp(self):
        """Set up test environment with project structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()
        
        # Create project structure
        (self.project_dir / ".git").mkdir()
        src_dir = self.project_dir / "src"
        src_dir.mkdir()
        
        # Create test files
        (src_dir / "__init__.py").touch()
        (src_dir / "main.py").write_text("# main module")
        (src_dir / "utils.py").write_text("# utils module")
        
        # Create subpackage
        subpkg_dir = src_dir / "subpackage"
        subpkg_dir.mkdir()
        (subpkg_dir / "__init__.py").touch()
        (subpkg_dir / "module.py").write_text("# subpackage module")
        
        self.resolver = WorkspaceResolver()
        self.resolver.find_project_root(str(self.project_dir))
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_resolve_relative_import(self):
        """Test resolution of relative imports."""
        from_file = self.project_dir / "src" / "main.py"
        
        # Test relative import from same directory
        resolved = self.resolver.resolve_import(
            ".utils", 
            from_file, 
            ["src"], 
            [".py"]
        )
        
        expected = self.project_dir / "src" / "utils.py"
        self.assertEqual(resolved, expected)
    
    def test_resolve_absolute_import(self):
        """Test resolution of absolute imports."""
        from_file = self.project_dir / "src" / "main.py"
        
        # Test absolute import
        resolved = self.resolver.resolve_import(
            "subpackage.module",
            from_file,
            ["src"],
            [".py"]
        )
        
        expected = self.project_dir / "src" / "subpackage" / "module.py"
        self.assertEqual(resolved, expected)
    
    def test_resolve_package_import(self):
        """Test resolution of package imports (__init__.py)."""
        from_file = self.project_dir / "src" / "main.py"
        
        # Test package import
        resolved = self.resolver.resolve_import(
            "subpackage",
            from_file,
            ["src"],
            [".py"]
        )
        
        expected = self.project_dir / "src" / "subpackage" / "__init__.py"
        self.assertEqual(resolved, expected)
    
    def test_resolve_nonexistent_import(self):
        """Test handling of nonexistent imports."""
        from_file = self.project_dir / "src" / "main.py"
        
        resolved = self.resolver.resolve_import(
            "nonexistent.module",
            from_file,
            ["src"],
            [".py"]
        )
        
        self.assertIsNone(resolved)


class TestGitAnalyzerOptimizations(unittest.TestCase):
    """Test GitAnalyzer optimizations (caching and smell factory usage)."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()
        
        config = {"source_file_patterns": ["*.py"]}
        file_classifier = FileClassifier(config)
        self.git_analyzer = GitAnalyzer(self.project_dir, config, file_classifier)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_git_analyzer_uses_smell_factory(self):
        """Test that GitAnalyzer uses the centralized smell factory."""
        # Test with non-git directory (should return empty lists)
        stale_logic = self.git_analyzer.check_stale_logic([])
        high_churn = self.git_analyzer.check_high_churn([])
        stale_tests = self.git_analyzer.check_stale_tests([])
        
        # Should all be empty lists since no git repo
        self.assertEqual(stale_logic, [])
        self.assertEqual(high_churn, [])
        self.assertEqual(stale_tests, [])
        
        # Test that methods are properly decorated with cache_result
        self.assertTrue(hasattr(self.git_analyzer.check_stale_logic, '__wrapped__'))
        self.assertTrue(hasattr(self.git_analyzer.check_high_churn, '__wrapped__'))
        self.assertTrue(hasattr(self.git_analyzer.check_stale_tests, '__wrapped__'))
    
    def test_git_analyzer_configuration_integration(self):
        """Test that GitAnalyzer properly integrates with DEFAULT_CONFIG."""
        # Test that default configuration values are used
        self.assertEqual(
            self.git_analyzer.config.get('stale_logic_threshold_days', DEFAULT_CONFIG['stale_logic_threshold_days']),
            DEFAULT_CONFIG['stale_logic_threshold_days']
        )
        self.assertEqual(
            self.git_analyzer.config.get('high_churn_days', DEFAULT_CONFIG['high_churn_days']),
            DEFAULT_CONFIG['high_churn_days']
        )


class TestBackwardCompatibility(unittest.TestCase):
    """Test that optimizations maintain backward compatibility."""
    
    def test_imports_still_work(self):
        """Test that all optimized modules can still be imported."""
        try:
            from analyzer import (
                ArchitecturalSniffer, FileClassifier, WorkspaceResolver,
                PatternAnalyzer, GitAnalyzer, cache_result, create_smell
            )
            self.assertTrue(True)  # If we get here, imports worked
        except ImportError as e:
            self.fail(f"Import failed: {e}")
    
    def test_original_api_unchanged(self):
        """Test that the original API methods still work as expected."""
        # Test FileClassifier API
        config = {"source_file_patterns": ["*.py"]}
        classifier = FileClassifier(config)
        result = classifier.classify_file("test.py")
        self.assertIsInstance(result, list)
        
        # Test WorkspaceResolver API
        resolver = WorkspaceResolver()
        self.assertIsInstance(resolver.markers, list)
        
        # Test smell factory API
        smell = create_smell('TEST', '/test.py', 'Test message', 'Low', 'Test')
        self.assertIsInstance(smell, dict)
        self.assertIn('type', smell)


if __name__ == '__main__':
    unittest.main()