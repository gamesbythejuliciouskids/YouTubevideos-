"""
Script Generator - generates engaging YouTube Shorts scripts using AI.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
import openai
import anthropic
from pathlib import Path
import json
from config.config import config
from modules.trending_topics.topic_processor import ProcessedTopic

logger = logging.getLogger(__name__)

@dataclass
class GeneratedScript:
    """Generated script for YouTube Short."""
    topic: ProcessedTopic
    hook: str
    main_content: str
    call_to_action: str
    full_script: str
    word_count: int
    estimated_duration: int  # in seconds
    style: str
    generated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "topic": self.topic.to_dict(),
            "hook": self.hook,
            "main_content": self.main_content,
            "call_to_action": self.call_to_action,
            "full_script": self.full_script,
            "word_count": self.word_count,
            "estimated_duration": self.estimated_duration,
            "style": self.style,
            "generated_at": self.generated_at.isoformat()
        }

class ScriptGenerator:
    """Generates YouTube Shorts scripts using AI."""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.setup_ai_clients()
        
    def setup_ai_clients(self):
        """Set up AI clients."""
        try:
            if config.OPENAI_API_KEY:
                openai.api_key = config.OPENAI_API_KEY
                self.openai_client = openai
                logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            
        try:
            if config.ANTHROPIC_API_KEY:
                self.anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
                logger.info("Anthropic client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
    
    async def generate_script(self, topic: ProcessedTopic, style: str = "engaging") -> Optional[GeneratedScript]:
        """Generate a complete script for a topic."""
        try:
            # Generate script components
            hook = await self._generate_hook(topic, style)
            main_content = await self._generate_main_content(topic, style)
            call_to_action = await self._generate_call_to_action(topic, style)
            
            # Combine into full script
            full_script = f"{hook}\n\n{main_content}\n\n{call_to_action}"
            
            # Calculate metrics
            word_count = len(full_script.split())
            estimated_duration = self._estimate_duration(word_count)
            
            # Check if script meets requirements
            if not self._validate_script(full_script, word_count, estimated_duration):
                logger.warning(f"Generated script doesn't meet requirements for topic: {topic.processed_title}")
                return None
            
            return GeneratedScript(
                topic=topic,
                hook=hook,
                main_content=main_content,
                call_to_action=call_to_action,
                full_script=full_script,
                word_count=word_count,
                estimated_duration=estimated_duration,
                style=style,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating script for topic '{topic.processed_title}': {e}")
            return None
    
    async def _generate_hook(self, topic: ProcessedTopic, style: str) -> str:
        """Generate an engaging hook for the script."""
        prompt = self._create_hook_prompt(topic, style)
        
        try:
            # Try OpenAI first
            if self.openai_client:
                response = await self._call_openai(prompt, max_tokens=100)
                if response:
                    return response.strip()
            
            # Fallback to Anthropic
            if self.anthropic_client:
                response = await self._call_anthropic(prompt, max_tokens=100)
                if response:
                    return response.strip()
            
            # Fallback to template
            return self._generate_hook_template(topic)
            
        except Exception as e:
            logger.error(f"Error generating hook: {e}")
            return self._generate_hook_template(topic)
    
    async def _generate_main_content(self, topic: ProcessedTopic, style: str) -> str:
        """Generate main content for the script."""
        prompt = self._create_main_content_prompt(topic, style)
        
        try:
            # Try OpenAI first
            if self.openai_client:
                response = await self._call_openai(prompt, max_tokens=200)
                if response:
                    return response.strip()
            
            # Fallback to Anthropic
            if self.anthropic_client:
                response = await self._call_anthropic(prompt, max_tokens=200)
                if response:
                    return response.strip()
            
            # Fallback to template
            return self._generate_main_content_template(topic)
            
        except Exception as e:
            logger.error(f"Error generating main content: {e}")
            return self._generate_main_content_template(topic)
    
    async def _generate_call_to_action(self, topic: ProcessedTopic, style: str) -> str:
        """Generate call-to-action for the script."""
        prompt = self._create_cta_prompt(topic, style)
        
        try:
            # Try OpenAI first
            if self.openai_client:
                response = await self._call_openai(prompt, max_tokens=50)
                if response:
                    return response.strip()
            
            # Fallback to Anthropic
            if self.anthropic_client:
                response = await self._call_anthropic(prompt, max_tokens=50)
                if response:
                    return response.strip()
            
            # Fallback to template
            return self._generate_cta_template(topic)
            
        except Exception as e:
            logger.error(f"Error generating CTA: {e}")
            return self._generate_cta_template(topic)
    
    async def _call_openai(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """Call OpenAI API."""
        try:
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a YouTube Shorts script writer. Create engaging, concise content that captures viewers' attention immediately."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    async def _call_anthropic(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """Call Anthropic API."""
        try:
            message = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=max_tokens,
                temperature=0.7,
                system="You are a YouTube Shorts script writer. Create engaging, concise content that captures viewers' attention immediately.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return None
    
    def _create_hook_prompt(self, topic: ProcessedTopic, style: str) -> str:
        """Create prompt for hook generation."""
        return f"""
        Create a compelling 5-8 second hook for a YouTube Short about "{topic.processed_title}".
        
        Topic details:
        - Content type: {topic.content_type}
        - Keywords: {', '.join(topic.target_keywords[:5])}
        - Style: {style}
        
        Requirements:
        - Start with something surprising or intriguing
        - Make viewers want to keep watching
        - Keep it under 20 words
        - Use active voice
        - Create curiosity or urgency
        
        Examples of good hooks:
        - "You won't believe what scientists just discovered..."
        - "This changes everything we thought we knew about..."
        - "The shocking truth about..."
        - "Here's why everyone's talking about..."
        
        Generate only the hook, no explanations.
        """
    
    def _create_main_content_prompt(self, topic: ProcessedTopic, style: str) -> str:
        """Create prompt for main content generation."""
        return f"""
        Create the main content for a YouTube Short about "{topic.processed_title}".
        
        Topic details:
        - Content type: {topic.content_type}
        - Video angle: {topic.video_angle}
        - Keywords: {', '.join(topic.target_keywords[:5])}
        - Style: {style}
        
        Requirements:
        - 2-3 key points or facts
        - Keep each point concise (1-2 sentences)
        - Use simple, conversational language
        - Include specific details or numbers when possible
        - Make it educational and entertaining
        - Total: 35-50 words
        
        Structure:
        1. First key point/fact
        2. Second key point/fact
        3. Third key point/fact (if applicable)
        
        Generate only the main content, no explanations.
        """
    
    def _create_cta_prompt(self, topic: ProcessedTopic, style: str) -> str:
        """Create prompt for call-to-action generation."""
        return f"""
        Create a call-to-action for a YouTube Short about "{topic.processed_title}".
        
        Topic details:
        - Content type: {topic.content_type}
        - Style: {style}
        
        Requirements:
        - Encourage engagement (like, subscribe, comment)
        - Ask a question related to the topic
        - Keep it under 15 words
        - Be enthusiastic and friendly
        - Make it specific to the topic
        
        Examples:
        - "What do you think about this? Let me know in the comments!"
        - "Like if this blew your mind! What should I cover next?"
        - "Subscribe for more amazing facts like this!"
        - "Comment your thoughts below and follow for more!"
        
        Generate only the CTA, no explanations.
        """
    
    def _generate_hook_template(self, topic: ProcessedTopic) -> str:
        """Generate hook using template as fallback."""
        templates = [
            f"You won't believe what I just learned about {topic.original_topic.title}!",
            f"This will change how you think about {topic.original_topic.title}!",
            f"The shocking truth about {topic.original_topic.title}!",
            f"Here's why everyone's talking about {topic.original_topic.title}!",
            f"This {topic.original_topic.title} fact will blow your mind!"
        ]
        
        # Choose template based on content type
        if topic.content_type == "educational":
            return f"Here's what you need to know about {topic.original_topic.title}!"
        elif topic.content_type == "entertainment":
            return templates[2]  # shocking truth
        elif topic.content_type == "news":
            return templates[3]  # everyone's talking
        else:
            return templates[0]  # won't believe
    
    def _generate_main_content_template(self, topic: ProcessedTopic) -> str:
        """Generate main content using template as fallback."""
        return f"""
        First, {topic.original_topic.title} is more important than most people realize.
        
        Second, recent studies show fascinating insights about this topic.
        
        Finally, this could impact your daily life in ways you never imagined.
        """
    
    def _generate_cta_template(self, topic: ProcessedTopic) -> str:
        """Generate CTA using template as fallback."""
        cta_templates = [
            "What do you think? Drop a comment below!",
            "Like if this was helpful! Subscribe for more!",
            "Let me know your thoughts in the comments!",
            "Follow for more amazing facts like this!",
            "Share this with someone who needs to see it!"
        ]
        
        return cta_templates[0]
    
    def _estimate_duration(self, word_count: int) -> int:
        """Estimate video duration based on word count."""
        # Average speaking rate: 2.5 words per second for YouTube Shorts
        words_per_second = 2.5
        return int(word_count / words_per_second)
    
    def _validate_script(self, script: str, word_count: int, duration: int) -> bool:
        """Validate that script meets requirements."""
        # Check word count
        if word_count > config.SCRIPT_MAX_WORDS:
            logger.warning(f"Script too long: {word_count} words (max: {config.SCRIPT_MAX_WORDS})")
            return False
        
        # Check duration
        if duration > config.VIDEO_DURATION_SECONDS:
            logger.warning(f"Script too long: {duration} seconds (max: {config.VIDEO_DURATION_SECONDS})")
            return False
        
        # Check minimum length
        if word_count < 20:
            logger.warning(f"Script too short: {word_count} words")
            return False
        
        # Check for basic structure
        if not script or len(script.strip()) < 50:
            logger.warning("Script too short or empty")
            return False
        
        return True
    
    def save_script(self, script: GeneratedScript, filename: str = None) -> Path:
        """Save generated script to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"script_{timestamp}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(script.to_dict(), f, indent=2)
        
        logger.info(f"Saved script to {filepath}")
        return filepath
    
    def load_script(self, filepath: Path) -> GeneratedScript:
        """Load script from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct objects
        from modules.trending_topics.topic_processor import ProcessedTopic
        from modules.trending_topics.trending_fetcher import TrendingTopic
        
        # This is a simplified reconstruction - in practice, you'd want more robust deserialization
        topic_data = data['topic']
        original_topic = TrendingTopic(
            title=topic_data['original_topic']['title'],
            description=topic_data['original_topic']['description'],
            source=topic_data['original_topic']['source'],
            score=topic_data['original_topic']['score'],
            keywords=topic_data['original_topic']['keywords'],
            url=topic_data['original_topic'].get('url'),
            created_at=datetime.fromisoformat(topic_data['original_topic']['created_at']) if topic_data['original_topic'].get('created_at') else None
        )
        
        processed_topic = ProcessedTopic(
            original_topic=original_topic,
            processed_title=topic_data['processed_title'],
            video_angle=topic_data['video_angle'],
            target_keywords=topic_data['target_keywords'],
            estimated_engagement=topic_data['estimated_engagement'],
            content_type=topic_data['content_type'],
            difficulty_level=topic_data['difficulty_level']
        )
        
        return GeneratedScript(
            topic=processed_topic,
            hook=data['hook'],
            main_content=data['main_content'],
            call_to_action=data['call_to_action'],
            full_script=data['full_script'],
            word_count=data['word_count'],
            estimated_duration=data['estimated_duration'],
            style=data['style'],
            generated_at=datetime.fromisoformat(data['generated_at'])
        )
    
    async def generate_multiple_scripts(self, topics: List[ProcessedTopic], style: str = "engaging") -> List[GeneratedScript]:
        """Generate scripts for multiple topics."""
        scripts = []
        
        # Generate scripts concurrently
        tasks = []
        for topic in topics:
            task = self.generate_script(topic, style)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, GeneratedScript):
                scripts.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error generating script: {result}")
        
        return scripts
    
    def optimize_script_for_engagement(self, script: GeneratedScript) -> GeneratedScript:
        """Optimize script for better engagement."""
        # Add engagement-boosting elements
        optimized_hook = self._add_urgency_to_hook(script.hook)
        optimized_main = self._add_specificity_to_main(script.main_content)
        optimized_cta = self._strengthen_cta(script.call_to_action)
        
        # Reconstruct full script
        full_script = f"{optimized_hook}\n\n{optimized_main}\n\n{optimized_cta}"
        word_count = len(full_script.split())
        estimated_duration = self._estimate_duration(word_count)
        
        return GeneratedScript(
            topic=script.topic,
            hook=optimized_hook,
            main_content=optimized_main,
            call_to_action=optimized_cta,
            full_script=full_script,
            word_count=word_count,
            estimated_duration=estimated_duration,
            style=script.style + "_optimized",
            generated_at=datetime.now()
        )
    
    def _add_urgency_to_hook(self, hook: str) -> str:
        """Add urgency elements to hook."""
        urgency_words = ["just", "now", "today", "right now", "immediately"]
        
        if not any(word in hook.lower() for word in urgency_words):
            return f"Right now, {hook.lower()}"
        
        return hook
    
    def _add_specificity_to_main(self, main_content: str) -> str:
        """Add specific details to main content."""
        # This is a simplified version - in practice, you'd use more sophisticated NLP
        return main_content.replace("recent studies", "a 2024 study").replace("scientists", "researchers at MIT")
    
    def _strengthen_cta(self, cta: str) -> str:
        """Strengthen call-to-action."""
        if "comment" in cta.lower():
            return cta + " I read every single one!"
        elif "subscribe" in cta.lower():
            return cta + " You won't regret it!"
        else:
            return cta + " Your engagement means everything!"

# Example usage and testing
async def main():
    """Test the script generator."""
    # This would be called with actual processed topics
    pass

if __name__ == "__main__":
    asyncio.run(main())