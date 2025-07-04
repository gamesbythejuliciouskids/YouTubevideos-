#!/usr/bin/env python3
"""
Main orchestrator for YouTube Shorts automation system.
This is the central hub that coordinates all modules.
"""

import asyncio
import logging
import argparse
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from config.config import config
from modules.trending_topics import TrendingTopicsFetcher, TopicProcessor
from modules.script_generation import ScriptGenerator

logger = logging.getLogger(__name__)

class YouTubeShortsOrchestrator:
    """Main orchestrator for YouTube Shorts automation."""
    
    def __init__(self):
        self.trending_fetcher = TrendingTopicsFetcher()
        self.topic_processor = TopicProcessor()
        self.script_generator = ScriptGenerator()
        
        # Will be initialized later
        self.voiceover_generator = None
        self.visual_generator = None
        self.video_stitcher = None
        self.metadata_generator = None
        self.youtube_uploader = None
        
    async def run_full_pipeline(self, debug: bool = False) -> Dict[str, Any]:
        """Run the full YouTube Shorts generation pipeline."""
        logger.info("Starting YouTube Shorts generation pipeline")
        
        pipeline_results = {
            "started_at": datetime.now().isoformat(),
            "steps": {},
            "success": False,
            "error": None
        }
        
        try:
            # Step 1: Fetch trending topics
            logger.info("Step 1: Fetching trending topics...")
            trending_topics = await self.trending_fetcher.fetch_all_trending_topics(limit=15)
            pipeline_results["steps"]["trending_topics"] = {
                "count": len(trending_topics),
                "topics": [topic.title for topic in trending_topics[:5]]  # Show first 5
            }
            
            if not trending_topics:
                raise ValueError("No trending topics found")
            
            # Step 2: Process topics
            logger.info("Step 2: Processing topics...")
            processed_topics = self.topic_processor.process_topics(trending_topics)
            pipeline_results["steps"]["processed_topics"] = {
                "count": len(processed_topics),
                "statistics": self.topic_processor.get_topic_statistics(processed_topics)
            }
            
            if not processed_topics:
                raise ValueError("No suitable topics found after processing")
            
            # Step 3: Select best topic
            logger.info("Step 3: Selecting best topic...")
            best_topic = self.topic_processor.get_best_topic_for_video(trending_topics)
            pipeline_results["steps"]["selected_topic"] = {
                "title": best_topic.processed_title,
                "content_type": best_topic.content_type,
                "engagement_score": best_topic.estimated_engagement,
                "difficulty": best_topic.difficulty_level
            }
            
            # Step 4: Generate script
            logger.info("Step 4: Generating script...")
            script = await self.script_generator.generate_script(best_topic)
            pipeline_results["steps"]["script_generation"] = {
                "word_count": script.word_count,
                "estimated_duration": script.estimated_duration,
                "style": script.style
            }
            
            if debug:
                logger.debug(f"Generated script:\n{script.full_script}")
            
            # Save script
            script_filepath = self.script_generator.save_script(script)
            pipeline_results["steps"]["script_generation"]["filepath"] = str(script_filepath)
            
            # Step 5: Generate voiceover (placeholder)
            logger.info("Step 5: Generating voiceover...")
            voiceover_filepath = await self._generate_voiceover_placeholder(script)
            pipeline_results["steps"]["voiceover"] = {
                "filepath": str(voiceover_filepath),
                "duration": script.estimated_duration
            }
            
            # Step 6: Generate visuals (placeholder)
            logger.info("Step 6: Generating visuals...")
            visuals_filepath = await self._generate_visuals_placeholder(best_topic)
            pipeline_results["steps"]["visuals"] = {
                "filepath": str(visuals_filepath),
                "type": "placeholder"
            }
            
            # Step 7: Generate video (placeholder)
            logger.info("Step 7: Generating video...")
            video_filepath = await self._generate_video_placeholder(script, voiceover_filepath, visuals_filepath)
            pipeline_results["steps"]["video"] = {
                "filepath": str(video_filepath),
                "resolution": f"{config.VIDEO_RESOLUTION['width']}x{config.VIDEO_RESOLUTION['height']}",
                "duration": script.estimated_duration
            }
            
            # Step 8: Generate metadata (placeholder)
            logger.info("Step 8: Generating metadata...")
            metadata = await self._generate_metadata_placeholder(script)
            pipeline_results["steps"]["metadata"] = metadata
            
            # Step 9: Upload to YouTube (placeholder)
            if not debug:
                logger.info("Step 9: Uploading to YouTube...")
                upload_result = await self._upload_to_youtube_placeholder(video_filepath, metadata)
                pipeline_results["steps"]["upload"] = upload_result
            else:
                logger.info("Step 9: Skipping upload (debug mode)")
                pipeline_results["steps"]["upload"] = {"status": "skipped_debug"}
            
            pipeline_results["success"] = True
            pipeline_results["completed_at"] = datetime.now().isoformat()
            
            logger.info("Pipeline completed successfully!")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            pipeline_results["error"] = str(e)
            pipeline_results["failed_at"] = datetime.now().isoformat()
            
        return pipeline_results
    
    async def _generate_voiceover_placeholder(self, script) -> Path:
        """Generate voiceover using ElevenLabs/Google TTS."""
        try:
            from modules.voiceover.voiceover_generator import VoiceoverGenerator
            from modules.voiceover.voice_config import VoiceConfig
            
            voiceover_generator = VoiceoverGenerator()
            voice_config = VoiceConfig()
            
            # Get voice settings for content type
            voice_settings = voice_config.get_voice_settings(
                script.topic.content_type
            )
            
            voiceover = await voiceover_generator.generate_voiceover(
                script, 
                voice_settings
            )
            
            if voiceover:
                logger.info(f"Voiceover generated: {voiceover.audio_path}")
                return voiceover.audio_path
            else:
                logger.warning("Voiceover generation failed, creating placeholder")
                raise Exception("Voiceover generation failed")
                
        except Exception as e:
            logger.warning(f"Voiceover generation error: {e}, creating placeholder")
            
            # Fallback to placeholder
            filepath = config.OUTPUT_DIR / "audio" / f"voiceover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                f.write(f"# Voiceover placeholder for script:\n{script.full_script}")
            
            return filepath
    
    async def _generate_visuals_placeholder(self, topic) -> Path:
        """Generate visuals using Pexels/Unsplash."""
        try:
            from modules.visual_generation.visual_generator import VisualGenerator
            
            async with VisualGenerator() as visual_generator:
                visuals = await visual_generator.generate_visuals(
                    topic,
                    preferred_source="pexels",
                    num_images=1
                )
            
            if visuals and visuals[0].image_path.exists():
                logger.info(f"Visual generated: {visuals[0].image_path}")
                return visuals[0].image_path
            else:
                logger.warning("Visual generation failed, creating placeholder")
                raise Exception("Visual generation failed")
                
        except Exception as e:
            logger.warning(f"Visual generation error: {e}, creating placeholder")
            
            # Fallback to placeholder
            filepath = config.OUTPUT_DIR / "images" / f"visuals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                f.write(f"# Visuals placeholder for topic: {topic.processed_title}")
            
            return filepath
    
    async def _generate_video_placeholder(self, script, voiceover_path, visuals_path) -> Path:
        """Generate video using ffmpeg video stitching."""
        try:
            from modules.video_stitching.video_stitcher import VideoStitcher, VideoProject
            from modules.voiceover.voiceover_generator import GeneratedVoiceover, VoiceSettings
            from modules.visual_generation.visual_generator import VisualAsset
            
            video_stitcher = VideoStitcher()
            
            # Create mock objects for the video stitcher
            # (In a real implementation, these would be passed from the actual generators)
            
            # Mock voiceover object
            voice_settings = VoiceSettings(voice_id="default")
            voiceover = GeneratedVoiceover(
                script=script,
                audio_path=voiceover_path,
                voice_settings=voice_settings,
                provider="placeholder",
                duration=script.estimated_duration,
                file_size=1024,
                generated_at=datetime.now()
            )
            
            # Mock visual object
            visual = VisualAsset(
                topic=script.topic,
                image_path=visuals_path,
                source="placeholder",
                source_url=None,
                description="Placeholder visual",
                width=720,
                height=1280,
                file_size=1024,
                generated_at=datetime.now(),
                keywords=script.topic.target_keywords
            )
            
            video_project = await video_stitcher.create_video(
                script,
                voiceover,
                [visual],
                include_subtitles=True
            )
            
            if video_project and video_project.video_path and video_project.video_path.exists():
                logger.info(f"Video generated: {video_project.video_path}")
                return video_project.video_path
            else:
                logger.warning("Video generation failed, creating placeholder")
                raise Exception("Video generation failed")
                
        except Exception as e:
            logger.warning(f"Video generation error: {e}, creating placeholder")
            
            # Fallback to placeholder
            filepath = config.OUTPUT_DIR / "videos" / f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                f.write(f"# Video placeholder\n")
                f.write(f"Script: {script.full_script}\n")
                f.write(f"Voiceover: {voiceover_path}\n")
                f.write(f"Visuals: {visuals_path}\n")
            
            return filepath
    
    async def _generate_metadata_placeholder(self, script) -> Dict[str, Any]:
        """Generate metadata using AI and SEO optimization."""
        try:
            from modules.metadata_generator.metadata_generator import MetadataGenerator
            from modules.metadata_generator.seo_optimizer import SEOOptimizer
            
            metadata_generator = MetadataGenerator()
            seo_optimizer = SEOOptimizer()
            
            # Generate base metadata
            metadata = await metadata_generator.generate_metadata(script)
            
            # Optimize for SEO
            metadata = seo_optimizer.optimize_metadata(
                metadata, 
                script.topic.target_keywords,
                script.topic.content_type
            )
            
            logger.info(f"Metadata generated: {metadata.title}")
            
            return {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "category": metadata.category,
                "privacy": metadata.privacy,
                "language": metadata.language
            }
            
        except Exception as e:
            logger.warning(f"Metadata generation error: {e}, using fallback")
            
            # Fallback metadata
            return {
                "title": script.topic.processed_title,
                "description": f"Learn about {script.topic.original_topic.title}!\n\n{script.main_content}",
                "tags": script.topic.target_keywords[:10],
                "category": "Education",
                "privacy": "public",
                "thumbnail": "auto"
            }
    
    async def _upload_to_youtube_placeholder(self, video_path, metadata) -> Dict[str, Any]:
        """Upload to YouTube using YouTube Data API."""
        try:
            from modules.youtube_upload.youtube_uploader import YouTubeUploader
            from modules.metadata_generator.metadata_generator import VideoMetadata
            from modules.video_stitching.video_stitcher import VideoProject
            
            youtube_uploader = YouTubeUploader()
            
            # Test authentication first
            if not await youtube_uploader.test_authentication():
                logger.warning("YouTube authentication not configured")
                return {
                    "status": "authentication_failed",
                    "error": "YouTube credentials not available",
                    "uploaded_at": datetime.now().isoformat()
                }
            
            # Create VideoMetadata object
            video_metadata = VideoMetadata(
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                category=metadata.get("category", "27"),
                privacy=metadata.get("privacy", "public"),
                language=metadata.get("language", "en")
            )
            
            # Create minimal VideoProject object
            video_project = VideoProject(
                script=None,  # Not needed for upload
                voiceover=None,  # Not needed for upload
                visuals=[],  # Not needed for upload
                video_path=video_path,
                duration=30.0  # Default duration
            )
            
            upload_result = await youtube_uploader.upload_video(
                video_project,
                video_metadata
            )
            
            if upload_result and upload_result.success:
                logger.info(f"Video uploaded successfully: {upload_result.video_url}")
                return {
                    "status": "uploaded",
                    "video_id": upload_result.video_id,
                    "url": upload_result.video_url,
                    "uploaded_at": upload_result.upload_time.isoformat()
                }
            else:
                logger.error(f"Upload failed: {upload_result.error_message if upload_result else 'Unknown error'}")
                return {
                    "status": "upload_failed",
                    "error": upload_result.error_message if upload_result else "Unknown error",
                    "uploaded_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.warning(f"YouTube upload error: {e}, using placeholder")
            
            # Fallback placeholder
            return {
                "status": "upload_error",
                "error": str(e),
                "video_path": str(video_path),
                "uploaded_at": datetime.now().isoformat()
            }
    
    async def test_individual_modules(self):
        """Test individual modules."""
        logger.info("Testing individual modules...")
        
        # Test trending topics
        try:
            logger.info("Testing trending topics fetcher...")
            topics = await self.trending_fetcher.fetch_all_trending_topics(limit=5)
            logger.info(f"✓ Fetched {len(topics)} trending topics")
            
            if topics:
                # Test topic processor
                logger.info("Testing topic processor...")
                processed = self.topic_processor.process_topics(topics)
                logger.info(f"✓ Processed {len(processed)} topics")
                
                if processed:
                    # Test script generator
                    logger.info("Testing script generator...")
                    script = await self.script_generator.generate_script(processed[0])
                    if script:
                        logger.info(f"✓ Generated script ({script.word_count} words, {script.estimated_duration}s)")
                    else:
                        logger.warning("✗ Failed to generate script")
                else:
                    logger.warning("✗ No processed topics available")
            else:
                logger.warning("✗ No trending topics available")
                
        except Exception as e:
            logger.error(f"Module testing failed: {e}")
    
    def save_pipeline_results(self, results: Dict[str, Any], filename: str = None) -> Path:
        """Save pipeline results to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pipeline_results_{timestamp}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Pipeline results saved to {filepath}")
        return filepath

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation System")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--test", action="store_true", help="Test individual modules")
    parser.add_argument("--run-once", action="store_true", help="Run pipeline once")
    parser.add_argument("--validate-config", action="store_true", help="Validate configuration")
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate configuration
    if args.validate_config:
        try:
            config.validate_config()
            logger.info("✓ Configuration is valid")
        except Exception as e:
            logger.error(f"✗ Configuration validation failed: {e}")
            return
    
    # Create orchestrator
    orchestrator = YouTubeShortsOrchestrator()
    
    # Test individual modules
    if args.test:
        await orchestrator.test_individual_modules()
        return
    
    # Run pipeline once
    if args.run_once:
        results = await orchestrator.run_full_pipeline(debug=args.debug)
        orchestrator.save_pipeline_results(results)
        
        if results["success"]:
            logger.info("✓ Pipeline completed successfully")
        else:
            logger.error(f"✗ Pipeline failed: {results.get('error', 'Unknown error')}")
        return
    
    # Default: show help
    parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())