"""
Database operations for the bot
"""

import sqlite3
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class Database:
    """Simple SQLite database for bot data"""
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        first_seen TIMESTAMP,
                        last_seen TIMESTAMP,
                        total_commands INTEGER DEFAULT 0,
                        phone_traces INTEGER DEFAULT 0,
                        vehicle_lookups INTEGER DEFAULT 0,
                        images_processed INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Activities table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        action TEXT,
                        details TEXT,
                        timestamp TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Bot statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        stat_name TEXT UNIQUE,
                        stat_value TEXT,
                        updated_at TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def add_user(self, user_id: int, username: str, first_name: str) -> bool:
        """Add a new user to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, first_seen, last_seen, total_commands)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (user_id, username, first_name, current_time, current_time))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def update_user_activity(self, user_id: int, action: str, details: str = None) -> bool:
        """Update user activity"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now()
                
                # Update user's last seen and command count
                cursor.execute('''
                    UPDATE users 
                    SET last_seen = ?, total_commands = total_commands + 1
                    WHERE user_id = ?
                ''', (current_time, user_id))
                
                # Add activity record
                cursor.execute('''
                    INSERT INTO activities (user_id, action, details, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, action, details, current_time))
                
                # Update specific counters
                if action.startswith('trace:'):
                    cursor.execute('''
                        UPDATE users SET phone_traces = phone_traces + 1 WHERE user_id = ?
                    ''', (user_id,))
                elif action.startswith('vehicle:'):
                    cursor.execute('''
                        UPDATE users SET vehicle_lookups = vehicle_lookups + 1 WHERE user_id = ?
                    ''', (user_id,))
                elif action == 'image_processing':
                    cursor.execute('''
                        UPDATE users SET images_processed = images_processed + 1 WHERE user_id = ?
                    ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
            return False
    
    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM users WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                columns = [description[0] for description in cursor.description]
                user_data = dict(zip(columns, row))
                
                # Get recent activities
                cursor.execute('''
                    SELECT action, details, timestamp FROM activities 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                ''', (user_id,))
                
                activities = cursor.fetchall()
                user_data['recent_activities'] = [
                    {'action': act[0], 'details': act[1], 'timestamp': act[2]}
                    for act in activities
                ]
                
                return user_data
                
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    def get_total_users(self) -> int:
        """Get total number of users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting total users: {e}")
            return 0
    
    def get_active_users(self, hours: int = 24) -> int:
        """Get number of active users in the last N hours"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE last_seen > datetime('now', '-{} hours')
                '''.format(hours))
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return 0
    
    def get_all_user_ids(self) -> List[int]:
        """Get all user IDs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users WHERE is_active = 1')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all user IDs: {e}")
            return []
    
    def update_bot_stat(self, stat_name: str, stat_value: str) -> bool:
        """Update bot statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO bot_stats (stat_name, stat_value, updated_at)
                    VALUES (?, ?, ?)
                ''', (stat_name, stat_value, datetime.now()))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating bot stat: {e}")
            return False
    
    def get_bot_stat(self, stat_name: str) -> Optional[str]:
        """Get bot statistic"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT stat_value FROM bot_stats WHERE stat_name = ?
                ''', (stat_name,))
                
                row = cursor.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"Error getting bot stat: {e}")
            return None
    
    def cleanup_old_activities(self, days: int = 30):
        """Clean up old activity records"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM activities 
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old activity records")
                
        except Exception as e:
            logger.error(f"Error cleaning up old activities: {e}")
    
    def backup_database(self, backup_path: str = None) -> bool:
        """Create a backup of the database"""
        try:
            if not backup_path:
                backup_path = f"bot_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Database backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
    
    def get_database_size(self) -> str:
        """Get database file size"""
        try:
            size = os.path.getsize(self.db_path)
            return f"{size / 1024:.2f} KB"
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return "Unknown"
