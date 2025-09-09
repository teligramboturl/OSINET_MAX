[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ulgg9/OSINET_MAX)



# Telegram Phone Tracer & Vehicle Lookup Bot

A comprehensive Telegram bot that provides phone number tracing and vehicle registration lookup services with advanced image processing capabilities.

## Features

### 🔍 Phone Tracing
- Comprehensive phone number lookup using multiple sources
- Support for international and local number formats
- Detailed information extraction including carrier, location, and more
- Rate limiting to prevent abuse

### 🚗 Vehicle Lookup
- Vehicle registration number lookup for Indian vehicles
- Comprehensive RTO database with detailed information
- State and district identification
- Vehicle type classification

### 📸 Image Processing
- EXIF data extraction from images
- GPS coordinate extraction and mapping
- OCR text extraction (optional)
- Support for multiple image formats

### 👥 User Management
- User activity tracking and statistics
- Membership verification for required channels
- Admin controls and broadcasting
- Comprehensive logging system

### 🛡️ Security Features
- Rate limiting to prevent spam
- Input validation and sanitization
- Secure environment variable handling
- Error handling and logging

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)
- Admin user ID

### 2. Environment Variables
Create a `.env` file or set the following environment variables:

```bash
# Required
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_admin_user_id

# Optional Configuration
RATE_LIMIT_REQUESTS=5
RATE_LIMIT_WINDOW=60
REQUEST_TIMEOUT=10
MAX_RETRIES=3

# Feature Flags
ENABLE_OCR=true
ENABLE_IMAGE_PROCESSING=true

# Database
DATABASE_FILE=bot_data.db
USERS_FILE=users.json

# Logging
LOG_LEVEL=INFO
LOG_FILE=bot.log

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ulgg9/OSINET_MAX)
