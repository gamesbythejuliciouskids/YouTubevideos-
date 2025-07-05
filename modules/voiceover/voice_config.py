"""
Voice Configuration - manages voice settings and preferences for different content types.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
from pathlib import Path
from config.config import config
from .voiceover_generator import VoiceSettings

@dataclass
class ContentTypeVoiceConfig:
    """Voice configuration for specific content types."""
    content_type: str
    preferred_provider: str
    voice_settings: VoiceSettings
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content_type": self.content_type,
            "preferred_provider": self.preferred_provider,
            "voice_settings": self.voice_settings.to_dict(),
            "description": self.description
        }

class VoiceConfig:
    """Manages voice configurations for different content types and channels."""
    
    def __init__(self):
        self.configs = self._load_default_configs()
        self.custom_configs = self._load_custom_configs()
    
    def _load_default_configs(self) -> Dict[str, ContentTypeVoiceConfig]:
        """Load default voice configurations."""
        return {
            "educational": ContentTypeVoiceConfig(
                content_type="educational",
                preferred_provider="elevenlabs",
                voice_settings=VoiceSettings(
                    voice_id="Rachel",
                    stability=0.7,
                    similarity_boost=0.6,
                    style=0.0,
                    use_speaker_boost=True,
                    speed=0.95,
                    pitch=1.0,
                    language="en"
                ),
                description="Clear, authoritative voice for educational content"
            ),
            
            "entertainment": ContentTypeVoiceConfig(
                content_type="entertainment",
                preferred_provider="elevenlabs",
                voice_settings=VoiceSettings(
                    voice_id="Josh",
                    stability=0.5,
                    similarity_boost=0.8,
                    style=0.3,
                    use_speaker_boost=True,
                    speed=1.1,
                    pitch=1.05,
                    language="en"
                ),
                description="Energetic, engaging voice for entertainment content"
            ),
            
            "news": ContentTypeVoiceConfig(
                content_type="news",
                preferred_provider="elevenlabs",
                voice_settings=VoiceSettings(
                    voice_id="Nicole",
                    stability=0.8,
                    similarity_boost=0.5,
                    style=0.0,
                    use_speaker_boost=True,
                    speed=1.0,
                    pitch=0.98,
                    language="en"
                ),
                description="Professional, trustworthy voice for news content"
            ),
            
            "lifestyle": ContentTypeVoiceConfig(
                content_type="lifestyle",
                preferred_provider="elevenlabs",
                voice_settings=VoiceSettings(
                    voice_id="Bella",
                    stability=0.6,
                    similarity_boost=0.7,
                    style=0.2,
                    use_speaker_boost=True,
                    speed=1.0,
                    pitch=1.02,
                    language="en"
                ),
                description="Warm, friendly voice for lifestyle content"
            ),
            
            "technology": ContentTypeVoiceConfig(
                content_type="technology",
                preferred_provider="elevenlabs",
                voice_settings=VoiceSettings(
                    voice_id="Adam",
                    stability=0.7,
                    similarity_boost=0.6,
                    style=0.1,
                    use_speaker_boost=True,
                    speed=1.05,
                    pitch=1.0,
                    language="en"
                ),
                description="Clear, confident voice for technology content"
            ),
            
            "health": ContentTypeVoiceConfig(
                content_type="health",
                preferred_provider="elevenlabs",
                voice_settings=VoiceSettings(
                    voice_id="Elli",
                    stability=0.8,
                    similarity_boost=0.6,
                    style=0.0,
                    use_speaker_boost=True,
                    speed=0.9,
                    pitch=0.98,
                    language="en"
                ),
                description="Calm, trustworthy voice for health content"
            ),
            
            "science": ContentTypeVoiceConfig(
                content_type="science",
                preferred_provider="elevenlabs",
                voice_settings=VoiceSettings(
                    voice_id="Sam",
                    stability=0.7,
                    similarity_boost=0.6,
                    style=0.1,
                    use_speaker_boost=True,
                    speed=0.95,
                    pitch=1.0,
                    language="en"
                ),
                description="Intelligent, clear voice for science content"
            ),
            
            "gtts_fallback": ContentTypeVoiceConfig(
                content_type="fallback",
                preferred_provider="gtts",
                voice_settings=VoiceSettings(
                    voice_id="en",
                    stability=0.5,
                    similarity_boost=0.5,
                    style=0.0,
                    use_speaker_boost=False,
                    speed=1.0,
                    pitch=1.0,
                    language="en"
                ),
                description="Google TTS fallback for any content type"
            )
        }
    
    def _load_custom_configs(self) -> Dict[str, ContentTypeVoiceConfig]:
        """Load custom voice configurations from file."""
        config_file = config.CONFIG_DIR / "voice_configs.json"
        
        if not config_file.exists():
            return {}
        
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            custom_configs = {}
            for key, config_data in data.items():
                voice_settings = VoiceSettings(**config_data["voice_settings"])
                custom_configs[key] = ContentTypeVoiceConfig(
                    content_type=config_data["content_type"],
                    preferred_provider=config_data["preferred_provider"],
                    voice_settings=voice_settings,
                    description=config_data["description"]
                )
            
            return custom_configs
            
        except Exception as e:
            print(f"Failed to load custom voice configs: {e}")
            return {}
    
    def get_voice_config(self, content_type: str, channel_name: str = None) -> ContentTypeVoiceConfig:
        """Get voice configuration for content type and channel."""
        # Check for channel-specific config first
        if channel_name:
            channel_key = f"{channel_name}_{content_type}"
            if channel_key in self.custom_configs:
                return self.custom_configs[channel_key]
        
        # Check for custom content type config
        if content_type in self.custom_configs:
            return self.custom_configs[content_type]
        
        # Check for default content type config
        if content_type in self.configs:
            return self.configs[content_type]
        
        # Fallback to educational config
        return self.configs.get("educational", self.configs["gtts_fallback"])
    
    def get_voice_settings(self, content_type: str, channel_name: str = None) -> VoiceSettings:
        """Get voice settings for content type and channel."""
        config = self.get_voice_config(content_type, channel_name)
        return config.voice_settings
    
    def get_preferred_provider(self, content_type: str, channel_name: str = None) -> str:
        """Get preferred provider for content type and channel."""
        config = self.get_voice_config(content_type, channel_name)
        return config.preferred_provider
    
    def save_custom_config(self, key: str, voice_config: ContentTypeVoiceConfig):
        """Save custom voice configuration."""
        self.custom_configs[key] = voice_config
        self._save_custom_configs()
    
    def _save_custom_configs(self):
        """Save custom configurations to file."""
        config_file = config.CONFIG_DIR / "voice_configs.json"
        config_file.parent.mkdir(exist_ok=True)
        
        data = {}
        for key, voice_config in self.custom_configs.items():
            data[key] = voice_config.to_dict()
        
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_channel_voice_config(
        self, 
        channel_name: str, 
        content_type: str, 
        voice_id: str,
        provider: str = "elevenlabs",
        **voice_params
    ) -> ContentTypeVoiceConfig:
        """Create and save a channel-specific voice configuration."""
        
        # Get default settings for the content type as base
        base_config = self.get_voice_config(content_type)
        
        # Create new voice settings with overrides
        voice_settings = VoiceSettings(
            voice_id=voice_id,
            stability=voice_params.get("stability", base_config.voice_settings.stability),
            similarity_boost=voice_params.get("similarity_boost", base_config.voice_settings.similarity_boost),
            style=voice_params.get("style", base_config.voice_settings.style),
            use_speaker_boost=voice_params.get("use_speaker_boost", base_config.voice_settings.use_speaker_boost),
            speed=voice_params.get("speed", base_config.voice_settings.speed),
            pitch=voice_params.get("pitch", base_config.voice_settings.pitch),
            language=voice_params.get("language", base_config.voice_settings.language)
        )
        
        # Create new config
        new_config = ContentTypeVoiceConfig(
            content_type=content_type,
            preferred_provider=provider,
            voice_settings=voice_settings,
            description=f"Custom voice config for {channel_name} {content_type} content"
        )
        
        # Save with channel-specific key
        key = f"{channel_name}_{content_type}"
        self.save_custom_config(key, new_config)
        
        return new_config
    
    def get_all_configs(self) -> Dict[str, ContentTypeVoiceConfig]:
        """Get all available voice configurations."""
        all_configs = {}
        all_configs.update(self.configs)
        all_configs.update(self.custom_configs)
        return all_configs
    
    def list_content_types(self) -> List[str]:
        """List all available content types."""
        return list(self.configs.keys())
    
    def optimize_for_engagement(self, content_type: str) -> VoiceSettings:
        """Get voice settings optimized for maximum engagement."""
        base_settings = self.get_voice_settings(content_type)
        
        # Engagement optimization adjustments
        if content_type in ["entertainment", "lifestyle"]:
            # More energetic for entertainment
            return VoiceSettings(
                voice_id=base_settings.voice_id,
                stability=max(0.3, base_settings.stability - 0.1),
                similarity_boost=min(1.0, base_settings.similarity_boost + 0.1),
                style=min(1.0, base_settings.style + 0.2),
                use_speaker_boost=True,
                speed=min(1.3, base_settings.speed + 0.1),
                pitch=min(1.1, base_settings.pitch + 0.02),
                language=base_settings.language
            )
        elif content_type in ["educational", "science"]:
            # Clear and authoritative for educational
            return VoiceSettings(
                voice_id=base_settings.voice_id,
                stability=min(1.0, base_settings.stability + 0.1),
                similarity_boost=base_settings.similarity_boost,
                style=max(0.0, base_settings.style - 0.1),
                use_speaker_boost=True,
                speed=base_settings.speed,
                pitch=base_settings.pitch,
                language=base_settings.language
            )
        else:
            return base_settings
    
    def get_multi_language_configs(self) -> Dict[str, VoiceSettings]:
        """Get voice configurations for multiple languages."""
        return {
            "en": VoiceSettings(voice_id="Rachel", language="en"),
            "es": VoiceSettings(voice_id="es", language="es", stability=0.6),
            "fr": VoiceSettings(voice_id="fr", language="fr", stability=0.6),
            "de": VoiceSettings(voice_id="de", language="de", stability=0.7),
            "it": VoiceSettings(voice_id="it", language="it", stability=0.6),
            "pt": VoiceSettings(voice_id="pt", language="pt", stability=0.6),
            "ru": VoiceSettings(voice_id="ru", language="ru", stability=0.7),
            "ja": VoiceSettings(voice_id="ja", language="ja", stability=0.8),
            "ko": VoiceSettings(voice_id="ko", language="ko", stability=0.8),
            "zh": VoiceSettings(voice_id="zh", language="zh", stability=0.8)
        }
    
    def validate_voice_settings(self, voice_settings: VoiceSettings) -> bool:
        """Validate voice settings parameters."""
        try:
            # Check ranges
            if not (0.0 <= voice_settings.stability <= 1.0):
                return False
            if not (0.0 <= voice_settings.similarity_boost <= 1.0):
                return False
            if not (0.0 <= voice_settings.style <= 1.0):
                return False
            if not (0.5 <= voice_settings.speed <= 2.0):
                return False
            if not (0.5 <= voice_settings.pitch <= 2.0):
                return False
            
            # Check required fields
            if not voice_settings.voice_id:
                return False
            if not voice_settings.language:
                return False
            
            return True
            
        except Exception:
            return False

# Example usage
def main():
    """Test voice configuration."""
    voice_config = VoiceConfig()
    
    # Test getting configs for different content types
    content_types = ["educational", "entertainment", "news", "lifestyle"]
    
    for content_type in content_types:
        config = voice_config.get_voice_config(content_type)
        print(f"{content_type}: {config.voice_settings.voice_id} ({config.preferred_provider})")
    
    # Test creating custom channel config
    custom_config = voice_config.create_channel_voice_config(
        channel_name="tech_facts",
        content_type="technology", 
        voice_id="Adam",
        speed=1.1,
        stability=0.8
    )
    print(f"Custom config: {custom_config.description}")

if __name__ == "__main__":
    main()