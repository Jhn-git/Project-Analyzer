"""
Report generation utilities for different output formats.
"""

import os
import re
import json
from datetime import datetime

from .config import BOLD, RESET, GREY, GREEN, SCRIPT_EXTS
from .utils import remove_ansi_colors

# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_html_report(directory, text_output, config, coverage_report):
    """Generate an HTML report of the analysis."""
    try:
        from jinja2 import Template
    except ImportError:
        print(f"Jinja2 is required for HTML report generation. Install with 'pip install jinja2'.")
        return
    
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Project Analyzer Report</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f8f8f8; color: #222; }
            .container { max-width: 900px; margin: 2em auto; background: #fff; padding: 2em; border-radius: 8px; box-shadow: 0 2px 8px #0001; }
            h1 { color: #2d5be3; }
            pre { background: #f4f4f4; padding: 1em; border-radius: 6px; overflow-x: auto; }
            .section { margin-bottom: 2em; }
            .coverage { background: #e8f5e9; padding: 1em; border-radius: 6px; }
            .timestamp { color: #888; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Project Analyzer Report</h1>
            <div class="timestamp">Generated: {{ timestamp }}</div>
            <div class="section">
                <h2>File Tree & Stats</h2>
                <pre>{{ file_tree }}</pre>
            </div>
            {% if coverage %}
            <div class="section coverage">
                <h2>Test Coverage</h2>
                <pre>{{ coverage }}</pre>
            </div>
            {% endif %}
            {% if config %}
            <div class="section">
                <h2>Analyzer Config</h2>
                <pre>{{ config }}</pre>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    
    template = Template(html_template)
    html = template.render(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        file_tree=remove_ansi_colors(text_output),
        coverage=remove_ansi_colors(coverage_report) if coverage_report else None,
        config=json.dumps(config, indent=2) if config else None
    )
    
    out_path = os.path.join(directory, "analyzer-report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{GREEN}HTML report generated at: {out_path}{RESET}")

def get_file_structure_from_data(directory, file_data, markdown=False, json_output=False, coverage_data=None):
    """
    Generate file structure output from collected file data.
    """
    output_lines = []
    
    if json_output:
        # Return JSON format
        result = {
            "directory": directory,
            "total_files": len(file_data['all_files']),
            "total_directories": len(file_data['all_directories']),
            "source_directories": file_data['source_directories'],
            "script_files": len(file_data['script_files'])
        }
        if coverage_data:
            result["coverage"] = coverage_data
        return json.dumps(result, indent=2)
    
    # Generate text output
    output_lines.append(f"\n{BOLD}📁 Project Structure Analysis{RESET}")
    output_lines.append(f"{GREY}================================{RESET}")
    output_lines.append(f"Directory: {directory}")
    output_lines.append(f"Total Files: {len(file_data['all_files'])}")
    output_lines.append(f"Total Directories: {len(file_data['all_directories'])}")
    output_lines.append(f"Script Files: {len(file_data['script_files'])}")
    
    if file_data['source_directories']:
        output_lines.append(f"\n{BOLD}Source Directories:{RESET}")
        for src_dir in file_data['source_directories']:
            output_lines.append(f"  📂 {os.path.relpath(src_dir, directory)}")
    
    if coverage_data:
        output_lines.append(f"\n{BOLD}Test Coverage:{RESET}")
        output_lines.append(coverage_data)
    
    result = "\n".join(output_lines)
    
    if markdown:
        # Convert to markdown format
        result = result.replace(BOLD, "**").replace(RESET, "**")
        result = re.sub(r"\033\[[0-9;]*m", "", result)  # Remove other ANSI codes
    
    return result

def format_architectural_summary(smells, markdown=False):
    """Format architectural analysis results for display."""
    if not smells:
        result = f"\n{GREEN}✅ No architectural issues detected! Your project structure looks healthy.{RESET}"
    else:
        lines = [f"\n{BOLD}🏗️ Architectural Issues Found: {len(smells)}{RESET}"]
        
        # Group by type
        from collections import defaultdict
        smell_groups = defaultdict(list)
        for smell in smells:
            smell_groups[smell['type']].append(smell)
        
        for smell_type, smell_list in smell_groups.items():
            from .config import ARCHITECTURAL_SMELLS
            emoji_type = ARCHITECTURAL_SMELLS.get(smell_type, '⚠️ ISSUE')
            lines.append(f"\n{emoji_type} ({len(smell_list)} issues):")
            
            for smell in smell_list[:3]:  # Show first 3 of each type
                file_info = ""
                if 'file' in smell:
                    file_info = f" in {os.path.basename(smell['file'])}"
                elif 'files' in smell:
                    file_info = f" involving {len(smell['files'])} files"
                lines.append(f"  • {smell['message']}{file_info}")
            
            if len(smell_list) > 3:
                lines.append(f"  ... and {len(smell_list) - 3} more")
        
        result = "\n".join(lines)
    
    if markdown:
        result = result.replace(BOLD, "**").replace(RESET, "**")
        result = re.sub(r"\033\[[0-9;]*m", "", result)
    
    return result
