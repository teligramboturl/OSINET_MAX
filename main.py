#!/usr/bin/env python3
"""
Telegram Bot for Phone Tracing and Vehicle Lookup
Main entry point for the bot application
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import Config
from bot_handlers import BotHandlers
from user_management import UserManager
from database import Database

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.config = Config()
        self.database = Database()
        self.user_manager = UserManager(self.database)
        self.handlers = BotHandlers(self.user_manager, self.config)
        self.application = None
        
    async def setup_bot(self):
        """Initialize the bot application"""
        try:
            # Clear any existing webhooks
            await self.clear_webhooks()
            
            # Create application
            self.application = Application.builder().token(self.config.BOT_TOKEN).build()
            
            # Add handlers
            await self.add_handlers()
            
            logger.info("✅ Bot setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup bot: {e}")
            return False
    
    async def clear_webhooks(self):
        """Clear any existing webhooks"""
        try:
            import requests
            webhook_url = f"https://api.telegram.org/bot{self.config.BOT_TOKEN}/deleteWebhook"
            response = requests.post(webhook_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    logger.info("✅ Cleared existing webhooks")
                else:
                    logger.warning(f"⚠️ Webhook clear response: {data}")
            else:
                logger.warning(f"⚠️ Webhook clear failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not clear webhooks: {e}")
    
    async def add_handlers(self):
        """Add all command and callback handlers"""
        try:
            # Command handlers
            self.application.add_handler(CommandHandler("start", self.handlers.start_command))
            self.application.add_handler(CommandHandler("help", self.handlers.help_command))
            self.application.add_handler(CommandHandler("trace", self.handlers.trace_command))
            self.application.add_handler(CommandHandler("vehicle", self.handlers.vehicle_command))
            self.application.add_handler(CommandHandler("stats", self.handlers.stats_command))
            self.application.add_handler(CommandHandler("admin", self.handlers.admin_command))
            self.application.add_handler(CommandHandler("broadcast", self.handlers.broadcast_command))
            
            # Callback query handler
            self.application.add_handler(CallbackQueryHandler(self.handlers.button_callback))
            
            # Message handlers
            self.application.add_handler(MessageHandler(filters.PHOTO, self.handlers.photo_handler))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.text_handler))
            
            # Error handler
            self.application.add_error_handler(self.handlers.error_handler)
            
            logger.info("✅ All handlers added successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to add handlers: {e}")
            raise
    
    async def start_polling(self):
        """Start the bot with polling"""
        try:
            logger.info("🚀 Starting bot polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query']
            )
            
            logger.info("✅ Bot is running! Press Ctrl+C to stop.")
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Error during polling: {e}")
            raise
        finally:
            await self.stop_bot()
    
    async def stop_bot(self):
        """Stop the bot gracefully"""
        try:
            if self.application:
                logger.info("🛑 Stopping bot...")
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("✅ Bot stopped successfully")
        except Exception as e:
            logger.error(f"❌ Error stopping bot: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"📡 Received signal {signum}")
    sys.exit(0)

async def main():
    """Main function to run the bot"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and start bot
        bot = TelegramBot()
        
        if await bot.setup_bot():
            await bot.start_polling()
        else:
            logger.error("❌ Failed to setup bot")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
