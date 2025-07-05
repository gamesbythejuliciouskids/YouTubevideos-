"""
Trending Topics Module for YouTube Shorts automation.
"""

from .trending_fetcher import TrendingTopicsFetcher
from .topic_processor import TopicProcessor

__all__ = ["TrendingTopicsFetcher", "TopicProcessor"]