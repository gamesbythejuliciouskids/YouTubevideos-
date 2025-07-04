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
        """Generate voiceover (placeholder implementation)."""
        # This will be implemented in the voiceover module
        filepath = config.OUTPUT_DIR / "audio" / f"voiceover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Create placeholder file
        with open(filepath, 'w') as f:
            f.write(f"# Voiceover placeholder for script:\n{script.full_script}")
        
        return filepath
    
    async def _generate_visuals_placeholder(self, topic) -> Path:
        """Generate visuals (placeholder implementation)."""
        # This will be implemented in the visual generation module
        filepath = config.OUTPUT_DIR / "images" / f"visuals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Create placeholder file
        with open(filepath, 'w') as f:
            f.write(f"# Visuals placeholder for topic: {topic.processed_title}")
        
        return filepath
    
    async def _generate_video_placeholder(self, script, voiceover_path, visuals_path) -> Path:
        """Generate video (placeholder implementation)."""
        # This will be implemented in the video stitching module
        filepath = config.OUTPUT_DIR / "videos" / f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Create placeholder file
        with open(filepath, 'w') as f:
            f.write(f"# Video placeholder\n")
            f.write(f"Script: {script.full_script}\n")
            f.write(f"Voiceover: {voiceover_path}\n")
            f.write(f"Visuals: {visuals_path}\n")
        
        return filepath
    
    async def _generate_metadata_placeholder(self, script) -> Dict[str, Any]:
        """Generate metadata (placeholder implementation)."""
        # This will be implemented in the metadata generator module
        return {
            "title": script.topic.processed_title,
            "description": f"Learn about {script.topic.original_topic.title}!\n\n{script.main_content}",
            "tags": script.topic.target_keywords[:10],
            "category": "Education",
            "privacy": "public",
            "thumbnail": "auto"
        }
    
    async def _upload_to_youtube_placeholder(self, video_path, metadata) -> Dict[str, Any]:
        """Upload to YouTube (placeholder implementation)."""
        # This will be implemented in the YouTube uploader module
        return {
            "status": "uploaded_placeholder",
            "video_id": "placeholder_video_id",
            "url": "https://youtube.com/watch?v=placeholder",
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