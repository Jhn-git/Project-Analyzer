#!/usr/bin/env python3
"""
Comprehensive Validation Test Suite

This test validates the complete Project-Analyzer pipeline end-to-end,
testing against the Project-Analyzer itself and a sample project structure.
This ensures all fixes are working correctly and no regressions exist.
"""

import unittest
import tempfile
import os
import shutil
import json
from pathlib import Path
import sys

# Add analyzer to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analyzer'))

from analyzer.architectural_analysis import ArchitecturalSniffer
from analyzer.file_classifier import FileClassifier
from analyzer.report_generators import format_architectural_summary, get_file_structure_from_data


class TestProjectAnalyzerSelfAnalysis(unittest.TestCase):
    """Test Project-Analyzer by analyzing itself."""
    
    def setUp(self):
        """Set up test environment."""
        # Get the Project-Analyzer root directory
        self.analyzer_root = Path(__file__).parent.parent
        self.assertTrue(self.analyzer_root.exists(), "Project-Analyzer root should exist")
    
    def test_self_analysis_file_classification(self):
        """Test that Project-Analyzer files are properly classified."""
        config = {
            "source_file_patterns": ["*.py"],
            "test_file_patterns": ["test_*"],
            "documentation_file_patterns": ["*.md", "*.txt", "README*", "LICENSE*", "CONTRIBUTING*", "CHANGELOG*"],
            "config_file_patterns": ["*.json", "*.yaml", "*.yml", ".env*"],
            "project_lifecycle_patterns": [".gitignore", "setup.py", "requirements.txt"]
        }
        classifier = FileClassifier(config)
        
        # Test key Project-Analyzer files
        test_files = {
            "README.md": "documentation",
            "LICENSE": "documentation", 
            "CHANGELOG.md": "documentation",
            "CONTRIBUTING.md": "documentation",
            ".gitignore": "project_lifecycle",
            ".env.example": "config",
            "requirements.txt": "project_lifecycle",
            "setup.py": "project_lifecycle",
            "analyzer/main.py": "source",
            "analyzer/file_classifier.py": "source",
            "analyzer/architectural_analysis.py": "source"
        }
        
        for file_path, expected_classification in test_files.items():
            full_path = self.analyzer_root / file_path
            if full_path.exists():
                with self.subTest(file=file_path):
                    classifications = classifier.classify_file(str(full_path))
                    self.assertIn(expected_classification, classifications,
                                f"File {file_path} should be classified as {expected_classification}, got: {classifications}")
    
    def test_self_analysis_no_false_positives(self):
        """Test that Project-Analyzer doesn't flag its own files as issues."""
        # Get source files from analyzer directory
        analyzer_dir = self.analyzer_root / "analyzer"
        if not analyzer_dir.exists():
            self.skipTest("Analyzer directory not found")
        
        source_files = []
        for py_file in analyzer_dir.glob("*.py"):
            source_files.append(str(py_file))
        
        if not source_files:
            self.skipTest("No source files found")
        
        # Run analysis
        sniffer = ArchitecturalSniffer(str(self.analyzer_root))
        smells = sniffer.analyze_architecture(source_files[:10])  # Limit for test performance
        
        # Check for common false positives
        unclassified_smells = [s for s in smells if s.get("type") == "UNCLASSIFIED_FILE"]
        self.assertEqual(len(unclassified_smells), 0,
                        f"Project-Analyzer should not flag its own files as unclassified: {unclassified_smells}")
        
        # The analysis should complete without crashing
        self.assertIsInstance(smells, list)
    
    def test_self_analysis_output_formatting(self):
        """Test that self-analysis produces well-formatted output."""
        # Analyze a few key files
        key_files = []
        analyzer_dir = self.analyzer_root / "analyzer"
        
        for filename in ["main.py", "file_classifier.py", "architectural_analysis.py"]:
            file_path = analyzer_dir / filename
            if file_path.exists():
                key_files.append(str(file_path))
        
        if not key_files:
            self.skipTest("Key analyzer files not found")
        
        sniffer = ArchitecturalSniffer(str(self.analyzer_root))
        smells = sniffer.analyze_architecture(key_files)
        
        # Format the output
        summary = format_architectural_summary(smells, markdown=False)
        
        # Output should be readable
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)
        
        # Should not contain raw data dumps
        self.assertNotIn("{'", summary)
        self.assertNotIn("[{", summary)
        self.assertNotIn("defaultdict", summary)


class TestSampleProjectAnalysis(unittest.TestCase):
    """Test with a comprehensive sample project."""
    
    def setUp(self):
        """Create a realistic sample project for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "sample_project"
        self.project_dir.mkdir()
        
        # Create comprehensive project structure
        self._create_sample_project()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_sample_project(self):
        """Create a realistic sample project structure."""
        # Documentation files
        (self.project_dir / "README.md").write_text("""
# Sample Project

This is a sample project for testing the Project-Analyzer.

## Features
- Feature A
- Feature B
- Feature C

## Installation
pip install -r requirements.txt

## Usage
python src/main.py
""")
        
        (self.project_dir / "LICENSE").write_text("MIT License\n\nCopyright (c) 2023 Test Project")
        
        (self.project_dir / "CHANGELOG.md").write_text("""
# Changelog

## [1.0.0] - 2023-01-01
- Initial release
- Added feature A
- Added feature B
""")
        
        (self.project_dir / "CONTRIBUTING.md").write_text("""
# Contributing

Thank you for your interest in contributing!

## Guidelines
1. Fork the repository
2. Create a feature branch
3. Submit a pull request
""")
        
        # Configuration files
        (self.project_dir / ".gitignore").write_text("""
*.pyc
__pycache__/
.venv/
.env
*.log
dist/
build/
""")
        
        (self.project_dir / ".env.example").write_text("""
DATABASE_URL=sqlite:///app.db
SECRET_KEY=your-secret-key-here
DEBUG=True
""")
        
        (self.project_dir / "requirements.txt").write_text("""
requests>=2.28.0
flask>=2.2.0
pytest>=7.0.0
black>=22.0.0
""")
        
        (self.project_dir / "setup.py").write_text("""
from setuptools import setup, find_packages

setup(
    name="sample-project",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "flask>=2.2.0",
    ],
)
""")
        
        (self.project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[tool.black]
line-length = 88
target-version = ['py38']
""")
        
        # Source code
        src_dir = self.project_dir / "src"
        src_dir.mkdir()
        
        (src_dir / "__init__.py").write_text("")
        
        (src_dir / "main.py").write_text("""
import sys
from pathlib import Path

from config import Config
from database import Database
from api.server import create_app
from utils.logger import setup_logging


def main():
    '''Main application entry point.'''
    config = Config()
    setup_logging(config.log_level)
    
    db = Database(config.database_url)
    app = create_app(db)
    
    app.run(host=config.host, port=config.port, debug=config.debug)


if __name__ == "__main__":
    main()
""")
        
        (src_dir / "config.py").write_text("""
import os
from dataclasses import dataclass


@dataclass
class Config:
    '''Application configuration.'''
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    secret_key: str = os.getenv('SECRET_KEY', 'dev-key')
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    host: str = os.getenv('HOST', '127.0.0.1')
    port: int = int(os.getenv('PORT', '5000'))
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
""")
        
        (src_dir / "database.py").write_text("""
import sqlite3
from typing import Optional, List, Dict, Any


class Database:
    '''Simple database wrapper.'''
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection: Optional[sqlite3.Connection] = None
    
    def connect(self):
        '''Connect to the database.'''
        self.connection = sqlite3.connect(self.database_url)
        self.connection.row_factory = sqlite3.Row
    
    def disconnect(self):
        '''Disconnect from the database.'''
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        '''Execute a query and return results.'''
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
""")
        
        # API module
        api_dir = src_dir / "api"
        api_dir.mkdir()
        (api_dir / "__init__.py").write_text("")
        
        (api_dir / "server.py").write_text("""
from flask import Flask, jsonify, request
from database import Database


def create_app(database: Database) -> Flask:
    '''Create and configure the Flask application.'''
    app = Flask(__name__)
    app.database = database
    
    @app.route('/')
    def index():
        return jsonify({'message': 'Welcome to Sample Project API'})
    
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy'})
    
    @app.route('/users')
    def list_users():
        users = app.database.execute('SELECT * FROM users')
        return jsonify({'users': users})
    
    @app.route('/users/<int:user_id>')
    def get_user(user_id):
        users = app.database.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        if not users:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': users[0]})
    
    return app
""")
        
        # Utils module
        utils_dir = src_dir / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text("")
        
        (utils_dir / "logger.py").write_text("""
import logging
import sys


def setup_logging(level: str = 'INFO'):
    '''Setup application logging.'''
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )


def get_logger(name: str) -> logging.Logger:
    '''Get a logger instance.'''
    return logging.getLogger(name)
""")
        
        (utils_dir / "helpers.py").write_text("""
import hashlib
import secrets
from typing import Dict, Any


def generate_token(length: int = 32) -> str:
    '''Generate a secure random token.'''
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: str = None) -> Dict[str, str]:
    '''Hash a password with salt.'''
    if salt is None:
        salt = secrets.token_hex(16)
    
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return {
        'hash': password_hash.hex(),
        'salt': salt
    }


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    '''Verify a password against its hash.'''
    computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return computed_hash.hex() == password_hash
""")
        
        # Tests
        tests_dir = self.project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        
        (tests_dir / "test_main.py").write_text("""
import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import main
from config import Config


class TestMain(unittest.TestCase):
    '''Test the main application entry point.'''
    
    @patch('main.create_app')
    @patch('main.Database')
    @patch('main.setup_logging')
    def test_main_function(self, mock_setup_logging, mock_database, mock_create_app):
        '''Test that main function initializes everything correctly.'''
        mock_app = Mock()
        mock_create_app.return_value = mock_app
        
        with patch('main.Config') as mock_config:
            mock_config_instance = Mock()
            mock_config.return_value = mock_config_instance
            
            main()
            
            mock_setup_logging.assert_called_once()
            mock_database.assert_called_once()
            mock_create_app.assert_called_once()
            mock_app.run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
""")
        
        (tests_dir / "test_config.py").write_text("""
import unittest
import os
from unittest.mock import patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config


class TestConfig(unittest.TestCase):
    '''Test configuration loading.'''
    
    def test_default_config(self):
        '''Test default configuration values.'''
        config = Config()
        self.assertEqual(config.host, '127.0.0.1')
        self.assertEqual(config.port, 5000)
        self.assertFalse(config.debug)
    
    @patch.dict(os.environ, {
        'HOST': '0.0.0.0',
        'PORT': '8000',
        'DEBUG': 'true'
    })
    def test_environment_config(self):
        '''Test configuration from environment variables.'''
        config = Config()
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8000)
        self.assertTrue(config.debug)


if __name__ == '__main__':
    unittest.main()
""")
        
        (tests_dir / "test_database.py").write_text("""
import unittest
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import Database


class TestDatabase(unittest.TestCase):
    '''Test database functionality.'''
    
    def setUp(self):
        '''Set up test database.'''
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = Database(self.temp_db.name)
    
    def tearDown(self):
        '''Clean up test database.'''
        self.db.disconnect()
        os.unlink(self.temp_db.name)
    
    def test_connection(self):
        '''Test database connection.'''
        self.db.connect()
        self.assertIsNotNone(self.db.connection)
        
        self.db.disconnect()
        self.assertIsNone(self.db.connection)
    
    def test_execute_query(self):
        '''Test query execution.'''
        # Create test table
        self.db.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        self.db.execute("INSERT INTO test (id, name) VALUES (1, 'Test')")
        
        # Query data
        results = self.db.execute("SELECT * FROM test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Test')


if __name__ == '__main__':
    unittest.main()
""")
    
    def test_sample_project_file_classification(self):
        """Test that all sample project files are properly classified."""
        config = {
            "source_file_patterns": ["*.py"],
            "test_file_patterns": ["test_*"],
            "documentation_file_patterns": ["*.md", "*.txt", "README*", "LICENSE*", "CONTRIBUTING*", "CHANGELOG*"],
            "config_file_patterns": ["*.json", "*.yaml", "*.yml", "*.toml", ".env*"],
            "project_lifecycle_patterns": [".gitignore", "setup.py", "requirements.txt"]
        }
        classifier = FileClassifier(config)
        
        # Expected classifications for key files
        expected_classifications = {
            "README.md": "documentation",
            "LICENSE": "documentation",
            "CHANGELOG.md": "documentation", 
            "CONTRIBUTING.md": "documentation",
            ".gitignore": "project_lifecycle",
            ".env.example": "config",
            "requirements.txt": "project_lifecycle",
            "setup.py": "project_lifecycle",
            "pyproject.toml": "config",
            "src/main.py": "source",
            "src/config.py": "source",
            "src/database.py": "source",
            "tests/test_main.py": "test"
        }
        
        for file_path, expected_type in expected_classifications.items():
            full_path = self.project_dir / file_path
            with self.subTest(file=file_path):
                classifications = classifier.classify_file(str(full_path))
                self.assertIn(expected_type, classifications,
                            f"File {file_path} should contain '{expected_type}' classification, got: {classifications}")
    
    def test_sample_project_no_false_positives(self):
        """Test that sample project doesn't generate false positive issues."""
        # Get all Python source files
        source_files = []
        for py_file in self.project_dir.rglob("*.py"):
            source_files.append(str(py_file))
        
        self.assertTrue(len(source_files) > 0, "Should find some Python files")
        
        # Run analysis
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        smells = sniffer.analyze_architecture(source_files)
        
        # Should not flag documentation/config files as unclassified
        unclassified_smells = [s for s in smells if s.get("type") == "UNCLASSIFIED_FILE"]
        self.assertEqual(len(unclassified_smells), 0,
                        f"Well-structured project should not have unclassified files: {unclassified_smells}")
        
        # Analysis should complete successfully
        self.assertIsInstance(smells, list)
    
    def test_sample_project_output_quality(self):
        """Test that sample project produces high-quality, readable output."""
        # Analyze subset of files for performance
        key_files = [
            str(self.project_dir / "src" / "main.py"),
            str(self.project_dir / "src" / "config.py"),
            str(self.project_dir / "src" / "database.py"),
            str(self.project_dir / "src" / "api" / "server.py")
        ]
        
        sniffer = ArchitecturalSniffer(str(self.project_dir))
        smells = sniffer.analyze_architecture(key_files)
        
        # Format output
        summary = format_architectural_summary(smells, markdown=False)
        
        # Output quality checks
        self.assertIsInstance(summary, str)
        
        if smells:  # If issues were found
            # Should contain structured information
            self.assertIn("🏗️", summary)
            
            # Should not contain raw technical dumps
            self.assertNotIn("defaultdict", summary)
            self.assertNotIn("{'type':", summary)
            
            # Should be multi-line formatted
            lines = summary.split('\n')
            self.assertGreater(len(lines), 1, "Should be multi-line output")
        else:  # If no issues (also good)
            self.assertIn("✅", summary)
            self.assertIn("No architectural issues", summary)
    
    def test_complete_pipeline_integration(self):
        """Test the complete analysis pipeline with all components."""
        # Test file structure analysis
        file_data = {
            'all_files': list(str(f) for f in self.project_dir.rglob("*") if f.is_file()),
            'all_directories': list(str(d) for d in self.project_dir.rglob("*") if d.is_dir()),
            'source_directories': [str(self.project_dir / "src")],
            'script_files': list(str(f) for f in self.project_dir.rglob("*.py"))
        }
        
        # Test different output formats
        text_output = get_file_structure_from_data(str(self.project_dir), file_data, markdown=False)
        self.assertIn("📁 Project Structure Analysis", text_output)
        self.assertIn("Source Directories", text_output)
        
        json_output = get_file_structure_from_data(str(self.project_dir), file_data, json_output=True)
        json_data = json.loads(json_output)
        self.assertIn("total_files", json_data)
        self.assertIn("source_directories", json_data)
        
        markdown_output = get_file_structure_from_data(str(self.project_dir), file_data, markdown=True)
        self.assertIn("**", markdown_output)  # Should contain markdown formatting
        
        # All formats should complete without errors
        self.assertTrue(len(text_output) > 0)
        self.assertTrue(len(json_output) > 0)
        self.assertTrue(len(markdown_output) > 0)


if __name__ == '__main__':
    unittest.main()