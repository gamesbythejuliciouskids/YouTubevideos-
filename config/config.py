"""
Main configuration file for YouTube Shorts automation system.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
import logging
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.setup_logging()
        
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    
    # YouTube API
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
    YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
    
    # Reddit API
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "YouTube-Shorts-Bot/1.0")
    
    # Twitter/X API
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    
    # Media APIs
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
    UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
    
    # Application Settings
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    UPLOAD_SCHEDULE_TIME = os.getenv("UPLOAD_SCHEDULE_TIME", "08:00")
    TIMEZONE = os.getenv("TIMEZONE", "America/New_York")
    MAX_DAILY_UPLOADS = int(os.getenv("MAX_DAILY_UPLOADS", "1"))
    VIDEO_DURATION_SECONDS = int(os.getenv("VIDEO_DURATION_SECONDS", "60"))
    SCRIPT_MAX_WORDS = int(os.getenv("SCRIPT_MAX_WORDS", "75"))
    
    # File Paths
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
    CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "./config"))
    LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs"))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./youtube_shorts.db")
    
    # Video Settings
    VIDEO_RESOLUTION = {
        "width": 720,
        "height": 1280,
        "fps": 30
    }
    
    # Trending Topics Settings
    TRENDING_TOPICS_SOURCES = [
        "google_trends",
        "reddit",
        # "twitter"  # Optional
    ]
    
    # Script Generation Settings
    SCRIPT_PROMPTS = {
        "hook": "Create an engaging opening hook for a YouTube Short about: {topic}",
        "main": "Write 2-3 interesting facts about: {topic}",
        "cta": "Create a call-to-action ending for a YouTube Short about: {topic}"
    }
    
    @staticmethod
    def setup_logging():
        """Set up logging configuration."""
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO if not Config.DEBUG else logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "youtube_shorts.log"),
                logging.StreamHandler()
            ]
        )
    
    @staticmethod
    def get_channel_config(channel_name: str = "default") -> Dict[str, Any]:
        """Get channel-specific configuration."""
        config_file = Path(f"./config/{channel_name}_channel.json")
        
        if config_file.exists():
            import json
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Default channel config
        return {
            "name": channel_name,
            "niche": "general",
            "language": "en",
            "target_audience": "general",
            "upload_frequency": "daily",
            "preferred_topics": [],
            "content_style": "informative",
            "voice_settings": {
                "voice_id": "default",
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
    
    @staticmethod
    def validate_config():
        """Validate that all required configuration is present."""
        required_keys = [
            "OPENAI_API_KEY",
            "YOUTUBE_API_KEY",
            "YOUTUBE_CLIENT_ID",
            "YOUTUBE_CLIENT_SECRET"
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(Config, key):
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Missing required configuration: {', '.join(missing_keys)}")
        
        return True

# Create global config instance
config = Config()