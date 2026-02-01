"""
Filename sanitization utilities.

Provides functions to sanitize filenames by removing or replacing
problematic characters like spaces, special characters, etc.
"""

import re
from pathlib import Path


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    Sanitize a filename by replacing spaces and removing special characters.
    
    Args:
        name: Original filename or name component
        max_length: Maximum length of the sanitized filename
    
    Returns:
        Sanitized filename safe for filesystem use
    
    Examples:
        >>> sanitize_filename("test file name")
        'test_file_name'
        >>> sanitize_filename("file@name#123")
        'filename123'
        >>> sanitize_filename("What's the best ecom")
        'Whats_the_best_ecom'
    """
    if not name:
        return "unnamed"
    
    # Replace spaces with underscores
    sanitized = name.replace(' ', '_')
    
    # Remove or replace special characters (keep alphanumeric, underscore, hyphen, dot)
    sanitized = re.sub(r'[^\w\-_\.]', '', sanitized)
    
    # Replace multiple underscores with single underscore
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_-.')
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized


def sanitize_screenshot_name(name: str, query: str = None, prefix: str = None) -> str:
    """
    Sanitize a screenshot filename, optionally including query and prefix.
    
    Args:
        name: Base name for the screenshot
        query: Optional query string to include (will be sanitized)
        prefix: Optional prefix (e.g., "google_ai", "error")
    
    Returns:
        Sanitized filename without extension
    
    Examples:
        >>> sanitize_screenshot_name("final", "What's the best ecom", "google_ai")
        'google_ai_final_Whats_the_best_ecom'
    """
    parts = []
    
    if prefix:
        parts.append(sanitize_filename(prefix))
    
    parts.append(sanitize_filename(name))
    
    if query:
        # Truncate query to reasonable length and sanitize
        query_part = sanitize_filename(query[:30])
        parts.append(query_part)
    
    return "_".join(parts)
