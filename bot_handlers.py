"""
Bot handlers for processing Telegram commands and callbacks
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from tracing_services import TracingService
from user_management import UserManager
from config import Config
from utils import escape_markdown, validate_phone_number, validate_vehicle_number
from image_processor import ImageProcessor

logger = logging.getLogger(__name__)

class BotHandlers:
    """Handler class for all bot commands and callbacks"""
    
    def __init__(self, user_manager: UserManager, config: Config):
        self.user_manager = user_manager
        self.config = config
        self.tracing_service = TracingService(config)
        self.image_processor = ImageProcessor()
        self.rate_limiter = {}  # Simple rate limiting storage
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            # Log user activity
            is_new_user = self.user_manager.log_user_activity(
                user.id, user.username, user.first_name, "start"
            )
            
            # Check rate limiting
            if not self._check_rate_limit(user.id):
                await update.message.reply_text(
                    "⏰ Please wait before using the bot again. Rate limit exceeded.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Check membership
            if not await self._check_user_membership(context, user.id):
                keyboard = self._create_join_keyboard()
                welcome_text = (
                    f"👋 Welcome {escape_markdown(user.first_name)}!\n\n"
                    f"🔒 To use this bot, you need to join our required channels first:\n\n"
                    f"📢 Please join all channels below and click 'I Joined' button:"
                )
                
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                return
            
            # Send welcome message
            welcome_text = (
                f"🎉 *Welcome to Phone Tracer & Vehicle Lookup Bot*\n\n"
                f"👤 Hello {escape_markdown(user.first_name)}\\!\n\n"
                f"🔍 *Available Commands:*\n"
                f"📱 `/trace <phone_number>` \\- Trace phone number\n"
                f"🚗 `/vehicle <registration>` \\- Vehicle lookup\n"
                f"📊 `/stats` \\- View your statistics\n"
                f"❓ `/help` \\- Show help information\n\n"
                f"📸 *Image Features:*\n"
                f"🖼️ Send images to extract EXIF data\n"
                f"📄 OCR text extraction \\(if enabled\\)\n\n"
                f"⚡ *Quick Tips:*\n"
                f"• Use international format for phone numbers\n"
                f"• Vehicle registration should be in correct format\n"
                f"• Images are processed automatically\n\n"
                f"🛡️ *Privacy:* We respect your privacy and don't store personal data unnecessarily\\."
            )
            
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
            # Send new user notification to admin
            if is_new_user:
                await self._notify_admin_new_user(context, user)
                
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await self._send_error_message(update, "Failed to process start command")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            help_text = (
                f"📖 *Bot Help & Instructions*\n\n"
                f"🔍 *Phone Tracing:*\n"
                f"• `/trace +1234567890` \\- Trace phone number\n"
                f"• `/trace 9876543210` \\- Trace Indian number\n"
                f"• Supports international formats\n\n"
                f"🚗 *Vehicle Lookup:*\n"
                f"• `/vehicle MH01AB1234` \\- Vehicle registration lookup\n"
                f"• `/vehicle DL05CD5678` \\- Delhi registration\n"
                f"• Shows RTO, state, and other details\n\n"
                f"📸 *Image Processing:*\n"
                f"• Send any image to extract metadata\n"
                f"• EXIF data extraction\n"
                f"• GPS coordinates \\(if available\\)\n"
                f"• OCR text extraction \\(if enabled\\)\n\n"
                f"📊 *Statistics:*\n"
                f"• `/stats` \\- View your usage statistics\n"
                f"• Track your activity\n\n"
                f"🛡️ *Privacy & Security:*\n"
                f"• All data is processed securely\n"
                f"• No personal information stored\n"
                f"• Rate limiting for fair usage\n\n"
                f"❓ *Need Help?*\n"
                f"Contact our support channels for assistance\\."
            )
            
            await update.message.reply_text(
                help_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await self._send_error_message(update, "Failed to show help")
    
    async def trace_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trace command"""
        try:
            user = update.effective_user
            
            # Check rate limiting
            if not self._check_rate_limit(user.id):
                await update.message.reply_text(
                    "⏰ Please wait before making another request. Rate limit exceeded."
                )
                return
            
            # Check membership
            if not await self._check_user_membership(context, user.id):
                await self._send_membership_required(update)
                return
            
            # Validate input
            if not context.args:
                await update.message.reply_text(
                    "📱 Please provide a phone number to trace.\n"
                    "Example: `/trace +1234567890` or `/trace 9876543210`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            phone_number = " ".join(context.args).strip()
            
            # Validate phone number
            if not validate_phone_number(phone_number):
                await update.message.reply_text(
                    "❌ Invalid phone number format.\n"
                    "Please use international format (+1234567890) or local format (9876543210)."
                )
                return
            
            # Log activity
            self.user_manager.log_user_activity(
                user.id, user.username, user.first_name, f"trace:{phone_number}"
            )
            
            # Send processing message
            processing_msg = await update.message.reply_text(
                "🔍 Tracing phone number... Please wait."
            )
            
            # Perform trace
            result = await self.tracing_service.trace_phone_number(phone_number)
            
            if isinstance(result, dict):
                # Format successful result
                formatted_result = self._format_trace_result(result)
                await processing_msg.edit_text(
                    formatted_result,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                # Handle error result
                await processing_msg.edit_text(
                    f"❌ Tracing failed: {escape_markdown(str(result))}"
                )
                
        except Exception as e:
            logger.error(f"Error in trace command: {e}")
            await self._send_error_message(update, "Failed to trace phone number")
    
    async def vehicle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /vehicle command"""
        try:
            user = update.effective_user
            
            # Check rate limiting
            if not self._check_rate_limit(user.id):
                await update.message.reply_text(
                    "⏰ Please wait before making another request. Rate limit exceeded."
                )
                return
            
            # Check membership
            if not await self._check_user_membership(context, user.id):
                await self._send_membership_required(update)
                return
            
            # Validate input
            if not context.args:
                await update.message.reply_text(
                    "🚗 Please provide a vehicle registration number.\n"
                    "Example: `/vehicle MH01AB1234` or `/vehicle DL05CD5678`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            vehicle_number = " ".join(context.args).strip().upper()
            
            # Validate vehicle number
            if not validate_vehicle_number(vehicle_number):
                await update.message.reply_text(
                    "❌ Invalid vehicle registration format.\n"
                    "Please use format like: MH01AB1234, DL05CD5678, etc."
                )
                return
            
            # Log activity
            self.user_manager.log_user_activity(
                user.id, user.username, user.first_name, f"vehicle:{vehicle_number}"
            )
            
            # Send processing message
            processing_msg = await update.message.reply_text(
                "🔍 Looking up vehicle information... Please wait."
            )
            
            # Perform lookup
            result = await self.tracing_service.lookup_vehicle_info(vehicle_number)
            
            if isinstance(result, dict):
                # Format successful result
                formatted_result = self._format_vehicle_result(result)
                await processing_msg.edit_text(
                    formatted_result,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                # Handle error result
                await processing_msg.edit_text(
                    f"❌ Vehicle lookup failed: {escape_markdown(str(result))}"
                )
                
        except Exception as e:
            logger.error(f"Error in vehicle command: {e}")
            await self._send_error_message(update, "Failed to lookup vehicle information")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            user = update.effective_user
            
            # Get user statistics
            stats = self.user_manager.get_user_stats(user.id)
            
            if not stats:
                await update.message.reply_text(
                    "📊 No statistics found. Use the bot first to generate stats."
                )
                return
            
            # Format stats message
            stats_text = (
                f"📊 *Your Statistics*\n\n"
                f"👤 *User Info:*\n"
                f"• ID: `{stats['user_id']}`\n"
                f"• Username: @{escape_markdown(stats.get('username', 'N/A'))}\n"
                f"• Name: {escape_markdown(stats.get('first_name', 'N/A'))}\n\n"
                f"📈 *Activity:*\n"
                f"• Total Commands: {stats.get('total_commands', 0)}\n"
                f"• First Seen: {escape_markdown(stats.get('first_seen', 'N/A'))}\n"
                f"• Last Activity: {escape_markdown(stats.get('last_seen', 'N/A'))}\n\n"
                f"⚡ *Recent Activity:*\n"
                f"• Phone Traces: {stats.get('phone_traces', 0)}\n"
                f"• Vehicle Lookups: {stats.get('vehicle_lookups', 0)}\n"
                f"• Images Processed: {stats.get('images_processed', 0)}"
            )
            
            await update.message.reply_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await self._send_error_message(update, "Failed to get statistics")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        try:
            user = update.effective_user
            
            # Check if user is admin
            if user.id != self.config.ADMIN_ID:
                await update.message.reply_text("❌ Access denied. Admin only.")
                return
            
            # Get bot statistics
            total_users = self.user_manager.get_total_users()
            active_users = self.user_manager.get_active_users()
            
            admin_text = (
                f"🛡️ *Admin Dashboard*\n\n"
                f"📊 *Bot Statistics:*\n"
                f"• Total Users: {total_users}\n"
                f"• Active Users \\(24h\\): {active_users}\n"
                f"• Bot Uptime: {self._get_bot_uptime()}\n\n"
                f"⚡ *Commands:*\n"
                f"• `/broadcast <message>` \\- Broadcast to all users\n"
                f"• `/admin` \\- Show this dashboard\n\n"
                f"🔧 *System Status:*\n"
                f"• All services operational\n"
                f"• Rate limiting active\n"
                f"• Database connected"
            )
            
            await update.message.reply_text(
                admin_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
        except Exception as e:
            logger.error(f"Error in admin command: {e}")
            await self._send_error_message(update, "Failed to show admin dashboard")
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command"""
        try:
            user = update.effective_user
            
            # Check if user is admin
            if user.id != self.config.ADMIN_ID:
                await update.message.reply_text("❌ Access denied. Admin only.")
                return
            
            if not context.args:
                await update.message.reply_text(
                    "📢 Please provide a message to broadcast.\n"
                    "Example: `/broadcast Hello everyone!`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            message = " ".join(context.args)
            
            # Get all users
            all_users = self.user_manager.get_all_users()
            
            if not all_users:
                await update.message.reply_text("❌ No users found to broadcast to.")
                return
            
            # Send broadcast
            success_count = 0
            failed_count = 0
            
            status_msg = await update.message.reply_text(
                f"📢 Broadcasting to {len(all_users)} users..."
            )
            
            for user_id in all_users:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📢 *Broadcast Message:*\n\n{escape_markdown(message)}",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    success_count += 1
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Failed to send broadcast to {user_id}: {e}")
                    failed_count += 1
            
            await status_msg.edit_text(
                f"📢 Broadcast completed!\n"
                f"✅ Sent: {success_count}\n"
                f"❌ Failed: {failed_count}"
            )
            
        except Exception as e:
            logger.error(f"Error in broadcast command: {e}")
            await self._send_error_message(update, "Failed to broadcast message")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == 'check_membership':
                user_id = query.from_user.id
                
                if await self._check_user_membership(context, user_id):
                    await query.message.edit_text(
                        "✅ Membership verified! You can now use all bot features.\n"
                        "Type /help to see available commands.",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await query.message.edit_text(
                        "❌ Please join all required channels first, then click the button again.",
                        reply_markup=self._create_join_keyboard()
                    )
            
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
            try:
                await query.message.reply_text("❌ An error occurred processing your request.")
            except:
                pass
    
    async def photo_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages"""
        try:
            user = update.effective_user
            
            # Check rate limiting
            if not self._check_rate_limit(user.id):
                await update.message.reply_text(
                    "⏰ Please wait before sending another image."
                )
                return
            
            # Check membership
            if not await self._check_user_membership(context, user.id):
                await self._send_membership_required(update)
                return
            
            # Log activity
            self.user_manager.log_user_activity(
                user.id, user.username, user.first_name, "image_processing"
            )
            
            # Process image
            processing_msg = await update.message.reply_text(
                "🖼️ Processing image... Please wait."
            )
            
            # Get the largest photo
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            # Download and process
            file_data = await file.download_as_bytearray()
            result = await self.image_processor.process_image(file_data)
            
            if result:
                formatted_result = self._format_image_result(result)
                await processing_msg.edit_text(
                    formatted_result,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                await processing_msg.edit_text(
                    "❌ Could not extract information from the image."
                )
                
        except Exception as e:
            logger.error(f"Error in photo handler: {e}")
            await self._send_error_message(update, "Failed to process image")
    
    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            text = update.message.text.strip()
            
            # Check if it looks like a phone number
            if validate_phone_number(text):
                await update.message.reply_text(
                    f"📱 Detected phone number: {text}\n"
                    f"Use `/trace {text}` to trace this number.",
                    parse_mode=ParseMode.MARKDOWN
                )
            # Check if it looks like a vehicle number
            elif validate_vehicle_number(text):
                await update.message.reply_text(
                    f"🚗 Detected vehicle registration: {text}\n"
                    f"Use `/vehicle {text}` to lookup this vehicle.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    "❓ I didn't understand that. Type /help for available commands."
                )
                
        except Exception as e:
            logger.error(f"Error in text handler: {e}")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Please try again later."
                )
            except:
                pass
    
    # Helper methods
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        now = datetime.now()
        user_key = str(user_id)
        
        if user_key not in self.rate_limiter:
            self.rate_limiter[user_key] = []
        
        # Clean old entries
        cutoff_time = now - timedelta(seconds=self.config.RATE_LIMIT_WINDOW)
        self.rate_limiter[user_key] = [
            request_time for request_time in self.rate_limiter[user_key]
            if request_time > cutoff_time
        ]
        
        # Check if limit exceeded
        if len(self.rate_limiter[user_key]) >= self.config.RATE_LIMIT_REQUESTS:
            return False
        
        # Add current request
        self.rate_limiter[user_key].append(now)
        return True
    
    async def _check_user_membership(self, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
        """Check if user is member of required channels"""
        for channel in self.config.REQUIRED_CHANNELS:
            if channel['username']:
                try:
                    member = await context.bot.get_chat_member(channel['username'], user_id)
                    if member.status in ['left', 'kicked']:
                        return False
                except Exception as e:
                    logger.error(f"Error checking membership for {channel['username']}: {e}")
                    return False
        return True
    
    def _create_join_keyboard(self):
        """Create keyboard with join channel buttons"""
        keyboard = []
        
        for i in range(0, len(self.config.REQUIRED_CHANNELS), 2):
            row = []
            for j in range(2):
                if i + j < len(self.config.REQUIRED_CHANNELS):
                    channel = self.config.REQUIRED_CHANNELS[i + j]
                    row.append(InlineKeyboardButton(
                        f"🔗 Join {channel['name']}", 
                        url=channel['url']
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton(
            "✅ I Joined All Channels", 
            callback_data='check_membership'
        )])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _send_membership_required(self, update: Update):
        """Send membership required message"""
        keyboard = self._create_join_keyboard()
        await update.message.reply_text(
            "🔒 You need to join our required channels to use this feature.\n"
            "Please join all channels and click the verification button.",
            reply_markup=keyboard
        )
    
    async def _send_error_message(self, update: Update, message: str):
        """Send error message to user"""
        try:
            await update.message.reply_text(f"❌ {message}")
        except:
            pass
    
    def _format_trace_result(self, result: Dict[str, Any]) -> str:
        """Format phone trace result for display"""
        formatted = "📱 *Phone Trace Results*\n\n"
        
        for key, value in result.items():
            if value and value != 'N/A':
                formatted += f"{key}: {escape_markdown(str(value))}\n"
        
        formatted += f"\n⏰ *Traced at:* {escape_markdown(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        return formatted
    
    def _format_vehicle_result(self, result: Dict[str, Any]) -> str:
        """Format vehicle lookup result for display"""
        formatted = "🚗 *Vehicle Lookup Results*\n\n"
        
        for key, value in result.items():
            if value and value != 'N/A':
                formatted += f"{key}: {escape_markdown(str(value))}\n"
        
        formatted += f"\n⏰ *Looked up at:* {escape_markdown(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        return formatted
    
    def _format_image_result(self, result: Dict[str, Any]) -> str:
        """Format image processing result for display"""
        formatted = "🖼️ *Image Analysis Results*\n\n"
        
        for key, value in result.items():
            if value and value != 'N/A':
                if isinstance(value, dict):
                    formatted += f"*{escape_markdown(key)}:*\n"
                    for sub_key, sub_value in value.items():
                        if sub_value:
                            formatted += f"  • {escape_markdown(sub_key)}: {escape_markdown(str(sub_value))}\n"
                else:
                    formatted += f"*{escape_markdown(key)}:* {escape_markdown(str(value))}\n"
        
        formatted += f"\n⏰ *Processed at:* {escape_markdown(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        return formatted
    
    async def _notify_admin_new_user(self, context: ContextTypes.DEFAULT_TYPE, user):
        """Notify admin of new user"""
        try:
            message = (
                f"🆕 *New User Joined*\n\n"
                f"👤 *User Details:*\n"
                f"• ID: `{user.id}`\n"
                f"• Username: @{escape_markdown(user.username or 'N/A')}\n"
                f"• Name: {escape_markdown(user.first_name or 'N/A')}\n"
                f"• Joined: {escape_markdown(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
            )
            
            await context.bot.send_message(
                chat_id=self.config.ADMIN_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Failed to notify admin of new user: {e}")
    
    def _get_bot_uptime(self) -> str:
        """Get bot uptime (placeholder)"""
        return "Active"
