"""
SEO Optimizer - enhances video metadata for better search rankings.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import re
from collections import Counter
import json

from config.config import config
from .metadata_generator import VideoMetadata

logger = logging.getLogger(__name__)

class SEOOptimizer:
    """Optimizes video metadata for search engine rankings."""
    
    def __init__(self):
        # SEO weight factors
        self.weights = {
            "title_keywords": 0.4,
            "description_keywords": 0.3,
            "tags": 0.2,
            "engagement_factors": 0.1
        }
        
        # Trending patterns by hour (engagement rates)
        self.hour_engagement = {
            6: 0.7, 7: 0.8, 8: 0.9, 9: 0.95,  # Morning
            12: 0.85, 13: 0.9, 14: 0.8,        # Lunch
            17: 0.95, 18: 1.0, 19: 1.0, 20: 0.95,  # Evening peak
            21: 0.9, 22: 0.8, 23: 0.6           # Late night
        }
        
        # Power words for different content types
        self.power_words = {
            "educational": ["learn", "discover", "understand", "master", "explained", "secrets"],
            "entertainment": ["amazing", "incredible", "shocking", "unbelievable", "viral", "epic"],
            "news": ["breaking", "latest", "exclusive", "revealed", "update", "confirmed"],
            "lifestyle": ["transform", "ultimate", "perfect", "essential", "proven", "simple"],
            "technology": ["revolutionary", "innovative", "breakthrough", "advanced", "cutting-edge", "future"],
            "health": ["proven", "effective", "natural", "safe", "powerful", "healing"],
            "science": ["discovered", "breakthrough", "research", "proven", "study", "evidence"]
        }
        
        # YouTube Shorts specific optimizations
        self.shorts_factors = {
            "optimal_title_length": (30, 50),
            "optimal_description_length": (100, 300),
            "max_tags": 15,
            "trending_hashtags": ["#shorts", "#viral", "#trending", "#fyp", "#foryou"]
        }
    
    def optimize_metadata(self, metadata: VideoMetadata, target_keywords: List[str], content_type: str = "educational") -> VideoMetadata:
        """Optimize metadata for SEO."""
        try:
            logger.info("Starting SEO optimization")
            
            # Create optimized copy
            optimized = VideoMetadata(
                title=metadata.title,
                description=metadata.description,
                tags=metadata.tags.copy(),
                category=metadata.category,
                privacy=metadata.privacy,
                thumbnail_path=metadata.thumbnail_path,
                language=metadata.language,
                default_audio_language=metadata.default_audio_language,
                publish_at=metadata.publish_at
            )
            
            # Optimize title
            optimized.title = self._optimize_title(optimized.title, target_keywords, content_type)
            
            # Optimize description
            optimized.description = self._optimize_description(optimized.description, target_keywords, content_type)
            
            # Optimize tags
            optimized.tags = self._optimize_tags(optimized.tags, target_keywords, content_type)
            
            logger.info("SEO optimization completed")
            return optimized
            
        except Exception as e:
            logger.error(f"SEO optimization failed: {e}")
            return metadata
    
    def _optimize_title(self, title: str, keywords: List[str], content_type: str) -> str:
        """Optimize title for SEO."""
        try:
            # Remove extra spaces and normalize
            title = re.sub(r'\s+', ' ', title.strip())
            
            # Check if primary keyword is in title
            primary_keyword = keywords[0] if keywords else ""
            if primary_keyword and primary_keyword.lower() not in title.lower():
                # Try to add primary keyword naturally
                if len(title) + len(primary_keyword) + 3 < 60:
                    title = f"{primary_keyword}: {title}"
            
            # Add power words if space allows
            power_words = self.power_words.get(content_type, [])
            for word in power_words:
                if word.lower() not in title.lower() and len(title) + len(word) + 1 < 60:
                    # Add power word at the beginning if it fits
                    title = f"{word.title()} {title}"
                    break
            
            # Ensure title is within optimal length
            optimal_min, optimal_max = self.shorts_factors["optimal_title_length"]
            if len(title) > optimal_max:
                # Truncate but keep important keywords
                words = title.split()
                truncated = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) + 1 <= optimal_max:
                        truncated.append(word)
                        current_length += len(word) + 1
                    else:
                        break
                
                title = " ".join(truncated)
                if not title.endswith("...") and len(title) + 3 <= optimal_max:
                    title += "..."
            
            return title
            
        except Exception as e:
            logger.error(f"Title optimization failed: {e}")
            return title
    
    def _optimize_description(self, description: str, keywords: List[str], content_type: str) -> str:
        """Optimize description for SEO."""
        try:
            # Ensure keywords are naturally distributed
            keyword_density = self._calculate_keyword_density(description, keywords)
            
            # Target keyword density: 2-3%
            target_density = 0.025
            
            # Add keywords if density is too low
            missing_keywords = []
            for keyword in keywords[:5]:  # Focus on top 5 keywords
                if keyword_density.get(keyword, 0) < target_density:
                    missing_keywords.append(keyword)
            
            # Add missing keywords naturally
            if missing_keywords:
                keyword_sentences = []
                for keyword in missing_keywords[:3]:  # Limit to avoid stuffing
                    if content_type == "educational":
                        keyword_sentences.append(f"Learn more about {keyword} and related topics.")
                    elif content_type == "entertainment":
                        keyword_sentences.append(f"This {keyword} content will amaze you!")
                    elif content_type == "technology":
                        keyword_sentences.append(f"Discover the latest in {keyword} innovation.")
                    else:
                        keyword_sentences.append(f"Everything you need to know about {keyword}.")
                
                # Insert keyword sentences naturally
                if keyword_sentences:
                    description += f"\n\n{' '.join(keyword_sentences)}"
            
            # Add trending hashtags if not present
            trending_hashtags = self.shorts_factors["trending_hashtags"]
            for hashtag in trending_hashtags[:3]:
                if hashtag not in description:
                    description += f" {hashtag}"
            
            # Ensure call-to-action is present
            cta_keywords = ["subscribe", "like", "comment", "share", "follow"]
            has_cta = any(word in description.lower() for word in cta_keywords)
            
            if not has_cta:
                description += "\n\n🔔 Subscribe for more amazing content!"
            
            return description
            
        except Exception as e:
            logger.error(f"Description optimization failed: {e}")
            return description
    
    def _optimize_tags(self, tags: List[str], keywords: List[str], content_type: str) -> List[str]:
        """Optimize tags for SEO."""
        try:
            optimized_tags = []
            
            # Add primary keywords as tags
            for keyword in keywords[:5]:
                if keyword.lower() not in [tag.lower() for tag in optimized_tags]:
                    optimized_tags.append(keyword.lower())
            
            # Add content-type specific tags
            content_tags = {
                "educational": ["education", "learning", "tutorial", "facts", "knowledge"],
                "entertainment": ["viral", "funny", "amazing", "entertainment", "cool"],
                "news": ["news", "breaking", "update", "current", "latest"],
                "lifestyle": ["lifestyle", "tips", "wellness", "life", "health"],
                "technology": ["tech", "technology", "innovation", "digital", "future"],
                "health": ["health", "wellness", "fitness", "medical", "healthy"],
                "science": ["science", "research", "discovery", "facts", "study"]
            }
            
            type_tags = content_tags.get(content_type, [])
            for tag in type_tags:
                if tag not in optimized_tags and len(optimized_tags) < 12:
                    optimized_tags.append(tag)
            
            # Add YouTube Shorts specific tags
            shorts_tags = ["shorts", "viral", "trending"]
            for tag in shorts_tags:
                if tag not in optimized_tags and len(optimized_tags) < 15:
                    optimized_tags.append(tag)
            
            # Add existing tags that aren't duplicates
            for tag in tags:
                clean_tag = tag.lower().strip()
                if clean_tag not in optimized_tags and len(optimized_tags) < 15:
                    optimized_tags.append(clean_tag)
            
            # Remove tags that are too short or generic
            filtered_tags = []
            for tag in optimized_tags:
                if len(tag) > 2 and tag not in ["the", "and", "for", "you", "are", "can"]:
                    filtered_tags.append(tag)
            
            return filtered_tags[:15]  # YouTube limit
            
        except Exception as e:
            logger.error(f"Tag optimization failed: {e}")
            return tags
    
    def _calculate_keyword_density(self, text: str, keywords: List[str]) -> Dict[str, float]:
        """Calculate keyword density in text."""
        text_lower = text.lower()
        word_count = len(text_lower.split())
        
        if word_count == 0:
            return {}
        
        densities = {}
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Count exact matches and partial matches
            exact_count = text_lower.count(keyword_lower)
            densities[keyword] = exact_count / word_count
        
        return densities
    
    def analyze_competition(self, title: str, keywords: List[str]) -> Dict[str, Any]:
        """Analyze competition for keywords (simplified)."""
        # This is a simplified version. In a real implementation,
        # you would use YouTube API to analyze competing videos
        
        analysis = {
            "competition_level": "medium",
            "keyword_difficulty": {},
            "suggestions": []
        }
        
        # Analyze each keyword
        for keyword in keywords:
            # Simplified difficulty calculation based on keyword length and commonality
            difficulty = min(100, len(keyword) * 5 + keyword.count(' ') * 10)
            analysis["keyword_difficulty"][keyword] = difficulty
            
            if difficulty > 70:
                analysis["suggestions"].append(f"Consider long-tail variations of '{keyword}'")
        
        return analysis
    
    def optimize_for_time_slot(self, metadata: VideoMetadata, publish_hour: int) -> VideoMetadata:
        """Optimize metadata for specific time slot."""
        try:
            engagement_multiplier = self.hour_engagement.get(publish_hour, 0.8)
            
            # Adjust title based on time
            if 6 <= publish_hour <= 9:  # Morning
                if "morning" not in metadata.title.lower():
                    metadata.title = f"Morning {metadata.title}"
            elif 17 <= publish_hour <= 20:  # Evening peak
                # Add urgency words for peak hours
                urgency_words = ["now", "today", "must see"]
                for word in urgency_words:
                    if word not in metadata.title.lower() and len(metadata.title) + len(word) + 1 < 60:
                        metadata.title = f"{word.title()} {metadata.title}"
                        break
            
            # Adjust description for engagement
            if engagement_multiplier > 0.9:  # High engagement time
                if "🔥" not in metadata.description:
                    metadata.description = f"🔥 {metadata.description}"
            
            return metadata
            
        except Exception as e:
            logger.error(f"Time slot optimization failed: {e}")
            return metadata
    
    def generate_ab_test_variants(self, metadata: VideoMetadata, keywords: List[str], count: int = 3) -> List[VideoMetadata]:
        """Generate A/B test variants of metadata."""
        variants = []
        
        for i in range(count):
            variant = VideoMetadata(
                title=metadata.title,
                description=metadata.description,
                tags=metadata.tags.copy(),
                category=metadata.category,
                privacy=metadata.privacy,
                thumbnail_path=metadata.thumbnail_path,
                language=metadata.language,
                default_audio_language=metadata.default_audio_language,
                publish_at=metadata.publish_at
            )
            
            # Variant A: Keyword-focused
            if i == 0:
                primary_keyword = keywords[0] if keywords else ""
                if primary_keyword and primary_keyword not in variant.title:
                    variant.title = f"{primary_keyword} - {variant.title}"
            
            # Variant B: Emotion-focused
            elif i == 1:
                emotion_words = ["Amazing", "Incredible", "Shocking", "Unbelievable"]
                emotion_word = emotion_words[i % len(emotion_words)]
                if emotion_word.lower() not in variant.title.lower():
                    variant.title = f"{emotion_word} {variant.title}"
            
            # Variant C: Question format
            elif i == 2:
                if not variant.title.endswith("?"):
                    words = variant.title.split()
                    if len(words) > 2:
                        variant.title = f"Did You Know {' '.join(words[1:])}?"
            
            # Limit title length
            if len(variant.title) > 60:
                variant.title = variant.title[:57] + "..."
            
            variants.append(variant)
        
        return variants
    
    def score_seo_quality(self, metadata: VideoMetadata, keywords: List[str]) -> Dict[str, Any]:
        """Score the SEO quality of metadata."""
        scores = {
            "title_score": 0,
            "description_score": 0,
            "tags_score": 0,
            "overall_score": 0,
            "recommendations": []
        }
        
        # Title scoring
        title_keywords = sum(1 for kw in keywords[:3] if kw.lower() in metadata.title.lower())
        scores["title_score"] = min(100, (title_keywords / min(3, len(keywords))) * 100)
        
        title_length = len(metadata.title)
        optimal_min, optimal_max = self.shorts_factors["optimal_title_length"]
        if title_length < optimal_min:
            scores["recommendations"].append(f"Title too short ({title_length} chars). Aim for {optimal_min}-{optimal_max} characters.")
        elif title_length > optimal_max:
            scores["recommendations"].append(f"Title too long ({title_length} chars). Aim for {optimal_min}-{optimal_max} characters.")
        
        # Description scoring
        desc_keywords = sum(1 for kw in keywords[:5] if kw.lower() in metadata.description.lower())
        scores["description_score"] = min(100, (desc_keywords / min(5, len(keywords))) * 100)
        
        desc_length = len(metadata.description)
        optimal_desc_min, optimal_desc_max = self.shorts_factors["optimal_description_length"]
        if desc_length < optimal_desc_min:
            scores["recommendations"].append(f"Description too short ({desc_length} chars). Aim for {optimal_desc_min}-{optimal_desc_max} characters.")
        
        # Tags scoring
        tag_keywords = sum(1 for kw in keywords if any(kw.lower() in tag.lower() for tag in metadata.tags))
        scores["tags_score"] = min(100, (tag_keywords / len(keywords)) * 100)
        
        if len(metadata.tags) < 5:
            scores["recommendations"].append(f"Add more tags. Currently {len(metadata.tags)}, recommended minimum: 5")
        
        # Overall score
        scores["overall_score"] = (
            scores["title_score"] * self.weights["title_keywords"] +
            scores["description_score"] * self.weights["description_keywords"] +
            scores["tags_score"] * self.weights["tags"]
        )
        
        return scores
    
    def suggest_improvements(self, metadata: VideoMetadata, keywords: List[str], content_type: str) -> List[str]:
        """Suggest specific improvements for metadata."""
        suggestions = []
        
        # Title suggestions
        if not any(kw.lower() in metadata.title.lower() for kw in keywords[:2]):
            suggestions.append(f"Add primary keywords to title: {', '.join(keywords[:2])}")
        
        power_words = self.power_words.get(content_type, [])
        if not any(word.lower() in metadata.title.lower() for word in power_words):
            suggestions.append(f"Consider adding power words: {', '.join(power_words[:3])}")
        
        # Description suggestions
        if len(metadata.description) < 100:
            suggestions.append("Expand description to at least 100 characters for better SEO")
        
        if "subscribe" not in metadata.description.lower():
            suggestions.append("Add call-to-action (subscribe, like, comment) to description")
        
        # Tags suggestions
        if len(metadata.tags) < 8:
            suggestions.append("Add more relevant tags (aim for 8-15 tags)")
        
        if "shorts" not in [tag.lower() for tag in metadata.tags]:
            suggestions.append("Add 'shorts' tag for YouTube Shorts visibility")
        
        return suggestions
    
    def optimize_for_viral_potential(self, metadata: VideoMetadata, trending_topics: List[str]) -> VideoMetadata:
        """Optimize metadata for viral potential."""
        try:
            # Add trending elements to title
            for topic in trending_topics[:2]:
                if topic.lower() not in metadata.title.lower() and len(metadata.title) + len(topic) + 3 < 60:
                    metadata.title = f"{topic} {metadata.title}"
                    break
            
            # Add viral hashtags to description
            viral_hashtags = ["#viral", "#trending", "#fyp", "#foryou", "#mustwatch"]
            existing_hashtags = re.findall(r'#\w+', metadata.description)
            
            for hashtag in viral_hashtags:
                if hashtag not in existing_hashtags:
                    metadata.description += f" {hashtag}"
                    if len(existing_hashtags) >= 5:  # Limit hashtags
                        break
            
            # Add urgency to description
            urgency_phrases = ["Don't miss this!", "Going viral now!", "Everyone's talking about this!"]
            if not any(phrase in metadata.description for phrase in urgency_phrases):
                metadata.description = f"{urgency_phrases[0]} {metadata.description}"
            
            return metadata
            
        except Exception as e:
            logger.error(f"Viral optimization failed: {e}")
            return metadata

# Example usage
def main():
    """Test SEO optimizer."""
    optimizer = SEOOptimizer()
    print("SEO optimizer initialized")
    print(f"Available content types: {list(optimizer.power_words.keys())}")

if __name__ == "__main__":
    main()