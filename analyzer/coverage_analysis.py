"""
Test coverage analysis functionality.
"""

import os
import json
import subprocess

from .config import BOLD, RESET, YELLOW, GREEN, RED, GREY

# =============================================================================
# TEST COVERAGE ANALYSIS
# =============================================================================

def is_jest_project(directory):
    """Check if project uses Jest for testing."""
    package_json_path = os.path.join(directory, "package.json")
    if not os.path.exists(package_json_path):
        return False
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})
        return "jest" in deps or "jest" in dev_deps or "jest" in data
    except (json.JSONDecodeError, IOError):
        return False

def run_jest_coverage(directory):
    """Run Jest coverage analysis."""
    print(f"\n{BOLD}--- Jest Coverage Analysis ---{RESET}")
    print(f"{YELLOW}Running 'npm test' to generate coverage report...{RESET}")
    
    try:
        subprocess.run([
            "npm", "test"
        ], cwd=directory, check=True, capture_output=True, text=True)
        print(f"{GREEN}✔ Test run completed successfully.{RESET}")
    except FileNotFoundError:
        print(f"{RED}✖ Error: 'npm' command not found. Is Node.js installed?{RESET}")
        return None
    except subprocess.CalledProcessError:
        print(f"{RED}✖ Error: 'npm test' failed. See test output for details.{RESET}")
        return None
    
    coverage_file = os.path.join(directory, "coverage", "coverage-summary.json")
    if not os.path.exists(coverage_file):
        print(f"{RED}✖ Analysis Error: 'coverage/coverage-summary.json' not found.{RESET}")
        print(f"{YELLOW}  Hint: Ensure your jest.config.js has 'json-summary' in coverageReport.{RESET}")
        return None
    
    with open(coverage_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_coverage = data.get("total", {})
    lines_pct = total_coverage.get("lines", {}).get("pct", 0)
    color = GREEN if lines_pct >= 70 else YELLOW if lines_pct >= 50 else RED
    
    return f"  Overall Line Coverage: {color}{lines_pct:.2f}%{RESET}\n{GREY}------------------------------------{RESET}"

def run_coverage_analysis(directory):
    """Run appropriate coverage analysis based on project type."""
    if is_jest_project(directory):
        return run_jest_coverage(directory)
    else:
        print(f"{GREY}No supported test framework detected for coverage analysis.{RESET}")
        return None
