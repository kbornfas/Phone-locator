"""
Phone Number Validators for PhoneTracker CLI
"""

import re
import phonenumbers
from phonenumbers import NumberParseException
from typing import Tuple, Optional


def validate_phone_number(number: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate a phone number.
    
    Args:
        number: Phone number to validate
        
    Returns:
        Tuple of (is_valid, formatted_number, error_message)
    """
    # Basic format check
    if not number:
        return False, None, "Phone number is required"
    
    # Clean the number
    cleaned = re.sub(r'[\s\-\(\)]', '', number)
    
    # Ensure it starts with +
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    
    try:
        parsed = phonenumbers.parse(cleaned, None)
        
        if not phonenumbers.is_valid_number(parsed):
            return False, None, "Invalid phone number"
        
        # Format in E.164
        formatted = phonenumbers.format_number(
            parsed, 
            phonenumbers.PhoneNumberFormat.E164
        )
        
        return True, formatted, None
        
    except NumberParseException as e:
        return False, None, f"Could not parse phone number: {str(e)}"


def validate_e164(number: str) -> bool:
    """
    Check if a number is in E.164 format.
    
    E.164 format: +[country code][subscriber number]
    Example: +14155552671
    
    Args:
        number: Phone number to check
        
    Returns:
        True if valid E.164 format
    """
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, number))


def format_phone_number(number: str, format_type: str = 'e164') -> str:
    """
    Format a phone number in various formats.
    
    Args:
        number: Phone number to format
        format_type: Format type ('e164', 'international', 'national')
        
    Returns:
        Formatted phone number string
    """
    try:
        parsed = phonenumbers.parse(number, None)
        
        formats = {
            'e164': phonenumbers.PhoneNumberFormat.E164,
            'international': phonenumbers.PhoneNumberFormat.INTERNATIONAL,
            'national': phonenumbers.PhoneNumberFormat.NATIONAL,
        }
        
        fmt = formats.get(format_type, phonenumbers.PhoneNumberFormat.E164)
        return phonenumbers.format_number(parsed, fmt)
        
    except NumberParseException:
        return number  # Return original if parsing fails


def get_country_code(number: str) -> Optional[str]:
    """
    Extract the country code from a phone number.
    
    Args:
        number: Phone number in E.164 format
        
    Returns:
        Country code string or None
    """
    try:
        parsed = phonenumbers.parse(number, None)
        return str(parsed.country_code)
    except NumberParseException:
        return None


def get_region(number: str) -> Optional[str]:
    """
    Get the region/country for a phone number.
    
    Args:
        number: Phone number
        
    Returns:
        Region code (e.g., 'US', 'KE') or None
    """
    try:
        parsed = phonenumbers.parse(number, None)
        return phonenumbers.region_code_for_number(parsed)
    except NumberParseException:
        return None
