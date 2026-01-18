import json
import aiofiles
import os
import asyncio
import logging
import discord
from typing import Any, Dict

class Database:
    def __init__(self, db_path: str = "utils/database.json"):
        self.db_path = db_path
        self.data: Dict[str, Any] = {}
        self.logger = logging.getLogger("Database")
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initializes the database by loading data into memory."""
        await self.load()

    async def load(self):
        """Loads the JSON database from disk."""
        if not os.path.exists(self.db_path):
            self.logger.warning(f"Database file {self.db_path} not found. Creating a new one.")
            self.data = {}
            await self.save()
            return

        try:
            async with aiofiles.open(self.db_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():
                    self.data = {}
                else:
                    self.data = json.loads(content)
        except Exception as e:
            self.logger.error(f"Error loading database: {e}")
            self.data = {}

    async def save(self):
        """Saves the current state of data to the JSON file."""
        async with self._lock:
            try:
                async with aiofiles.open(self.db_path, mode='w', encoding='utf-8') as f:
                    await f.write(json.dumps(self.data, indent=4, ensure_ascii=False))
            except Exception as e:
                self.logger.error(f"Error saving database: {e}")

    async def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Retrieves configuration for a specific guild."""
        key = str(guild_id)
        
        defaults = {
            "moderation": {
                "enabled": False,
                "bad_words": [],
                "whitelist_links": [],
                "log_channel": None,
                "spam_protection": False,
                "link_protection": False,
                "scan_admins": False
            },
            "social": {
                "youtube": [],
                "tiktok": [],
                "kick": [],
                "instagram": [],
                "notification_channel": None
            },
            "greeting": {
                "enabled": False,
                "channel_id": None,
                "morning_msg": "Günaydın! ☀️",
                "evening_msg": "İyi Akşamlar! 🌙",
                "morning_hour": 10,
                "morning_minute": 0,
                "evening_hour": 22,
                "evening_minute": 0
            },
            "welcome": {
                "enabled": False,
                "channel_id": None,
                "rules_channel_id": None,
                "message": "Hoş geldin {user}! Seninle birlikte {count} kişiyiz. Hedefimiz {target} üye! ✨",
                "leave_enabled": False,
                "leave_message": "Güle güle {user}! Senden sonra {count} kişi kaldık. 😢",
                "member_target": 100
            },
            "auto_role": {
                "enabled": False,
                "role_id": None
            },
            "feature_channel": {
                "enabled": False,
                "channel_id": None
            },
            "users": {}
        }

        if key not in self.data:
            self.data[key] = defaults
            await self.save()
            return self.data[key]
            
        # Ensure deep keys exist for existing records (Migration)
        current = self.data[key]
        modified = False
        
        for section, content in defaults.items():
            if section not in current:
                current[section] = content
                modified = True
            elif isinstance(content, dict):
                for k, v in content.items():
                    if k not in current[section]:
                        current[section][k] = v
                        modified = True
                        
        if modified:
            await self.save()
            
        return self.data[key]

    async def update_guild_config(self, guild_id: int, module: str, key: str, value: Any):
        """Updates a specific configuration setting for a guild."""
        guild_key = str(guild_id)
        await self.get_guild_config(guild_id) # Ensure defaults exist
        
        if module not in self.data[guild_key]:
            self.data[guild_key][module] = {}
            
        self.data[guild_key][module][key] = value
        await self.save()

    async def add_warn(self, guild_id: int, user_id: int, reason: str):
        """Adds a warning to a user and returns total warn count."""
        guild_key = str(guild_id)
        user_key = str(user_id)
        await self.get_guild_config(guild_id)

        if "users" not in self.data[guild_key]:
            self.data[guild_key]["users"] = {}
        
        if user_key not in self.data[guild_key]["users"]:
            self.data[guild_key]["users"][user_key] = {"warns": []}
            
        self.data[guild_key]["users"][user_key]["warns"].append({
            "reason": reason,
            "timestamp": discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })
        await self.save()
        return len(self.data[guild_key]["users"][user_key]["warns"])

    async def clear_warns(self, guild_id: int, user_id: int):
        """Clears all warnings for a user."""
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.data and "users" in self.data[guild_key] and user_key in self.data[guild_key]["users"]:
            self.data[guild_key]["users"][user_key]["warns"] = []
            await self.save()
            return True
        return False

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a value by key."""
        return self.data.get(key, default)

    async def set(self, key: str, value: Any):
        """Sets a value and saves the database."""
        self.data[key] = value
        await self.save()

    async def delete(self, key: str):
        """Deletes a key and saves the database."""
        if key in self.data:
            del self.data[key]
            await self.save()

    async def get_all(self) -> Dict[str, Any]:
        """Returns all data."""
        return self.data

db = Database()
