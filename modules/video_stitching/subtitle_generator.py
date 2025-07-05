"""
Subtitle Generator - generates SRT subtitle files for videos.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import re
from dataclasses import dataclass

from config.config import config
from modules.script_generation.script_generator import GeneratedScript

logger = logging.getLogger(__name__)

@dataclass
class SubtitleSegment:
    """Individual subtitle segment."""
    index: int
    start_time: timedelta
    end_time: timedelta
    text: str
    
    def to_srt_format(self) -> str:
        """Convert to SRT format."""
        start_str = self._timedelta_to_srt_time(self.start_time)
        end_str = self._timedelta_to_srt_time(self.end_time)
        
        return f"{self.index}\n{start_str} --> {end_str}\n{self.text}\n"
    
    def _timedelta_to_srt_time(self, td: timedelta) -> str:
        """Convert timedelta to SRT time format."""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = int(td.microseconds / 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

class SubtitleGenerator:
    """Generates subtitle files for videos."""
    
    def __init__(self):
        self.words_per_second = 2.5  # Average speaking rate
        self.max_chars_per_line = 40
        self.max_lines_per_subtitle = 2
        
    async def generate_subtitles(
        self, 
        script: GeneratedScript, 
        duration: float,
        style: str = "word_by_word"
    ) -> Optional[Path]:
        """Generate subtitle file from script."""
        try:
            if style == "word_by_word":
                segments = self._create_word_by_word_subtitles(script, duration)
            elif style == "sentence_by_sentence":
                segments = self._create_sentence_subtitles(script, duration)
            elif style == "phrase_by_phrase":
                segments = self._create_phrase_subtitles(script, duration)
            else:
                logger.warning(f"Unknown subtitle style: {style}, using word_by_word")
                segments = self._create_word_by_word_subtitles(script, duration)
            
            if not segments:
                logger.warning("No subtitle segments generated")
                return None
            
            # Save to SRT file
            return self._save_srt_file(segments, script.topic.processed_title)
            
        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}")
            return None
    
    def _create_word_by_word_subtitles(
        self, 
        script: GeneratedScript, 
        duration: float
    ) -> List[SubtitleSegment]:
        """Create word-by-word subtitles."""
        words = self._extract_words(script.full_script)
        segments = []
        
        if not words:
            return segments
        
        # Calculate timing
        time_per_word = duration / len(words)
        
        for i, word in enumerate(words):
            start_time = timedelta(seconds=i * time_per_word)
            end_time = timedelta(seconds=(i + 1) * time_per_word)
            
            segment = SubtitleSegment(
                index=i + 1,
                start_time=start_time,
                end_time=end_time,
                text=word.upper()  # YouTube Shorts style
            )
            segments.append(segment)
        
        return segments
    
    def _create_sentence_subtitles(
        self, 
        script: GeneratedScript, 
        duration: float
    ) -> List[SubtitleSegment]:
        """Create sentence-by-sentence subtitles."""
        sentences = self._extract_sentences(script.full_script)
        segments = []
        
        if not sentences:
            return segments
        
        # Calculate timing
        time_per_sentence = duration / len(sentences)
        
        for i, sentence in enumerate(sentences):
            start_time = timedelta(seconds=i * time_per_sentence)
            end_time = timedelta(seconds=(i + 1) * time_per_sentence)
            
            # Split long sentences into multiple lines
            lines = self._split_text_into_lines(sentence)
            
            segment = SubtitleSegment(
                index=i + 1,
                start_time=start_time,
                end_time=end_time,
                text="\n".join(lines)
            )
            segments.append(segment)
        
        return segments
    
    def _create_phrase_subtitles(
        self, 
        script: GeneratedScript, 
        duration: float
    ) -> List[SubtitleSegment]:
        """Create phrase-by-phrase subtitles."""
        phrases = self._extract_phrases(script.full_script)
        segments = []
        
        if not phrases:
            return segments
        
        # Calculate timing based on phrase length
        total_chars = sum(len(phrase) for phrase in phrases)
        
        current_time = 0.0
        
        for i, phrase in enumerate(phrases):
            # Calculate duration based on phrase length
            phrase_duration = (len(phrase) / total_chars) * duration
            phrase_duration = max(1.0, phrase_duration)  # Minimum 1 second
            
            start_time = timedelta(seconds=current_time)
            end_time = timedelta(seconds=current_time + phrase_duration)
            
            # Split phrase into lines if needed
            lines = self._split_text_into_lines(phrase)
            
            segment = SubtitleSegment(
                index=i + 1,
                start_time=start_time,
                end_time=end_time,
                text="\n".join(lines)
            )
            segments.append(segment)
            
            current_time += phrase_duration
        
        return segments
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text."""
        # Remove punctuation and split into words
        cleaned_text = re.sub(r'[^\w\s]', '', text)
        words = cleaned_text.split()
        return [word for word in words if word.strip()]
    
    def _extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text."""
        # Split by sentence-ending punctuation
        sentences = re.split(r'[.!?]+', text)
        return [sentence.strip() for sentence in sentences if sentence.strip()]
    
    def _extract_phrases(self, text: str) -> List[str]:
        """Extract phrases from text."""
        # Split by commas, semicolons, and other phrase delimiters
        phrases = re.split(r'[,.;:]+', text)
        return [phrase.strip() for phrase in phrases if phrase.strip()]
    
    def _split_text_into_lines(self, text: str) -> List[str]:
        """Split text into lines for subtitles."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            # Check if adding this word would exceed line length
            if current_length + len(word) + 1 > self.max_chars_per_line and current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word) + (1 if current_line else 0)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Limit to max lines per subtitle
        if len(lines) > self.max_lines_per_subtitle:
            # Combine lines if too many
            combined_lines = []
            for i in range(0, len(lines), self.max_lines_per_subtitle):
                combined_text = ' '.join(lines[i:i + self.max_lines_per_subtitle])
                combined_lines.append(combined_text)
            return combined_lines[:self.max_lines_per_subtitle]
        
        return lines
    
    def _save_srt_file(self, segments: List[SubtitleSegment], title: str) -> Path:
        """Save segments to SRT file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"subtitles_{timestamp}.srt"
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for segment in segments:
                f.write(segment.to_srt_format())
                f.write('\n')  # Empty line between segments
        
        logger.info(f"Saved subtitle file: {filepath}")
        return filepath
    
    def create_youtube_shorts_style_subtitles(
        self, 
        script: GeneratedScript, 
        duration: float
    ) -> Optional[Path]:
        """Create YouTube Shorts style subtitles (large, centered, animated)."""
        try:
            # Create word-by-word subtitles with styling
            words = self._extract_words(script.full_script)
            segments = []
            
            if not words:
                return None
            
            # Calculate timing for dynamic appearance
            time_per_word = duration / len(words)
            
            for i, word in enumerate(words):
                start_time = timedelta(seconds=i * time_per_word)
                end_time = timedelta(seconds=(i + 1) * time_per_word)
                
                # Style the word for YouTube Shorts
                styled_text = self._style_word_for_shorts(word, i)
                
                segment = SubtitleSegment(
                    index=i + 1,
                    start_time=start_time,
                    end_time=end_time,
                    text=styled_text
                )
                segments.append(segment)
            
            return self._save_srt_file(segments, f"{script.topic.processed_title}_shorts")
            
        except Exception as e:
            logger.error(f"YouTube Shorts subtitle creation failed: {e}")
            return None
    
    def _style_word_for_shorts(self, word: str, index: int) -> str:
        """Style word for YouTube Shorts format."""
        # Emphasize certain words
        emphasis_words = ['amazing', 'incredible', 'shocking', 'unbelievable', 'wow', 'never']
        
        if word.lower() in emphasis_words:
            return f"✨ {word.upper()} ✨"
        elif index == 0:  # First word
            return f"🎯 {word.upper()}"
        else:
            return word.upper()
    
    def create_multilingual_subtitles(
        self, 
        script: GeneratedScript, 
        duration: float,
        languages: List[str] = ['en', 'es', 'fr']
    ) -> Dict[str, Optional[Path]]:
        """Create subtitles in multiple languages."""
        subtitle_files = {}
        
        for lang in languages:
            try:
                # For now, we'll just create subtitles in the original language
                # In a full implementation, you'd use translation APIs
                if lang == 'en':
                    subtitle_file = self.generate_subtitles(script, duration)
                    subtitle_files[lang] = subtitle_file
                else:
                    # Placeholder for translation
                    logger.info(f"Translation to {lang} not yet implemented")
                    subtitle_files[lang] = None
                    
            except Exception as e:
                logger.error(f"Failed to create {lang} subtitles: {e}")
                subtitle_files[lang] = None
        
        return subtitle_files
    
    def create_accessibility_subtitles(
        self, 
        script: GeneratedScript, 
        duration: float
    ) -> Optional[Path]:
        """Create accessibility-focused subtitles with sound descriptions."""
        try:
            sentences = self._extract_sentences(script.full_script)
            segments = []
            
            if not sentences:
                return None
            
            time_per_sentence = duration / len(sentences)
            
            for i, sentence in enumerate(sentences):
                start_time = timedelta(seconds=i * time_per_sentence)
                end_time = timedelta(seconds=(i + 1) * time_per_sentence)
                
                # Add accessibility information
                if i == 0:
                    text = f"[Narrator speaking] {sentence}"
                else:
                    text = sentence
                
                # Add sound descriptions for different content types
                if script.topic.content_type == "entertainment":
                    if i == len(sentences) - 1:
                        text += " [Upbeat music continues]"
                elif script.topic.content_type == "educational":
                    if i == 0:
                        text = f"[Educational content] {text}"
                
                lines = self._split_text_into_lines(text)
                
                segment = SubtitleSegment(
                    index=i + 1,
                    start_time=start_time,
                    end_time=end_time,
                    text="\n".join(lines)
                )
                segments.append(segment)
            
            return self._save_srt_file(segments, f"{script.topic.processed_title}_accessibility")
            
        except Exception as e:
            logger.error(f"Accessibility subtitle creation failed: {e}")
            return None
    
    def create_karaoke_style_subtitles(
        self, 
        script: GeneratedScript, 
        duration: float
    ) -> Optional[Path]:
        """Create karaoke-style subtitles with word highlighting."""
        try:
            words = self._extract_words(script.full_script)
            segments = []
            
            if not words:
                return None
            
            # Group words into phrases for better readability
            phrase_size = 3  # Words per phrase
            phrases = []
            
            for i in range(0, len(words), phrase_size):
                phrase = words[i:i + phrase_size]
                phrases.append(phrase)
            
            time_per_phrase = duration / len(phrases)
            
            for i, phrase in enumerate(phrases):
                start_time = timedelta(seconds=i * time_per_phrase)
                end_time = timedelta(seconds=(i + 1) * time_per_phrase)
                
                # Create karaoke-style text with highlighting
                phrase_text = ' '.join(phrase).upper()
                
                segment = SubtitleSegment(
                    index=i + 1,
                    start_time=start_time,
                    end_time=end_time,
                    text=phrase_text
                )
                segments.append(segment)
            
            return self._save_srt_file(segments, f"{script.topic.processed_title}_karaoke")
            
        except Exception as e:
            logger.error(f"Karaoke subtitle creation failed: {e}")
            return None
    
    def validate_subtitle_timing(self, segments: List[SubtitleSegment]) -> bool:
        """Validate subtitle timing for overlaps and gaps."""
        for i in range(len(segments) - 1):
            current = segments[i]
            next_segment = segments[i + 1]
            
            # Check for overlaps
            if current.end_time > next_segment.start_time:
                logger.warning(f"Subtitle overlap detected between segments {current.index} and {next_segment.index}")
                return False
            
            # Check for large gaps (>2 seconds)
            gap = next_segment.start_time - current.end_time
            if gap.total_seconds() > 2.0:
                logger.warning(f"Large gap ({gap.total_seconds():.1f}s) between segments {current.index} and {next_segment.index}")
        
        return True
    
    def optimize_subtitle_timing(self, segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
        """Optimize subtitle timing to remove overlaps and large gaps."""
        optimized = []
        
        for i, segment in enumerate(segments):
            if i == 0:
                optimized.append(segment)
                continue
            
            prev_segment = optimized[-1]
            
            # Adjust start time to avoid overlap
            if segment.start_time <= prev_segment.end_time:
                segment.start_time = prev_segment.end_time + timedelta(milliseconds=100)
            
            # Ensure minimum duration
            min_duration = timedelta(seconds=0.5)
            if segment.end_time - segment.start_time < min_duration:
                segment.end_time = segment.start_time + min_duration
            
            optimized.append(segment)
        
        return optimized

# Example usage
def main():
    """Test subtitle generation."""
    generator = SubtitleGenerator()
    print("Subtitle generator initialized")
    print(f"Words per second: {generator.words_per_second}")
    print(f"Max chars per line: {generator.max_chars_per_line}")

if __name__ == "__main__":
    main()