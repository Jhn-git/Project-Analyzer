# Contributing to Project Analyzer

Thank you for your interest in contributing to Project Analyzer! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.7 or higher
- Git
- A Google API key (for testing AI features)

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub
2. **Clone your fork locally:**
   ```bash
   git clone https://github.com/yourusername/Project_Analyzer.git
   cd Project_Analyzer
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Add your Google API key to .env
   ```

5. **Test the installation:**
   ```bash
   python project_analyzer.py --help
   ```

## 🐛 Reporting Issues

When reporting issues, please include:

- **Clear description** of the problem
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **System information** (OS, Python version)
- **Error messages** (if any)
- **Sample project structure** (if relevant)

## 💡 Suggesting Features

We welcome feature suggestions! Please:

- **Check existing issues** first
- **Provide detailed description** of the feature
- **Explain the use case** and benefits
- **Consider implementation complexity**

## 🔧 Code Contributions

### Branching Strategy

- `main` - Stable, production-ready code
- `develop` - Integration branch for features
- `feature/feature-name` - Individual feature branches
- `bugfix/issue-description` - Bug fix branches

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

3. **Test your changes:**
   ```bash
   # Test basic functionality
   python project_analyzer.py
   
   # Test different output formats
   python project_analyzer.py --markdown
   python project_analyzer.py --json
   
   # Test AI features (if applicable)
   python project_analyzer.py --summarize
   python project_analyzer.py --review
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add awesome new feature"
   ```

### Commit Message Guidelines

Use conventional commit format:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add support for pytest coverage
fix: handle binary files correctly
docs: update installation instructions
refactor: extract file analysis logic
```

### Code Style Guidelines

- **Follow PEP 8** for Python code
- **Use meaningful variable names**
- **Add docstrings** for functions and classes
- **Keep functions focused** and reasonably sized
- **Handle errors gracefully**
- **Use type hints** where appropriate

Example:
```python
def analyze_file_structure(directory: str, ignore_patterns: set) -> dict:
    """
    Analyzes the file structure of a directory.
    
    Args:
        directory: Path to the directory to analyze
        ignore_patterns: Set of gitignore patterns to respect
        
    Returns:
        Dictionary containing analysis results
        
    Raises:
        OSError: If directory cannot be accessed
    """
    # Implementation here
```

## 🧪 Testing

### Manual Testing

Test your changes with various project types:

- **Python projects** (with and without tests)
- **JavaScript/Node.js projects** (with and without Jest)
- **Mixed language projects**
- **Projects with complex .gitignore files**
- **Large projects** (to test performance)

### Testing Checklist

- [ ] Basic file structure analysis works
- [ ] Gitignore patterns are respected
- [ ] Color coding displays correctly
- [ ] Markdown output is properly formatted
- [ ] JSON output is valid
- [ ] AI features work (if API key is available)
- [ ] Error handling works for edge cases

## 📚 Documentation

When contributing:

- **Update README.md** if adding new features
- **Add inline comments** for complex logic
- **Update help text** for new command-line options
- **Include usage examples** for new features

## 🔄 Pull Request Process

1. **Ensure your code follows** the style guidelines
2. **Test thoroughly** on different project types
3. **Update documentation** as needed
4. **Create a pull request** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots (if UI changes)
   - Testing steps

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tested on Python projects
- [ ] Tested on JavaScript projects
- [ ] Tested AI features
- [ ] Tested edge cases

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

## 🏆 Recognition

Contributors will be:
- **Listed in README.md** acknowledgments
- **Mentioned in release notes** for significant contributions
- **Given credit** in commit messages and pull requests

## 🤔 Questions?

- **Open an issue** for questions about contributing
- **Check existing issues** for similar questions
- **Be patient** - we're all volunteers!

## 🎯 Priority Areas

We especially welcome contributions in:

- **New test framework support** (pytest, mocha, etc.)
- **Performance improvements** for large projects  
- **Better error handling** and user messages
- **Cross-platform compatibility** improvements
- **Additional AI model support**
- **Documentation improvements**

Thank you for contributing to Project Analyzer! 🎉
