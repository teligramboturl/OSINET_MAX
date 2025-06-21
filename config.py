"""
Configuration module for the Telegram bot
Handles all configuration settings and environment variables
"""

import os
from typing import List, Dict, Any

class Config:
    """Configuration class for bot settings"""
    
    def __init__(self):
        # Bot configuration
        self.BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        self.ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
        
        # Validate required environment variables
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        if not self.ADMIN_ID:
            raise ValueError("ADMIN_ID environment variable is required")
        
        # Required channels for bot access
        self.REQUIRED_CHANNELS = [
            {
                'name': 'Bots Update Channel',
                'username': '@DONATE_ARMY_BOTS',
                'url': 'https://t.me/DONATE_ARMY_BOTS'
            },
            {
                'name': 'Main Channel',
                'username': None,
                'url': 'https://t.me/+TEOLVuOuPl01Y2U1'
            },
            {
                'name': 'Join Must Channel',
                'username': None,
                'url': 'https://t.me/DonateMod'
            }
        ]
        
        # Rate limiting settings
        self.RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '5'))
        self.RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))  # seconds
        
        # Database settings
        self.DATABASE_FILE = os.getenv('DATABASE_FILE', 'bot_data.db')
        self.USERS_FILE = os.getenv('USERS_FILE', 'users.json')
        
        # Scraping settings
        self.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))
        self.MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
        
        # Feature flags
        self.ENABLE_OCR = os.getenv('ENABLE_OCR', 'false').lower() == 'true'
        self.ENABLE_IMAGE_PROCESSING = os.getenv('ENABLE_IMAGE_PROCESSING', 'true').lower() == 'true'
        
        # Logging settings
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
        
    def get_user_agent(self) -> str:
        """Get a realistic user agent string"""
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def get_request_headers(self) -> Dict[str, str]:
        """Get standard request headers"""
        return {
            "User-Agent": self.get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
