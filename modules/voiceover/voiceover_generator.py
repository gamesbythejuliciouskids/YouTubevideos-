"""
Voiceover Generator - converts scripts to realistic voiceovers using ElevenLabs and Google TTS.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import aiohttp
import json
from dataclasses import dataclass
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
import io
import hashlib

try:
    import elevenlabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

from config.config import config
from modules.script_generation.script_generator import GeneratedScript

logger = logging.getLogger(__name__)

@dataclass
class VoiceSettings:
    """Voice settings configuration."""
    voice_id: str
    stability: float = 0.5
    similarity_boost: float = 0.5
    style: float = 0.0
    use_speaker_boost: bool = True
    speed: float = 1.0
    pitch: float = 1.0
    language: str = "en"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "voice_id": self.voice_id,
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
            "speed": self.speed,
            "pitch": self.pitch,
            "language": self.language
        }

@dataclass
class GeneratedVoiceover:
    """Generated voiceover data."""
    script: GeneratedScript
    audio_path: Path
    voice_settings: VoiceSettings
    provider: str
    duration: float
    file_size: int
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "script": self.script.to_dict(),
            "audio_path": str(self.audio_path),
            "voice_settings": self.voice_settings.to_dict(),
            "provider": self.provider,
            "duration": self.duration,
            "file_size": self.file_size,
            "generated_at": self.generated_at.isoformat()
        }

class VoiceoverGenerator:
    """Generates voiceovers using ElevenLabs and Google TTS."""
    
    def __init__(self):
        self.elevenlabs_client = None
        self.setup_elevenlabs()
        self.voice_cache = {}
        
    def setup_elevenlabs(self):
        """Set up ElevenLabs client."""
        try:
            if ELEVENLABS_AVAILABLE and config.ELEVENLABS_API_KEY:
                elevenlabs.set_api_key(config.ELEVENLABS_API_KEY)
                self.elevenlabs_client = elevenlabs
                logger.info("ElevenLabs client initialized successfully")
            else:
                logger.warning("ElevenLabs not available or API key not configured")
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs client: {e}")
    
    async def generate_voiceover(
        self, 
        script: GeneratedScript, 
        voice_settings: Optional[VoiceSettings] = None,
        preferred_provider: str = "elevenlabs"
    ) -> Optional[GeneratedVoiceover]:
        """Generate voiceover from script."""
        if voice_settings is None:
            voice_settings = self._get_default_voice_settings()
        
        # Try preferred provider first
        if preferred_provider == "elevenlabs":
            voiceover = await self._generate_elevenlabs_voiceover(script, voice_settings)
            if voiceover:
                return voiceover
            
            # Fallback to Google TTS
            logger.info("ElevenLabs failed, falling back to Google TTS")
            return await self._generate_gtts_voiceover(script, voice_settings)
        
        elif preferred_provider == "gtts":
            voiceover = await self._generate_gtts_voiceover(script, voice_settings)
            if voiceover:
                return voiceover
            
            # Fallback to ElevenLabs
            logger.info("Google TTS failed, falling back to ElevenLabs")
            return await self._generate_elevenlabs_voiceover(script, voice_settings)
        
        else:
            logger.error(f"Unknown provider: {preferred_provider}")
            return None
    
    async def _generate_elevenlabs_voiceover(
        self, 
        script: GeneratedScript, 
        voice_settings: VoiceSettings
    ) -> Optional[GeneratedVoiceover]:
        """Generate voiceover using ElevenLabs."""
        try:
            if not self.elevenlabs_client:
                logger.error("ElevenLabs client not available")
                return None
            
            # Check cache first
            cache_key = self._get_cache_key(script.full_script, voice_settings)
            if cache_key in self.voice_cache:
                logger.info("Using cached voiceover")
                return self.voice_cache[cache_key]
            
            logger.info(f"Generating ElevenLabs voiceover with voice: {voice_settings.voice_id}")
            
            # Generate audio
            audio = self.elevenlabs_client.generate(
                text=script.full_script,
                voice=voice_settings.voice_id,
                model="eleven_multilingual_v2",
                voice_settings=elevenlabs.VoiceSettings(
                    stability=voice_settings.stability,
                    similarity_boost=voice_settings.similarity_boost,
                    style=voice_settings.style,
                    use_speaker_boost=voice_settings.use_speaker_boost
                )
            )
            
            # Save audio file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = config.OUTPUT_DIR / "audio" / f"voiceover_elevenlabs_{timestamp}.mp3"
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to bytes and save
            audio_bytes = b"".join(audio)
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            
            # Process and enhance audio
            enhanced_path = await self._enhance_audio(audio_path, voice_settings)
            
            # Get file info
            file_size = enhanced_path.stat().st_size
            duration = await self._get_audio_duration(enhanced_path)
            
            voiceover = GeneratedVoiceover(
                script=script,
                audio_path=enhanced_path,
                voice_settings=voice_settings,
                provider="elevenlabs",
                duration=duration,
                file_size=file_size,
                generated_at=datetime.now()
            )
            
            # Cache the result
            self.voice_cache[cache_key] = voiceover
            
            logger.info(f"ElevenLabs voiceover generated successfully ({duration:.1f}s, {file_size/1024:.1f}KB)")
            return voiceover
            
        except Exception as e:
            logger.error(f"ElevenLabs voiceover generation failed: {e}")
            return None
    
    async def _generate_gtts_voiceover(
        self, 
        script: GeneratedScript, 
        voice_settings: VoiceSettings
    ) -> Optional[GeneratedVoiceover]:
        """Generate voiceover using Google TTS."""
        try:
            if not GTTS_AVAILABLE:
                logger.error("Google TTS not available")
                return None
            
            # Check cache first
            cache_key = self._get_cache_key(script.full_script, voice_settings)
            if cache_key in self.voice_cache:
                logger.info("Using cached voiceover")
                return self.voice_cache[cache_key]
            
            logger.info("Generating Google TTS voiceover")
            
            # Generate TTS
            tts = gTTS(
                text=script.full_script,
                lang=voice_settings.language,
                slow=False if voice_settings.speed >= 1.0 else True
            )
            
            # Save to temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_path = config.OUTPUT_DIR / "audio" / f"temp_gtts_{timestamp}.mp3"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            tts.save(str(temp_path))
            
            # Process and enhance audio
            enhanced_path = await self._enhance_audio(temp_path, voice_settings)
            
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            
            # Get file info
            file_size = enhanced_path.stat().st_size
            duration = await self._get_audio_duration(enhanced_path)
            
            voiceover = GeneratedVoiceover(
                script=script,
                audio_path=enhanced_path,
                voice_settings=voice_settings,
                provider="gtts",
                duration=duration,
                file_size=file_size,
                generated_at=datetime.now()
            )
            
            # Cache the result
            self.voice_cache[cache_key] = voiceover
            
            logger.info(f"Google TTS voiceover generated successfully ({duration:.1f}s, {file_size/1024:.1f}KB)")
            return voiceover
            
        except Exception as e:
            logger.error(f"Google TTS voiceover generation failed: {e}")
            return None
    
    async def _enhance_audio(self, input_path: Path, voice_settings: VoiceSettings) -> Path:
        """Enhance audio quality and apply effects."""
        try:
            # Load audio
            audio = AudioSegment.from_file(str(input_path))
            
            # Apply speed adjustment
            if voice_settings.speed != 1.0:
                # Change speed without changing pitch
                audio = audio.speedup(playback_speed=voice_settings.speed)
            
            # Apply pitch adjustment
            if voice_settings.pitch != 1.0:
                # Change pitch (this is approximate)
                octaves = (voice_settings.pitch - 1.0) * 0.5
                new_sample_rate = int(audio.frame_rate * (2.0 ** octaves))
                audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
                audio = audio.set_frame_rate(audio.frame_rate)
            
            # Normalize audio
            audio = normalize(audio)
            
            # Apply compression for better dynamics
            audio = compress_dynamic_range(audio, threshold=-20.0, ratio=4.0)
            
            # Ensure optimal format for YouTube
            # Convert to mono if stereo (saves space)
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Set sample rate to 44.1kHz (YouTube standard)
            audio = audio.set_frame_rate(44100)
            
            # Export enhanced audio
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            provider = "elevenlabs" if "elevenlabs" in str(input_path) else "gtts"
            enhanced_path = config.OUTPUT_DIR / "audio" / f"voiceover_{provider}_{timestamp}.mp3"
            
            audio.export(
                str(enhanced_path),
                format="mp3",
                bitrate="128k",
                parameters=["-q:a", "0"]  # Highest quality
            )
            
            logger.info(f"Audio enhanced and saved to: {enhanced_path}")
            return enhanced_path
            
        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
            return input_path
    
    async def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds."""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0  # Convert milliseconds to seconds
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0
    
    def _get_cache_key(self, text: str, voice_settings: VoiceSettings) -> str:
        """Generate cache key for voiceover."""
        content = f"{text}_{voice_settings.voice_id}_{voice_settings.stability}_{voice_settings.similarity_boost}_{voice_settings.speed}_{voice_settings.pitch}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_default_voice_settings(self) -> VoiceSettings:
        """Get default voice settings."""
        return VoiceSettings(
            voice_id="Rachel",  # Default ElevenLabs voice
            stability=0.5,
            similarity_boost=0.5,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
            pitch=1.0,
            language="en"
        )
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voices."""
        voices = []
        
        # Get ElevenLabs voices
        if self.elevenlabs_client:
            try:
                elevenlabs_voices = self.elevenlabs_client.voices()
                for voice in elevenlabs_voices:
                    voices.append({
                        "provider": "elevenlabs",
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "category": voice.category,
                        "description": voice.description,
                        "labels": voice.labels
                    })
            except Exception as e:
                logger.error(f"Failed to get ElevenLabs voices: {e}")
        
        # Add Google TTS voices (limited selection)
        if GTTS_AVAILABLE:
            gtts_voices = [
                {"provider": "gtts", "voice_id": "en", "name": "English", "language": "en"},
                {"provider": "gtts", "voice_id": "es", "name": "Spanish", "language": "es"},
                {"provider": "gtts", "voice_id": "fr", "name": "French", "language": "fr"},
                {"provider": "gtts", "voice_id": "de", "name": "German", "language": "de"},
                {"provider": "gtts", "voice_id": "it", "name": "Italian", "language": "it"},
                {"provider": "gtts", "voice_id": "pt", "name": "Portuguese", "language": "pt"},
                {"provider": "gtts", "voice_id": "ru", "name": "Russian", "language": "ru"},
                {"provider": "gtts", "voice_id": "ja", "name": "Japanese", "language": "ja"},
                {"provider": "gtts", "voice_id": "ko", "name": "Korean", "language": "ko"},
                {"provider": "gtts", "voice_id": "zh", "name": "Chinese", "language": "zh"}
            ]
            voices.extend(gtts_voices)
        
        return voices
    
    def save_voiceover_metadata(self, voiceover: GeneratedVoiceover, filename: str = None) -> Path:
        """Save voiceover metadata to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"voiceover_metadata_{timestamp}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(voiceover.to_dict(), f, indent=2)
        
        logger.info(f"Voiceover metadata saved to: {filepath}")
        return filepath
    
    async def generate_multiple_voiceovers(
        self, 
        scripts: List[GeneratedScript], 
        voice_settings: Optional[VoiceSettings] = None
    ) -> List[GeneratedVoiceover]:
        """Generate voiceovers for multiple scripts."""
        voiceovers = []
        
        # Generate voiceovers concurrently
        tasks = []
        for script in scripts:
            task = self.generate_voiceover(script, voice_settings)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, GeneratedVoiceover):
                voiceovers.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error generating voiceover: {result}")
        
        return voiceovers
    
    def clear_cache(self):
        """Clear voiceover cache."""
        self.voice_cache.clear()
        logger.info("Voiceover cache cleared")
    
    async def test_voice_generation(self, test_text: str = "Hello, this is a test of the voice generation system.") -> bool:
        """Test voice generation with sample text."""
        try:
            # Create a dummy script for testing
            from modules.script_generation.script_generator import GeneratedScript
            from modules.trending_topics.topic_processor import ProcessedTopic
            from modules.trending_topics.trending_fetcher import TrendingTopic
            
            dummy_topic = TrendingTopic(
                title="Test Topic",
                description="Test description",
                source="test",
                score=100.0,
                keywords=["test"],
                created_at=datetime.now()
            )
            
            dummy_processed_topic = ProcessedTopic(
                original_topic=dummy_topic,
                processed_title="Test Title",
                video_angle="Test Angle",
                target_keywords=["test"],
                estimated_engagement=100.0,
                content_type="educational",
                difficulty_level="easy"
            )
            
            test_script = GeneratedScript(
                topic=dummy_processed_topic,
                hook="Test hook",
                main_content="Test main content",
                call_to_action="Test CTA",
                full_script=test_text,
                word_count=len(test_text.split()),
                estimated_duration=10,
                style="test",
                generated_at=datetime.now()
            )
            
            # Test voice generation
            voiceover = await self.generate_voiceover(test_script)
            
            if voiceover and voiceover.audio_path.exists():
                logger.info(f"✅ Voice generation test passed: {voiceover.audio_path}")
                return True
            else:
                logger.error("❌ Voice generation test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Voice generation test failed: {e}")
            return False

# Example usage and testing
async def main():
    """Test the voiceover generator."""
    generator = VoiceoverGenerator()
    
    # Test voice generation
    success = await generator.test_voice_generation()
    print(f"Voice generation test: {'✅ PASSED' if success else '❌ FAILED'}")
    
    # List available voices
    voices = await generator.get_available_voices()
    print(f"\nAvailable voices: {len(voices)}")
    for voice in voices[:5]:  # Show first 5
        print(f"  - {voice['provider']}: {voice['name']} ({voice.get('voice_id', 'N/A')})")

if __name__ == "__main__":
    asyncio.run(main())