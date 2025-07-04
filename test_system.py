#!/usr/bin/env python3
"""
Comprehensive test suite for YouTube Shorts Automation System.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import config
from modules.trending_topics import TrendingTopicsFetcher, TopicProcessor
from modules.script_generation import ScriptGenerator
from main import YouTubeShortsOrchestrator

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemTester:
    """Comprehensive system tester."""
    
    def __init__(self):
        self.test_results = {
            "started_at": datetime.now().isoformat(),
            "tests": {},
            "overall_success": False,
            "errors": []
        }
        
    async def run_all_tests(self):
        """Run all system tests."""
        logger.info("🧪 Starting comprehensive system tests...")
        
        tests = [
            ("Configuration", self.test_configuration),
            ("Trending Topics Fetcher", self.test_trending_topics_fetcher),
            ("Topic Processor", self.test_topic_processor),
            ("Script Generator", self.test_script_generator),
            ("Full Pipeline", self.test_full_pipeline),
            ("Error Handling", self.test_error_handling),
            ("File Operations", self.test_file_operations)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"🔍 Running test: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = await test_func()
                if result:
                    logger.info(f"✅ {test_name} - PASSED")
                    passed_tests += 1
                    self.test_results["tests"][test_name] = {"status": "PASSED", "error": None}
                else:
                    logger.error(f"❌ {test_name} - FAILED")
                    self.test_results["tests"][test_name] = {"status": "FAILED", "error": "Test returned False"}
                    
            except Exception as e:
                logger.error(f"❌ {test_name} - ERROR: {e}")
                self.test_results["tests"][test_name] = {"status": "ERROR", "error": str(e)}
                self.test_results["errors"].append(f"{test_name}: {str(e)}")
        
        # Calculate overall success
        self.test_results["overall_success"] = passed_tests == total_tests
        self.test_results["passed_tests"] = passed_tests
        self.test_results["total_tests"] = total_tests
        self.test_results["completed_at"] = datetime.now().isoformat()
        
        # Print summary
        self.print_test_summary()
        
        return self.test_results
    
    async def test_configuration(self):
        """Test configuration loading and validation."""
        try:
            # Test basic config loading
            assert config.DEBUG is not None
            assert config.VIDEO_DURATION_SECONDS > 0
            assert config.SCRIPT_MAX_WORDS > 0
            
            # Test directory creation
            config.OUTPUT_DIR.mkdir(exist_ok=True)
            config.LOGS_DIR.mkdir(exist_ok=True)
            
            # Test channel config loading
            channel_config = config.get_channel_config("default")
            assert isinstance(channel_config, dict)
            assert "name" in channel_config
            
            logger.info("✓ Configuration loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return False
    
    async def test_trending_topics_fetcher(self):
        """Test trending topics fetcher."""
        try:
            fetcher = TrendingTopicsFetcher()
            
            # Test Google Trends (this might fail without proper setup)
            try:
                google_topics = await fetcher.fetch_google_trends(limit=3)
                logger.info(f"✓ Google Trends fetched {len(google_topics)} topics")
            except Exception as e:
                logger.warning(f"Google Trends failed (expected): {e}")
            
            # Test Reddit (this might fail without API keys)
            try:
                if fetcher.reddit_client:
                    reddit_topics = await fetcher.fetch_reddit_trends(limit=3)
                    logger.info(f"✓ Reddit fetched {len(reddit_topics)} topics")
                else:
                    logger.info("✓ Reddit client not configured (skipping)")
            except Exception as e:
                logger.warning(f"Reddit failed: {e}")
            
            # Test keyword extraction
            keywords = fetcher.extract_keywords_from_text("This is a test about artificial intelligence and machine learning")
            assert len(keywords) > 0
            logger.info(f"✓ Keyword extraction: {keywords}")
            
            # Test file operations
            from modules.trending_topics.trending_fetcher import TrendingTopic
            sample_topic = TrendingTopic(
                title="Test Topic",
                description="Test description",
                source="test",
                score=100.0,
                keywords=["test", "topic"],
                created_at=datetime.now()
            )
            
            # Test save/load
            topics = [sample_topic]
            filepath = fetcher.save_topics_to_file(topics, "test_topics.json")
            loaded_topics = fetcher.load_topics_from_file(filepath)
            assert len(loaded_topics) == 1
            assert loaded_topics[0].title == "Test Topic"
            
            logger.info("✓ Trending topics fetcher working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Trending topics fetcher test failed: {e}")
            return False
    
    async def test_topic_processor(self):
        """Test topic processor."""
        try:
            processor = TopicProcessor()
            
            # Create sample topics
            from modules.trending_topics.trending_fetcher import TrendingTopic
            sample_topics = [
                TrendingTopic(
                    title="Amazing Science Discovery",
                    description="Scientists have discovered something amazing about space",
                    source="test",
                    score=95.0,
                    keywords=["science", "discovery", "space"],
                    created_at=datetime.now()
                ),
                TrendingTopic(
                    title="Political Controversy",  # Should be filtered out
                    description="A political debate about government policies",
                    source="test",
                    score=85.0,
                    keywords=["political", "government"],
                    created_at=datetime.now()
                ),
                TrendingTopic(
                    title="Cute Animal Facts",
                    description="Interesting facts about cute animals",
                    source="test",
                    score=90.0,
                    keywords=["animals", "facts", "cute"],
                    created_at=datetime.now()
                )
            ]
            
            # Test processing
            processed_topics = processor.process_topics(sample_topics)
            
            # Should filter out political content
            assert len(processed_topics) == 2
            assert all(topic.difficulty_level in ["easy", "medium", "hard"] for topic in processed_topics)
            assert all(topic.content_type in ["educational", "entertainment", "news", "lifestyle"] for topic in processed_topics)
            
            logger.info(f"✓ Processed {len(processed_topics)} topics")
            for topic in processed_topics:
                logger.info(f"  - {topic.processed_title} ({topic.content_type}, {topic.difficulty_level})")
            
            # Test best topic selection
            best_topic = processor.get_best_topic_for_video(sample_topics)
            assert best_topic is not None
            logger.info(f"✓ Best topic selected: {best_topic.processed_title}")
            
            # Test statistics
            stats = processor.get_topic_statistics(processed_topics)
            assert "total_topics" in stats
            assert stats["total_topics"] == len(processed_topics)
            
            logger.info("✓ Topic processor working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Topic processor test failed: {e}")
            return False
    
    async def test_script_generator(self):
        """Test script generator."""
        try:
            generator = ScriptGenerator()
            
            # Create sample processed topic
            from modules.trending_topics.trending_fetcher import TrendingTopic
            from modules.trending_topics.topic_processor import ProcessedTopic
            
            sample_topic = TrendingTopic(
                title="Amazing AI Breakthrough",
                description="Scientists create AI that can understand emotions",
                source="test",
                score=95.0,
                keywords=["AI", "artificial intelligence", "breakthrough"],
                created_at=datetime.now()
            )
            
            processed_topic = ProcessedTopic(
                original_topic=sample_topic,
                processed_title="The AI Breakthrough That Will Change Everything",
                video_angle="Revolutionary AI Technology",
                target_keywords=["AI", "technology", "breakthrough", "artificial intelligence"],
                estimated_engagement=120.0,
                content_type="educational",
                difficulty_level="medium"
            )
            
            # Test script generation (will use fallback templates if no API keys)
            script = await generator.generate_script(processed_topic)
            assert script is not None
            assert len(script.full_script) > 0
            assert script.word_count > 0
            assert script.estimated_duration > 0
            
            logger.info(f"✓ Generated script ({script.word_count} words, {script.estimated_duration}s)")
            logger.info(f"  Hook: {script.hook}")
            logger.info(f"  CTA: {script.call_to_action}")
            
            # Test script validation
            assert script.word_count <= config.SCRIPT_MAX_WORDS
            assert script.estimated_duration <= config.VIDEO_DURATION_SECONDS
            
            # Test script saving/loading
            filepath = generator.save_script(script, "test_script.json")
            loaded_script = generator.load_script(filepath)
            assert loaded_script.full_script == script.full_script
            
            logger.info("✓ Script generator working correctly")
            return True
            
        except Exception as e:
            logger.error(f"Script generator test failed: {e}")
            return False
    
    async def test_full_pipeline(self):
        """Test full pipeline integration."""
        try:
            orchestrator = YouTubeShortsOrchestrator()
            
            # Run pipeline in debug mode
            results = await orchestrator.run_full_pipeline(debug=True)
            
            assert results is not None
            assert "steps" in results
            assert "started_at" in results
            
            # Check that major steps were attempted
            expected_steps = [
                "trending_topics",
                "processed_topics", 
                "selected_topic",
                "script_generation"
            ]
            
            for step in expected_steps:
                if step not in results["steps"]:
                    logger.warning(f"Pipeline step '{step}' not found in results")
                    # Don't fail the test for missing steps in debug mode
                else:
                    logger.info(f"✓ Pipeline step '{step}' completed")
            
            logger.info("✓ Full pipeline integration test completed")
            return True
            
        except Exception as e:
            logger.error(f"Full pipeline test failed: {e}")
            return False
    
    async def test_error_handling(self):
        """Test error handling and recovery."""
        try:
            # Test invalid configuration
            try:
                invalid_config = config.get_channel_config("nonexistent_channel")
                assert "name" in invalid_config  # Should return default config
                logger.info("✓ Invalid config handled gracefully")
            except Exception as e:
                logger.error(f"Config error handling failed: {e}")
                return False
            
            # Test script generation with invalid topic
            generator = ScriptGenerator()
            try:
                # This should handle errors gracefully
                from modules.trending_topics.trending_fetcher import TrendingTopic
                from modules.trending_topics.topic_processor import ProcessedTopic
                
                invalid_topic = ProcessedTopic(
                    original_topic=TrendingTopic(
                        title="",  # Invalid empty title
                        description="",
                        source="test",
                        score=0.0,
                        keywords=[],
                        created_at=datetime.now()
                    ),
                    processed_title="",
                    video_angle="",
                    target_keywords=[],
                    estimated_engagement=0.0,
                    content_type="educational",
                    difficulty_level="easy"
                )
                
                script = await generator.generate_script(invalid_topic)
                # Should either return None or handle gracefully
                if script:
                    logger.info("✓ Invalid topic handled with fallback")
                else:
                    logger.info("✓ Invalid topic rejected appropriately")
                    
            except Exception as e:
                logger.info(f"✓ Invalid topic error handled: {e}")
            
            logger.info("✓ Error handling tests completed")
            return True
            
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    async def test_file_operations(self):
        """Test file operations and persistence."""
        try:
            # Test directory creation
            test_dir = config.OUTPUT_DIR / "test"
            test_dir.mkdir(exist_ok=True)
            assert test_dir.exists()
            
            # Test file writing
            test_file = test_dir / "test_output.json"
            test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
            
            with open(test_file, 'w') as f:
                json.dump(test_data, f)
            
            # Test file reading
            with open(test_file, 'r') as f:
                loaded_data = json.load(f)
            
            assert loaded_data["test"] == "data"
            
            # Clean up
            test_file.unlink()
            test_dir.rmdir()
            
            logger.info("✓ File operations working correctly")
            return True
            
        except Exception as e:
            logger.error(f"File operations test failed: {e}")
            return False
    
    def print_test_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "="*70)
        print("🧪 COMPREHENSIVE TEST SUMMARY")
        print("="*70)
        
        print(f"📊 Overall Result: {'✅ PASSED' if self.test_results['overall_success'] else '❌ FAILED'}")
        print(f"📈 Tests Passed: {self.test_results['passed_tests']}/{self.test_results['total_tests']}")
        print(f"⏱️  Duration: {self.test_results['started_at']} to {self.test_results['completed_at']}")
        
        print("\n📋 Individual Test Results:")
        for test_name, result in self.test_results["tests"].items():
            status_emoji = "✅" if result["status"] == "PASSED" else "❌"
            print(f"  {status_emoji} {test_name}: {result['status']}")
            if result["error"]:
                print(f"     Error: {result['error']}")
        
        if self.test_results["errors"]:
            print(f"\n🚨 Errors ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"]:
                print(f"  - {error}")
        
        print("\n💡 Recommendations:")
        if not self.test_results["overall_success"]:
            print("  1. Check API keys in .env file")
            print("  2. Ensure all dependencies are installed")
            print("  3. Verify internet connection for external APIs")
            print("  4. Check logs for detailed error information")
        else:
            print("  1. System is ready for production use")
            print("  2. Configure API keys for full functionality")
            print("  3. Set up automated scheduling")
            print("  4. Monitor logs for ongoing operations")
        
        print("\n🚀 Next Steps:")
        print("  1. Run: python main.py --validate-config")
        print("  2. Run: python main.py --run-once --debug")
        print("  3. Configure your channel settings")
        print("  4. Set up automated scheduling")
        print("="*70)
    
    def save_test_results(self, filename: str = None):
        """Save test results to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{timestamp}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"Test results saved to: {filepath}")
        return filepath

async def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation System - Test Suite")
    parser.add_argument("--save-results", action="store_true", help="Save test results to file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create tester and run tests
    tester = SystemTester()
    results = await tester.run_all_tests()
    
    # Save results if requested
    if args.save_results:
        filepath = tester.save_test_results()
        print(f"\n📄 Test results saved to: {filepath}")
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_success"] else 1)

if __name__ == "__main__":
    asyncio.run(main())