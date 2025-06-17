"""
AI-powered code analysis using Google Gemini API.
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

from .config import (
    CODE_REVIEW_SCHEMA, CODE_SUMMARY_SCHEMA, BOLD, RESET, GREY, GREEN, RED, YELLOW, BLUE,
    get_configured_source_dirs, get_configured_llm_review_file_count
)
from .utils import load_cache, save_cache, get_file_md5, is_binary_file, count_lines
from .dependency_analysis import find_all_source_dirs

# Optional dependencies
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# =============================================================================
# AI-POWERED ANALYSIS
# =============================================================================

def configure_gemini():
    """Configure the Gemini client with API key."""
    if not HAS_GENAI:
        print(f"{RED}✖ Error: google-generativeai package not installed. Install with 'pip install google-generativeai'.{RESET}")
        return None
        
    load_dotenv()
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
    """Call the Google Gemini API with optional JSON schema enforcement."""
    if not HAS_GENAI:
        return '{"error": "Google Generative AI not available"}'
        
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Convert OpenAI-style messages to Gemini format
        system_prompt = ""
        user_prompt = ""
        for msg in prompt_messages:
            if msg['role'] == 'system':
                system_prompt += msg['content'] + "\n"
            elif msg['role'] == 'user':
                user_prompt += msg['content'] + "\n"
        
        full_prompt = system_prompt + user_prompt
        
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 20,
        }
        
        if json_schema:
            full_prompt += f"\n\nPlease respond with valid JSON matching this schema: {json.dumps(json_schema)}"
        
        response = model.generate_content(full_prompt, generation_config=generation_config)
        return response.text
        
    except Exception as e:
        return f'{{"error": "Error calling Google Gemini API: {str(e)}"}}'

def find_top_script_files(directory, ignore_patterns, base_dir, count=3, config=None):
    """Find the top script files for analysis based on various criteria."""
    source_dirs = get_configured_source_dirs(config) if config else {"src", "app", "main"}
    all_source_dirs = find_all_source_dirs(directory, source_dirs, ignore_patterns, base_dir, config)
    
    # Store the top file found for each source directory
    top_files_per_dir = {str(path): (0, 0, None) for path in all_source_dirs}
    
    if not all_source_dirs:
        print(f"{YELLOW}Warning: No source directories found. Analyzing project root as fallback.{RESET}")
        return []
    
    now = time.time()
    for search_path in all_source_dirs:
        for root, dirs, files in os.walk(search_path):
            # Remove ignored directories in-place
            from .utils import should_ignore
            dirs[:] = [d for d in dirs if not should_ignore(
                os.path.join(root, d), ignore_patterns, base_dir, config)]
            
            for file in files:
                file_path = os.path.join(root, file)
                if (not should_ignore(file_path, ignore_patterns, base_dir, config) and
                    not is_binary_file(file_path)):
                    
                    line_count = count_lines(file_path)
                    if line_count > 50:  # Only consider substantial files
                        current_max = top_files_per_dir[search_path][0]
                        if line_count > current_max:
                            top_files_per_dir[search_path] = (line_count, line_count, file_path)
    
    # Collect results
    final_files = []
    for _, line_count, file_path in top_files_per_dir.values():
        if file_path:
            final_files.append((line_count, file_path))
    
    final_files.sort(key=lambda item: item[0], reverse=True)
    return final_files

def run_llm_analysis_on_top_files(directory, system_prompt, output_label, schema=None, config=None):
    """Run LLM analysis on top files in the project."""
    print(f"\n{BOLD}--- LLM-Powered {output_label} ---{RESET}")
    
    if not configure_gemini():
        return
    
    from .utils import parse_gitignore
    base_dir = directory
    ignore_patterns = parse_gitignore(base_dir, config)
    top_files = find_top_script_files(
        directory, ignore_patterns, base_dir, 
        count=get_configured_llm_review_file_count(config) if config else 3, config=config
    )
    
    if not top_files:
        print(f"{GREY}No script files found to analyze.{RESET}")
        return
    
    cache = load_cache()
    cache_updated = False
    project_context = config.get("project_context", "This file is part of a software project.") if config else "This file is part of a software project."
    
    for idx, (line_count, file_path) in enumerate(top_files, 1):
        print(f"\n{BOLD}File {idx}: {os.path.relpath(file_path, directory)} ({line_count} lines){RESET}")
        
        file_hash = get_file_md5(file_path)
        cache_key = f"{file_path}|{file_hash}|{output_label}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"{GREEN}✓ Using cached result{RESET}")
            result = cached_result
        else:
            print(f"{GREY}Analyzing with AI...{RESET}")
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            except Exception as e:
                print(f"{RED}✖ Error reading file: {e}{RESET}")
                continue
            
            # Prepare the prompt
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {project_context}\n\nFile: {os.path.relpath(file_path, directory)}\n\nCode:\n{file_content}"}
            ]
            
            result = call_llm(messages, schema)
            cache[cache_key] = result
            cache_updated = True
        
        # Parse and display results
        try:
            if result.startswith('{"') or result.startswith('{'):
                parsed_result = json.loads(result)
                
                if output_label == "Summary":
                    summary = parsed_result.get("summary", "No summary available")
                    print(f"{BLUE}Summary:{RESET} {summary}")
                    
                elif output_label == "Review":
                    positive_points = parsed_result.get("positive_points", [])
                    suggestions = parsed_result.get("refactoring_suggestions", [])
                    
                    if positive_points:
                        print(f"{GREEN}✓ Positive Points:{RESET}")
                        for point in positive_points:
                            print(f"  • {point}")
                    
                    if suggestions:
                        print(f"{YELLOW}⚠ Refactoring Suggestions:{RESET}")
                        for suggestion in suggestions:
                            smell = suggestion.get("smell", "Unknown")
                            explanation = suggestion.get("explanation", "")
                            fix = suggestion.get("suggestion", "")
                            print(f"  • {BOLD}{smell}:{RESET} {explanation}")
                            if fix:
                                print(f"    → {fix}")
                    
                    if not positive_points and not suggestions:
                        print(f"{GREEN}✓ Code looks clean!{RESET}")
                        
            else:
                print(f"{GREY}Raw response: {result}{RESET}")
                
        except json.JSONDecodeError:
            print(f"{RED}✖ Failed to parse AI response as JSON{RESET}")
            print(f"{GREY}Raw response: {result[:200]}...{RESET}")
    
    if cache_updated:
        save_cache(cache)

def run_llm_summarization(directory, config=None):
    """Run LLM-powered code summarization."""
    system_prompt = (
        "You are a senior software architect. Your task is to summarize the following code file in 2-3 sentences. "
        "Focus on its primary responsibility, its main inputs, and its key outputs or side effects. "
        "Respond ONLY with a JSON object matching the provided schema."
    )
    run_llm_analysis_on_top_files(directory, system_prompt, "Summary", CODE_SUMMARY_SCHEMA, config=config)

def run_llm_code_review(directory, config=None):
    """Run LLM-powered code review."""
    system_prompt = (
        "You are a code review expert specializing in clean code principles. Analyze the following code. "
        "Identify potential code smells such as long functions, high cyclomatic complexity, tight coupling, or poor naming. "
        "For each smell, provide a brief explanation and a suggestion for refactoring. "
        "If there are no obvious smells, say 'Code looks clean.' "
        "Respond ONLY with a JSON object matching the provided schema."
    )
    run_llm_analysis_on_top_files(directory, system_prompt, "Review", CODE_REVIEW_SCHEMA, config=config)
