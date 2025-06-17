#!/usr/bin/env python3
"""
Integration Test Suite for Project-Analyzer Refactored Modules

This script validates that all refactored modules work together correctly
and that the public API maintains backward compatibility.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add the analyzer module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'analyzer'))

def test_imports():
    """Test that all refactored modules can be imported without errors."""
    print("Testing imports...")
    
    try:
        from analyzer import ArchitecturalSniffer, FileClassifier, WorkspaceResolver, PatternAnalyzer, GitAnalyzer
        from analyzer.architectural_analysis import ArchitecturalSniffer as DirectImport
        print("  All imports successful")
        return True
    except ImportError as e:
        print(f"  Import failed: {e}")
        return False

def test_file_classifier():
    """Test FileClassifier functionality."""
    print("Testing FileClassifier...")
    
    try:
        from analyzer.file_classifier import FileClassifier
        
        config = {
            "source_file_patterns": ["*.py", "*.js", "*.ts"],
            "test_file_patterns": ["test_*", "*_test.py"],
            "documentation_file_patterns": ["*.md", "*.rst"],
            "config_file_patterns": ["*.json", "*.yaml", "*.yml"]
        }
        
        classifier = FileClassifier(config)
        
        # Test various file classifications
        test_cases = [
            ("src/main.py", ["source", "python"]),
            ("tests/test_main.py", ["test", "python"]),
            ("README.md", ["documentation"]),
            ("config.json", ["config", "data_config"]),
            ("app.js", ["source", "javascript_typescript"])
        ]
        
        for file_path, expected_categories in test_cases:
            result = classifier.classify_file(file_path)
            if any(cat in result for cat in expected_categories):
                print(f"  {file_path} classified correctly: {result}")
            else:
                print(f"  {file_path} classification failed. Expected: {expected_categories}, Got: {result}")
                return False
        
        return True
    except Exception as e:
        print(f"  FileClassifier test failed: {e}")
        return False

def test_workspace_resolver():
    """Test WorkspaceResolver functionality."""
    print("✅ Testing WorkspaceResolver...")
    
    try:
        from analyzer.workspace_resolver import WorkspaceResolver
        
        # Create a temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock project structure
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()
            (project_dir / "package.json").touch()
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.js").touch()
            
            resolver = WorkspaceResolver()
            root = resolver.find_project_root(str(project_dir / "src"))
            
            if root and Path(root) == project_dir:
                print(f"  ✓ Project root found correctly: {root}")
                
                # Test path resolution
                relative_path = resolver.get_relative_path(str(project_dir / "src" / "main.js"))
                if relative_path:
                    print(f"  ✓ Relative path resolution works: {relative_path}")
                    return True
                else:
                    print("  ❌ Relative path resolution failed")
                    return False
            else:
                print(f"  ❌ Project root detection failed. Expected: {project_dir}, Got: {root}")
                return False
                
    except Exception as e:
        print(f"  ❌ WorkspaceResolver test failed: {e}")
        return False

def test_pattern_analyzer():
    """Test PatternAnalyzer functionality."""
    print("✅ Testing PatternAnalyzer...")
    
    try:
        from analyzer.pattern_analysis import PatternAnalyzer
        
        config = {"architectural_patterns": {}}
        analyzer = PatternAnalyzer(config)
        
        # Test with a simple dependency graph that has a cycle
        dependency_graph = {
            "file1.py": ["file2.py"],
            "file2.py": ["file3.py"],
            "file3.py": ["file1.py"]  # Creates a cycle
        }
        
        file_classifications = {
            "file1.py": ["source", "python"],
            "file2.py": ["source", "python"],
            "file3.py": ["source", "python"]
        }
        
        code_metrics = {}
        
        patterns = analyzer.analyze_patterns(dependency_graph, file_classifications, code_metrics)
        
        if patterns.get("cyclic_dependencies", {}).get("detected"):
            print("  ✓ Cyclic dependency detection works")
            return True
        else:
            print("  ❌ Cyclic dependency detection failed")
            return False
            
    except Exception as e:
        print(f"  ❌ PatternAnalyzer test failed: {e}")
        return False

def test_architectural_sniffer():
    """Test the main ArchitecturalSniffer integration."""
    print("✅ Testing ArchitecturalSniffer integration...")
    
    try:
        from analyzer.architectural_analysis import ArchitecturalSniffer
        
        # Create a temporary project
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()
            (project_dir / "package.json").touch()
            
            # Create some test files
            src_dir = project_dir / "src"
            src_dir.mkdir()
            (src_dir / "main.py").write_text("import utils\n")
            (src_dir / "utils.py").write_text("# utility functions\n")
            
            sniffer = ArchitecturalSniffer(str(project_dir))
            file_paths = [str(src_dir / "main.py"), str(src_dir / "utils.py")]
            
            # Run analysis
            smells = sniffer.analyze_architecture(file_paths)
            
            # Should complete without errors
            print(f"  ✓ Analysis completed. Found {len(smells)} architectural issues")
            return True
            
    except Exception as e:
        print(f"  ❌ ArchitecturalSniffer integration test failed: {e}")
        return False

def test_git_analyzer():
    """Test GitAnalyzer functionality."""
    print("✅ Testing GitAnalyzer...")
    
    try:
        from analyzer.git_analysis import GitAnalyzer
        from analyzer.file_classifier import FileClassifier
        
        config = {"source_file_patterns": [".py"]}
        file_classifier = FileClassifier(config)
        
        # Test with a non-git directory (should gracefully handle)
        with tempfile.TemporaryDirectory() as temp_dir:
            git_analyzer = GitAnalyzer(Path(temp_dir), config, file_classifier)
            
            if not git_analyzer.has_git_repo():
                print("  ✓ Git analyzer correctly detects non-Git directory")
                
                # Test methods with no git repo (should return empty lists)
                smells = git_analyzer.check_stale_logic([])
                if smells == []:
                    print("  ✓ Stale logic check works without Git")
                    return True
                else:
                    print("  ❌ Stale logic check failed")
                    return False
            else:
                print("  ❌ Git detection failed")
                return False
                
    except Exception as e:
        print(f"  ❌ GitAnalyzer test failed: {e}")
        return False

def test_caching_system():
    """Test that the caching system works correctly."""
    print("✅ Testing caching system...")
    
    try:
        from analyzer.utils import load_cache, save_cache, get_project_hash
        
        # Test basic caching operations
        test_cache = {"test_key": "test_value"}
        save_cache(test_cache)
        loaded_cache = load_cache()
        
        if loaded_cache.get("test_key") == "test_value":
            print("  ✓ Basic caching works")
            
            # Test project hash generation
            test_files = [__file__]
            hash1 = get_project_hash(test_files)
            hash2 = get_project_hash(test_files)
            
            if hash1 == hash2:
                print("  ✓ Project hash generation is consistent")
                return True
            else:
                print("  ❌ Project hash generation inconsistent")
                return False
        else:
            print("  ❌ Basic caching failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Caching system test failed: {e}")
        return False

def run_integration_tests():
    """Run all integration tests."""
    print("Project-Analyzer Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_file_classifier,
        test_workspace_resolver,
        test_pattern_analyzer,
        test_git_analyzer,
        test_architectural_sniffer,
        test_caching_system
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}\n")
    
    print("=" * 50)
    print(f"Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! The refactored modules are working correctly.")
        return True
    else:
        print("❌ Some integration tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)