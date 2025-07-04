"""
Video Stitcher - combines audio, visuals, and subtitles using ffmpeg.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
from dataclasses import dataclass
import ffmpeg
import subprocess
import tempfile
import shutil

from config.config import config
from modules.script_generation.script_generator import GeneratedScript
from modules.voiceover.voiceover_generator import GeneratedVoiceover
from modules.visual_generation.visual_generator import VisualAsset

logger = logging.getLogger(__name__)

@dataclass
class VideoProject:
    """Video project data."""
    script: GeneratedScript
    voiceover: GeneratedVoiceover
    visuals: List[VisualAsset]
    video_path: Optional[Path] = None
    subtitle_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None
    duration: float = 0.0
    resolution: tuple = (720, 1280)
    framerate: int = 30
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "script": self.script.to_dict(),
            "voiceover": self.voiceover.to_dict(),
            "visuals": [visual.to_dict() for visual in self.visuals],
            "video_path": str(self.video_path) if self.video_path else None,
            "subtitle_path": str(self.subtitle_path) if self.subtitle_path else None,
            "thumbnail_path": str(self.thumbnail_path) if self.thumbnail_path else None,
            "duration": self.duration,
            "resolution": self.resolution,
            "framerate": self.framerate,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class VideoStitcher:
    """Stitches videos using ffmpeg."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "youtube_shorts_temp"
        self.temp_dir.mkdir(exist_ok=True)
        
    def check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            logger.error("ffmpeg not found. Please install ffmpeg.")
            return False
    
    async def create_video(
        self, 
        script: GeneratedScript, 
        voiceover: GeneratedVoiceover, 
        visuals: List[VisualAsset],
        include_subtitles: bool = True,
        background_music: Optional[Path] = None
    ) -> Optional[VideoProject]:
        """Create complete video from components."""
        
        if not self.check_ffmpeg():
            logger.error("ffmpeg not available")
            return None
        
        try:
            logger.info("Starting video creation process")
            
            # Create video project
            project = VideoProject(
                script=script,
                voiceover=voiceover,
                visuals=visuals,
                duration=voiceover.duration,
                created_at=datetime.now()
            )
            
            # Step 1: Prepare visual track
            video_track = await self._prepare_visual_track(visuals, voiceover.duration)
            if not video_track:
                logger.error("Failed to prepare visual track")
                return None
            
            # Step 2: Prepare audio track
            audio_track = await self._prepare_audio_track(voiceover, background_music)
            if not audio_track:
                logger.error("Failed to prepare audio track")
                return None
            
            # Step 3: Generate subtitles if requested
            if include_subtitles:
                subtitle_path = await self._generate_subtitles(script, voiceover.duration)
                project.subtitle_path = subtitle_path
            
            # Step 4: Combine video and audio
            final_video = await self._combine_video_audio(
                video_track, audio_track, project.subtitle_path
            )
            
            if not final_video:
                logger.error("Failed to combine video and audio")
                return None
            
            project.video_path = final_video
            project.duration = await self._get_video_duration(final_video)
            
            # Step 5: Create thumbnail
            if visuals:
                from modules.visual_generation.image_processor import ImageProcessor
                processor = ImageProcessor()
                thumbnail = processor.create_thumbnail(
                    visuals[0].image_path, 
                    script.topic.processed_title,
                    script.topic.content_type
                )
                project.thumbnail_path = thumbnail
            
            logger.info(f"Video creation completed: {final_video}")
            return project
            
        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            return None
        finally:
            # Cleanup temp files
            await self._cleanup_temp_files()
    
    async def _prepare_visual_track(self, visuals: List[VisualAsset], duration: float) -> Optional[Path]:
        """Prepare visual track from images."""
        try:
            if not visuals:
                # Create blank video
                return await self._create_blank_video(duration)
            
            # If single image, create video from it
            if len(visuals) == 1:
                return await self._image_to_video(visuals[0].image_path, duration)
            
            # If multiple images, create slideshow
            return await self._create_slideshow(visuals, duration)
            
        except Exception as e:
            logger.error(f"Visual track preparation failed: {e}")
            return None
    
    async def _image_to_video(self, image_path: Path, duration: float) -> Path:
        """Convert single image to video."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.temp_dir / f"visual_track_{timestamp}.mp4"
        
        try:
            # Use ffmpeg to create video from image
            (
                ffmpeg
                .input(str(image_path), loop=1, t=duration, framerate=config.VIDEO_RESOLUTION["fps"])
                .output(
                    str(output_path),
                    vcodec='libx264',
                    pix_fmt='yuv420p',
                    s=f"{config.VIDEO_RESOLUTION['width']}x{config.VIDEO_RESOLUTION['height']}",
                    r=config.VIDEO_RESOLUTION["fps"]
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Created video from image: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Image to video conversion failed: {e}")
            return await self._create_blank_video(duration)
    
    async def _create_slideshow(self, visuals: List[VisualAsset], duration: float) -> Path:
        """Create slideshow from multiple images."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.temp_dir / f"slideshow_{timestamp}.mp4"
        
        try:
            # Calculate duration per image
            duration_per_image = duration / len(visuals)
            
            # Create temp video files for each image
            video_segments = []
            for i, visual in enumerate(visuals):
                segment_path = await self._image_to_video(visual.image_path, duration_per_image)
                video_segments.append(segment_path)
            
            # Concatenate video segments
            if len(video_segments) > 1:
                return await self._concatenate_videos(video_segments)
            else:
                return video_segments[0]
                
        except Exception as e:
            logger.error(f"Slideshow creation failed: {e}")
            return await self._create_blank_video(duration)
    
    async def _concatenate_videos(self, video_paths: List[Path]) -> Path:
        """Concatenate multiple video files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.temp_dir / f"concatenated_{timestamp}.mp4"
        concat_file = self.temp_dir / f"concat_list_{timestamp}.txt"
        
        try:
            # Create concat file list
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path.absolute()}'\n")
            
            # Concatenate videos
            (
                ffmpeg
                .input(str(concat_file), format='concat', safe=0)
                .output(
                    str(output_path),
                    vcodec='libx264',
                    pix_fmt='yuv420p'
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Concatenated videos: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Video concatenation failed: {e}")
            return video_paths[0] if video_paths else await self._create_blank_video(30)
    
    async def _create_blank_video(self, duration: float) -> Path:
        """Create blank video as fallback."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.temp_dir / f"blank_video_{timestamp}.mp4"
        
        try:
            # Create solid color video
            (
                ffmpeg
                .input(
                    f'color=c=black:s={config.VIDEO_RESOLUTION["width"]}x{config.VIDEO_RESOLUTION["height"]}:d={duration}',
                    format='lavfi'
                )
                .output(
                    str(output_path),
                    vcodec='libx264',
                    pix_fmt='yuv420p',
                    r=config.VIDEO_RESOLUTION["fps"]
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Created blank video: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Blank video creation failed: {e}")
            raise
    
    async def _prepare_audio_track(
        self, 
        voiceover: GeneratedVoiceover, 
        background_music: Optional[Path] = None
    ) -> Path:
        """Prepare audio track with optional background music."""
        if not background_music:
            return voiceover.audio_path
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.temp_dir / f"audio_mix_{timestamp}.mp3"
        
        try:
            # Mix voiceover with background music
            voiceover_input = ffmpeg.input(str(voiceover.audio_path))
            music_input = ffmpeg.input(str(background_music))
            
            # Lower background music volume and mix
            mixed_audio = ffmpeg.filter(
                [voiceover_input, music_input.audio.filter('volume', 0.3)],
                'amix',
                inputs=2,
                duration='first'
            )
            
            ffmpeg.output(mixed_audio, str(output_path)).overwrite_output().run(quiet=True)
            
            logger.info(f"Mixed audio track: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio mixing failed: {e}")
            return voiceover.audio_path
    
    async def _generate_subtitles(self, script: GeneratedScript, duration: float) -> Optional[Path]:
        """Generate subtitle file."""
        try:
            from .subtitle_generator import SubtitleGenerator
            subtitle_gen = SubtitleGenerator()
            return await subtitle_gen.generate_subtitles(script, duration)
        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}")
            return None
    
    async def _combine_video_audio(
        self, 
        video_path: Path, 
        audio_path: Path, 
        subtitle_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Combine video and audio tracks."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / "videos" / f"youtube_short_{timestamp}.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Prepare inputs
            video_input = ffmpeg.input(str(video_path))
            audio_input = ffmpeg.input(str(audio_path))
            
            # Combine video and audio
            if subtitle_path and subtitle_path.exists():
                # Add subtitles
                output = ffmpeg.output(
                    video_input, audio_input,
                    str(output_path),
                    vcodec='libx264',
                    acodec='aac',
                    pix_fmt='yuv420p',
                    vf=f"subtitles={subtitle_path}",
                    r=config.VIDEO_RESOLUTION["fps"],
                    s=f"{config.VIDEO_RESOLUTION['width']}x{config.VIDEO_RESOLUTION['height']}",
                    movflags='faststart'  # Optimize for web streaming
                )
            else:
                # No subtitles
                output = ffmpeg.output(
                    video_input, audio_input,
                    str(output_path),
                    vcodec='libx264',
                    acodec='aac',
                    pix_fmt='yuv420p',
                    r=config.VIDEO_RESOLUTION["fps"],
                    s=f"{config.VIDEO_RESOLUTION['width']}x{config.VIDEO_RESOLUTION['height']}",
                    movflags='faststart'
                )
            
            output.overwrite_output().run(quiet=True)
            
            logger.info(f"Combined video and audio: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Video/audio combination failed: {e}")
            return None
    
    async def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds."""
        try:
            probe = ffmpeg.probe(str(video_path))
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            logger.error(f"Failed to get video duration: {e}")
            return 0.0
    
    async def _cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            if self.temp_dir.exists():
                # Remove files older than 1 hour
                import time
                current_time = time.time()
                
                for file_path in self.temp_dir.iterdir():
                    if file_path.is_file():
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > 3600:  # 1 hour
                            file_path.unlink()
                            
        except Exception as e:
            logger.warning(f"Temp file cleanup failed: {e}")
    
    def save_project(self, project: VideoProject, filename: str = None) -> Path:
        """Save video project metadata."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"video_project_{timestamp}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(project.to_dict(), f, indent=2)
        
        logger.info(f"Video project saved to: {filepath}")
        return filepath
    
    async def create_preview(self, project: VideoProject, duration: float = 10.0) -> Optional[Path]:
        """Create preview video (first N seconds)."""
        if not project.video_path or not project.video_path.exists():
            logger.error("No video file to create preview from")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preview_path = config.OUTPUT_DIR / "videos" / f"preview_{timestamp}.mp4"
        
        try:
            (
                ffmpeg
                .input(str(project.video_path), t=duration)
                .output(
                    str(preview_path),
                    vcodec='libx264',
                    acodec='aac',
                    pix_fmt='yuv420p'
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Created preview: {preview_path}")
            return preview_path
            
        except Exception as e:
            logger.error(f"Preview creation failed: {e}")
            return None
    
    async def optimize_for_youtube(self, video_path: Path) -> Path:
        """Optimize video for YouTube upload."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        optimized_path = config.OUTPUT_DIR / "videos" / f"optimized_{timestamp}.mp4"
        
        try:
            (
                ffmpeg
                .input(str(video_path))
                .output(
                    str(optimized_path),
                    vcodec='libx264',
                    acodec='aac',
                    pix_fmt='yuv420p',
                    preset='medium',  # Balance between quality and encoding speed
                    crf=23,  # Constant Rate Factor for quality
                    maxrate='8M',  # Max bitrate for YouTube
                    bufsize='16M',  # Buffer size
                    movflags='faststart',  # Optimize for web streaming
                    r=config.VIDEO_RESOLUTION["fps"],
                    s=f"{config.VIDEO_RESOLUTION['width']}x{config.VIDEO_RESOLUTION['height']}"
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Optimized video for YouTube: {optimized_path}")
            return optimized_path
            
        except Exception as e:
            logger.error(f"YouTube optimization failed: {e}")
            return video_path
    
    async def add_intro_outro(
        self, 
        main_video: Path, 
        intro_video: Optional[Path] = None, 
        outro_video: Optional[Path] = None
    ) -> Path:
        """Add intro and outro to main video."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / "videos" / f"with_intro_outro_{timestamp}.mp4"
        
        try:
            video_list = []
            
            if intro_video and intro_video.exists():
                video_list.append(intro_video)
            
            video_list.append(main_video)
            
            if outro_video and outro_video.exists():
                video_list.append(outro_video)
            
            if len(video_list) == 1:
                # No intro/outro, just copy
                shutil.copy2(main_video, output_path)
            else:
                # Concatenate videos
                output_path = await self._concatenate_videos(video_list)
            
            logger.info(f"Added intro/outro: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Intro/outro addition failed: {e}")
            return main_video
    
    async def test_video_creation(self) -> bool:
        """Test video creation with sample data."""
        try:
            logger.info("Testing video creation...")
            
            # Create test blank video
            test_duration = 5.0
            test_video = await self._create_blank_video(test_duration)
            
            if test_video and test_video.exists():
                # Test duration
                duration = await self._get_video_duration(test_video)
                
                if abs(duration - test_duration) < 1.0:  # Allow 1 second tolerance
                    logger.info("✅ Video creation test passed")
                    return True
                else:
                    logger.error(f"❌ Duration mismatch: expected {test_duration}, got {duration}")
            
            logger.error("❌ Video creation test failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Video creation test failed: {e}")
            return False

# Example usage and testing
async def main():
    """Test the video stitcher."""
    stitcher = VideoStitcher()
    
    # Test ffmpeg availability
    if stitcher.check_ffmpeg():
        print("✅ ffmpeg is available")
    else:
        print("❌ ffmpeg is not available")
        return
    
    # Test video creation
    success = await stitcher.test_video_creation()
    print(f"Video creation test: {'✅ PASSED' if success else '❌ FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())