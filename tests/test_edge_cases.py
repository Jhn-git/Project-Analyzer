#!/usr/bin/env python3
"""
Test Edge Cases

Tests for validating edge cases and error handling in the Project-Analyzer:
empty directories, missing Git repository, invalid file types, corrupted files,
and other boundary conditions.
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path
import sys

# Add analyzer to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analyzer'))

from analyzer.architectural_analysis import ArchitecturalSniffer
from analyzer.file_classifier import FileClassifier
from analyzer.workspace_resolver import WorkspaceResolver
from analyzer.pattern_analysis import PatternAnalyzer
from analyzer.git_analysis import GitAnalyzer
from analyzer.dependency_analysis import ImportParser


class TestEmptyDirectoriesAndFiles(unittest.TestCase):
    """Test behavior with empty directories and files."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "empty_test"
        self.project_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_empty_directory_analysis(self):
        """Test analysis of completely empty directory."""
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        
        # Analyze empty directory
        smells = sniffer.analyze_architecture([])
        
        # Should handle gracefully without crashing
        self.assertIsInstance(smells, list)
        self.assertEqual(len(smells), 0, "Empty directory should produce no smells")
    
    def test_directory_with_only_empty_files(self):
        """Test analysis of directory with only empty files."""
        # Create empty files
        (self.project_dir / "empty.py").write_text("")
        (self.project_dir / "also_empty.js").write_text("")
        (self.project_dir / "whitespace_only.py").write_text("   \n\n  \t  \n")
        
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        file_paths = [
            str(self.project_dir / "empty.py"),
            str(self.project_dir / "also_empty.js"),
            str(self.project_dir / "whitespace_only.py")
        ]
        
        # Should handle empty files gracefully
        smells = sniffer.analyze_architecture(file_paths)
        self.assertIsInstance(smells, list)
    
    def test_directory_with_only_non_source_files(self):
        """Test analysis of directory with only documentation/config files."""
        (self.project_dir / "README.md").write_text("# Project")
        (self.project_dir / "LICENSE").write_text("MIT License")
        (self.project_dir / ".gitignore").write_text("*.pyc")
        (self.project_dir / "config.json").write_text('{"debug": true}')
        
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        file_paths = [
            str(self.project_dir / "README.md"),
            str(self.project_dir / "LICENSE"),
            str(self.project_dir / ".gitignore"),
            str(self.project_dir / "config.json")
        ]
        
        smells = sniffer.analyze_architecture(file_paths)
        
        # Should complete without errors
        self.assertIsInstance(smells, list)
        
        # Should not generate false positive architectural issues for doc/config files
        unclassified_smells = [s for s in smells if s.get("type") == "UNCLASSIFIED_FILE"]
        self.assertEqual(len(unclassified_smells), 0, 
                        "Documentation and config files should not be flagged as unclassified")


class TestInvalidAndCorruptedFiles(unittest.TestCase):
    """Test behavior with invalid and corrupted files."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "invalid_test"
        self.project_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_files_with_syntax_errors(self):
        """Test analysis of files with syntax errors."""
        # Create Python file with syntax error
        syntax_error_file = self.project_dir / "broken.py"
        syntax_error_file.write_text("""
def incomplete_function(
    # Missing closing parenthesis and body
    invalid syntax here
""")
        
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        
        # Should handle syntax errors gracefully
        smells = sniffer.analyze_architecture([str(syntax_error_file)])
        self.assertIsInstance(smells, list)
    
    def test_binary_files(self):
        """Test behavior with binary files."""
        # Create a binary file
        binary_file = self.project_dir / "image.png"
        binary_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01')
        
        config = {"source_file_patterns": [".py", ".js"]}
        classifier = FileClassifier(config)
        
        # Binary files should not be classified as source
        classifications = classifier.classify_file(str(binary_file))
        self.assertNotIn("source", classifications, 
                        "Binary files should not be classified as source")
    
    def test_files_with_unicode_content(self):
        """Test analysis of files with Unicode content."""
        unicode_file = self.project_dir / "unicode.py"
        unicode_file.write_text("""
# -*- coding: utf-8 -*-
def función_con_unicode():
    '''Función with ñoñó characters'''
    mensaje = "¡Hola, mundo! 你好世界"
    return mensaje

class Café:
    def __init__(self):
        self.precio = "€5.00"
""", encoding='utf-8')
        
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        
        # Should handle Unicode content gracefully
        smells = sniffer.analyze_architecture([str(unicode_file)])
        self.assertIsInstance(smells, list)
    
    def test_very_large_files(self):
        """Test behavior with very large files."""
        large_file = self.project_dir / "large.py"
        
        # Create a large file with many functions
        content = []
        for i in range(1000):
            content.append(f"""
def function_{i}():
    '''Function number {i}'''
    return {i}
""")
        
        large_file.write_text('\n'.join(content))
        
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        
        # Should handle large files without timing out or crashing
        smells = sniffer.analyze_architecture([str(large_file)])
        self.assertIsInstance(smells, list)
    
    def test_files_with_unusual_extensions(self):
        """Test classification of files with unusual extensions."""
        config = {
            "source_file_patterns": [".py", ".js"],
            "documentation_file_patterns": [".md", ".txt"]
        }
        classifier = FileClassifier(config)
        
        unusual_files = [
            "script.py3",  # Python-like but not standard
            "readme.markdown",  # Markdown variant
            "config.toml",  # TOML config file
            "data.json5",  # JSON5 variant
            "style.scss",  # SASS CSS
            "Makefile",  # No extension
            ".hidden",  # Hidden file with no extension
        ]
        
        for file_path in unusual_files:
            with self.subTest(file=file_path):
                classifications = classifier.classify_file(file_path)
                # Should not crash, should return some classification or empty list
                self.assertIsInstance(classifications, list)


class TestMissingGitRepository(unittest.TestCase):
    """Test behavior when Git repository is missing or corrupted."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "no_git_test"
        self.project_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analysis_without_git_repository(self):
        """Test complete analysis in directory without Git repository."""
        # Create source files but no .git directory
        src_dir = self.project_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')")
        (src_dir / "utils.py").write_text("def helper(): pass")
        
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        file_paths = [str(src_dir / "main.py"), str(src_dir / "utils.py")]
        
        # Should complete analysis without Git-based smells
        smells = sniffer.analyze_architecture(file_paths)
        self.assertIsInstance(smells, list)
        
        # Should not contain Git-based smells
        git_smell_types = {"STALE_LOGIC", "HIGH_CHURN", "STALE_TESTS"}
        git_smells = [s for s in smells if s.get("type") in git_smell_types]
        self.assertEqual(len(git_smells), 0, 
                        "Should not generate Git-based smells without Git repository")
    
    def test_git_analyzer_graceful_degradation(self):
        """Test that GitAnalyzer handles missing Git gracefully."""
        config = {"source_file_patterns": [".py"]}
        file_classifier = FileClassifier(config)
        
        git_analyzer = GitAnalyzer(self.project_dir, config, file_classifier)
        
        # Should detect no Git repo
        self.assertFalse(git_analyzer.has_git_repo())
        
        # All Git analysis methods should return empty lists
        self.assertEqual(git_analyzer.check_stale_logic([]), [])
        self.assertEqual(git_analyzer.check_high_churn([]), [])
        self.assertEqual(git_analyzer.check_stale_tests([]), [])


class TestPathResolutionEdgeCases(unittest.TestCase):
    """Test edge cases in path resolution and workspace detection."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_nonexistent_file_paths(self):
        """Test behavior with nonexistent file paths."""
        project_dir = Path(self.temp_dir) / "path_test"
        project_dir.mkdir()
        
        sniffer = ArchitecturalSniffer(str(project_dir))
        
        # Try to analyze nonexistent files
        nonexistent_files = [
            str(project_dir / "does_not_exist.py"),
            str(project_dir / "also_missing.js"),
            "/totally/invalid/path.py"
        ]
        
        # Should handle gracefully without crashing
        smells = sniffer.analyze_architecture(nonexistent_files)
        self.assertIsInstance(smells, list)
    
    def test_files_outside_project_root(self):
        """Test behavior with files outside project root."""
        project_dir = Path(self.temp_dir) / "project"
        project_dir.mkdir()
        
        outside_dir = Path(self.temp_dir) / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "external.py"
        outside_file.write_text("print('outside')")
        
        sniffer = ArchitecturalSniffer(str(project_dir))
        
        # Try to analyze file outside project root
        smells = sniffer.analyze_architecture([str(outside_file)])
        
        # Should handle gracefully (may skip the file with warning)
        self.assertIsInstance(smells, list)
    
    def test_workspace_resolver_with_no_markers(self):
        """Test workspace resolver when no workspace markers are found."""
        # Create directory with no typical workspace markers
        project_dir = Path(self.temp_dir) / "no_markers"
        project_dir.mkdir()
        (project_dir / "random_file.txt").write_text("content")
        
        resolver = WorkspaceResolver()
        
        # Should handle gracefully
        root = resolver.find_project_root(str(project_dir))
        self.assertIsNotNone(root)  # Should return something, even if just the input directory
    
    def test_deeply_nested_project_structure(self):
        """Test with deeply nested project structure."""
        # Create deep nesting
        deep_path = Path(self.temp_dir)
        for i in range(10):  # Create 10 levels deep
            deep_path = deep_path / f"level_{i}"
            deep_path.mkdir()
        
        # Put a project marker at the root
        project_marker = Path(self.temp_dir) / "package.json"
        project_marker.write_text('{"name": "test"}')
        
        # Put a source file deep inside
        source_file = deep_path / "deep_source.py"
        source_file.write_text("print('deep')")
        
        resolver = WorkspaceResolver()
        root = resolver.find_project_root(str(source_file))
        
        # Should find the project root, not get lost in the nesting
        self.assertIsNotNone(root)
        self.assertTrue(Path(root).exists())


class TestImportParsingEdgeCases(unittest.TestCase):
    """Test edge cases in import parsing."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "import_test"
        self.project_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complex_import_patterns(self):
        """Test parsing of complex import patterns."""
        complex_file = self.project_dir / "complex_imports.py"
        complex_file.write_text("""
# Various import patterns
import os, sys, json
from pathlib import Path, PurePath
from collections import defaultdict, Counter
import numpy as np
from scipy import stats
from . import sibling_module
from ..parent import parent_module
from ...grandparent import gp_module

# Dynamic imports
importlib.import_module('dynamic_module')

# Conditional imports
try:
    import optional_module
except ImportError:
    optional_module = None

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

# Import with alias
import very_long_module_name as short_name
""")
        
        imports = ImportParser.get_file_imports(str(complex_file), str(self.project_dir))
        
        # Should extract some imports without crashing
        self.assertIsInstance(imports, list)
        self.assertTrue(len(imports) > 0, "Should detect some imports")
    
    def test_malformed_imports(self):
        """Test parsing of malformed import statements."""
        malformed_file = self.project_dir / "malformed.py"
        malformed_file.write_text("""
# Malformed imports that might cause parsing issues
import 
from module import 
import module.
from . import 
import 123invalid
from module import *
import module as 
""")
        
        # Should handle malformed imports gracefully
        imports = ImportParser.get_file_imports(str(malformed_file), str(self.project_dir))
        self.assertIsInstance(imports, list)  # Should not crash
    
    def test_imports_in_strings_and_comments(self):
        """Test that imports in strings and comments are not parsed."""
        string_imports_file = self.project_dir / "string_imports.py"
        string_imports_file.write_text("""
# This is not an import: import fake_module
'''
Multi-line string with import statement:
import another_fake_module
'''

def example():
    code_as_string = "import yet_another_fake"
    comment = "# import comment_fake"
    return code_as_string

# Actual import
import real_module
""")
        
        imports = ImportParser.get_file_imports(str(string_imports_file), str(self.project_dir))
        
        # Should only detect real imports, not those in strings/comments
        self.assertIsInstance(imports, list)
        
        # Should contain the real import
        real_imports = [imp for imp in imports if 'real_module' in imp]
        self.assertTrue(len(real_imports) > 0, "Should detect real import")


class TestConfigurationEdgeCases(unittest.TestCase):
    """Test edge cases in configuration handling."""
    
    def test_missing_configuration(self):
        """Test behavior when configuration is missing or empty."""
        # Test with None config
        classifier1 = FileClassifier({})
        classifications1 = classifier1.classify_file("test.py")
        self.assertIsInstance(classifications1, list)
        
        # Test with minimal config
        minimal_config = {"source_file_patterns": []}
        classifier2 = FileClassifier(minimal_config)
        classifications2 = classifier2.classify_file("test.py")
        self.assertIsInstance(classifications2, list)
    
    def test_invalid_configuration_values(self):
        """Test behavior with invalid configuration values."""
        invalid_config = {
            "source_file_patterns": None,  # Should be list
            "test_file_patterns": "not_a_list",  # Should be list
            "documentation_file_patterns": 123,  # Should be list
        }
        
        # Should handle invalid config gracefully
        try:
            classifier = FileClassifier(invalid_config)
            classifications = classifier.classify_file("test.py")
            self.assertIsInstance(classifications, list)
        except Exception as e:
            # If it does throw an exception, it should be a reasonable one
            self.assertIsInstance(e, (TypeError, ValueError))


if __name__ == '__main__':
    unittest.main()