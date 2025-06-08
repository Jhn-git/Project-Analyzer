# Project Analyzer 🔍

A powerful, free command-line tool that goes beyond simple linters. It acts as an **architectural health monitoring system** for your codebase, using dependency analysis, Git history, and AI to find deep, systemic issues before they become major problems.

Perfect for developers onboarding to a new project, conducting a tech-debt audit, or wanting to maintain high architectural quality over time.

---

### A Note on the Monolith

> Yes, `project_analyzer.py` is a single, massive file.
>
> And yes, the analyzer flags its own size as a `(!!! TOO LARGE !!!)` issue every time it runs. We consider this a feature, not a bug.
>
> It is the ultimate, unbiased proof that the sniffer works. The cobbler's children have no shoes, and our analyzer is its own first and most honest user.

---

## ✨ Key Features

*   **🕵️‍♂️ Architectural Smell Detection**: Automatically "sniffs" your codebase for common architectural problems:
    *   **💥 High Blast Radius**: Finds "god files" that are imported everywhere and are risky to change.
    *   **👻 Ghost Files**: Identifies critical source code in `src/` that has no corresponding test file.
    *   **🔗 Entanglement**: Detects when different feature modules are improperly coupled.
    *   **🔄 Circular Dependencies**: Finds and reports dependency loops that complicate your code.
    *   **👀 Stale Tests**: Warns you when source code changes but its tests don't, indicating a potential gap in test coverage.
    *   **🔥 High Churn & 🕰️ Stale Logic**: Uses Git history to find both unstable, rapidly changing files and abandoned code that may contain outdated logic.

*   **🤖 AI-Powered Interactive Deep Dive**: Don't just find problems—solve them. After identifying issues, the analyzer lets you select any smell for a deep-dive analysis with Google's Gemini AI, providing expert, context-specific refactoring advice.

*   **🚀 Monorepo-Aware Dependency Analysis**: Accurately builds a dependency graph for complex JavaScript/TypeScript projects by understanding `tsconfig.json`/`jsconfig.json` path aliases and monorepo workspaces (Yarn, Lerna, PNPM, NX).

*   **📊 Comprehensive Reporting**:
    *   **Console**: A clean, color-coded report highlighting critical issues.
    *   **File Tree**: An optional, detailed view of your project structure with size warnings.
    *   **Multiple Formats**: Supports `JSON`, `Markdown`, and `HTML` outputs for integration and documentation.

*   **🧪 Test Coverage Integration**: Automatically runs and displays your Jest test coverage summary.

## 🚀 Quick Start

### Prerequisites

*   Python 3.8+
*   Node.js and npm (for Jest coverage feature)
*   Git command line (for history-based analysis)
*   A Google API key (for all AI features)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Project_Analyzer.git
    cd Project_Analyzer
    ```

2.  **Run the quick setup script:**
    ```bash
    # This will create a virtual environment, install dependencies, and set up your .env file
    python setup.py
    ```
    Follow the prompts to add your Google API key.

3.  **Activate the environment:**
    ```bash
    # On macOS/Linux
    source venv/bin/activate
    # On Windows
    .\venv\Scripts\activate
    ```

### Usage

The analyzer is designed to be a "sniffer" first. The default command gives you the most important architectural health report.

```bash
# Run the default architectural analysis
python project_analyzer.py
```
After listing the issues, it will prompt you for an **interactive AI deep dive**.

```bash
# Get a visual tree of the entire project
python project_analyzer.py --tree

# Run all analyses: architecture, coverage, and file tree
python project_analyzer.py --full

# Generate a standalone HTML report
python project_analyzer.py --html-report
```

## 📖 Detailed Usage & Configuration

For detailed command-line options and configuration (like setting up custom rules for architectural boundaries or untestable files), please see [**USAGE.md**](./USAGE.md).

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

Please see [**CONTRIBUTING.md**](./CONTRIBUTING.md) for our contribution guidelines and development setup.

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

*   **Google's Gemini AI** for powering the intelligent analysis features.
*   The **GitPython** and **Jinja2** communities for their excellent libraries.
*   All contributors who help make this tool better.

---

**Made with ❤️ for the developer community.**

*If this tool helps you understand or improve your project, please consider giving it a ⭐ star on GitHub!*