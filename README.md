# Project Analyzer 🔍

> **Documentation Overview:**
> - For a quick usage reference, see [USAGE.md](./USAGE.md)
> - For contribution guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md)

Yes, project_analyzer.py is a single, massive file.
And yes, the analyzer flags its own size as a (!!! TOO LARGE !!!) issue every time it runs. We consider this a feature, not a bug.
It is the ultimate, unbiased proof that the sniffer works. The cobbler's children have no shoes, and our analyzer is its own first and most honest user.

A powerful, free command-line tool that analyzes your project structure, provides test coverage insights, and uses AI to review your code quality. Perfect for developers who want to quickly understand and improve their codebases.

## ✨ Features

- **📁 Smart Project Structure Analysis** - Visualizes your project with color-coded file trees
- **🧪 Test Coverage Integration** - Automatic Jest coverage reporting
- **🤖 AI-Powered Code Review** - Uses Google Gemini to identify code smells and suggest improvements
- **📊 AI Code Summarization** - Get concise summaries of your largest files
- **🎨 Multiple Output Formats** - Console (colored), Markdown, and JSON
- **⚡ Intelligent Filtering** - Respects .gitignore and excludes build artifacts
- **🚨 File Size Warnings** - Highlights potentially problematic large files

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google API key (for AI features)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/Project_Analyzer.git
cd Project_Analyzer
```

2. **Quick setup (recommended):**
```bash
python setup.py
```

Or **manual setup:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment file
cp .env.example .env
# Edit .env and add your Google API key
```

### Basic Usage

```bash
# Analyze current project structure
python project_analyzer.py

# Generate markdown report
python project_analyzer.py --markdown

# Include test coverage (for Jest projects)
python project_analyzer.py --coverage

# AI-powered code summarization
python project_analyzer.py --summarize

# AI-powered code review
python project_analyzer.py --review

# JSON output for automation
python project_analyzer.py --json
```

## 📖 Detailed Usage

### Command Line Options

| Option | Description |
|--------|-------------|
| `--markdown` | Output results in Markdown format |
| `--json` | Output results in JSON format |
| `--coverage` | Run Jest test coverage analysis |
| `--summarize` | Use AI to summarize key files |
| `--review` | Use AI to review code for potential improvements |

### File Size Warnings

The tool automatically identifies potentially problematic files:

- **🟡 Yellow Warning**: Script files with 400+ lines
- **🔴 Red Alert**: Script files with 550+ lines
- **📁 Directory Warnings**: Folders with 5000+ or 10000+ total lines

### Supported Project Types

- **JavaScript/TypeScript** (Node.js, React, Vue, etc.)
- **Python** projects
- **Any project** with common file structures

### AI Features Setup

1. **Get a Google API Key:**
   - Visit [Google AI Studio](https://aistudio.google.com/)
   - Create a new API key
   - Add it to your `.env` file

2. **List available models:**
```bash
python list_gemini_models.py
```

## 📊 Example Output

### Console Output
```
my-project/
├── src/
│   ├── components/
│   │   ├── Header.tsx (45 lines)
│   │   └── Footer.tsx (32 lines)
│   ├── utils/
│   │   └── helpers.js (234 lines)
│   └── app.py (567 lines) (!!! TOO LARGE !!!)
├── tests/
│   └── app.test.py (89 lines)
└── package.json (23 lines)

--- Jest Test Coverage ---
Overall Line Coverage: 78.50%
```

### AI Code Review Example
```
File 1: src/main.py (456 lines)

Review:
  Positive Points:
    - Good use of type hints throughout the codebase
    - Clear separation of concerns with helper functions
    - Comprehensive error handling

  Refactoring Suggestions:
    - Smell: Long Function
      Explanation: The main() function is 89 lines long, making it hard to understand and test
      Suggestion: Break down main() into smaller, focused functions like parse_arguments(), setup_environment(), and run_analysis()
```

## 🛠️ Configuration

### Customizing Excluded Directories

Edit the `EXCLUDED_DIRS` set in `project_analyzer.py`:

```python
EXCLUDED_DIRS = {"node_modules", ".git", ".vscode", ".idea", "dist", "coverage", "__pycache__"}
```

### File Type Recognition

The tool recognizes these file categories:

- **Script Files**: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.go`, `.rs`, `.java`, `.c`, `.cpp`, etc.
- **Data Files**: `.json`, `.csv`, `.yml`, `.yaml`, `.xml`, `.txt`, `.md`, etc.

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Add tests** if applicable
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/Project_Analyzer.git
cd Project_Analyzer

# Install development dependencies
pip install -r requirements.txt

# Set up pre-commit hooks (if you add them)
pre-commit install
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Issues & Support

- **Bug Reports**: [Open an issue](https://github.com/yourusername/Project_Analyzer/issues)
- **Feature Requests**: [Open an issue](https://github.com/yourusername/Project_Analyzer/issues)
- **Questions**: Check existing issues or open a new one

## 🙏 Acknowledgments

- **Google Gemini AI** for powering the code analysis features
- **Jest** community for test coverage integration
- All contributors who help make this tool better

## 🔮 Roadmap

- [ ] Support for more test frameworks (pytest, mocha, etc.)
- [ ] GitHub Actions integration
- [ ] VS Code extension
- [ ] More AI model options
- [ ] Custom rule configuration
- [ ] Web dashboard

---

**Made with ❤️ for the developer community**

*This tool is completely free and open source. Star ⭐ the repository if you find it useful!*
