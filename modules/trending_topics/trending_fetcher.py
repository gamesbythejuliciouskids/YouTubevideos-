"""
Trending Topics Fetcher - pulls trending topics from multiple sources.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import aiohttp
from pytrends.request import TrendReq
import praw
import requests
from dataclasses import dataclass
from config.config import config

logger = logging.getLogger(__name__)

@dataclass
class TrendingTopic:
    """Data class for trending topic."""
    title: str
    description: str
    source: str
    score: float
    keywords: List[str]
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "score": self.score,
            "keywords": self.keywords,
            "url": self.url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class TrendingTopicsFetcher:
    """Fetches trending topics from multiple sources."""
    
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360)
        self.reddit_client = None
        self.setup_reddit_client()
        
    def setup_reddit_client(self):
        """Set up Reddit client."""
        try:
            if config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET:
                self.reddit_client = praw.Reddit(
                    client_id=config.REDDIT_CLIENT_ID,
                    client_secret=config.REDDIT_CLIENT_SECRET,
                    user_agent=config.REDDIT_USER_AGENT
                )
                logger.info("Reddit client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
    
    async def fetch_all_trending_topics(self, limit: int = 10) -> List[TrendingTopic]:
        """Fetch trending topics from all sources."""
        topics = []
        
        # Fetch from multiple sources concurrently
        tasks = []
        
        if "google_trends" in config.TRENDING_TOPICS_SOURCES:
            tasks.append(self.fetch_google_trends(limit))
        
        if "reddit" in config.TRENDING_TOPICS_SOURCES and self.reddit_client:
            tasks.append(self.fetch_reddit_trends(limit))
        
        if "twitter" in config.TRENDING_TOPICS_SOURCES and config.TWITTER_BEARER_TOKEN:
            tasks.append(self.fetch_twitter_trends(limit))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        for result in results:
            if isinstance(result, list):
                topics.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Error fetching trending topics: {result}")
        
        # Sort by score and return top topics
        topics.sort(key=lambda x: x.score, reverse=True)
        return topics[:limit]
    
    async def fetch_google_trends(self, limit: int = 5) -> List[TrendingTopic]:
        """Fetch trending topics from Google Trends."""
        topics = []
        
        try:
            # Get trending searches
            trending_searches = self.pytrends.trending_searches(pn='united_states')
            
            for idx, trend in enumerate(trending_searches.head(limit).iterrows()):
                topic_title = trend[1][0]
                
                # Get related queries for more context
                try:
                    self.pytrends.build_payload([topic_title], cat=0, timeframe='today 1-d')
                    related_queries = self.pytrends.related_queries()
                    
                    # Extract keywords from related queries
                    keywords = [topic_title.lower()]
                    if topic_title in related_queries and related_queries[topic_title]['top'] is not None:
                        keywords.extend(related_queries[topic_title]['top']['query'].head(3).tolist())
                    
                    topic = TrendingTopic(
                        title=topic_title,
                        description=f"Trending topic: {topic_title}",
                        source="google_trends",
                        score=100 - (idx * 10),  # Higher score for higher trending position
                        keywords=keywords,
                        created_at=datetime.now()
                    )
                    topics.append(topic)
                    
                except Exception as e:
                    logger.warning(f"Error getting details for trend '{topic_title}': {e}")
                    # Add basic topic without detailed info
                    topic = TrendingTopic(
                        title=topic_title,
                        description=f"Trending topic: {topic_title}",
                        source="google_trends",
                        score=100 - (idx * 10),
                        keywords=[topic_title.lower()],
                        created_at=datetime.now()
                    )
                    topics.append(topic)
                    
                # Add delay to respect rate limits
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
        
        return topics
    
    async def fetch_reddit_trends(self, limit: int = 5) -> List[TrendingTopic]:
        """Fetch trending topics from Reddit."""
        topics = []
        
        try:
            # Popular subreddits for trending content
            subreddits = ['all', 'popular', 'todayilearned', 'science', 'technology', 'news']
            
            for subreddit_name in subreddits[:3]:  # Limit to avoid rate limits
                try:
                    subreddit = self.reddit_client.subreddit(subreddit_name)
                    
                    # Get hot posts from the subreddit
                    hot_posts = list(subreddit.hot(limit=limit))
                    
                    for post in hot_posts:
                        # Skip if post is too old (more than 24 hours)
                        post_time = datetime.fromtimestamp(post.created_utc)
                        if datetime.now() - post_time > timedelta(days=1):
                            continue
                            
                        # Create topic from post
                        topic = TrendingTopic(
                            title=post.title,
                            description=post.selftext[:200] if post.selftext else f"Reddit post from r/{subreddit_name}",
                            source=f"reddit_r_{subreddit_name}",
                            score=post.score / 100,  # Normalize score
                            keywords=self.extract_keywords_from_text(post.title),
                            url=f"https://reddit.com{post.permalink}",
                            created_at=post_time
                        )
                        topics.append(topic)
                        
                except Exception as e:
                    logger.warning(f"Error fetching from r/{subreddit_name}: {e}")
                    continue
                    
                # Add delay to respect rate limits
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error fetching Reddit trends: {e}")
        
        return topics
    
    async def fetch_twitter_trends(self, limit: int = 5) -> List[TrendingTopic]:
        """Fetch trending topics from Twitter/X."""
        topics = []
        
        try:
            if not config.TWITTER_BEARER_TOKEN:
                logger.warning("Twitter Bearer Token not configured")
                return topics
                
            headers = {
                'Authorization': f'Bearer {config.TWITTER_BEARER_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            # Get trending topics for US
            url = 'https://api.twitter.com/2/trends/by/woeid/23424977'  # WOEID for US
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'data' in data:
                            for idx, trend in enumerate(data['data'][:limit]):
                                topic = TrendingTopic(
                                    title=trend['name'],
                                    description=f"Trending on Twitter: {trend['name']}",
                                    source="twitter",
                                    score=100 - (idx * 10),
                                    keywords=[trend['name'].lower()],
                                    url=trend.get('url'),
                                    created_at=datetime.now()
                                )
                                topics.append(topic)
                    else:
                        logger.error(f"Twitter API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error fetching Twitter trends: {e}")
        
        return topics
    
    def extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract keywords from text."""
        import re
        
        # Simple keyword extraction - remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'this', 'that', 'these', 'those'
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords[:5]  # Return top 5 keywords
    
    def save_topics_to_file(self, topics: List[TrendingTopic], filename: str = None):
        """Save topics to JSON file."""
        if filename is None:
            filename = f"trending_topics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        topics_data = [topic.to_dict() for topic in topics]
        
        with open(filepath, 'w') as f:
            json.dump(topics_data, f, indent=2)
        
        logger.info(f"Saved {len(topics)} trending topics to {filepath}")
        return filepath
    
    def load_topics_from_file(self, filepath: str) -> List[TrendingTopic]:
        """Load topics from JSON file."""
        with open(filepath, 'r') as f:
            topics_data = json.load(f)
        
        topics = []
        for topic_data in topics_data:
            topic = TrendingTopic(
                title=topic_data['title'],
                description=topic_data['description'],
                source=topic_data['source'],
                score=topic_data['score'],
                keywords=topic_data['keywords'],
                url=topic_data.get('url'),
                created_at=datetime.fromisoformat(topic_data['created_at']) if topic_data.get('created_at') else None
            )
            topics.append(topic)
        
        return topics

# Example usage and testing
async def main():
    """Test the trending topics fetcher."""
    fetcher = TrendingTopicsFetcher()
    
    print("Fetching trending topics...")
    topics = await fetcher.fetch_all_trending_topics(limit=10)
    
    print(f"\nFound {len(topics)} trending topics:")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic.title} (Score: {topic.score:.1f}, Source: {topic.source})")
        print(f"   Keywords: {', '.join(topic.keywords)}")
        print(f"   Description: {topic.description[:100]}...")
        print()
    
    # Save topics to file
    filepath = fetcher.save_topics_to_file(topics)
    print(f"Topics saved to: {filepath}")

if __name__ == "__main__":
    asyncio.run(main())