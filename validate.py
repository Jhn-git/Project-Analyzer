#!/usr/bin/env python3
"""
Validation script to check if Project Analyzer is set up correctly
Run this after installation to verify everything works
"""

import sys
import os
import subprocess
import json
from pathlib import Path

def check_mark(success):
    return "✅" if success else "❌"

def test_basic_functionality():
    """Test basic project analysis functionality"""
    print("🧪 Testing basic functionality...")
    
    tests = [
        ("Help command", ["python", "project_analyzer.py", "--help"]),
        ("Basic analysis", ["python", "project_analyzer.py"]),
        ("JSON output", ["python", "project_analyzer.py", "--json"]),
        ("Markdown output", ["python", "project_analyzer.py", "--markdown"])
    ]
    
    results = []
    for test_name, command in tests:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            success = result.returncode == 0
            results.append((test_name, success, result.stderr if not success else ""))
            print(f"   {check_mark(success)} {test_name}")
            if not success:
                print(f"      Error: {result.stderr[:100]}...")
        except subprocess.TimeoutExpired:
            results.append((test_name, False, "Timeout"))
            print(f"   ❌ {test_name} (timeout)")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"   ❌ {test_name} (error: {e})")
    
    return results

def test_json_validity():
    """Test that JSON output is valid"""
    print("🔍 Testing JSON output validity...")
    try:
        result = subprocess.run(["python", "project_analyzer.py", "--json"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            json.loads(result.stdout)  # This will raise an exception if invalid
            print("   ✅ JSON output is valid")
            return True
        else:
            print("   ❌ Failed to generate JSON")
            return False
    except json.JSONDecodeError:
        print("   ❌ JSON output is malformed")
        return False
    except Exception as e:
        print(f"   ❌ Error testing JSON: {e}")
        return False

def test_dependencies():
    """Test that all dependencies are installed"""
    print("📦 Testing dependencies...")
    
    dependencies = [
        "google.generativeai",
        "dotenv", 
        "requests",
        "pathlib",
        "json",
        "os",
        "subprocess"
    ]
    
    success = True
    for dep in dependencies:
        try:
            if dep == "dotenv":
                __import__("dotenv")
            elif dep == "google.generativeai":
                __import__("google.generativeai")
            else:
                __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} (not installed)")
            success = False
    
    return success

def test_file_structure():
    """Test that all required files exist"""
    print("📁 Testing file structure...")
    
    required_files = [
        "project_analyzer.py",
        "requirements.txt",
        "README.md",
        "LICENSE",
        "setup.py",
        ".env.example",
        ".gitignore"
    ]
    
    success = True
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (missing)")
            success = False
    
    return success

def test_ai_setup():
    """Test AI functionality setup (without requiring API key)"""
    print("🤖 Testing AI setup...")
      # Test that the model listing script exists and can be imported
    try:
        result = subprocess.run(["python", "list_gemini_models.py"], 
                              capture_output=True, text=True, timeout=10)
        # It should fail without API key, but not with import errors
        if ("Error: GOOGLE_API_KEY not found" in result.stdout or 
            "API key not valid" in result.stderr or
            "API_KEY_INVALID" in result.stderr):
            print("   ✅ AI modules load correctly (API key needed for full functionality)")
            return True
        elif result.returncode == 0:
            print("   ✅ AI functionality fully working")
            return True
        else:
            print(f"   ❌ AI setup issue: {result.stderr[:100]}...")
            return False
    except Exception as e:
        print(f"   ❌ AI setup error: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🚀 Project Analyzer Validation")
    print("=" * 35)
    
    all_tests = [
        ("File Structure", test_file_structure),
        ("Dependencies", test_dependencies),
        ("Basic Functionality", test_basic_functionality),
        ("JSON Validity", test_json_validity),
        ("AI Setup", test_ai_setup)
    ]
    
    results = {}
    for test_name, test_func in all_tests:
        print(f"\n{test_name}:")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"   ❌ Test failed with error: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 35)
    print("📊 Validation Summary:")
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        print(f"   {check_mark(success)} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Project Analyzer is ready to use.")
        print("\n📖 Quick start:")
        print("   python project_analyzer.py")
        print("   python project_analyzer.py --help")
        print("\n💡 For AI features, add your Google API key to .env file")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        print("💡 Try running 'python setup.py' to fix common issues.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
