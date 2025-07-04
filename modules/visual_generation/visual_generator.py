"""
Visual Generator - generates visuals for YouTube Shorts using multiple sources.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
import aiohttp
import json
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import requests
import hashlib
import random

from config.config import config
from modules.trending_topics.topic_processor import ProcessedTopic

logger = logging.getLogger(__name__)

@dataclass
class VisualAsset:
    """Visual asset data."""
    topic: ProcessedTopic
    image_path: Path
    source: str
    source_url: Optional[str]
    description: str
    width: int
    height: int
    file_size: int
    generated_at: datetime
    keywords: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "topic": self.topic.to_dict(),
            "image_path": str(self.image_path),
            "source": self.source,
            "source_url": self.source_url,
            "description": self.description,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
            "generated_at": self.generated_at.isoformat(),
            "keywords": self.keywords
        }

class VisualGenerator:
    """Generates visuals using Pexels, Unsplash, and AI sources."""
    
    def __init__(self):
        self.visual_cache = {}
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def generate_visuals(
        self, 
        topic: ProcessedTopic, 
        preferred_source: str = "pexels",
        num_images: int = 1
    ) -> List[VisualAsset]:
        """Generate visuals for a topic."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Check cache first
        cache_key = self._get_cache_key(topic, preferred_source, num_images)
        if cache_key in self.visual_cache:
            logger.info("Using cached visuals")
            return self.visual_cache[cache_key]
        
        visuals = []
        
        # Try preferred source first
        if preferred_source == "pexels":
            visuals = await self._generate_pexels_visuals(topic, num_images)
        elif preferred_source == "unsplash":
            visuals = await self._generate_unsplash_visuals(topic, num_images)
        elif preferred_source == "ai":
            visuals = await self._generate_ai_visuals(topic, num_images)
        
        # Fallback to other sources if primary fails
        if not visuals:
            logger.info(f"{preferred_source} failed, trying fallback sources")
            
            fallback_sources = ["pexels", "unsplash", "ai"]
            if preferred_source in fallback_sources:
                fallback_sources.remove(preferred_source)
            
            for source in fallback_sources:
                if source == "pexels":
                    visuals = await self._generate_pexels_visuals(topic, num_images)
                elif source == "unsplash":
                    visuals = await self._generate_unsplash_visuals(topic, num_images)
                elif source == "ai":
                    visuals = await self._generate_ai_visuals(topic, num_images)
                
                if visuals:
                    break
        
        # Create fallback visuals if all sources fail
        if not visuals:
            logger.warning("All visual sources failed, creating fallback visuals")
            visuals = await self._create_fallback_visuals(topic, num_images)
        
        # Process and optimize visuals
        processed_visuals = []
        for visual in visuals:
            processed_visual = await self._process_visual(visual)
            if processed_visual:
                processed_visuals.append(processed_visual)
        
        # Cache the results
        self.visual_cache[cache_key] = processed_visuals
        
        return processed_visuals
    
    async def _generate_pexels_visuals(self, topic: ProcessedTopic, num_images: int) -> List[VisualAsset]:
        """Generate visuals using Pexels API."""
        if not config.PEXELS_API_KEY:
            logger.warning("Pexels API key not configured")
            return []
        
        try:
            # Search for images
            search_terms = self._get_search_terms(topic)
            
            headers = {
                "Authorization": config.PEXELS_API_KEY
            }
            
            visuals = []
            
            for search_term in search_terms:
                if len(visuals) >= num_images:
                    break
                
                url = "https://api.pexels.com/v1/search"
                params = {
                    "query": search_term,
                    "per_page": min(20, num_images * 2),
                    "orientation": "portrait",  # For YouTube Shorts 9:16 format
                    "size": "large"
                }
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for photo in data.get("photos", []):
                            if len(visuals) >= num_images:
                                break
                            
                            # Download image
                            image_url = photo["src"]["large2x"]
                            image_path = await self._download_image(image_url, f"pexels_{photo['id']}")
                            
                            if image_path:
                                visual = VisualAsset(
                                    topic=topic,
                                    image_path=image_path,
                                    source="pexels",
                                    source_url=photo["url"],
                                    description=photo.get("alt", search_term),
                                    width=photo["width"],
                                    height=photo["height"],
                                    file_size=image_path.stat().st_size,
                                    generated_at=datetime.now(),
                                    keywords=[search_term]
                                )
                                visuals.append(visual)
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
            
            logger.info(f"Generated {len(visuals)} Pexels visuals")
            return visuals
            
        except Exception as e:
            logger.error(f"Pexels visual generation failed: {e}")
            return []
    
    async def _generate_unsplash_visuals(self, topic: ProcessedTopic, num_images: int) -> List[VisualAsset]:
        """Generate visuals using Unsplash API."""
        if not config.UNSPLASH_ACCESS_KEY:
            logger.warning("Unsplash API key not configured")
            return []
        
        try:
            search_terms = self._get_search_terms(topic)
            
            headers = {
                "Authorization": f"Client-ID {config.UNSPLASH_ACCESS_KEY}"
            }
            
            visuals = []
            
            for search_term in search_terms:
                if len(visuals) >= num_images:
                    break
                
                url = "https://api.unsplash.com/search/photos"
                params = {
                    "query": search_term,
                    "per_page": min(20, num_images * 2),
                    "orientation": "portrait"
                }
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for photo in data.get("results", []):
                            if len(visuals) >= num_images:
                                break
                            
                            # Download image
                            image_url = photo["urls"]["regular"]
                            image_path = await self._download_image(image_url, f"unsplash_{photo['id']}")
                            
                            if image_path:
                                visual = VisualAsset(
                                    topic=topic,
                                    image_path=image_path,
                                    source="unsplash",
                                    source_url=photo["links"]["html"],
                                    description=photo.get("alt_description", search_term),
                                    width=photo["width"],
                                    height=photo["height"],
                                    file_size=image_path.stat().st_size,
                                    generated_at=datetime.now(),
                                    keywords=[search_term]
                                )
                                visuals.append(visual)
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
            
            logger.info(f"Generated {len(visuals)} Unsplash visuals")
            return visuals
            
        except Exception as e:
            logger.error(f"Unsplash visual generation failed: {e}")
            return []
    
    async def _generate_ai_visuals(self, topic: ProcessedTopic, num_images: int) -> List[VisualAsset]:
        """Generate visuals using AI (placeholder for Stable Diffusion/DALL-E)."""
        try:
            # This would integrate with Replicate, Stability AI, or OpenAI DALL-E
            # For now, create placeholder visuals
            logger.info("AI visual generation not yet implemented, creating styled placeholders")
            
            visuals = []
            search_terms = self._get_search_terms(topic)
            
            for i in range(num_images):
                # Create styled placeholder image
                image_path = await self._create_ai_placeholder(topic, search_terms[0] if search_terms else "concept", i)
                
                if image_path:
                    visual = VisualAsset(
                        topic=topic,
                        image_path=image_path,
                        source="ai_placeholder",
                        source_url=None,
                        description=f"AI-generated placeholder for {topic.processed_title}",
                        width=720,
                        height=1280,
                        file_size=image_path.stat().st_size,
                        generated_at=datetime.now(),
                        keywords=search_terms
                    )
                    visuals.append(visual)
            
            return visuals
            
        except Exception as e:
            logger.error(f"AI visual generation failed: {e}")
            return []
    
    async def _create_fallback_visuals(self, topic: ProcessedTopic, num_images: int) -> List[VisualAsset]:
        """Create fallback visuals when all sources fail."""
        visuals = []
        
        for i in range(num_images):
            image_path = await self._create_text_visual(topic, i)
            
            if image_path:
                visual = VisualAsset(
                    topic=topic,
                    image_path=image_path,
                    source="fallback",
                    source_url=None,
                    description=f"Text-based visual for {topic.processed_title}",
                    width=720,
                    height=1280,
                    file_size=image_path.stat().st_size,
                    generated_at=datetime.now(),
                    keywords=topic.target_keywords
                )
                visuals.append(visual)
        
        return visuals
    
    async def _download_image(self, url: str, filename_prefix: str) -> Optional[Path]:
        """Download image from URL."""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{filename_prefix}_{timestamp}.jpg"
                    image_path = config.OUTPUT_DIR / "images" / filename
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(image_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    return image_path
                else:
                    logger.error(f"Failed to download image: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Image download failed: {e}")
            return None
    
    async def _create_ai_placeholder(self, topic: ProcessedTopic, concept: str, index: int) -> Path:
        """Create AI-style placeholder image."""
        # Create a visually appealing placeholder that mimics AI-generated content
        width, height = 720, 1280
        
        # Create gradient background
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Create gradient effect
        for y in range(height):
            # Create a gradient from topic-based colors
            if topic.content_type == "technology":
                color1, color2 = (0, 100, 200), (100, 0, 200)
            elif topic.content_type == "health":
                color1, color2 = (0, 150, 100), (100, 200, 0)
            elif topic.content_type == "entertainment":
                color1, color2 = (200, 0, 100), (200, 100, 0)
            else:
                color1, color2 = (50, 50, 150), (150, 50, 150)
            
            ratio = y / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add geometric shapes for visual interest
        for _ in range(5):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(50, 200)
            
            # Create semi-transparent overlay
            overlay = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Random geometric shape
            shape_type = random.choice(['circle', 'rectangle'])
            if shape_type == 'circle':
                overlay_draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], 
                                   fill=(255, 255, 255, 30))
            else:
                overlay_draw.rectangle([x-size//2, y-size//2, x+size//2, y+size//2], 
                                     fill=(255, 255, 255, 20))
            
            image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        
        # Add text overlay
        try:
            # Try to use a nice font, fallback to default
            font_size = 48
            font = ImageFont.load_default()
            
            # Add main concept text
            text = concept.upper()
            draw = ImageDraw.Draw(image)
            
            # Get text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Center text
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # Add text with shadow effect
            draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 128), font=font)  # Shadow
            draw.text((x, y), text, fill=(255, 255, 255), font=font)  # Main text
            
        except Exception as e:
            logger.warning(f"Font loading failed: {e}")
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_placeholder_{index}_{timestamp}.jpg"
        image_path = config.OUTPUT_DIR / "images" / filename
        image_path.parent.mkdir(parents=True, exist_ok=True)
        
        image.save(image_path, 'JPEG', quality=85)
        return image_path
    
    async def _create_text_visual(self, topic: ProcessedTopic, index: int) -> Path:
        """Create text-based visual as ultimate fallback."""
        width, height = 720, 1280
        
        # Create base image with solid color
        colors = {
            "educational": (70, 130, 180),
            "entertainment": (255, 69, 0),
            "news": (25, 25, 112),
            "lifestyle": (218, 165, 32),
            "technology": (72, 61, 139),
            "health": (34, 139, 34),
            "science": (106, 90, 205)
        }
        
        bg_color = colors.get(topic.content_type, (70, 130, 180))
        image = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        
        # Add title text
        try:
            font = ImageFont.load_default()
            
            # Wrap title text
            title = topic.processed_title
            words = title.split()
            lines = []
            current_line = []
            
            for word in words:
                current_line.append(word)
                line_text = ' '.join(current_line)
                bbox = draw.textbbox((0, 0), line_text, font=font)
                if bbox[2] - bbox[0] > width - 40:  # Leave margin
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw text lines
            total_height = len(lines) * 60
            start_y = (height - total_height) // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = start_y + i * 60
                
                # Text with shadow
                draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font)
                draw.text((x, y), line, fill=(255, 255, 255), font=font)
            
            # Add category badge
            category_text = topic.content_type.upper()
            bbox = draw.textbbox((0, 0), category_text, font=font)
            cat_width = bbox[2] - bbox[0]
            cat_x = (width - cat_width) // 2
            cat_y = start_y - 80
            
            # Badge background
            draw.rectangle([cat_x - 10, cat_y - 10, cat_x + cat_width + 10, cat_y + 40], 
                         fill=(255, 255, 255, 200))
            draw.text((cat_x, cat_y), category_text, fill=bg_color, font=font)
            
        except Exception as e:
            logger.warning(f"Text rendering failed: {e}")
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"text_visual_{index}_{timestamp}.jpg"
        image_path = config.OUTPUT_DIR / "images" / filename
        image_path.parent.mkdir(parents=True, exist_ok=True)
        
        image.save(image_path, 'JPEG', quality=85)
        return image_path
    
    async def _process_visual(self, visual: VisualAsset) -> Optional[VisualAsset]:
        """Process and optimize visual for YouTube Shorts."""
        try:
            # Load image
            image = Image.open(visual.image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to YouTube Shorts optimal resolution (9:16 aspect ratio)
            target_width, target_height = 720, 1280
            
            # Calculate crop/resize parameters
            current_ratio = image.width / image.height
            target_ratio = target_width / target_height
            
            if current_ratio > target_ratio:
                # Image is too wide, crop width
                new_width = int(image.height * target_ratio)
                left = (image.width - new_width) // 2
                image = image.crop((left, 0, left + new_width, image.height))
            elif current_ratio < target_ratio:
                # Image is too tall, crop height
                new_height = int(image.width / target_ratio)
                top = (image.height - new_height) // 2
                image = image.crop((0, top, image.width, top + new_height))
            
            # Resize to target dimensions
            image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Enhance image quality
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.05)
            
            # Save optimized image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"optimized_{visual.source}_{timestamp}.jpg"
            optimized_path = config.OUTPUT_DIR / "images" / filename
            
            image.save(optimized_path, 'JPEG', quality=90, optimize=True)
            
            # Update visual asset
            visual.image_path = optimized_path
            visual.width = target_width
            visual.height = target_height
            visual.file_size = optimized_path.stat().st_size
            
            logger.info(f"Visual processed and optimized: {optimized_path}")
            return visual
            
        except Exception as e:
            logger.error(f"Visual processing failed: {e}")
            return visual
    
    def _get_search_terms(self, topic: ProcessedTopic) -> List[str]:
        """Get search terms for visual generation."""
        terms = []
        
        # Primary keywords
        terms.extend(topic.target_keywords[:3])
        
        # Content type specific terms
        content_terms = {
            "educational": ["learning", "knowledge", "education", "study"],
            "entertainment": ["fun", "exciting", "entertainment", "vibrant"],
            "news": ["modern", "current", "professional", "contemporary"],
            "lifestyle": ["lifestyle", "wellness", "modern living", "happiness"],
            "technology": ["technology", "innovation", "digital", "futuristic"],
            "health": ["health", "wellness", "medical", "fitness"],
            "science": ["science", "research", "laboratory", "discovery"]
        }
        
        if topic.content_type in content_terms:
            terms.extend(content_terms[topic.content_type][:2])
        
        # Remove duplicates and return
        return list(dict.fromkeys(terms))
    
    def _get_cache_key(self, topic: ProcessedTopic, source: str, num_images: int) -> str:
        """Generate cache key for visual."""
        content = f"{topic.processed_title}_{source}_{num_images}_{','.join(topic.target_keywords[:3])}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def save_visual_metadata(self, visual: VisualAsset, filename: str = None) -> Path:
        """Save visual metadata to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"visual_metadata_{timestamp}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(visual.to_dict(), f, indent=2)
        
        logger.info(f"Visual metadata saved to: {filepath}")
        return filepath
    
    async def generate_multiple_visuals(
        self, 
        topics: List[ProcessedTopic], 
        preferred_source: str = "pexels"
    ) -> List[VisualAsset]:
        """Generate visuals for multiple topics."""
        all_visuals = []
        
        # Generate visuals concurrently
        tasks = []
        for topic in topics:
            task = self.generate_visuals(topic, preferred_source, 1)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_visuals.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Error generating visuals: {result}")
        
        return all_visuals
    
    def clear_cache(self):
        """Clear visual cache."""
        self.visual_cache.clear()
        logger.info("Visual cache cleared")
    
    async def test_visual_generation(self) -> bool:
        """Test visual generation with sample topic."""
        try:
            from modules.trending_topics.topic_processor import ProcessedTopic
            from modules.trending_topics.trending_fetcher import TrendingTopic
            
            # Create test topic
            test_topic = TrendingTopic(
                title="Amazing Technology",
                description="Latest technology trends",
                source="test",
                score=100.0,
                keywords=["technology", "innovation"],
                created_at=datetime.now()
            )
            
            processed_topic = ProcessedTopic(
                original_topic=test_topic,
                processed_title="Amazing Technology Breakthrough",
                video_angle="Technology Innovation",
                target_keywords=["technology", "innovation", "future"],
                estimated_engagement=100.0,
                content_type="technology",
                difficulty_level="easy"
            )
            
            # Test visual generation
            visuals = await self.generate_visuals(processed_topic, "fallback", 1)
            
            if visuals and visuals[0].image_path.exists():
                logger.info(f"✅ Visual generation test passed: {visuals[0].image_path}")
                return True
            else:
                logger.error("❌ Visual generation test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Visual generation test failed: {e}")
            return False

# Example usage and testing
async def main():
    """Test the visual generator."""
    async with VisualGenerator() as generator:
        # Test visual generation
        success = await generator.test_visual_generation()
        print(f"Visual generation test: {'✅ PASSED' if success else '❌ FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())