# Changelog

All notable changes to Project Analyzer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Refined Ghost File Detection**: Added `untestable_patterns` configuration to exclude files that shouldn't be tested (scripts, configs, etc.) from ghost file analysis, reducing noise
- **Contextualized Blast Radius Alerts**: Added `utility_patterns` configuration to differentiate between utility files (expected high imports) and core business logic files (concerning high imports)  
- **Stale Logic Detection**: New sniffer that identifies files in source directories that haven't been modified in over a year, helping spot potentially outdated business rules
- **High Churn Detection**: New sniffer that identifies files with high commit frequency, indicating potential instability or bug hotspots
- **Enhanced Configuration**: Comprehensive `.analyzer-config.example.json` with all new configuration options
- **Smarter Default Behavior**: Running the analyzer without flags now defaults to architectural analysis (the "alerter" mode) instead of file tree display

### Improved  
- **Ghost File Analysis**: Now focuses primarily on files within configured source directories and respects untestable patterns, dramatically reducing false positives
- **Blast Radius Analysis**: Utility files now show informational messages instead of warnings, while core business logic files get appropriate severity levels
- **Architectural Analysis**: Added calls to new stale logic and high churn sniffers for comprehensive code health monitoring
- **CLI Experience**: Updated help text and examples to reflect the new default behavior prioritizing architectural health analysis
- **Configuration System**: Added helper functions for new config options: `untestable_patterns`, `utility_patterns`, and thresholds for new sniffers

### Fixed
- **Indentation Issues**: Resolved various indentation problems in the ArchitecturalSniffer class and main function
- **Code Structure**: Improved code organization and consistency across architectural analysis methods

### Technical Details
- New configuration options: `untestable_patterns`, `utility_patterns`, `stale_logic_threshold_days`, `high_churn_threshold`, `high_churn_days`
- Enhanced ARCHITECTURAL_SMELLS with new categories: `STALE_LOGIC`, `HIGH_CHURN`
- Improved pattern matching for file classification and filtering

### Migration Notes
- The default behavior has changed: `python project_analyzer.py` now runs architectural analysis instead of showing file tree
- Use `python project_analyzer.py --tree` to display the file tree structure
- Consider creating a `.analyzer-config.json` file based on the example to customize the new filtering options

---

### Previous Releases

### Added
- Initial GitHub release preparation
- Comprehensive README with usage examples
- MIT License
- Contributing guidelines
- Requirements.txt for easy installation

### Improved
- Source directory discovery is now fully recursive: all configured source directories (e.g., `src`, `app`, `main`) are found at any depth in the project tree, not just at the top level. This makes file prioritization for AI analysis and reporting much more robust, especially for monorepos and complex project structures.
- General robustness and code quality improvements, including better error handling and configuration management.
- Project root cleanup: `.analyzer-cache.json` is now ignored by git to prevent cache files from being tracked.

### Fixed
- Bug in top script file selection: The analyzer now correctly selects the top script file from each discovered source directory (e.g., `src`, `app`, `main`) instead of only the first one found. This ensures all relevant code is considered for AI analysis and reporting, especially in monorepos or multi-package projects.

## [1.0.0] - 2025-06-06

### Added
- **Core project structure analysis** with color-coded output
- **Jest test coverage integration** for JavaScript/Node.js projects
- **Google Gemini AI integration** for code summarization and review
- **Multiple output formats**: Console (with colors), Markdown, and JSON
- **Smart file filtering** that respects .gitignore patterns
- **File size warnings** for potentially problematic large files
- **Binary file detection** to avoid processing non-text files
- **Configurable thresholds** for file and directory size warnings
- **Source directory prioritization** for AI analysis
- **Robust error handling** for various edge cases

### Features
- Command-line interface with multiple analysis modes
- AI-powered code smell detection and refactoring suggestions
- Automatic exclusion of common build artifacts and dependencies
- Support for wide range of file types and project structures
- Environment variable configuration for API keys
- Detailed file and directory statistics

### Technical Details
- Built with Python 3.7+ compatibility
- Uses Google Generative AI (Gemini) for code analysis
- Implements JSON schema validation for AI responses
- Supports both relative and absolute path handling
- Cross-platform compatibility (Windows, macOS, Linux)

## [1.0.1] - 2025-06-06

### Improved
- Source directory discovery is now fully recursive: all configured source directories (e.g., `src`, `app`, `main`) are found at any depth in the project tree, not just at the top level. This makes file prioritization for AI analysis and reporting much more robust, especially for monorepos and complex project structures.
- The `_find_all_source_dirs` helper function was introduced for clean, efficient, and robust recursive source directory detection, following the Single Responsibility Principle.
- Directory pruning in `os.walk` now ensures ignored directories (like `node_modules`, `.git`, etc.) are efficiently skipped, improving performance on large projects.
- Fallback logic ensures that if no configured source directories are found, the analyzer safely analyzes the whole project, making it adaptable to any project layout.
- General code quality improvements and additional comments for maintainability.

### Notes
- This release marks the script as feature-complete and production-ready for its current scope. Future enhancements may include parallel execution or richer HTML reports, but the core tool is now robust and reliable for daily use.

---

## Release Notes Format

### Added
- New features and capabilities

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Features that were removed

### Fixed
- Bug fixes

### Security
- Security-related changes
