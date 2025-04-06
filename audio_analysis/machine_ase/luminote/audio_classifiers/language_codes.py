import csv
from typing import Dict, Optional
import os

def load_language_codes() -> Dict[str, str]:
    """Load language codes from CSV and return mapping of 3-letter codes to language names."""
    language_map = {}

    this_folder = os.path.dirname(__file__)
    csv_path = os.path.join(this_folder, 'iso-639-3.csv')
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                three_letter = parts[0]
                language_name = parts[1]
                if three_letter:  # Only add if three-letter code exists
                    language_map[three_letter] = language_name
    
    return language_map

def get_language_name(code: str) -> Optional[str]:
    """
    Get language name from three-letter language code.
    
    Args:
        code: Three-letter language code (e.g. 'eng', 'fra', 'deu')
        
    Returns:
        Language name or None if code not found
    """
    global _language_map
    
    if not hasattr(get_language_name, '_language_map'):
        _language_map = load_language_codes()
        
    return _language_map.get(code.lower())