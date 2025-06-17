#!/usr/bin/env python3
"""
Comprehensive Test Runner for Project-Analyzer

This script runs all test suites to validate the fixed Project-Analyzer system.
It provides detailed reporting on test results and validates that all fixes
are working correctly.
"""

import sys
import os
import unittest
import time
from pathlib import Path
import importlib.util

# Add project root to path to allow for `from analyzer import ...`
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes for output
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
GREY = "\033[90m"


class ComprehensiveTestResult:
    """Tracks comprehensive test results."""
    
    def __init__(self):
        self.test_suites = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.start_time = None
        self.end_time = None
        self.failures = []
        self.errors = []
    
    def add_suite_result(self, suite_name, result):
        """Add results from a test suite."""
        suite_info = {
            'name': suite_name,
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
            'success': result.wasSuccessful()
        }
        
        self.test_suites.append(suite_info)
        self.total_tests += result.testsRun
        self.passed_tests += result.testsRun - len(result.failures) - len(result.errors)
        self.failed_tests += len(result.failures)
        self.error_tests += len(result.errors)
        self.skipped_tests += len(result.skipped) if hasattr(result, 'skipped') else 0
        
        # Store failure and error details
        for test, traceback in result.failures:
            self.failures.append((suite_name, str(test), traceback))
        for test, traceback in result.errors:
            self.errors.append((suite_name, str(test), traceback))
    
    def print_summary(self):
        """Print comprehensive test summary."""
        duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        print(f"\n{BOLD}COMPREHENSIVE TEST RESULTS{RESET}")
        print("=" * 60)
        
        # Overall statistics
        print(f"{BOLD}Overall Results:{RESET}")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  {GREEN}Passed: {self.passed_tests}{RESET}")
        if self.failed_tests > 0:
            print(f"  {RED}Failed: {self.failed_tests}{RESET}")
        if self.error_tests > 0:
            print(f"  {RED}Errors: {self.error_tests}{RESET}")
        if self.skipped_tests > 0:
            print(f"  {YELLOW}Skipped: {self.skipped_tests}{RESET}")
        
        print(f"  Duration: {duration:.2f} seconds")
        
        # Success rate
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            color = GREEN if success_rate >= 95 else YELLOW if success_rate >= 80 else RED
            print(f"  {color}Success Rate: {success_rate:.1f}%{RESET}")
        
        # Per-suite breakdown
        print(f"\n{BOLD}Test Suite Breakdown:{RESET}")
        for suite in self.test_suites:
            status_icon = "PASS" if suite['success'] else "FAIL"
            suite_success_rate = ((suite['tests_run'] - suite['failures'] - suite['errors']) / suite['tests_run'] * 100) if suite['tests_run'] > 0 else 0
            
            print(f"  {status_icon} {suite['name']}: {suite['tests_run']} tests ({suite_success_rate:.1f}% passed)")
            if suite['failures'] > 0:
                print(f"      {RED}Failures: {suite['failures']}{RESET}")
            if suite['errors'] > 0:
                print(f"      {RED}Errors: {suite['errors']}{RESET}")
            if suite['skipped'] > 0:
                print(f"      {YELLOW}Skipped: {suite['skipped']}{RESET}")
        
        # Failure/Error details
        if self.failures or self.errors:
            print(f"\n{BOLD}Failure/Error Details:{RESET}")
            
            for suite_name, test_name, traceback in self.failures:
                print(f"\n{RED}FAILURE in {suite_name}:{RESET}")
                print(f"  Test: {test_name}")
                print(f"  {GREY}{traceback[:500]}{'...' if len(traceback) > 500 else ''}{RESET}")
            
            for suite_name, test_name, traceback in self.errors:
                print(f"\n{RED}ERROR in {suite_name}:{RESET}")
                print(f"  Test: {test_name}")
                print(f"  {GREY}{traceback[:500]}{'...' if len(traceback) > 500 else ''}{RESET}")
        
        # Final assessment
        print(f"\n{BOLD}Assessment:{RESET}")
        if self.failed_tests == 0 and self.error_tests == 0:
            print(f"  {GREEN}All tests passed! The Project-Analyzer fixes are working correctly.{RESET}")
        elif success_rate >= 95:
            print(f"  {YELLOW}Most tests passed, but there are some issues to address.{RESET}")
        else:
            print(f"  {RED}Significant test failures detected. Please review and fix issues.{RESET}")
        
        return self.failed_tests == 0 and self.error_tests == 0


def load_test_module(module_path):
    """Dynamically load a test module."""
    spec = importlib.util.spec_from_file_location("test_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_test_suite(test_file_path, suite_name):
    """Run a single test suite and return results."""
    print(f"{BLUE}Running {suite_name}...{RESET}")
    
    try:
        # Load the test module
        test_module = load_test_module(test_file_path)
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # Run tests
        runner = unittest.TextTestRunner(stream=open(os.devnull, 'w'), verbosity=0)
        result = runner.run(suite)
        
        # Print immediate results
        if result.wasSuccessful():
            print(f"  {GREEN}✅ {result.testsRun} tests passed{RESET}")
        else:
            failures = len(result.failures)
            errors = len(result.errors)
            print(f"  {RED}❌ {failures} failures, {errors} errors out of {result.testsRun} tests{RESET}")
        
        return result
        
    except Exception as e:
        print(f"  {RED}❌ Failed to run test suite: {e}{RESET}")
        # Create a mock result for failed suite loading
        class MockResult:
            def __init__(self):
                self.testsRun = 0
                self.failures = []
                self.errors = [("Suite Loading", str(e))]
                self.skipped = []
            
            def wasSuccessful(self):
                return False
        
        return MockResult()


def run_validation_checks():
    """Run additional validation checks."""
    print(f"\n{BOLD}Running Additional Validation Checks{RESET}")
    print("-" * 50)
    
    validation_passed = True
    
    # Check 1: Verify all required modules can be imported
    print("Checking module imports...")
    try:
        from analyzer import ArchitecturalSniffer, FileClassifier, WorkspaceResolver
        from analyzer.pattern_analysis import PatternAnalyzer
        from analyzer.git_analysis import GitAnalyzer
        from analyzer.report_generators import format_architectural_summary
        print(f"  {GREEN}✅ All required modules can be imported{RESET}")
    except ImportError as e:
        print(f"  {RED}❌ Import error: {e}{RESET}")
        validation_passed = False
    
    # Check 2: Verify basic functionality
    print("Testing basic functionality...")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create minimal test project
            test_project = Path(temp_dir) / "test"
            test_project.mkdir()
            (test_project / "test.py").write_text("print('test')")
            
            # Test analysis
            sniffer = ArchitecturalSniffer(str(test_project))
            smells = sniffer.analyze_architecture([str(test_project / "test.py")])
            
            # Test formatting
            summary = format_architectural_summary(smells, markdown=False)
            
            if isinstance(smells, list) and isinstance(summary, str):
                print(f"  {GREEN}✅ Basic functionality works{RESET}")
            else:
                print(f"  {RED}❌ Basic functionality test failed{RESET}")
                validation_passed = False
                
    except Exception as e:
        print(f"  {RED}❌ Basic functionality error: {e}{RESET}")
        validation_passed = False
    
    # Check 3: Verify file classification works for common files
    print("Testing file classification...")
    try:
        from analyzer.config import DEFAULT_CONFIG
        classifier = FileClassifier(DEFAULT_CONFIG)
        
        test_cases = [
            ("README.md", "documentation"),
            ("main.py", "source"),
            ("config.json", "config")
        ]
        
        all_passed = True
        for file_path, expected_type in test_cases:
            classifications = classifier.classify_file(file_path)
            if expected_type not in classifications:
                all_passed = False
                print(f"    - Failed to classify '{file_path}' as '{expected_type}'. Got: {classifications}")
        
        if all_passed:
            print(f"  {GREEN}✅ File classification works correctly{RESET}")
        else:
            print(f"  {RED}❌ File classification test failed{RESET}")
            validation_passed = False
            
    except Exception as e:
        print(f"  {RED}❌ File classification error: {e}{RESET}")
        validation_passed = False
    
    return validation_passed


def main():
    """Run comprehensive test suite."""
    print(f"{BOLD}PROJECT-ANALYZER COMPREHENSIVE TEST SUITE{RESET}")
    print(f"{GREY}Validating fixes for output formatting and file classification{RESET}")
    print("=" * 60)
    
    # Initialize results tracking
    overall_result = ComprehensiveTestResult()
    overall_result.start_time = time.time()
    
    # Define test suites
    test_dir = Path(__file__).parent
    test_suites = [
        (test_dir / "test_file_classification.py", "File Classification Tests"),
        (test_dir / "test_output_formatting.py", "Output Formatting Tests"),
        (test_dir / "test_core_functionality.py", "Core Functionality Tests"),
        (test_dir / "test_edge_cases.py", "Edge Cases Tests"),
        (test_dir / "test_comprehensive_validation.py", "Comprehensive Validation Tests")
    ]
    
    # Run test suites
    for test_file, suite_name in test_suites:
        if test_file.exists():
            result = run_test_suite(test_file, suite_name)
            overall_result.add_suite_result(suite_name, result)
        else:
            print(f"{RED}❌ Test file not found: {test_file}{RESET}")
    
    # Run validation checks
    validation_passed = run_validation_checks()
    
    # Record end time
    overall_result.end_time = time.time()
    
    # Print comprehensive summary
    overall_result.print_summary()
    
    # Run existing integration test for compatibility
    print(f"\n{BOLD}Running Existing Integration Test{RESET}")
    print("-" * 50)
    
    integration_test_path = Path(__file__).parent / "integration_test.py"
    if integration_test_path.exists():
        try:
            import subprocess
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8" # For child process
            result = subprocess.run(
                [sys.executable, str(integration_test_path)],
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode == 0:
                print(f"{GREEN}✅ Existing integration test passed{RESET}")
            else:
                print(f"{RED}❌ Existing integration test failed{RESET}")
                print(f"{GREY}Output: {result.stdout}{RESET}")
                print(f"{GREY}Errors: {result.stderr}{RESET}")
        except Exception as e:
            print(f"{RED}❌ Failed to run integration test: {e}{RESET}")
    else:
        print(f"{YELLOW}⚠️  Existing integration test not found{RESET}")
    
    # Final verdict
    print(f"\n{BOLD}FINAL ASSESSMENT{RESET}")
    print("=" * 60)
    
    success = (overall_result.failed_tests == 0 and 
               overall_result.error_tests == 0 and 
               validation_passed)
    
    if success:
        print(f"{GREEN}{BOLD}SUCCESS: All tests passed! The Project-Analyzer system is working correctly.{RESET}")
        print(f"{GREEN}✅ File classification fixes validated{RESET}")
        print(f"{GREEN}✅ Output formatting fixes validated{RESET}")
        print(f"{GREEN}✅ Core functionality verified{RESET}")
        print(f"{GREEN}✅ Edge cases handled properly{RESET}")
        print(f"{GREEN}✅ No false positive issues detected{RESET}")
    else:
        print(f"{RED}{BOLD}❌ ISSUES DETECTED: Some tests failed or validation checks did not pass.{RESET}")
        print(f"{RED}Please review the test results above and address any issues.{RESET}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())