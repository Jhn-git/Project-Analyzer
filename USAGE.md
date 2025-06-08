# Quick Usage Guide

> **See [README.md](./README.md) for full documentation, features, and troubleshooting.**

This is a quick reference for using Project Analyzer.

## Installation

```bash
git clone https://github.com/Jhn-git/Project-Analyzer.git
cd Project-Analyzer
python setup.py
```

## Basic Commands

### Analyze Current Project
```bash
python project_analyzer.py
```

### Generate Reports
```bash
# Markdown report (great for documentation)
python project_analyzer.py --markdown

# JSON output (for automation/scripting)
python project_analyzer.py --json
```

### Test Coverage (Jest projects only)
```bash
python project_analyzer.py --coverage
```

### AI Features (requires Google API key)
```bash
# Summarize key files
python project_analyzer.py --summarize

# Code review and suggestions
python project_analyzer.py --review
```

## Setting up AI Features

1. Get a free Google API key from [Google AI Studio](https://aistudio.google.com/)
2. Copy `.env.example` to `.env`
3. Add your API key to the `.env` file:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

## Example Output

### Console Output
```
my-project/
├── src/
│   ├── components/ (5 files, 234 lines)
│   ├── utils/ (3 files, 156 lines)
│   └── main.py (567 lines) (!!! TOO LARGE !!!)
├── tests/ (8 files, 445 lines)
└── README.md (45 lines)
```

### File Size Warnings
- 🟡 **Yellow**: 400+ lines (approaching limit)
- 🔴 **Red**: 550+ lines (too large!)

## Tips

- The tool respects `.gitignore` files automatically
- Large files are highlighted to help identify refactoring opportunities
- Use `--json` output for integration with other tools
- AI features work best on the largest/most complex files in your project

## Troubleshooting

### "Command not found" errors
Make sure Python is installed and in your PATH.

### AI features not working
1. Check your `.env` file has the correct API key
2. Test with: `python list_gemini_models.py`
3. Ensure you have internet connectivity

### No coverage data
Jest coverage only works if:
- You have a `package.json` with Jest configured
- Your project has test files
- Tests can run successfully with `npm test`

## Need Help?

- Check the [README.md](README.md) for detailed documentation
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup
- Open an issue on GitHub for bugs or feature requests
