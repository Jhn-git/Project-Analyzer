"""
Interactive deep dive analysis features.
"""

import os
from collections import defaultdict

from .config import BOLD, RESET, GREY, RED, GREEN, YELLOW, ARCHITECTURAL_SMELLS
from .ai_analysis import configure_gemini, call_llm

# =============================================================================
# INTERACTIVE DEEP DIVE MODE
# =============================================================================

def interactive_deep_dive(smells, directory, config=None):
    """Interactive mode for deep-diving into specific architectural issues with AI."""
    if not smells:
        return
    
    # Configure AI if not already done
    if not configure_gemini():
        print(f"{RED}AI not configured. Cannot perform deep dive analysis.{RESET}")
        return
    
    print(f"\n{BOLD}🔍 Interactive Deep Dive Mode{RESET}")
    print(f"{GREY}Select an issue to analyze with AI, or 'q' to quit:{RESET}")
    
    # Group smells by type for better organization
    smell_groups = defaultdict(list)
    for smell in smells:
        smell_groups[smell['type']].append(smell)
    
    # Create a numbered list of all issues
    issues = []
    index = 1
    
    for smell_type, smell_list in smell_groups.items():
        emoji_type = ARCHITECTURAL_SMELLS.get(smell_type, '⚠️  ISSUE')
        print(f"\n{RED}{emoji_type}:{RESET}")
        
        for smell in smell_list:
            file_info = ""
            if 'file' in smell:
                file_info = f" in {os.path.basename(smell['file'])}"
            elif 'files' in smell:
                file_info = f" involving {len(smell['files'])} files"
            
            print(f"  {index}. {smell['message']}{file_info}")
            issues.append(smell)
            index += 1
    
    while True:
        try:
            choice = input(f"\n{GREY}Enter number (1-{len(issues)}) or 'q' to quit: {RESET}").strip()
            if choice.lower() == 'q':
                break
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(issues):
                    selected_smell = issues[choice_num - 1]
                    analyze_smell_with_ai(selected_smell, directory, config)
                else:
                    print(f"{RED}Invalid selection. Please enter a number between 1 and {len(issues)}.{RESET}")
            except ValueError:
                print(f"{RED}Invalid input. Please enter a number or 'q'.{RESET}")
                
        except KeyboardInterrupt:
            print(f"\n{GREY}Exiting deep dive analysis.{RESET}")
            break

def analyze_smell_with_ai(smell, directory, config=None):
    """Analyze a specific architectural smell with AI."""
    smell_type = smell['type']
    
    # Get the relevant file(s) for analysis
    target_files = []
    if 'file' in smell:
        target_files = [smell['file']]
    elif 'files' in smell:
        target_files = smell['files'][:3]  # Limit to 3 files for token limits
    
    if not target_files:
        print(f"{RED}No files associated with this issue.{RESET}")
        return
    
    print(f"\n{BOLD}🤖 AI Deep Dive Analysis{RESET}")
    print(f"{YELLOW}Issue Type:{RESET} {ARCHITECTURAL_SMELLS.get(smell_type, smell_type)}")
    print(f"{YELLOW}Description:{RESET} {smell['message']}")
    
    # Create specialized prompts based on smell type
    system_prompt = get_deep_dive_prompt(smell_type)
    
    for i, file_path in enumerate(target_files, 1):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
            
            print(f"\n{BOLD}Analysis {i}/{len(target_files)}: {os.path.relpath(file_path, directory)}{RESET}")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"File: {os.path.relpath(file_path, directory)}\n\nCode:\n{file_content}"}
            ]
            
            print(f"{GREY}Analyzing with AI...{RESET}")
            response = call_llm(messages)
            
            print(f"{GREEN}AI Analysis:{RESET}")
            print(response)
            
        except Exception as e:
            print(f"{RED}Error analyzing {file_path}: {e}{RESET}")
    
    print(f"\n{GREY}{'='*60}{RESET}")

def get_deep_dive_prompt(smell_type):
    """Get specialized AI prompts based on architectural smell type."""
    prompts = {
        'BOUNDARY_VIOLATION': """You are an expert software architect specializing in layered architecture and dependency management. 
        Analyze the code for architectural boundary violations and provide specific refactoring steps to fix dependency issues.""",
        
        'ENTANGLEMENT': """You are an expert in feature-driven development and module decoupling. 
        Analyze the code for feature entanglement and suggest ways to extract shared dependencies into common modules.""",
        
        'BLAST_RADIUS': """You are an expert in dependency injection and module design. 
        Analyze this highly-imported file and suggest ways to reduce its blast radius through better abstraction and interface design.""",
        
        'CIRCULAR_DEPENDENCY': """You are an expert in dependency graph analysis and refactoring. 
        Analyze the code for circular dependencies and provide step-by-step instructions to break the dependency cycle.""",
        
        'GHOST_FILE': """You are a test-driven development expert. 
        Analyze this untested file and suggest the most important test cases to write, considering edge cases and business logic.""",
        
        'STALE_LOGIC': """You are an expert in legacy code modernization and technical debt management. 
        Analyze this old code and identify potential risks, outdated patterns, and modernization opportunities.""",
        
        'HIGH_CHURN': """You are an expert in code stability and change impact analysis. 
        Analyze this frequently-changed file to identify why it changes often and suggest refactoring to improve stability.""",
        
        'STALE_TESTS': """You are a testing strategy expert. 
        Analyze the relationship between this source file and its tests, and suggest how to bring the test coverage up to date."""
    }
    
    return prompts.get(smell_type, 
        "You are a software architecture expert. Analyze the code and provide specific recommendations for improvement.")

def run_architectural_analysis(directory, config=None, file_data=None):
    """
    Run architectural analysis and provide interactive deep-dive capabilities.
    
    This function:
    1. Runs the architectural smell detection using ArchitecturalSniffer
    2. Displays issues found in a numbered format
    3. Prompts user to select issues for AI deep-dive analysis
    4. Calls interactive_deep_dive() when issues are found
    """
    print(f"\n{BOLD}🏗️  Architectural Health Analysis{RESET}")
    print(f"{GREY}==================================={RESET}")
    
    # Get file data if not provided
    if file_data is None:
        from .utils import collect_all_project_files
        file_data = collect_all_project_files(directory, config=config)
    
    # Initialize architectural sniffer
    from .architectural_analysis import ArchitecturalSniffer
    sniffer = ArchitecturalSniffer(directory, config)
    
    # Run architectural analysis
    smells = sniffer.analyze_architecture(file_data['all_files'])
    
    # Display results
    if not smells:
        print(f"\n{GREEN}✅ No architectural issues detected! Your project structure looks healthy.{RESET}")
        return smells
    
    # Display architectural issues summary
    print(f"\n{RED}Found {len(smells)} architectural issues.{RESET}")
    
    # Group smells by type for better organization
    smell_groups = defaultdict(list)
    for smell in smells:
        smell_groups[smell['type']].append(smell)
    
    # Display numbered list of issues
    issues = []
    index = 1
    
    for smell_type, smell_list in smell_groups.items():
        emoji_type = ARCHITECTURAL_SMELLS.get(smell_type, '⚠️  ISSUE')
        print(f"\n{RED}{emoji_type}:{RESET}")
        
        for smell in smell_list:
            file_info = ""
            if 'file' in smell:
                file_info = f" in {os.path.basename(smell['file'])}"
            elif 'files' in smell:
                file_info = f" involving {len(smell['files'])} files"
            
            print(f"  {index}. {smell['message']}{file_info}")
            issues.append(smell)
            index += 1
    
    # Prompt for interactive analysis
    print(f"\n{BOLD}Enter number to deep-dive with AI, or 'q' to quit:{RESET}")
    
    try:
        choice = input(f"{GREY}> {RESET}").strip()
        if choice.lower() != 'q':
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(issues):
                    selected_smell = issues[choice_num - 1]
                    analyze_smell_with_ai(selected_smell, directory, config)
                    # Continue with interactive mode
                    interactive_deep_dive(smells, directory, config)
                else:
                    print(f"{YELLOW}Invalid selection. Entering interactive mode...{RESET}")
                    interactive_deep_dive(smells, directory, config)
            except ValueError:
                print(f"{YELLOW}Invalid input. Entering interactive mode...{RESET}")
                interactive_deep_dive(smells, directory, config)
            
    except KeyboardInterrupt:
        print(f"\n{GREY}Exiting analysis.{RESET}")
    
    return smells
