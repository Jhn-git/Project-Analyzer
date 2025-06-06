import os
import sys
import fnmatch
import re
import collections
import json
import subprocess
import hashlib
import requests  # For LLM API calls
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# ANSI escape sequences for colored output
RESET = "\033[0m"
GREY = "\033[90m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"

FILE_WARNING_THRESHOLD = 400
FILE_DANGER_THRESHOLD = 550
DIR_WARNING_THRESHOLD = 5000
DIR_DANGER_THRESHOLD = 10000

SCRIPT_EXTS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.sh', '.bat', '.ps1', '.rb', '.php', '.pl', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.cs', '.m', '.swift', '.kt', '.dart'
}
DATA_EXTS = {
    '.json', '.csv', '.yml', '.yaml', '.xml', '.txt', '.md', '.ini', '.conf', '.log'
}
EXCLUDED_DIRS = {"node_modules", ".git", ".vscode", ".idea", "dist", "coverage", "__pycache__"}
SOURCE_CODE_DIRS = {"src", "app", "main"} # Common names for source directories

PROJECT_ROOT = os.getcwd()

def parse_gitignore(directory):
    gitignore_path = Path(directory) / ".gitignore"
    ignore_patterns = set()
    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ignore_patterns.add(line)
        except (OSError, IOError):
            pass
    return ignore_patterns

def should_ignore(path_str: str, gitignore_patterns: set, base_dir: str) -> bool:
    """
    Checks if a file or directory should be ignored.
    This is the most critical function for getting a clean report.
    """
    try:
        relative_path = Path(path_str).relative_to(base_dir)
    except ValueError:
        return True
    if any(part in EXCLUDED_DIRS for part in relative_path.parts):
        return True
    for pattern in gitignore_patterns:
        if fnmatch.fnmatch(str(relative_path), pattern) or fnmatch.fnmatch(relative_path.name, pattern):
            return True
    return False

def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

# --- Coverage/Jest logic ---
def is_jest_project(directory):
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
    except subprocess.CalledProcessError as e:
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

# --- LLM-powered summarization: helper to call LLM, function to summarize top 3 largest script files, argparse flag, and main() logic to trigger it.
CODE_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "positive_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "A list of 2-3 things that are well-designed in the code."
        },
        "refactoring_suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "smell": {"type": "string", "description": "The name of the identified code smell (e.g., 'Long Function')."},
                    "explanation": {"type": "string", "description": "A brief explanation of why this is a code smell."},
                    "suggestion": {"type": "string", "description": "A concrete suggestion for how to refactor the code."}
                },
                "required": ["smell", "explanation", "suggestion"]
            },
            "description": "A list of potential code smells and refactoring suggestions."
        }
    },
    "required": ["positive_points", "refactoring_suggestions"]
}

CODE_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "A 2-3 sentence summary of the file's primary responsibility, main inputs, and key outputs."
        }
    },
    "required": ["summary"]
}

def configure_gemini():
    """Configures the Gemini client with the API key."""
    load_dotenv() # Loads variables from a .env file
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(f"{RED}✖ Error: GOOGLE_API_KEY not found in environment variables or .env file.{RESET}")
        return None
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"{RED}✖ Error configuring Gemini client: {e}{RESET}")
        return None


def call_llm(prompt_messages, json_schema=None):
    """
    A helper function to call the Google Gemini API with optional JSON schema enforcement.
    This replaces the local model call.
    """
    try:
        # We use Gemini 1.5 Flash - it's fast, cheap, and supports structured output.
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Convert your OpenAI-style message format to Gemini's format
        # Gemini expects a simple list of strings or dicts, not a "messages" key.
        # We'll just concatenate the system and user prompts.
        system_prompt = ""
        user_prompt = ""
        for msg in prompt_messages:
            if msg['role'] == 'system':
                system_prompt += msg['content'] + "\n\n"
            elif msg['role'] == 'user':
                user_prompt += msg['content']

        full_prompt = system_prompt + user_prompt

        generation_config = {
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 20,
        }

        # Gemini's way of enforcing JSON output
        if json_schema:
            generation_config["response_mime_type"] = "application/json"
            # We add the schema instructions to the prompt itself for Gemini
            full_prompt += "\n\nIMPORTANT: Your entire response MUST be a single JSON object matching this schema:\n" + json.dumps(json_schema)
        
        # Make the API call
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config,
        )
        
        return response.text

    except Exception as e:
        return f'{{"error": "Error calling Google Gemini API: {str(e)}"}}'


def _find_top_script_files(directory, count=3):
    """Helper to find the largest script files BY LINE COUNT within the primary source directories."""
    script_files = []
    # NEW: Determine which source directories exist in the project
    search_paths = [Path(directory) / d for d in SOURCE_CODE_DIRS if (Path(directory) / d).is_dir()]
    # If no standard source folders are found, default to the project root as a fallback
    if not search_paths:
        search_paths = [Path(directory)]
    print(f"{GREY}  (Analyzing files in: {[str(p.relative_to(directory)) for p in search_paths]}){RESET}")
    for search_path in search_paths:
        for root, _, files in os.walk(search_path):
            for name in files:
                if Path(name).suffix in SCRIPT_EXTS:
                    file_path = os.path.join(root, name)
                    line_count = count_lines(file_path)
                    script_files.append((line_count, file_path))
    script_files.sort(key=lambda item: item[0], reverse=True)
    return script_files[:count]

def _run_llm_analysis_on_top_files(directory, system_prompt, output_label, schema=None):
    print(f"\n{BOLD}--- LLM-Powered {output_label} ---{RESET}")
    top_files = _find_top_script_files(directory)
    if not top_files:
        print(f"{GREY}No script files found to analyze.{RESET}")
        return
    for idx, (line_count, file_path) in enumerate(top_files, 1):
        print(f"\n{BOLD}File {idx}: {os.path.relpath(file_path, directory)} ({line_count} lines){RESET}")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read(4000)
        except Exception as e:
            print(f"{RED}Could not read file: {e}{RESET}")
            continue
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": code}
        ]
        # --- Provide feedback to the user before the long wait ---
        print(f"{GREY}  -> Sending to LLM for {output_label}. This may take a few minutes...{RESET}")
        response_str = call_llm(messages, json_schema=schema)
        # --- Robust JSON Extraction Layer ---
        cleaned_json_str = None
        match = re.search(r'```(?:json)?\s*({.*})\s*```', response_str, re.DOTALL)
        if match:
            cleaned_json_str = match.group(1)
        else:
            cleaned_json_str = response_str
        try:
            response_data = json.loads(cleaned_json_str)
            if 'error' in response_data:
                print(f"{RED}{response_data['error']}{RESET}")
                continue
            print(f"{YELLOW}{output_label}:{RESET}")
            if output_label == "Review":
                print(f"  {GREEN}Positive Points:{RESET}")
                for point in response_data.get("positive_points", []):
                    print(f"    - {point}")
                print(f"  {YELLOW}Refactoring Suggestions:{RESET}")
                for sugg in response_data.get("refactoring_suggestions", []):
                    print(f"    - {BOLD}Smell:{RESET} {sugg['smell']}")
                    print(f"      {BOLD}Explanation:{RESET} {sugg['explanation']}")
                    print(f"      {BOLD}Suggestion:{RESET} {sugg['suggestion']}")
            elif output_label == "Summary":
                print(f"  {GREEN}Summary:{RESET} {response_data.get('summary', '')}")
        except json.JSONDecodeError:
            print(f"{RED}✖ Failed to parse LLM response as JSON.{RESET}")
            print(f"{GREY}--- Raw LLM Output ---{RESET}")
            print(response_str)
            print(f"{GREY}------------------------{RESET}")

def run_llm_summarization(directory):
    system_prompt = (
        "You are a senior software architect. Your task is to summarize the following code file in 2-3 sentences. "
        "Focus on its primary responsibility, its main inputs, and its key outputs or side effects. "
        "Respond ONLY with a JSON object matching the provided schema."
    )
    _run_llm_analysis_on_top_files(directory, system_prompt, "Summary", CODE_SUMMARY_SCHEMA)

def run_llm_code_review(directory):
    system_prompt = (
        "You are a code review expert specializing in clean code principles. Analyze the following code. "
        "Identify potential code smells such as long functions, high cyclomatic complexity, tight coupling, or poor naming. "
        "For each smell, provide a brief explanation and a suggestion for refactoring. "
        "If there are no obvious smells, say 'Code looks clean.' "
        "Respond ONLY with a JSON object matching the provided schema."
    )
    _run_llm_analysis_on_top_files(directory, system_prompt, "Review", CODE_REVIEW_SCHEMA)

# --- Main universal analysis (get_file_structure) ---
def get_file_structure(directory, ignore_patterns=None, markdown=False, json_output=False, coverage_data=None):
    if ignore_patterns is None:
        ignore_patterns = parse_gitignore(directory)
    lines = []
    directory_totals = {}
    file_stats = []  # For summary and markdown
    base_dir = directory
    duplicate_files = collections.defaultdict(list)
    ext_counts = collections.Counter()
    suspicious_files = []
    deprecated_files = []
    line_endings = collections.Counter()
    todo_fixme_count = 0
    largest_files_by_size = []
    top_level_files = set()
    recent_files = []
    errors = []  # Collect errors for LLMs
    # Suspicious/deprecated patterns
    suspicious_patterns = ["test.py", "debug.log", "temp.", "tmp."]
    deprecated_patterns = ["bower.json", "gulpfile.js", "Gruntfile.js"]
    important_top_level = ["README.md", "readme.md", "requirements.txt", "package.json", "main.py", "index.js", "tsconfig.json", "webpack.config.js", ".env"]
    stats = {
        "total_files": 0,
        "script_files": 0,
        "data_files": 0,
        "binary_files": 0,
        "total_lines": 0,
        "script_lines": 0,
        "data_lines": 0,
        "other_lines": 0,
    }
    def walk_dir(path, prefix="", depth=0):
        dirs, files = [], []
        dir_total_lines = 0
        rel_path = os.path.relpath(path, directory)
        if rel_path == ".":
            rel_path = os.path.basename(directory)
        if depth == 0:
            try:
                for entry in sorted(os.listdir(path)):
                    entry_path = os.path.join(path, entry)
                    if os.path.isfile(entry_path):
                        top_level_files.add(entry)
            except (OSError, IOError):
                pass
        try:
            for entry in sorted(os.listdir(path)):
                entry_path = os.path.join(path, entry)
                if should_ignore(entry_path, ignore_patterns, base_dir):
                    continue
                if os.path.isdir(entry_path):
                    dirs.append(entry)
                else:
                    files.append(entry)
        except PermissionError:
            lines.append(f"{prefix}├── {RED}Permission denied{RESET}")
            errors.append({"path": path, "error": "Permission denied"})
            return 0
        except (OSError, IOError) as e:
            lines.append(f"{prefix}├── Error: {str(e)}")
            errors.append({"path": path, "error": str(e)})
            return 0
        pointers = ["├── "] * (len(dirs) - 1) + ["└── "] if dirs else []
        for pointer, name in zip(pointers, dirs):
            full_path = os.path.join(path, name)
            subdir_rel_path = os.path.join(rel_path, name) if rel_path != "." else name
            try:
                if not os.listdir(full_path):
                    lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET} {GREY}(Empty){RESET}")
                    subdir_lines = 0
                else:
                    lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET}")
                    extension = "│   " if pointer == "├── " else "    "
                    subdir_lines = walk_dir(full_path, prefix + extension, depth+1)
                if subdir_lines > 0:
                    directory_totals[subdir_rel_path] = subdir_lines
                dir_total_lines += subdir_lines
            except PermissionError:
                lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET} {GREY}(Permission denied){RESET}")
            except (OSError, IOError) as e:
                lines.append(f"{prefix}{pointer}{BLUE}{name}/{RESET} {GREY}(Error: {str(e)}){RESET}")
        for name in files:
            file_path = os.path.join(path, name)
            stats["total_files"] += 1
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            ext_counts[ext] += 1
            file_size = get_file_size(file_path)
            file_hash = None  # hash not used in output
            tags = []  # tags not used in output
            code_sample = None  # code_sample not used in output
            largest_files_by_size.append((file_size, os.path.join(rel_path, name)))
            duplicate_files[name].append(os.path.join(rel_path, name))
            for pat in suspicious_patterns:
                if pat in name:
                    suspicious_files.append(os.path.join(rel_path, name))
            for pat in deprecated_patterns:
                if pat == name:
                    deprecated_files.append(os.path.join(rel_path, name))
            le_type = None  # line ending type not used in output
            todo_fixme = 0  # todo/fixme not used in output
            nonlocal todo_fixme_count
            todo_fixme_count += todo_fixme
            is_binary = False
            try:
                with open(file_path, 'rb') as f:
                    chunk = f.read(2048)
                    if chunk:
                        text_characters = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)))
                        nontext = chunk.translate(None, text_characters)
                        if b'\0' in chunk or float(len(nontext)) / len(chunk) > 0.3:
                            is_binary = True
            except (OSError, IOError) as e:
                is_binary = True
                errors.append({"path": file_path, "error": str(e)})
            if is_binary:
                stats["binary_files"] += 1
                file_stats.append({"path": os.path.join(rel_path, name), "lines": 0, "type": "binary", "size": file_size, "hash": file_hash, "tags": tags, "code_sample": None})
                lines.append(f"{prefix}├── {GREEN}{name}{RESET} {GREY}(binary file){RESET}")
                continue
            if ext in SCRIPT_EXTS:
                line_count = count_lines(file_path)
                dir_total_lines += line_count
                stats["total_lines"] += line_count
                stats["script_files"] += 1
                stats["script_lines"] += line_count
                file_type = "script"
                file_stats.append({"path": os.path.join(rel_path, name), "lines": line_count, "type": file_type, "size": file_size, "hash": file_hash, "tags": tags, "code_sample": code_sample})
            elif ext in DATA_EXTS:
                line_count = count_lines(file_path)
                dir_total_lines += line_count
                stats["total_lines"] += line_count
                stats["data_files"] += 1
                stats["data_lines"] += line_count
                file_type = "data"
                file_stats.append({"path": os.path.join(rel_path, name), "lines": line_count, "type": file_type, "size": file_size, "hash": file_hash, "tags": tags, "code_sample": None})
            else:
                line_count = count_lines(file_path)
                dir_total_lines += line_count
                stats["total_lines"] += line_count
                stats["other_lines"] += line_count
                file_type = "other"
                file_stats.append({"path": os.path.join(rel_path, name), "lines": line_count, "type": file_type, "size": file_size, "hash": file_hash, "tags": tags, "code_sample": None})
        pointers = ["├── "] * (len(files) - 1) + ["└── "] if files else []
        for pointer, name in zip(pointers, files):
            file_path = os.path.join(path, name)
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            is_binary = False
            try:
                with open(file_path, 'rb') as f:
                    chunk = f.read(2048)
                    if chunk:
                        text_characters = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)))
                        nontext = chunk.translate(None, text_characters)
                        if b'\0' in chunk or float(len(nontext)) / len(chunk) > 0.3:
                            is_binary = True
            except (OSError, IOError):
                is_binary = True
            if is_binary:
                lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} {GREY}(binary file){RESET}")
            else:
                line_count = count_lines(file_path)
                if ext in SCRIPT_EXTS:
                    if line_count >= FILE_DANGER_THRESHOLD:
                        line_color = RED
                        warning = " (!!! TOO LARGE !!!)"
                    elif line_count >= FILE_WARNING_THRESHOLD:
                        line_color = YELLOW
                        warning = " (! approaching limit !)"
                    else:
                        line_color = RESET
                        warning = ""
                    lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} {line_color}({line_count} lines){warning}{RESET}")
                else:
                    lines.append(f"{prefix}{pointer}{GREEN}{name}{RESET} ({line_count} lines)")
        return dir_total_lines
    lines.append(f"{os.path.basename(directory)}/")
    walk_dir(directory)

    # Add coverage data to all output types
    if coverage_data:
        lines.append(f"\n{BOLD}--- Jest Test Coverage ---{RESET}")
        lines.append(coverage_data)

    if markdown:
        md = []
        # Markdown output
        md.append("## File Tree\n")
        md.append("```")
        md.append(remove_ansi_colors("\n".join(lines)))
        md.append("```")
        if coverage_data:
            md.append("\n## Test Coverage\n")
            md.append(f"```\n{remove_ansi_colors(coverage_data)}\n```")
        return "\n".join(md)
    elif json_output:
        # JSON output
        if coverage_data:
            stats['coverage_report'] = remove_ansi_colors(coverage_data)
        return json.dumps({"stats": stats}, indent=2)
    else:
        return "\n".join(lines)

# --- Main entry point ---
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Universal Project Analyzer with optional coverage checks.")
    parser.add_argument('--markdown', action='store_true', help='Output as Markdown')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--coverage', action='store_true', help='Run test coverage analysis if possible')
    parser.add_argument('--summarize', action='store_true', help='Use local LLM to summarize key files')
    parser.add_argument('--review', action='store_true', help='Use local LLM to review key files for code smells')
    args = parser.parse_args()

    # NEW: Configure Gemini at the start if LLM is needed
    if args.summarize or args.review:
        if not configure_gemini():
            sys.exit(1)

    directory = PROJECT_ROOT
    ignore_patterns = parse_gitignore(directory)

    coverage_report = None
    if args.coverage:
        if is_jest_project(directory):
            coverage_report = run_jest_coverage(directory)
        else:
            print(f"{GREY}(No supported test coverage found for this project.){RESET}")

    if args.summarize:
        run_llm_summarization(directory)
        return

    if args.review:
        run_llm_code_review(directory)
        return

    final_output = get_file_structure(
        directory,
        ignore_patterns,
        markdown=args.markdown,
        json_output=args.json,
        coverage_data=coverage_report
    )
    print(final_output)

def remove_ansi_colors(text):
    """Remove ANSI color codes from text."""
    return re.sub(r"\033\[[0-9;]*m", "", text)

def count_lines(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, IOError):
        return 0

if __name__ == "__main__":
    main()