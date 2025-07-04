"""
Topic Processor - filters and processes trending topics for video generation.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from dataclasses import dataclass
from .trending_fetcher import TrendingTopic
from config.config import config

logger = logging.getLogger(__name__)

@dataclass
class ProcessedTopic:
    """Processed topic ready for video generation."""
    original_topic: TrendingTopic
    processed_title: str
    video_angle: str
    target_keywords: List[str]
    estimated_engagement: float
    content_type: str  # 'educational', 'entertainment', 'news', 'lifestyle'
    difficulty_level: str  # 'easy', 'medium', 'hard'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_topic": self.original_topic.to_dict(),
            "processed_title": self.processed_title,
            "video_angle": self.video_angle,
            "target_keywords": self.target_keywords,
            "estimated_engagement": self.estimated_engagement,
            "content_type": self.content_type,
            "difficulty_level": self.difficulty_level
        }

class TopicProcessor:
    """Processes and filters trending topics for video generation."""
    
    def __init__(self):
        self.content_filters = self._load_content_filters()
        self.engagement_multipliers = self._load_engagement_multipliers()
        
    def _load_content_filters(self) -> Dict[str, Any]:
        """Load content filtering rules."""
        return {
            # Topics to avoid (controversial, inappropriate, etc.)
            "blacklisted_keywords": [
                "death", "suicide", "murder", "violence", "war", "terrorism",
                "explicit", "nsfw", "drug", "alcohol", "gambling", "hate",
                "political", "election", "voting", "government", "protest"
            ],
            
            # Preferred content types
            "preferred_topics": [
                "science", "technology", "health", "education", "diy",
                "cooking", "travel", "fitness", "animals", "nature",
                "space", "facts", "trivia", "history", "art", "music"
            ],
            
            # Minimum engagement threshold
            "min_engagement_score": 10.0,
            
            # Title length constraints
            "max_title_length": 100,
            "min_title_length": 10
        }
    
    def _load_engagement_multipliers(self) -> Dict[str, float]:
        """Load engagement multipliers for different content types."""
        return {
            "science": 1.2,
            "technology": 1.1,
            "health": 1.3,
            "animals": 1.4,
            "space": 1.2,
            "food": 1.3,
            "travel": 1.1,
            "diy": 1.2,
            "facts": 1.5,
            "trivia": 1.4,
            "history": 1.1,
            "mystery": 1.3,
            "nature": 1.2
        }
    
    def process_topics(self, topics: List[TrendingTopic]) -> List[ProcessedTopic]:
        """Process and filter trending topics."""
        processed_topics = []
        
        for topic in topics:
            try:
                # Filter out inappropriate content
                if not self._is_topic_appropriate(topic):
                    logger.debug(f"Filtering out inappropriate topic: {topic.title}")
                    continue
                
                # Process the topic
                processed_topic = self._process_single_topic(topic)
                
                if processed_topic:
                    processed_topics.append(processed_topic)
                    
            except Exception as e:
                logger.error(f"Error processing topic '{topic.title}': {e}")
                continue
        
        # Sort by estimated engagement
        processed_topics.sort(key=lambda x: x.estimated_engagement, reverse=True)
        
        return processed_topics
    
    def _is_topic_appropriate(self, topic: TrendingTopic) -> bool:
        """Check if topic is appropriate for video generation."""
        # Check blacklisted keywords
        text_to_check = (topic.title + " " + topic.description).lower()
        
        for keyword in self.content_filters["blacklisted_keywords"]:
            if keyword in text_to_check:
                return False
        
        # Check title length
        if len(topic.title) < self.content_filters["min_title_length"]:
            return False
        
        if len(topic.title) > self.content_filters["max_title_length"]:
            return False
        
        # Check minimum engagement score
        if topic.score < self.content_filters["min_engagement_score"]:
            return False
        
        return True
    
    def _process_single_topic(self, topic: TrendingTopic) -> Optional[ProcessedTopic]:
        """Process a single topic."""
        try:
            # Determine content type
            content_type = self._determine_content_type(topic)
            
            # Generate video angle
            video_angle = self._generate_video_angle(topic, content_type)
            
            # Process title for video
            processed_title = self._process_title_for_video(topic.title, video_angle)
            
            # Extract target keywords
            target_keywords = self._extract_target_keywords(topic)
            
            # Calculate estimated engagement
            estimated_engagement = self._calculate_estimated_engagement(topic, content_type)
            
            # Determine difficulty level
            difficulty_level = self._determine_difficulty_level(topic, content_type)
            
            return ProcessedTopic(
                original_topic=topic,
                processed_title=processed_title,
                video_angle=video_angle,
                target_keywords=target_keywords,
                estimated_engagement=estimated_engagement,
                content_type=content_type,
                difficulty_level=difficulty_level
            )
            
        except Exception as e:
            logger.error(f"Error processing topic: {e}")
            return None
    
    def _determine_content_type(self, topic: TrendingTopic) -> str:
        """Determine the content type based on topic."""
        text = (topic.title + " " + topic.description).lower()
        
        # Content type mapping
        content_patterns = {
            "educational": ["learn", "how to", "tutorial", "guide", "explain", "science", "study", "research"],
            "entertainment": ["funny", "amazing", "incredible", "shocking", "viral", "meme", "celebrity"],
            "news": ["breaking", "news", "update", "announcement", "report", "today", "latest"],
            "lifestyle": ["health", "fitness", "food", "travel", "home", "style", "beauty", "wellness"]
        }
        
        scores = {}
        for content_type, patterns in content_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text)
            scores[content_type] = score
        
        # Return the content type with highest score, default to educational
        return max(scores, key=scores.get) if any(scores.values()) else "educational"
    
    def _generate_video_angle(self, topic: TrendingTopic, content_type: str) -> str:
        """Generate a video angle based on topic and content type."""
        title = topic.title
        
        angles = {
            "educational": [
                f"The Science Behind {title}",
                f"5 Facts You Didn't Know About {title}",
                f"Why {title} Matters",
                f"The Truth About {title}",
                f"How {title} Works"
            ],
            "entertainment": [
                f"The Shocking Truth About {title}",
                f"You Won't Believe What Happened with {title}",
                f"The Craziest Facts About {title}",
                f"This Will Change How You See {title}",
                f"The Mind-Blowing Story of {title}"
            ],
            "news": [
                f"Breaking: What's Happening with {title}",
                f"The Latest on {title}",
                f"Everything You Need to Know About {title}",
                f"The Real Story Behind {title}",
                f"What {title} Means for You"
            ],
            "lifestyle": [
                f"How {title} Can Change Your Life",
                f"The Benefits of {title}",
                f"Why Everyone's Talking About {title}",
                f"The Secret to {title}",
                f"Transform Your Life with {title}"
            ]
        }
        
        # Return first angle for the content type
        return angles.get(content_type, angles["educational"])[0]
    
    def _process_title_for_video(self, original_title: str, video_angle: str) -> str:
        """Process title to make it more engaging for video."""
        # If video angle is more engaging, use it
        if len(video_angle) <= 60 and any(word in video_angle.lower() for word in ["shocking", "amazing", "secret", "truth", "facts"]):
            return video_angle
        
        # Otherwise, enhance the original title
        enhanced_title = original_title
        
        # Add engaging prefixes for short titles
        if len(enhanced_title) < 30:
            prefixes = ["The Truth About", "Amazing Facts:", "You Won't Believe", "The Secret of"]
            enhanced_title = f"{prefixes[0]} {enhanced_title}"
        
        # Ensure title is not too long
        if len(enhanced_title) > 60:
            enhanced_title = enhanced_title[:57] + "..."
        
        return enhanced_title
    
    def _extract_target_keywords(self, topic: TrendingTopic) -> List[str]:
        """Extract target keywords for SEO."""
        keywords = topic.keywords.copy()
        
        # Add variations and related terms
        title_words = re.findall(r'\b\w+\b', topic.title.lower())
        description_words = re.findall(r'\b\w+\b', topic.description.lower())
        
        # Combine and filter
        all_words = title_words + description_words
        
        # Remove stop words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        filtered_words = [word for word in all_words if word not in stop_words and len(word) > 2]
        
        # Add unique words to keywords
        for word in filtered_words:
            if word not in keywords:
                keywords.append(word)
        
        return keywords[:10]  # Return top 10 keywords
    
    def _calculate_estimated_engagement(self, topic: TrendingTopic, content_type: str) -> float:
        """Calculate estimated engagement score."""
        base_score = topic.score
        
        # Apply content type multiplier
        multiplier = self.engagement_multipliers.get(content_type, 1.0)
        
        # Apply keyword multipliers
        text = (topic.title + " " + topic.description).lower()
        for keyword, mult in self.engagement_multipliers.items():
            if keyword in text:
                multiplier *= mult
                break
        
        # Apply source multiplier
        source_multipliers = {
            "google_trends": 1.2,
            "reddit": 1.1,
            "twitter": 1.0
        }
        
        for source, mult in source_multipliers.items():
            if source in topic.source:
                multiplier *= mult
                break
        
        # Apply recency bonus (recent topics get higher score)
        if topic.created_at:
            hours_old = (datetime.now() - topic.created_at).total_seconds() / 3600
            if hours_old < 6:  # Less than 6 hours old
                multiplier *= 1.3
            elif hours_old < 24:  # Less than 24 hours old
                multiplier *= 1.1
        
        return base_score * multiplier
    
    def _determine_difficulty_level(self, topic: TrendingTopic, content_type: str) -> str:
        """Determine difficulty level for content creation."""
        text = (topic.title + " " + topic.description).lower()
        
        # Complex topics that require more research
        complex_keywords = [
            "science", "research", "study", "technology", "medical", "quantum",
            "economics", "finance", "politics", "law", "academic", "technical"
        ]
        
        # Simple topics that are easy to create content for
        simple_keywords = [
            "food", "animals", "travel", "celebrity", "sports", "weather",
            "entertainment", "music", "art", "fashion", "lifestyle"
        ]
        
        complex_score = sum(1 for keyword in complex_keywords if keyword in text)
        simple_score = sum(1 for keyword in simple_keywords if keyword in text)
        
        if complex_score > simple_score:
            return "hard"
        elif simple_score > complex_score:
            return "easy"
        else:
            return "medium"
    
    def get_best_topic_for_video(self, topics: List[TrendingTopic]) -> Optional[ProcessedTopic]:
        """Get the best topic for video generation."""
        processed_topics = self.process_topics(topics)
        
        if not processed_topics:
            return None
        
        # Filter by difficulty level (prefer easy and medium)
        easy_topics = [t for t in processed_topics if t.difficulty_level in ["easy", "medium"]]
        
        if easy_topics:
            return easy_topics[0]  # Return highest scoring easy/medium topic
        
        return processed_topics[0]  # Return highest scoring topic overall
    
    def filter_by_content_type(self, topics: List[ProcessedTopic], content_type: str) -> List[ProcessedTopic]:
        """Filter topics by content type."""
        return [topic for topic in topics if topic.content_type == content_type]
    
    def get_topic_statistics(self, topics: List[ProcessedTopic]) -> Dict[str, Any]:
        """Get statistics about processed topics."""
        if not topics:
            return {}
        
        content_types = [topic.content_type for topic in topics]
        difficulty_levels = [topic.difficulty_level for topic in topics]
        
        return {
            "total_topics": len(topics),
            "content_types": {ct: content_types.count(ct) for ct in set(content_types)},
            "difficulty_levels": {dl: difficulty_levels.count(dl) for dl in set(difficulty_levels)},
            "average_engagement": sum(topic.estimated_engagement for topic in topics) / len(topics),
            "top_keywords": self._get_top_keywords(topics)
        }
    
    def _get_top_keywords(self, topics: List[ProcessedTopic]) -> List[str]:
        """Get top keywords across all topics."""
        all_keywords = []
        for topic in topics:
            all_keywords.extend(topic.target_keywords)
        
        # Count keyword frequency
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Return top 10 keywords
        return sorted(keyword_counts.keys(), key=lambda x: keyword_counts[x], reverse=True)[:10]

# Example usage
if __name__ == "__main__":
    # This would be used with actual trending topics
    pass