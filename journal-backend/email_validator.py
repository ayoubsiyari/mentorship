# email_validator.py
# Email validation utilities with domain typo checker and optional API validation

import re
import os
import requests
from typing import Tuple, Optional

# Common domain typos and their corrections
DOMAIN_CORRECTIONS = {
    # Gmail typos
    'gmial.com': 'gmail.com',
    'gmal.com': 'gmail.com',
    'gamil.com': 'gmail.com',
    'gmali.com': 'gmail.com',
    'gmaill.com': 'gmail.com',
    'gnail.com': 'gmail.com',
    'gmsil.com': 'gmail.com',
    'gmeil.com': 'gmail.com',
    'gmail.co': 'gmail.com',
    'gmail.cm': 'gmail.com',
    'gmail.con': 'gmail.com',
    'gmail.vom': 'gmail.com',
    'gmail.cpm': 'gmail.com',
    'gmail.om': 'gmail.com',
    'gmai.com': 'gmail.com',
    'gmailcom': 'gmail.com',
    'gmaik.com': 'gmail.com',
    'gmaio.com': 'gmail.com',
    'gmaiil.com': 'gmail.com',
    
    # Yahoo typos
    'yaho.com': 'yahoo.com',
    'yahooo.com': 'yahoo.com',
    'yhoo.com': 'yahoo.com',
    'yhaoo.com': 'yahoo.com',
    'yahoo.co': 'yahoo.com',
    'yahoo.cm': 'yahoo.com',
    'yahoo.con': 'yahoo.com',
    
    # Hotmail typos
    'hotmal.com': 'hotmail.com',
    'hotmial.com': 'hotmail.com',
    'hotmai.com': 'hotmail.com',
    'hotmaill.com': 'hotmail.com',
    'hotmail.co': 'hotmail.com',
    'hotmail.cm': 'hotmail.com',
    'hotmail.con': 'hotmail.com',
    'hotnail.com': 'hotmail.com',
    
    # Outlook typos
    'outloo.com': 'outlook.com',
    'outlok.com': 'outlook.com',
    'outloook.com': 'outlook.com',
    'outlook.co': 'outlook.com',
    'outlook.cm': 'outlook.com',
    'outlook.con': 'outlook.com',
    
    # iCloud typos
    'iclod.com': 'icloud.com',
    'icoud.com': 'icloud.com',
    'icloud.co': 'icloud.com',
    'icloud.cm': 'icloud.com',
}

# Known invalid/disposable email domains
BLOCKED_DOMAINS = {
    'tempmail.com', 'throwaway.com', 'mailinator.com', 'guerrillamail.com',
    'temp-mail.org', '10minutemail.com', 'fakeinbox.com', 'trashmail.com',
    'getairmail.com', 'mohmal.com', 'tempail.com', 'emailondeck.com'
}


def is_valid_email_format(email: str) -> bool:
    """Check if email has valid format."""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip().lower()))


def check_domain_typo(email: str) -> Tuple[str, Optional[str]]:
    """
    Check for common domain typos and suggest corrections.
    Returns: (corrected_email, suggestion_message or None)
    """
    if not email or '@' not in email:
        return email, None
    
    email = email.strip().lower()
    local_part, domain = email.rsplit('@', 1)
    
    # Check for exact domain match in corrections
    if domain in DOMAIN_CORRECTIONS:
        corrected_domain = DOMAIN_CORRECTIONS[domain]
        corrected_email = f"{local_part}@{corrected_domain}"
        return corrected_email, f"Did you mean {corrected_email}?"
    
    return email, None


def is_blocked_domain(email: str) -> bool:
    """Check if email domain is in blocked/disposable list."""
    if not email or '@' not in email:
        return False
    domain = email.strip().lower().split('@')[1]
    return domain in BLOCKED_DOMAINS


def validate_email_with_api(email: str) -> Tuple[bool, str]:
    """
    Validate email using external API (optional).
    Uses AbstractAPI (free tier: 100 requests/month).
    Set EMAIL_VALIDATION_API_KEY in environment to enable.
    Returns: (is_valid, message)
    """
    api_key = os.environ.get('EMAIL_VALIDATION_API_KEY')
    
    if not api_key:
        # API not configured, skip validation
        return True, "API validation skipped (no API key configured)"
    
    try:
        response = requests.get(
            'https://emailvalidation.abstractapi.com/v1/',
            params={'api_key': api_key, 'email': email},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check deliverability
            deliverability = data.get('deliverability', 'UNKNOWN')
            is_valid_format = data.get('is_valid_format', {}).get('value', True)
            is_disposable = data.get('is_disposable_email', {}).get('value', False)
            is_smtp_valid = data.get('is_smtp_valid', {}).get('value', True)
            
            if not is_valid_format:
                return False, "Invalid email format"
            if is_disposable:
                return False, "Disposable email addresses are not allowed"
            if deliverability == 'UNDELIVERABLE':
                return False, "This email address appears to be undeliverable"
            if not is_smtp_valid:
                return False, "This email mailbox does not exist"
            
            return True, "Email validated successfully"
        else:
            # API error, allow email (fail-open)
            return True, f"API validation unavailable (status {response.status_code})"
            
    except requests.Timeout:
        return True, "API validation timed out"
    except Exception as e:
        return True, f"API validation error: {str(e)}"


def validate_email(email: str, check_api: bool = True) -> Tuple[bool, str, Optional[str]]:
    """
    Full email validation with all checks.
    Returns: (is_valid, message, suggested_correction)
    """
    if not email:
        return False, "Email is required", None
    
    email = email.strip().lower()
    
    # Check format
    if not is_valid_email_format(email):
        return False, "Invalid email format", None
    
    # Check for blocked domains
    if is_blocked_domain(email):
        return False, "This email provider is not allowed", None
    
    # Check for typos and get suggestion
    corrected_email, suggestion = check_domain_typo(email)
    
    # If API check is enabled and configured
    if check_api and corrected_email == email:  # Only check API if no typo found
        is_valid, api_message = validate_email_with_api(email)
        if not is_valid:
            return False, api_message, suggestion
    
    # Return with suggestion if typo found
    if suggestion:
        return True, suggestion, corrected_email
    
    return True, "Email is valid", None
