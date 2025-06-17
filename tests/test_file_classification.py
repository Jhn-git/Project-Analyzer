#!/usr/bin/env python3
"""
Test File Classification

Tests for validating that files are properly classified and NOT flagged as issues.
This addresses the user-reported issue with file classification false positives.
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add analyzer to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analyzer'))

from analyzer.file_classifier import FileClassifier


class TestFileClassification(unittest.TestCase):
    """Test file classification functionality."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = {
            "source_file_patterns": ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"],
            "test_file_patterns": ["test_*", "*_test.py", "*.test.js", "*.spec.js"],
            "documentation_file_patterns": ["*.md", "*.txt", "README*", "LICENSE*", "CONTRIBUTING*", "CHANGELOG*"],
            "config_file_patterns": ["*.json", "*.yaml", "*.yml", "*.xml", "*.ini", "*.toml", "*.cfg", "config*", ".env*"],
            "ignore_file_patterns": ["*.pyc", "*.pyo", "*.pyd", "__pycache__", ".DS_Store"],
            "project_lifecycle_patterns": [".gitignore", "setup.py", "requirements.txt", "Dockerfile", "docker-compose.yml"]
        }
        self.classifier = FileClassifier(self.config)
    
    def test_readme_files_classified_as_documentation(self):
        """Test that README files are properly classified as documentation."""
        test_cases = [
            "README.md",
            "README.txt", 
            "README",
            "readme.md",
            "Readme.md"
        ]
        
        for file_path in test_cases:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                self.assertIn("documentation", classifications, 
                             f"README file {file_path} should be classified as documentation")
                # Should NOT be flagged as unclassified
                self.assertTrue(len(classifications) > 0, 
                               f"README file {file_path} should have classifications")
    
    def test_changelog_files_classified_as_documentation(self):
        """Test that CHANGELOG files are properly classified as documentation."""
        test_cases = [
            "CHANGELOG.md",
            "CHANGELOG.txt",
            "CHANGELOG",
            "changelog.md",
            "Changelog.md"
        ]
        
        for file_path in test_cases:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                self.assertIn("documentation", classifications, 
                             f"CHANGELOG file {file_path} should be classified as documentation")
    
    def test_license_files_classified_correctly(self):
        """Test that LICENSE files are properly classified."""
        test_cases = [
            "LICENSE",
            "LICENSE.txt",
            "LICENSE.md",
            "license",
            "License.txt"
        ]
        
        for file_path in test_cases:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                self.assertIn("documentation", classifications, 
                             f"LICENSE file {file_path} should be classified as documentation")
    
    def test_gitignore_files_classified_as_config(self):
        """Test that .gitignore files are properly classified as configuration."""
        test_cases = [
            ".gitignore",
            "path/to/.gitignore"
        ]
        
        for file_path in test_cases:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                # Should be classified as project_lifecycle due to specific pattern matching
                self.assertTrue("project_lifecycle" in classifications or "config" in classifications,
                               f".gitignore file {file_path} should be classified as project_lifecycle or config")
    
    def test_env_files_classified_as_config(self):
        """Test that .env files are properly classified as configuration."""
        test_cases = [
            ".env",
            ".env.example",
            ".env.local", 
            ".env.production",
            "config/.env"
        ]
        
        for file_path in test_cases:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                self.assertIn("config", classifications, 
                             f"Environment file {file_path} should be classified as config")
    
    def test_source_files_classified_correctly(self):
        """Test that source code files are properly classified."""
        test_cases = [
            ("src/main.py", "python"),
            ("app.js", "javascript_typescript"),
            ("component.tsx", "javascript_typescript"),
            ("utils.ts", "javascript_typescript"),
            ("main.java", "java"),
            ("app.go", "go"),
            ("script.rb", "ruby")
        ]
        
        for file_path, expected_language in test_cases:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                self.assertIn("source", classifications, 
                             f"Source file {file_path} should be classified as source")
                self.assertIn(expected_language, classifications,
                             f"Source file {file_path} should be classified as {expected_language}")
    
    def test_no_false_positive_unclassified_files(self):
        """Test that common project files are not flagged as unclassified."""
        # These files should all have proper classifications
        well_known_files = [
            "README.md",
            "LICENSE", 
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            ".gitignore",
            ".env.example",
            "package.json",
            "requirements.txt",
            "setup.py",
            "Dockerfile",
            "docker-compose.yml",
            "config.yaml",
            "settings.ini"
        ]
        
        for file_path in well_known_files:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                self.assertTrue(len(classifications) > 0, 
                               f"Well-known file {file_path} should have classifications, got: {classifications}")
    
    def test_ignore_patterns_work(self):
        """Test that files matching ignore patterns are properly ignored."""
        ignored_files = [
            "__pycache__/module.pyc",
            "file.pyc",
            ".DS_Store",
            "temp.pyo"
        ]
        
        for file_path in ignored_files:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                self.assertEqual([], classifications, 
                               f"Ignored file {file_path} should return empty classifications")
    
    def test_multiple_classifications(self):
        """Test that files can have multiple valid classifications."""
        # A Python test file should be both 'test' and 'python'
        classifications = self.classifier.classify_file("tests/test_main.py")
        self.assertIn("test", classifications)
        self.assertIn("python", classifications)
        
        # A config JSON file should be both 'config' and 'data_config'
        classifications = self.classifier.classify_file("config.json")
        self.assertIn("config", classifications)
        self.assertIn("data_config", classifications)
    
    def test_pattern_matching_case_insensitive(self):
        """Test that pattern matching works case-insensitively where appropriate."""
        test_cases = [
            "README.MD",  # Should match .md pattern
            "LICENSE.TXT",  # Should match .txt pattern
            "Config.JSON"  # Should match .json pattern
        ]
        
        for file_path in test_cases:
            with self.subTest(file=file_path):
                classifications = self.classifier.classify_file(file_path)
                self.assertTrue(len(classifications) > 0, 
                               f"Case-variant file {file_path} should be classified")


class TestFileClassificationIntegration(unittest.TestCase):
    """Integration tests with real file system."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = {
            "source_file_patterns": ["*.py", "*.js", "*.ts"],
            "test_file_patterns": ["test_*", "*_test.py"],
            "documentation_file_patterns": ["*.md", "*.txt", "README*", "LICENSE*"],
            "config_file_patterns": ["*.json", "*.yaml", "*.yml", ".env*"],
            "project_lifecycle_patterns": [".gitignore", "setup.py", "requirements.txt"]
        }
        self.classifier = FileClassifier(self.config)
    
    def test_with_temporary_files(self):
        """Test classification with actual temporary files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = {
                "README.md": "documentation",
                "main.py": "source", 
                "test_main.py": "test",
                ".gitignore": "project_lifecycle",
                "config.json": "config"
            }
            
            for filename, expected_type in test_files.items():
                file_path = os.path.join(temp_dir, filename)
                # Create the file
                Path(file_path).touch()
                
                # Test classification
                classifications = self.classifier.classify_file(file_path)
                self.assertIn(expected_type, classifications,
                             f"File {filename} should be classified as {expected_type}, got: {classifications}")


if __name__ == '__main__':
    unittest.main()