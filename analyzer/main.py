"""
Main application entry point and CLI handling.
"""

import argparse
import os
from .config import PROJECT_ROOT, load_config, GREY, RESET
from .utils import collect_all_project_files, clear_cache
from .ai_analysis import run_llm_summarization, run_llm_code_review, configure_gemini
from .coverage_analysis import run_coverage_analysis
from .report_generators import generate_html_report, get_file_structure_from_data
from .interactive import run_architectural_analysis

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the Project Analyzer."""
    
    parser = argparse.ArgumentParser(
        description="Project Analyzer - Advanced Architectural Health Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,        epilog="""
Examples:
  python analyzer_main.py                         # Run architectural analysis (current directory)
  python analyzer_main.py ../bogart               # Analyze the bogart project  
  python analyzer_main.py --tree                  # Show file tree structure
  python analyzer_main.py --full                  # Run all analyses
  python analyzer_main.py --coverage              # Include test coverage
  python analyzer_main.py --review                # AI-powered code review
  python analyzer_main.py --markdown              # Output as Markdown"""
    )
    parser.add_argument('--tree', action='store_true', 
                       help='Show file tree structure')
    parser.add_argument('--markdown', action='store_true', 
                       help='Output results in Markdown format')
    parser.add_argument('--json', action='store_true', 
                       help='Output results in JSON format')
    parser.add_argument('--coverage', action='store_true', 
                       help='Run test coverage analysis if possible')
    parser.add_argument('--summarize', action='store_true', 
                       help='Use AI to summarize key files')
    parser.add_argument('--review', action='store_true', 
                       help='Use AI to review key files for code smells')
    parser.add_argument('--html-report', action='store_true', 
                       help='Generate an HTML report')
    parser.add_argument('--architecture', action='store_true', 
                       help='Run architectural health analysis (same as default)')
    parser.add_argument('--full', action='store_true', 
                       help='Run all analyses (structure, coverage, architecture)')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Clear the analysis cache before running')
    parser.add_argument('directory', nargs='?', default=None,
                       help='Directory to analyze (defaults to current directory)')
    
    args = parser.parse_args()
    
    # Clear cache if requested
    if args.clear_cache:
        clear_cache()
    
    # Load configuration
    config = load_config()
      # Configure AI if needed
    if args.summarize or args.review:
        configure_gemini()
    
    # Determine directory to analyze
    directory = args.directory if args.directory else PROJECT_ROOT
    
    # Convert to absolute path for consistency
    directory = os.path.abspath(directory)
    
    # Centralized file collection - walk filesystem once
    print(f"{GREY}Collecting project files...{RESET}")
    file_data = collect_all_project_files(directory, config=config)
    
    # Handle AI-only modes
    if args.summarize:
        run_llm_summarization(directory, config)
        return
    
    if args.review:
        run_llm_code_review(directory, config)
        return
    
    # If no flags are given, run architectural analysis by default (the "alerter" mode)
    if not any([args.tree, args.architecture, args.full, args.coverage, args.markdown, args.json, args.html_report]):
        run_architectural_analysis(directory, config, file_data)
        return
    
    # Handle architectural analysis
    if args.architecture or args.full:
        smells = run_architectural_analysis(directory, config, file_data)
    
    # Handle coverage analysis
    coverage_report = None
    if args.coverage or args.full:
        coverage_report = run_coverage_analysis(directory)
    
    # Generate main structure analysis (only if --tree flag or --full)
    text_output = ""
    if args.tree or args.full:
        text_output = get_file_structure_from_data(
            directory, file_data, 
            markdown=args.markdown, 
            json_output=args.json, 
            coverage_data=coverage_report
        )
        print(text_output)
    
    # Generate HTML report if requested
    if args.html_report:
        generate_html_report(directory, text_output, config, coverage_report)

if __name__ == "__main__":
    main()
