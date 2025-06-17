# Project Analyzer - Modular Architecture

This directory contains the refactored, modular version of the Project Analyzer. The original monolithic `project_analyzer.py` has been broken down into focused, maintainable modules.

## Module Structure

```
analyzer/
├── __init__.py              # Package initialization and exports
├── config.py                # Configuration constants and settings
├── utils.py                 # Utility functions (file ops, caching, gitignore)
├── dependency_analysis.py   # Dependency graph building and analysis
├── architectural_analysis.py # Architectural smell detection
├── ai_analysis.py           # AI-powered code analysis (Gemini API)
├── coverage_analysis.py     # Test coverage analysis (Jest support)
├── report_generators.py     # Output formatting (HTML, JSON, markdown)
├── interactive.py           # Interactive deep dive analysis
└── main.py                  # CLI and main application logic
```

## Usage

### Using the new modular entry point:
```bash
python analyzer_main.py                    # Run architectural analysis (default)
python analyzer_main.py --tree             # Show file tree structure  
python analyzer_main.py --full             # Run all analyses
python analyzer_main.py --coverage         # Include test coverage
python analyzer_main.py --review           # AI-powered code review
python analyzer_main.py --markdown         # Output as Markdown
```

### Using as a Python package:
```python
from analyzer import ArchitecturalSniffer, DependencyGraph
from analyzer.utils import collect_all_project_files
from analyzer.config import load_config

# Load project configuration
config = load_config()

# Collect all project files
file_data = collect_all_project_files(".", config=config)

# Run architectural analysis
sniffer = ArchitecturalSniffer(".", config)
smells = sniffer.analyze_architecture(file_data['all_files'])
```

## Benefits of the Modular Approach

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Easier Testing**: Individual modules can be tested in isolation
3. **Better Maintainability**: Changes to one feature don't affect others
4. **Reusability**: Modules can be imported and used independently
5. **Reduced Complexity**: Smaller files are easier to understand and modify
6. **Extensibility**: New analysis features can be added as separate modules

## Module Responsibilities

- **config.py**: Centralized configuration management, constants, and settings
- **utils.py**: File system operations, caching, gitignore parsing, and common utilities
- **dependency_analysis.py**: Building dependency graphs and analyzing import relationships
- **architectural_analysis.py**: Detecting architectural smells and pattern violations
- **ai_analysis.py**: AI-powered code review and summarization using Gemini API
- **coverage_analysis.py**: Test coverage analysis and reporting
- **report_generators.py**: Formatting output for different formats (HTML, JSON, markdown)
- **interactive.py**: Interactive deep dive analysis with AI assistance
- **main.py**: Command-line interface and application orchestration

## Migration from Original

The original `project_analyzer.py` is still functional, but the new modular version offers:
- Better code organization
- Easier maintenance and debugging
- Improved testability
- Enhanced extensibility

All functionality from the original has been preserved and organized into appropriate modules.
