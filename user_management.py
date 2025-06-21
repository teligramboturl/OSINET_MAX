"""
User management and activity tracking
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from database import Database

logger = logging.getLogger(__name__)

class UserManager:
    """Manage user data and activity tracking"""
    
    def __init__(self, database: Database):
        self.database = database
        self.users_file = 'users.json'
        self.users_cache = {}
        self.load_users()
    
    def load_users(self):
        """Load users from JSON file"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users_cache = json.load(f)
                logger.info(f"Loaded {len(self.users_cache)} users from file")
            else:
                self.users_cache = {}
                logger.info("No existing users file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            self.users_cache = {}
    
    def save_users(self):
        """Save users to JSON file"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users_cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.users_cache)} users to file")
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def log_user_activity(self, user_id: int, username: str, first_name: str, action: str) -> bool:
        """Log user activity and return True if new user"""
        try:
            user_str = str(user_id)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            is_new_user = user_str not in self.users_cache
            
            if is_new_user:
                # New user
                self.users_cache[user_str] = {
                    'user_id': user_id,
                    'username': username,
                    'first_name': first_name,
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'total_commands': 1,
                    'activities': [{'action': action, 'timestamp': current_time}],
                    'phone_traces': 0,
                    'vehicle_lookups': 0,
                    'images_processed': 0
                }
                logger.info(f"🆕 NEW USER: {user_id} (@{username}) - {first_name}")
            else:
                # Existing user
                user_data = self.users_cache[user_str]
                user_data['last_seen'] = current_time
                user_data['total_commands'] += 1
                user_data['username'] = username  # Update in case it changed
                user_data['first_name'] = first_name  # Update in case it changed
                
                # Add activity
                if 'activities' not in user_data:
                    user_data['activities'] = []
                
                user_data['activities'].append({
                    'action': action,
                    'timestamp': current_time
                })
                
                # Keep only last 50 activities
                if len(user_data['activities']) > 50:
                    user_data['activities'] = user_data['activities'][-50:]
                
                # Update specific counters
                if action.startswith('trace:'):
                    user_data['phone_traces'] = user_data.get('phone_traces', 0) + 1
                elif action.startswith('vehicle:'):
                    user_data['vehicle_lookups'] = user_data.get('vehicle_lookups', 0) + 1
                elif action == 'image_processing':
                    user_data['images_processed'] = user_data.get('images_processed', 0) + 1
            
            # Save to file
            self.save_users()
            
            logger.info(f"📊 USER ACTIVITY: {user_id} (@{username}) - {action}")
            return is_new_user
            
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
            return False
    
    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user statistics"""
        try:
            user_str = str(user_id)
            if user_str in self.users_cache:
                user_data = self.users_cache[user_str].copy()
                
                # Add calculated stats
                user_data['days_active'] = self._calculate_days_active(user_data)
                user_data['recent_activities'] = self._get_recent_activities(user_data)
                
                return user_data
            return None
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    def get_total_users(self) -> int:
        """Get total number of users"""
        return len(self.users_cache)
    
    def get_active_users(self, hours: int = 24) -> int:
        """Get number of active users in last N hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            active_count = 0
            
            for user_data in self.users_cache.values():
                try:
                    last_seen = datetime.strptime(user_data['last_seen'], "%Y-%m-%d %H:%M:%S")
                    if last_seen > cutoff_time:
                        active_count += 1
                except Exception as e:
                    logger.warning(f"Error parsing last_seen for user: {e}")
                    continue
            
            return active_count
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return 0
    
    def get_all_users(self) -> List[int]:
        """Get list of all user IDs"""
        try:
            return [int(user_id) for user_id in self.users_cache.keys()]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def get_user_activity_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get activity summary for the last N days"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            summary = {
                'total_users': len(self.users_cache),
                'active_users': 0,
                'new_users': 0,
                'total_commands': 0,
                'phone_traces': 0,
                'vehicle_lookups': 0,
                'images_processed': 0,
                'top_activities': {}
            }
            
            for user_data in self.users_cache.values():
                try:
                    # Check if user was active in the period
                    last_seen = datetime.strptime(user_data['last_seen'], "%Y-%m-%d %H:%M:%S")
                    if last_seen > cutoff_time:
                        summary['active_users'] += 1
                    
                    # Check if user is new in the period
                    first_seen = datetime.strptime(user_data['first_seen'], "%Y-%m-%d %H:%M:%S")
                    if first_seen > cutoff_time:
                        summary['new_users'] += 1
                    
                    # Count activities in the period
                    if 'activities' in user_data:
                        for activity in user_data['activities']:
                            try:
                                activity_time = datetime.strptime(activity['timestamp'], "%Y-%m-%d %H:%M:%S")
                                if activity_time > cutoff_time:
                                    summary['total_commands'] += 1
                                    
                                    # Count specific activity types
                                    action = activity['action']
                                    if action.startswith('trace:'):
                                        summary['phone_traces'] += 1
                                    elif action.startswith('vehicle:'):
                                        summary['vehicle_lookups'] += 1
                                    elif action == 'image_processing':
                                        summary['images_processed'] += 1
                                    
                                    # Track activity frequency
                                    if action in summary['top_activities']:
                                        summary['top_activities'][action] += 1
                                    else:
                                        summary['top_activities'][action] = 1
                            except Exception as e:
                                logger.warning(f"Error parsing activity timestamp: {e}")
                                continue
                    
                except Exception as e:
                    logger.warning(f"Error processing user data: {e}")
                    continue
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting activity summary: {e}")
            return {}
    
    def _calculate_days_active(self, user_data: Dict[str, Any]) -> int:
        """Calculate number of days user has been active"""
        try:
            first_seen = datetime.strptime(user_data['first_seen'], "%Y-%m-%d %H:%M:%S")
            last_seen = datetime.strptime(user_data['last_seen'], "%Y-%m-%d %H:%M:%S")
            return (last_seen - first_seen).days + 1
        except Exception as e:
            logger.warning(f"Error calculating days active: {e}")
            return 0
    
    def _get_recent_activities(self, user_data: Dict[str, Any], limit: int = 10) -> List[Dict[str, str]]:
        """Get recent activities for user"""
        try:
            if 'activities' in user_data:
                return user_data['activities'][-limit:]
            return []
        except Exception as e:
            logger.warning(f"Error getting recent activities: {e}")
            return []
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old user data"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            users_to_remove = []
            
            for user_id, user_data in self.users_cache.items():
                try:
                    last_seen = datetime.strptime(user_data['last_seen'], "%Y-%m-%d %H:%M:%S")
                    if last_seen < cutoff_time:
                        users_to_remove.append(user_id)
                except Exception as e:
                    logger.warning(f"Error parsing date for user {user_id}: {e}")
                    continue
            
            # Remove inactive users
            for user_id in users_to_remove:
                del self.users_cache[user_id]
                logger.info(f"Removed inactive user: {user_id}")
            
            if users_to_remove:
                self.save_users()
                logger.info(f"Cleaned up {len(users_to_remove)} inactive users")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def export_user_data(self, file_path: str = None) -> bool:
        """Export user data to file"""
        try:
            if not file_path:
                file_path = f"user_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                'exported_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_users': len(self.users_cache),
                'users': self.users_cache
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported user data to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            return False
