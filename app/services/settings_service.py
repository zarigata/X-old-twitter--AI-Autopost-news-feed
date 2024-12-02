import json
import os
from pathlib import Path
import logging
import httpx

logger = logging.getLogger(__name__)

class SettingsService:
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent / "config"
        self.settings_file = self.config_dir / "settings.json"
        self.settings = self.load_settings()

    def load_settings(self):
        """Load settings from JSON file."""
        try:
            if not self.config_dir.exists():
                self.config_dir.mkdir(parents=True)
            
            if not self.settings_file.exists():
                # Create default settings
                default_settings = {
                    "ollama_host": "http://host.docker.internal:11434",
                    "model_name": "llama3.2",
                    "available_models": ["llama3.2", "mistral", "llama2"],
                    "news_refresh_interval": 30,
                    "max_news_items": 5
                }
                self.save_settings(default_settings)
                return default_settings

            with open(self.settings_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return {}

    def save_settings(self, settings):
        """Save settings to JSON file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            self.settings = settings
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

    def get_setting(self, key, default=None):
        """Get a specific setting value."""
        return self.settings.get(key, default)

    def update_setting(self, key, value):
        """Update a specific setting."""
        self.settings[key] = value
        return self.save_settings(self.settings)

    def get_all_settings(self):
        """Get all settings."""
        return self.settings

    def get_settings(self) -> dict:
        return self.settings

    async def fetch_available_models(self) -> list:
        """Fetch available models from Ollama server."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.settings['ollama_host']}/api/tags")
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    return [model['name'] for model in models]
                return []
        except Exception as e:
            print(f"Error fetching models: {str(e)}")
            return []

    def update_settings(self, new_settings: dict) -> None:
        self.settings = new_settings
        self.save_settings(self.settings)
