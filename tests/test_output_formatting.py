#!/usr/bin/env python3
"""
Test Output Formatting

Tests for validating that architectural analysis produces human-readable output
with proper formatting, color coding, and structure.
"""

import unittest
import tempfile
import os
import re
from pathlib import Path
import sys

# Add analyzer to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analyzer'))

from analyzer.architectural_analysis import ArchitecturalSniffer
from analyzer.report_generators import format_architectural_summary, get_file_structure_from_data
from analyzer.config import ARCHITECTURAL_SMELLS, RESET, BOLD, GREEN


class TestOutputFormatting(unittest.TestCase):
    """Test output formatting functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = None
        self.project_dir = None
    
    def tearDown(self):
        """Clean up test environment."""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_project(self):
        """Create a temporary test project with various file types."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.project_dir.mkdir()
        
        # Create project structure
        (self.project_dir / "README.md").write_text("# Test Project\nA test project for validation.")
        (self.project_dir / "LICENSE").write_text("MIT License")
        (self.project_dir / ".gitignore").write_text("*.pyc\n__pycache__/")
        (self.project_dir / ".env.example").write_text("DATABASE_URL=example")
        
        # Source files
        src_dir = self.project_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("import utils\nprint('Hello World')")
        (src_dir / "utils.py").write_text("def helper():\n    pass")
        (src_dir / "circular_a.py").write_text("import circular_b")
        (src_dir / "circular_b.py").write_text("import circular_a")  # Creates circular dependency
        
        # Test files
        tests_dir = self.project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("def test_main():\n    pass")
        
        return str(self.project_dir)
    
    def test_architectural_summary_formatting_no_issues(self):
        """Test formatting when no architectural issues are found."""
        smells = []
        summary = format_architectural_summary(smells, markdown=False)
        
        # Should contain positive message
        self.assertIn("No architectural issues detected", summary)
        self.assertIn("✅", summary)
        self.assertIn("healthy", summary)
        
        # Should contain ANSI color codes for terminal display
        self.assertIn(GREEN, summary)
        self.assertIn(RESET, summary)
    
    def test_architectural_summary_formatting_with_issues(self):
        """Test formatting when architectural issues are found."""
        smells = [
            {
                "type": "CIRCULAR_DEPENDENCY",
                "file": "src/circular_a.py",
                "line": "N/A",
                "severity": "High",
                "message": "Circular dependency detected: circular_a.py -> circular_b.py -> circular_a.py",
                "category": "Architectural Smell"
            },
            {
                "type": "CIRCULAR_DEPENDENCY", 
                "file": "src/circular_b.py",
                "line": "N/A",
                "severity": "High",
                "message": "Circular dependency detected: circular_b.py -> circular_a.py -> circular_b.py",
                "category": "Architectural Smell"
            },
            {
                "type": "STALE_LOGIC",
                "file": "src/old_module.py",
                "line": "N/A", 
                "severity": "Medium",
                "message": "File hasn't been modified in 6 months",
                "category": "Code Quality"
            }
        ]
        
        summary = format_architectural_summary(smells, markdown=False)
        
        # Should show issue count
        self.assertIn("Architectural Issues Found: 3", summary)
        self.assertIn(BOLD, summary)
        
        # Should group by type
        self.assertIn("CIRCULAR DEPENDENCY", summary)
        self.assertIn("(2 issues)", summary)
        
        # Should show emoji indicators from config
        circular_emoji = ARCHITECTURAL_SMELLS.get("CIRCULAR_DEPENDENCY", "⚠️")
        self.assertIn(circular_emoji, summary)
        
        # Should show readable file names (not full paths)
        self.assertIn("circular_a.py", summary)
        self.assertIn("old_module.py", summary)
        
        # Should contain bullets for individual issues
        self.assertIn("•", summary)
    
    def test_markdown_output_formatting(self):
        """Test that markdown formatting removes ANSI codes and adds markdown syntax."""
        smells = [
            {
                "type": "CIRCULAR_DEPENDENCY",
                "file": "src/test.py",
                "message": "Test circular dependency"
            }
        ]
        
        markdown_summary = format_architectural_summary(smells, markdown=True)
        
        # Should not contain ANSI color codes
        ansi_pattern = re.compile(r'\033\[[0-9;]*m')
        self.assertFalse(ansi_pattern.search(markdown_summary), 
                        "Markdown output should not contain ANSI color codes")
        
        # Should contain markdown formatting
        self.assertIn("**", markdown_summary)
    
    def test_file_structure_formatting(self):
        """Test file structure output formatting."""
        file_data = {
            'all_files': ['README.md', 'src/main.py', 'tests/test_main.py'],
            'all_directories': ['src/', 'tests/'],
            'source_directories': ['src/'],
            'script_files': ['src/main.py', 'tests/test_main.py']
        }
        
        output = get_file_structure_from_data("/test/project", file_data, markdown=False)
        
        # Should contain structured output
        self.assertIn("Project Structure Analysis", output)
        self.assertIn("Total Files: 3", output)
        self.assertIn("Total Directories: 2", output)
        self.assertIn("Script Files: 2", output)
        self.assertIn("Source Directories:", output)
        self.assertIn("src", output)
        
        # Should contain formatting
        self.assertIn(BOLD, output)
        self.assertIn(RESET, output)
    
    def test_json_output_formatting(self):
        """Test JSON output formatting."""
        file_data = {
            'all_files': ['README.md', 'src/main.py'],
            'all_directories': ['src/'],
            'source_directories': ['src/'],
            'script_files': ['src/main.py']
        }
        
        json_output = get_file_structure_from_data("/test/project", file_data, json_output=True)
        
        # Should be valid JSON
        import json
        data = json.loads(json_output)
        
        # Should contain expected fields
        self.assertEqual(data['total_files'], 2)
        self.assertEqual(data['total_directories'], 1)
        self.assertEqual(data['script_files'], 1)
        self.assertEqual(data['source_directories'], ['src/'])
    
    def test_integration_output_formatting(self):
        """Test end-to-end output formatting with real analysis."""
        project_dir = self._create_test_project()
        
        # Run analysis
        sniffer = ArchitecturalSniffer(project_dir)
        src_files = [
            str(self.project_dir / "src" / "main.py"),
            str(self.project_dir / "src" / "utils.py"),
            str(self.project_dir / "src" / "circular_a.py"),
            str(self.project_dir / "src" / "circular_b.py")
        ]
        
        smells = sniffer.analyze_architecture(src_files)
        
        # Format the output
        summary = format_architectural_summary(smells, markdown=False)
        
        # Should be readable and well-formatted
        self.assertTrue(len(summary) > 0, "Summary should not be empty")
        
        # Should not contain raw data dumps
        self.assertNotIn("{'", summary, "Should not contain raw dictionary output")
        self.assertNotIn("[{", summary, "Should not contain raw list output")
        
        # Should contain proper formatting elements
        if smells:  # If issues were found
            self.assertIn("🏗️", summary, "Should contain architecture emoji")
            lines = summary.split('\n')
            # Should have multiple lines (not a single line dump)
            self.assertGreater(len(lines), 1, "Should be multi-line formatted output")
        else:  # If no issues (also valid)
            self.assertIn("✅", summary, "Should contain success indicator")
    
    def test_color_coding_preservation(self):
        """Test that color coding is preserved in terminal output."""
        smells = [
            {
                "type": "HIGH_CHURN",
                "file": "src/volatile.py",
                "message": "File changes frequently"
            }
        ]
        
        terminal_output = format_architectural_summary(smells, markdown=False)
        
        # Should contain ANSI color codes for terminal
        self.assertIn(BOLD, terminal_output)
        self.assertIn(RESET, terminal_output)
    
    def test_severity_based_formatting(self):
        """Test that different severities are handled appropriately."""
        smells = [
            {
                "type": "CIRCULAR_DEPENDENCY",
                "file": "src/a.py",
                "severity": "High",
                "message": "High severity issue"
            },
            {
                "type": "STALE_LOGIC",
                "file": "src/b.py", 
                "severity": "Low",
                "message": "Low severity issue"
            }
        ]
        
        summary = format_architectural_summary(smells, markdown=False)
        
        # Both should be included in output
        self.assertIn("High severity issue", summary)
        self.assertIn("Low severity issue", summary)
        
        # Should group by type regardless of severity
        lines = summary.split('\n')
        issue_lines = [line for line in lines if '•' in line]
        self.assertEqual(len(issue_lines), 2, "Should show both issues")
    
    def test_file_path_readability(self):
        """Test that file paths are displayed in a readable format."""
        smells = [
            {
                "type": "GHOST_FILE",
                "file": "/very/long/project/path/src/deep/nested/module.py",
                "message": "Ghost file detected"
            }
        ]
        
        summary = format_architectural_summary(smells, markdown=False)
        
        # Should show basename, not full path
        self.assertIn("module.py", summary)
        self.assertNotIn("/very/long/project/path", summary)


class TestOutputFormattingEdgeCases(unittest.TestCase):
    """Test edge cases in output formatting."""
    
    def test_empty_smells_list(self):
        """Test formatting with empty smells list."""
        summary = format_architectural_summary([], markdown=False)
        self.assertIn("No architectural issues", summary)
    
    def test_smells_without_file_field(self):
        """Test formatting smells that don't have file field."""
        smells = [
            {
                "type": "MONOLITHIC_STRUCTURE",
                "message": "Project structure is monolithic",
                "severity": "Medium"
                # No 'file' field
            }
        ]
        
        summary = format_architectural_summary(smells, markdown=False)
        self.assertIn("monolithic", summary.lower())
        # Should not crash on missing file field
        self.assertTrue(len(summary) > 0)
    
    def test_large_number_of_issues(self):
        """Test formatting when there are many issues."""
        smells = []
        for i in range(10):
            smells.append({
                "type": "CIRCULAR_DEPENDENCY",
                "file": f"src/file_{i}.py",
                "message": f"Issue {i}"
            })
        
        summary = format_architectural_summary(smells, markdown=False)
        
        # Should show count
        self.assertIn("10 issues", summary)
        
        # Should limit display (show first 3, then "and X more")
        self.assertIn("... and", summary)
        self.assertIn("more", summary)


if __name__ == '__main__':
    unittest.main()