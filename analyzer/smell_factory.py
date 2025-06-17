"""
smell_factory.py

Provides a centralized factory for creating "smell" dictionaries, ensuring
a consistent structure for all code quality issues reported by the analyzer.
"""

from typing import Dict, Any, Optional

def create_smell(
    smell_type: str,
    file_path: str,
    message: str,
    severity: str,
    category: str,
    line: Optional[int] = None
) -> Dict[str, Any]:
    """
    Creates a standardized dictionary representing a code smell.

    Args:
        smell_type (str): The type of the smell (e.g., 'STALE_LOGIC').
        file_path (str): The path to the file where the smell was detected.
        message (str): A descriptive message about the smell.
        severity (str): The severity of the smell (e.g., 'Low', 'Medium', 'High').
        category (str): The category of the analysis that found the smell (e.g., 'Git Analysis').
        line (Optional[int]): The line number where the smell was detected.

    Returns:
        Dict[str, Any]: A dictionary representing the smell.
    """
    smell = {
        'type': smell_type,
        'file': file_path,
        'message': message,
        'severity': severity,
        'category': category,
    }
    if line is not None:
        smell['line'] = line
    else:
        smell['line'] = "N/A"
        
    return smell