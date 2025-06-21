"""
Utility functions for the bot
"""

import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

def escape_markdown(text: Any) -> str:
    """Escape special characters for Telegram MarkdownV2"""
    if not text or text == 'N/A':
        return 'N/A'
    
    text = str(text)
    # Escape all MarkdownV2 special characters
    special_chars = r'([_*\[\]()~`>#+\-=|{}.!\\])'
    escaped_text = re.sub(special_chars, r'\\\1', text)
    return escaped_text

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return 'N/A'
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\s\-.,()@+:]', '', text)
    
    return text if text else 'N/A'

def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number format"""
    if not phone_number:
        return False
    
    # Remove spaces, dashes, and other non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone_number)
    
    # Check various phone number patterns
    patterns = [
        r'^\+\d{10,15}$',  # International format
        r'^\d{10}$',       # 10-digit local format
        r'^\d{11}$',       # 11-digit format
        r'^\+91\d{10}$',   # Indian format
        r'^\+1\d{10}$',    # US/Canada format
    ]
    
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return True
    
    return False

def validate_vehicle_number(vehicle_number: str) -> bool:
    """Validate vehicle registration number format"""
    if not vehicle_number:
        return False
    
    # Remove spaces and convert to uppercase
    cleaned = vehicle_number.upper().replace(' ', '').replace('-', '')
    
    # Indian vehicle registration patterns
    patterns = [
        r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{1,4}$',  # Standard format: MH01AB1234
        r'^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{1,4}$',  # Variable format
    ]
    
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return True
    
    return False

def extract_numbers(text: str) -> list:
    """Extract all numbers from text"""
    if not text:
        return []
    
    # Find all number sequences
    numbers = re.findall(r'\d+', str(text))
    return numbers

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def is_valid_image_format(filename: str) -> bool:
    """Check if file is a valid image format"""
    if not filename:
        return False
    
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']
    return any(filename.lower().endswith(ext) for ext in valid_extensions)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    if not filename:
        return "unknown_file"
    
    # Remove path separators and other dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Ensure it's not empty
    if not sanitized.strip('_'):
        sanitized = "unknown_file"
    
    return sanitized

def parse_coordinates(lat_str: str, lon_str: str) -> Optional[tuple]:
    """Parse GPS coordinates from strings"""
    try:
        if not lat_str or not lon_str:
            return None
        
        # Handle different coordinate formats
        lat = float(lat_str.replace(',', '.'))
        lon = float(lon_str.replace(',', '.'))
        
        # Basic validation
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return (lat, lon)
        
        return None
    
    except (ValueError, TypeError):
        return None

def format_coordinates(lat: float, lon: float) -> str:
    """Format coordinates for display"""
    try:
        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"
        
        return f"{abs(lat):.6f}°{lat_dir}, {abs(lon):.6f}°{lon_dir}"
    
    except (ValueError, TypeError):
        return "Invalid coordinates"

def get_google_maps_link(lat: float, lon: float) -> str:
    """Generate Google Maps link for coordinates"""
    try:
        return f"https://www.google.com/maps?q={lat},{lon}"
    except (ValueError, TypeError):
        return ""

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def is_suspicious_activity(user_id: int, action: str, recent_actions: list) -> bool:
    """Check if user activity is suspicious (spam detection)"""
    try:
        # Count recent similar actions
        similar_actions = [a for a in recent_actions if a.get('action') == action]
        
        # If more than 5 similar actions in recent history, flag as suspicious
        if len(similar_actions) > 5:
            return True
        
        return False
    
    except Exception as e:
        logger.warning(f"Error checking suspicious activity: {e}")
        return False

def validate_admin_command(user_id: int, admin_id: int) -> bool:
    """Validate if user can execute admin commands"""
    return user_id == admin_id

def format_uptime(start_time) -> str:
    """Format uptime duration"""
    try:
        from datetime import datetime
        
        if not start_time:
            return "Unknown"
        
        uptime = datetime.now() - start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    except Exception as e:
        logger.warning(f"Error formatting uptime: {e}")
        return "Unknown"

def log_function_call(func_name: str, user_id: int, params: dict = None):
    """Log function calls for debugging"""
    try:
        log_message = f"Function: {func_name}, User: {user_id}"
        if params:
            log_message += f", Params: {params}"
        
        logger.debug(log_message)
    
    except Exception as e:
        logger.warning(f"Error logging function call: {e}")

def safe_get(dictionary: dict, key: str, default: Any = None) -> Any:
    """Safely get value from dictionary"""
    try:
        return dictionary.get(key, default)
    except (AttributeError, TypeError):
        return default

def rate_limit_key(user_id: int, action: str) -> str:
    """Generate rate limit key"""
    return f"rate_limit:{user_id}:{action}"

def is_test_environment() -> bool:
    """Check if running in test environment"""
    import os
    return os.getenv('ENVIRONMENT', '').lower() in ['test', 'testing', 'dev', 'development']
