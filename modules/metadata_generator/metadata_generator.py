"""
Metadata Generator - creates SEO-optimized titles, descriptions, and tags for YouTube videos.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
from dataclasses import dataclass
import random
import re

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from config.config import config
from modules.script_generation.script_generator import GeneratedScript
from modules.trending_topics.topic_processor import ProcessedTopic

logger = logging.getLogger(__name__)

@dataclass
class VideoMetadata:
    """Video metadata for YouTube upload."""
    title: str
    description: str
    tags: List[str]
    category: str
    privacy: str = "public"
    thumbnail_path: Optional[Path] = None
    language: str = "en"
    default_audio_language: str = "en"
    publish_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "privacy": self.privacy,
            "thumbnail_path": str(self.thumbnail_path) if self.thumbnail_path else None,
            "language": self.language,
            "default_audio_language": self.default_audio_language,
            "publish_at": self.publish_at.isoformat() if self.publish_at else None
        }

class MetadataGenerator:
    """Generates SEO-optimized metadata for YouTube videos."""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.setup_ai_clients()
        
        # YouTube categories
        self.categories = {
            "educational": "27",  # Education
            "entertainment": "24",  # Entertainment
            "news": "25",  # News & Politics
            "lifestyle": "26",  # Howto & Style
            "technology": "28",  # Science & Technology
            "health": "26",  # Howto & Style
            "science": "28"  # Science & Technology
        }
        
        # SEO keywords by content type
        self.seo_keywords = {
            "educational": ["learn", "facts", "explained", "education", "knowledge", "tutorial"],
            "entertainment": ["viral", "funny", "amazing", "incredible", "must watch", "trending"],
            "news": ["breaking", "news", "update", "latest", "today", "current"],
            "lifestyle": ["tips", "life", "lifestyle", "wellness", "health", "fitness"],
            "technology": ["tech", "technology", "innovation", "future", "digital", "ai"],
            "health": ["health", "wellness", "fitness", "medical", "healthy", "tips"],
            "science": ["science", "research", "discovery", "experiment", "study", "facts"]
        }
        
    def setup_ai_clients(self):
        """Set up AI clients for metadata generation."""
        try:
            if OPENAI_AVAILABLE and config.OPENAI_API_KEY:
                openai.api_key = config.OPENAI_API_KEY
                self.openai_client = openai
                logger.info("OpenAI client initialized for metadata generation")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            
        try:
            if ANTHROPIC_AVAILABLE and config.ANTHROPIC_API_KEY:
                self.anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
                logger.info("Anthropic client initialized for metadata generation")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
    
    async def generate_metadata(
        self, 
        script: GeneratedScript, 
        include_thumbnail: bool = True
    ) -> VideoMetadata:
        """Generate complete metadata for video."""
        try:
            logger.info(f"Generating metadata for: {script.topic.processed_title}")
            
            # Generate title
            title = await self._generate_title(script)
            
            # Generate description
            description = await self._generate_description(script)
            
            # Generate tags
            tags = await self._generate_tags(script)
            
            # Determine category
            category = self._get_category(script.topic.content_type)
            
            # Create metadata object
            metadata = VideoMetadata(
                title=title,
                description=description,
                tags=tags,
                category=category,
                privacy="public",
                language="en",
                default_audio_language="en"
            )
            
            logger.info(f"Generated metadata successfully for: {title}")
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata generation failed: {e}")
            return self._create_fallback_metadata(script)
    
    async def _generate_title(self, script: GeneratedScript) -> str:
        """Generate SEO-optimized title."""
        try:
            # Try AI generation first
            if self.openai_client:
                title = await self._generate_title_openai(script)
                if title and self._validate_title(title):
                    return title
            
            if self.anthropic_client:
                title = await self._generate_title_anthropic(script)
                if title and self._validate_title(title):
                    return title
            
            # Fallback to template-based generation
            return self._generate_title_template(script)
            
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return self._generate_title_template(script)
    
    async def _generate_title_openai(self, script: GeneratedScript) -> Optional[str]:
        """Generate title using OpenAI."""
        try:
            prompt = f"""
            Create an SEO-optimized YouTube Shorts title for this content:
            
            Topic: {script.topic.processed_title}
            Content Type: {script.topic.content_type}
            Keywords: {', '.join(script.topic.target_keywords[:5])}
            
            Requirements:
            - Maximum 60 characters
            - Include 1-2 main keywords
            - Make it clickable and engaging
            - Use title case
            - Don't use clickbait or misleading language
            
            Examples of good titles:
            - "The Science Behind Dreams Explained"
            - "5 Tech Facts That Will Blow Your Mind"
            - "This Health Trick Changed Everything"
            
            Generate only the title, no explanations.
            """
            
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a YouTube SEO expert. Create optimized titles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            title = response.choices[0].message.content.strip()
            return title.strip('"')  # Remove quotes if present
            
        except Exception as e:
            logger.error(f"OpenAI title generation failed: {e}")
            return None
    
    async def _generate_title_anthropic(self, script: GeneratedScript) -> Optional[str]:
        """Generate title using Anthropic."""
        try:
            prompt = f"""
            Create an SEO-optimized YouTube Shorts title for this content:
            
            Topic: {script.topic.processed_title}
            Content Type: {script.topic.content_type}
            Keywords: {', '.join(script.topic.target_keywords[:5])}
            
            Requirements:
            - Maximum 60 characters
            - Include 1-2 main keywords
            - Make it clickable and engaging
            - Use title case
            - Don't use clickbait or misleading language
            
            Generate only the title, no explanations.
            """
            
            message = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=100,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            title = message.content[0].text.strip()
            return title.strip('"')  # Remove quotes if present
            
        except Exception as e:
            logger.error(f"Anthropic title generation failed: {e}")
            return None
    
    def _generate_title_template(self, script: GeneratedScript) -> str:
        """Generate title using templates."""
        topic = script.topic
        
        # Title templates by content type
        templates = {
            "educational": [
                f"The Truth About {topic.original_topic.title}",
                f"5 Facts About {topic.original_topic.title}",
                f"How {topic.original_topic.title} Works",
                f"Everything About {topic.original_topic.title}",
                f"The Science Behind {topic.original_topic.title}"
            ],
            "entertainment": [
                f"This {topic.original_topic.title} Will Shock You",
                f"Amazing {topic.original_topic.title} Facts",
                f"You Won't Believe This {topic.original_topic.title}",
                f"Incredible {topic.original_topic.title} Story",
                f"Mind-Blowing {topic.original_topic.title}"
            ],
            "news": [
                f"Breaking: {topic.original_topic.title}",
                f"Latest Update on {topic.original_topic.title}",
                f"What's Happening with {topic.original_topic.title}",
                f"The Real Story: {topic.original_topic.title}",
                f"Today's News: {topic.original_topic.title}"
            ],
            "lifestyle": [
                f"Life-Changing {topic.original_topic.title} Tips",
                f"Transform Your Life with {topic.original_topic.title}",
                f"The Secret to {topic.original_topic.title}",
                f"Master {topic.original_topic.title} Today",
                f"Ultimate {topic.original_topic.title} Guide"
            ]
        }
        
        content_templates = templates.get(topic.content_type, templates["educational"])
        title = random.choice(content_templates)
        
        # Ensure title is under 60 characters
        if len(title) > 60:
            # Shorten the original topic title
            max_topic_length = 60 - len(title) + len(topic.original_topic.title)
            shortened_topic = topic.original_topic.title[:max_topic_length-3] + "..."
            title = title.replace(topic.original_topic.title, shortened_topic)
        
        return title
    
    async def _generate_description(self, script: GeneratedScript) -> str:
        """Generate SEO-optimized description."""
        try:
            # Try AI generation first
            if self.openai_client:
                description = await self._generate_description_openai(script)
                if description:
                    return description
            
            if self.anthropic_client:
                description = await self._generate_description_anthropic(script)
                if description:
                    return description
            
            # Fallback to template
            return self._generate_description_template(script)
            
        except Exception as e:
            logger.error(f"Description generation failed: {e}")
            return self._generate_description_template(script)
    
    async def _generate_description_openai(self, script: GeneratedScript) -> Optional[str]:
        """Generate description using OpenAI."""
        try:
            prompt = f"""
            Create a YouTube video description for this content:
            
            Title: {script.topic.processed_title}
            Content Type: {script.topic.content_type}
            Script: {script.main_content}
            Keywords: {', '.join(script.topic.target_keywords)}
            
            Requirements:
            - Start with 2-3 engaging sentences about the video
            - Include main keywords naturally
            - Add a call-to-action (like, subscribe, comment)
            - Include relevant hashtags at the end
            - Keep it under 300 words
            - Make it SEO-friendly
            
            Generate the description:
            """
            
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a YouTube SEO expert. Create engaging descriptions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI description generation failed: {e}")
            return None
    
    async def _generate_description_anthropic(self, script: GeneratedScript) -> Optional[str]:
        """Generate description using Anthropic."""
        try:
            prompt = f"""
            Create a YouTube video description for this content:
            
            Title: {script.topic.processed_title}
            Content Type: {script.topic.content_type}
            Script: {script.main_content}
            Keywords: {', '.join(script.topic.target_keywords)}
            
            Requirements:
            - Start with 2-3 engaging sentences about the video
            - Include main keywords naturally
            - Add a call-to-action (like, subscribe, comment)
            - Include relevant hashtags at the end
            - Keep it under 300 words
            - Make it SEO-friendly
            
            Generate the description:
            """
            
            message = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=400,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Anthropic description generation failed: {e}")
            return None
    
    def _generate_description_template(self, script: GeneratedScript) -> str:
        """Generate description using template."""
        topic = script.topic
        
        # Base description
        description = f"🎯 {script.main_content}\n\n"
        
        # Add engagement hook
        hooks = [
            "Did you know about this?",
            "This will change how you think!",
            "Amazing facts you need to know!",
            "Incredible information ahead!",
            "You won't believe this!"
        ]
        description += f"{random.choice(hooks)}\n\n"
        
        # Add call to action
        ctas = [
            "🔔 Subscribe for more amazing content!",
            "👍 Like if this was helpful!",
            "💬 Comment your thoughts below!",
            "📤 Share with someone who needs to see this!",
            "🔥 Follow for daily interesting facts!"
        ]
        description += f"{random.choice(ctas)}\n\n"
        
        # Add hashtags
        hashtags = self._generate_hashtags(topic)
        description += " ".join(hashtags)
        
        return description
    
    async def _generate_tags(self, script: GeneratedScript) -> List[str]:
        """Generate SEO tags."""
        try:
            tags = []
            topic = script.topic
            
            # Add main topic keywords
            tags.extend(topic.target_keywords[:5])
            
            # Add content type keywords
            content_keywords = self.seo_keywords.get(topic.content_type, [])
            tags.extend(content_keywords[:3])
            
            # Add general YouTube Shorts tags
            shorts_tags = ["shorts", "viral", "trending", "facts", "amazing"]
            tags.extend(shorts_tags[:3])
            
            # Add specific tags based on content
            if "technology" in topic.target_keywords:
                tags.extend(["tech", "innovation", "future"])
            elif "health" in topic.target_keywords:
                tags.extend(["wellness", "fitness", "healthy"])
            elif "science" in topic.target_keywords:
                tags.extend(["research", "discovery", "experiment"])
            
            # Remove duplicates and clean
            unique_tags = []
            for tag in tags:
                clean_tag = tag.lower().strip()
                if clean_tag and clean_tag not in unique_tags and len(clean_tag) > 2:
                    unique_tags.append(clean_tag)
            
            # Limit to 15 tags (YouTube recommendation)
            return unique_tags[:15]
            
        except Exception as e:
            logger.error(f"Tag generation failed: {e}")
            return script.topic.target_keywords[:10]
    
    def _generate_hashtags(self, topic: ProcessedTopic) -> List[str]:
        """Generate hashtags for description."""
        hashtags = []
        
        # Add main keywords as hashtags
        for keyword in topic.target_keywords[:3]:
            hashtag = f"#{keyword.replace(' ', '').lower()}"
            hashtags.append(hashtag)
        
        # Add content type hashtag
        hashtags.append(f"#{topic.content_type}")
        
        # Add common YouTube Shorts hashtags
        common_hashtags = ["#shorts", "#viral", "#trending", "#facts"]
        hashtags.extend(common_hashtags[:3])
        
        return hashtags
    
    def _get_category(self, content_type: str) -> str:
        """Get YouTube category ID for content type."""
        return self.categories.get(content_type, "27")  # Default to Education
    
    def _validate_title(self, title: str) -> bool:
        """Validate title meets YouTube requirements."""
        if not title or len(title) > 100:  # YouTube max is 100 chars
            return False
        
        # Check for forbidden characters
        forbidden_chars = ['<', '>', '"']
        if any(char in title for char in forbidden_chars):
            return False
        
        return True
    
    def _create_fallback_metadata(self, script: GeneratedScript) -> VideoMetadata:
        """Create fallback metadata when AI generation fails."""
        topic = script.topic
        
        title = f"Amazing Facts About {topic.original_topic.title}"
        if len(title) > 60:
            title = f"Facts About {topic.original_topic.title}"
        
        description = f"""
        Learn amazing facts about {topic.original_topic.title}!
        
        {script.main_content}
        
        🔔 Subscribe for more interesting content!
        👍 Like if you found this helpful!
        💬 Share your thoughts in the comments!
        
        #shorts #facts #{topic.content_type} #amazing #trending
        """
        
        tags = topic.target_keywords[:10] + ["shorts", "facts", "amazing"]
        
        return VideoMetadata(
            title=title,
            description=description.strip(),
            tags=tags,
            category=self._get_category(topic.content_type)
        )
    
    def save_metadata(self, metadata: VideoMetadata, filename: str = None) -> Path:
        """Save metadata to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metadata_{timestamp}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        logger.info(f"Metadata saved to: {filepath}")
        return filepath
    
    async def optimize_for_trending(self, metadata: VideoMetadata, trending_keywords: List[str]) -> VideoMetadata:
        """Optimize metadata for trending keywords."""
        try:
            # Add trending keywords to tags
            for keyword in trending_keywords[:5]:
                if keyword not in metadata.tags:
                    metadata.tags.append(keyword.lower())
            
            # Limit tags to 15
            metadata.tags = metadata.tags[:15]
            
            # Add trending hashtags to description
            trending_hashtags = [f"#{kw.replace(' ', '').lower()}" for kw in trending_keywords[:3]]
            
            if not any(hashtag in metadata.description for hashtag in trending_hashtags):
                metadata.description += f"\n\n{' '.join(trending_hashtags)}"
            
            logger.info("Metadata optimized for trending keywords")
            return metadata
            
        except Exception as e:
            logger.error(f"Trending optimization failed: {e}")
            return metadata
    
    async def create_multiple_variants(self, script: GeneratedScript, count: int = 3) -> List[VideoMetadata]:
        """Create multiple metadata variants for A/B testing."""
        variants = []
        
        for i in range(count):
            # Generate slightly different metadata each time
            metadata = await self.generate_metadata(script)
            
            # Add variant suffix for tracking
            metadata.title += f" #{i+1}" if count > 1 else ""
            
            variants.append(metadata)
        
        return variants
    
    def analyze_seo_score(self, metadata: VideoMetadata, target_keywords: List[str]) -> Dict[str, Any]:
        """Analyze SEO score of metadata."""
        score_data = {
            "total_score": 0,
            "title_score": 0,
            "description_score": 0,
            "tags_score": 0,
            "recommendations": []
        }
        
        # Title analysis
        title_keywords = sum(1 for kw in target_keywords if kw.lower() in metadata.title.lower())
        score_data["title_score"] = min(100, title_keywords * 30)
        
        if len(metadata.title) > 60:
            score_data["recommendations"].append("Title too long (>60 chars)")
        
        # Description analysis
        desc_keywords = sum(1 for kw in target_keywords if kw.lower() in metadata.description.lower())
        score_data["description_score"] = min(100, desc_keywords * 20)
        
        if len(metadata.description) < 100:
            score_data["recommendations"].append("Description too short (<100 chars)")
        
        # Tags analysis
        tag_keywords = sum(1 for kw in target_keywords if any(kw.lower() in tag for tag in metadata.tags))
        score_data["tags_score"] = min(100, tag_keywords * 25)
        
        if len(metadata.tags) < 5:
            score_data["recommendations"].append("Add more tags (minimum 5)")
        
        # Total score
        score_data["total_score"] = (
            score_data["title_score"] + 
            score_data["description_score"] + 
            score_data["tags_score"]
        ) / 3
        
        return score_data

# Example usage and testing
async def main():
    """Test the metadata generator."""
    generator = MetadataGenerator()
    
    # This would be called with actual script data
    print("Metadata generator initialized")

if __name__ == "__main__":
    asyncio.run(main())