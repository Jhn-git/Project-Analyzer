# 🚀 Quick Usage Guide

> **See [README.md](./README.md) for the full project philosophy, features, and contribution guidelines.**

This page is a quick reference for the most common commands and configurations.

## 🛠️ Installation & Setup

```bash
# 1. Clone the repository
git clone https://github.com/Jhn-git/Project-Analyzer.git
cd Project-Analyzer

# 2. Run the interactive setup script
python setup.py

# 3. Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```
The setup script will guide you through installing dependencies and adding your optional Google API key.

## 🤖 Main Commands

### 🕵️‍♂️ Run Architectural Analysis (Default)
This is the primary function of the tool. It sniffs for deep architectural issues and then prompts you for an AI deep-dive.

```bash
python project_analyzer.py
```
**Output Example:**
```
🏗️  Architectural Health Analysis
===================================
Found 5 architectural issues.
1. 💥 BLAST RADIUS: 'logger.ts'
2. 👻 GHOST FILE: 'payment.ts'
3. ...

Enter number to deep-dive with AI, or 'q' to quit:
>
```

### 🌲 View Project File Tree
Use the `--tree` flag to get a visual representation of your project structure, complete with file size warnings.

```bash
python project_analyzer.py --tree
```
**Output Example:**
```
my-project/
├── src/
│   └── main.py (567 lines) 🔴 (!!! TOO LARGE !!!)
├── tests/
│   └── main.test.py (89 lines)
└── README.md (45 lines)
```

### 🧪 Include Test Coverage
For Jest-based projects, add the `--coverage` flag to any command to include a test coverage summary in the report.

```bash
python project_analyzer.py --full --coverage
```

### 🧩 Run All Analyses
The `--full` flag runs the architectural analysis, displays the file tree, and includes test coverage all in one command.

```bash
python project_analyzer.py --full
```

## 📄 Generating Reports

Generate reports for documentation or automation.

```bash
# Markdown report (great for pull requests or wikis)
python project_analyzer.py --full --markdown > report.md

# JSON output (for integration with other tools)
python project_analyzer.py --full --json > report.json

# HTML report (a self-contained, viewable file)
python project_analyzer.py --full --html-report
```

## 🧠 Standalone AI Features
These commands bypass the architectural analysis and run the AI directly on the most "interesting" files in your project.

```bash
# Get a high-level summary of key files
python project_analyzer.py --summarize

# Get a detailed code review with refactoring suggestions
python project_analyzer.py --review
```

## ⚙️ Configuration
The analyzer is designed to work out-of-the-box, but you can customize its behavior by creating a `.analyzer-config.json` file in your project root.

**Example `.analyzer-config.json`:**
```json
{
  "source_dirs": ["src", "lib"],
  "untestable_patterns": [
    "*.config.js",
    "scripts/**/*.py",
    "src/types/**/*.ts"
  ],
  "utility_patterns": [
    "src/utils/logger.ts"
  ],
  "architecture_rules": [
    {
      "layer": "ui",
      "path": "src/components/",
      "cannot_be_imported_by": ["utils", "services"]
    }
  ]
}
```
*   `source_dirs`: Directories containing your main application logic.
*   `untestable_patterns`: File patterns to exclude from the "Ghost File" analysis.
*   `utility_patterns`: File patterns to treat as utilities (lowers severity of "Blast Radius" alerts).
*   `architecture_rules`: Define your project's layers to detect boundary violations.

## 🐛 Troubleshooting

*   **"Command not found" errors**: Ensure you have activated the virtual environment (`source venv/bin/activate`).
*   **AI features not working**:
    1.  Verify your `GOOGLE_API_KEY` in the `.env` file is correct.
    2.  Test your key with `python list_gemini_models.py`.
    3.  Check your internet connection.
*   **Git-based features failing**: Make sure `git` is installed and you are running the analyzer inside a Git repository.
*   **No coverage data**: This feature requires a `package.json` with Jest configured and tests that pass when running `npm test`.