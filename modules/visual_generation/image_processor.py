"""
Image Processor - advanced image processing for YouTube Shorts visuals.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import json
from datetime import datetime
import random
import colorsys

from config.config import config

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Advanced image processing for YouTube Shorts."""
    
    def __init__(self):
        self.filters = self._load_filter_presets()
        
    def _load_filter_presets(self) -> Dict[str, Dict[str, Any]]:
        """Load filter presets for different content types."""
        return {
            "educational": {
                "brightness": 1.1,
                "contrast": 1.2,
                "saturation": 0.9,
                "sharpness": 1.1,
                "blur": 0,
                "overlay_color": (50, 100, 150, 50),
                "vignette": 0.3
            },
            "entertainment": {
                "brightness": 1.2,
                "contrast": 1.3,
                "saturation": 1.4,
                "sharpness": 1.2,
                "blur": 0,
                "overlay_color": (255, 100, 50, 40),
                "vignette": 0.2
            },
            "news": {
                "brightness": 1.0,
                "contrast": 1.1,
                "saturation": 0.8,
                "sharpness": 1.0,
                "blur": 0,
                "overlay_color": (30, 50, 100, 60),
                "vignette": 0.4
            },
            "lifestyle": {
                "brightness": 1.15,
                "contrast": 1.1,
                "saturation": 1.2,
                "sharpness": 1.0,
                "blur": 0,
                "overlay_color": (200, 150, 100, 30),
                "vignette": 0.1
            },
            "technology": {
                "brightness": 1.0,
                "contrast": 1.3,
                "saturation": 1.1,
                "sharpness": 1.3,
                "blur": 0,
                "overlay_color": (0, 150, 255, 40),
                "vignette": 0.3
            },
            "health": {
                "brightness": 1.1,
                "contrast": 1.1,
                "saturation": 1.0,
                "sharpness": 1.0,
                "blur": 0,
                "overlay_color": (100, 200, 100, 35),
                "vignette": 0.2
            },
            "science": {
                "brightness": 1.05,
                "contrast": 1.2,
                "saturation": 0.9,
                "sharpness": 1.2,
                "blur": 0,
                "overlay_color": (100, 50, 200, 45),
                "vignette": 0.35
            }
        }
    
    def apply_content_filter(self, image_path: Path, content_type: str) -> Path:
        """Apply content-type specific filter to image."""
        try:
            # Load image
            image = Image.open(image_path).convert('RGB')
            
            # Get filter settings
            filter_settings = self.filters.get(content_type, self.filters["educational"])
            
            # Apply enhancements
            image = self._apply_enhancements(image, filter_settings)
            
            # Apply overlay
            if filter_settings.get("overlay_color"):
                image = self._apply_color_overlay(image, filter_settings["overlay_color"])
            
            # Apply vignette
            if filter_settings.get("vignette", 0) > 0:
                image = self._apply_vignette(image, filter_settings["vignette"])
            
            # Save processed image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"filtered_{content_type}_{timestamp}.jpg"
            output_path = config.OUTPUT_DIR / "images" / filename
            
            image.save(output_path, 'JPEG', quality=90, optimize=True)
            
            logger.info(f"Applied {content_type} filter to {image_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Filter application failed: {e}")
            return image_path
    
    def _apply_enhancements(self, image: Image.Image, settings: Dict[str, Any]) -> Image.Image:
        """Apply basic enhancements to image."""
        # Brightness
        if settings.get("brightness", 1.0) != 1.0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(settings["brightness"])
        
        # Contrast
        if settings.get("contrast", 1.0) != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(settings["contrast"])
        
        # Color saturation
        if settings.get("saturation", 1.0) != 1.0:
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(settings["saturation"])
        
        # Sharpness
        if settings.get("sharpness", 1.0) != 1.0:
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(settings["sharpness"])
        
        # Blur
        if settings.get("blur", 0) > 0:
            image = image.filter(ImageFilter.GaussianBlur(radius=settings["blur"]))
        
        return image
    
    def _apply_color_overlay(self, image: Image.Image, overlay_color: Tuple[int, int, int, int]) -> Image.Image:
        """Apply color overlay to image."""
        try:
            # Create overlay
            overlay = Image.new('RGBA', image.size, overlay_color)
            
            # Convert image to RGBA
            image_rgba = image.convert('RGBA')
            
            # Blend overlay with image
            blended = Image.alpha_composite(image_rgba, overlay)
            
            return blended.convert('RGB')
            
        except Exception as e:
            logger.error(f"Color overlay failed: {e}")
            return image
    
    def _apply_vignette(self, image: Image.Image, intensity: float) -> Image.Image:
        """Apply vignette effect to image."""
        try:
            width, height = image.size
            
            # Create vignette mask
            mask = Image.new('L', (width, height), 255)
            mask_draw = ImageDraw.Draw(mask)
            
            # Calculate vignette parameters
            center_x, center_y = width // 2, height // 2
            max_distance = min(width, height) // 2
            
            # Create radial gradient
            for y in range(height):
                for x in range(width):
                    distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                    if distance > max_distance:
                        distance = max_distance
                    
                    # Calculate vignette strength
                    vignette_strength = 1 - (distance / max_distance * intensity)
                    vignette_strength = max(0, min(1, vignette_strength))
                    
                    # Set pixel value
                    pixel_value = int(255 * vignette_strength)
                    mask.putpixel((x, y), pixel_value)
            
            # Apply vignette
            image_rgba = image.convert('RGBA')
            image_rgba.putalpha(mask)
            
            # Create background
            background = Image.new('RGB', image.size, (0, 0, 0))
            result = Image.alpha_composite(background.convert('RGBA'), image_rgba)
            
            return result.convert('RGB')
            
        except Exception as e:
            logger.error(f"Vignette application failed: {e}")
            return image
    
    def add_text_overlay(
        self, 
        image_path: Path, 
        text: str, 
        position: str = "bottom",
        font_size: int = 48,
        text_color: Tuple[int, int, int] = (255, 255, 255),
        background_color: Optional[Tuple[int, int, int, int]] = None,
        padding: int = 20
    ) -> Path:
        """Add text overlay to image."""
        try:
            # Load image
            image = Image.open(image_path).convert('RGBA')
            
            # Create drawing context
            draw = ImageDraw.Draw(image)
            
            # Load font (fallback to default)
            try:
                font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Calculate text dimensions
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate position
            image_width, image_height = image.size
            
            if position == "top":
                x = (image_width - text_width) // 2
                y = padding
            elif position == "bottom":
                x = (image_width - text_width) // 2
                y = image_height - text_height - padding
            elif position == "center":
                x = (image_width - text_width) // 2
                y = (image_height - text_height) // 2
            else:
                x, y = padding, padding
            
            # Add background rectangle if specified
            if background_color:
                rect_x1 = x - padding
                rect_y1 = y - padding // 2
                rect_x2 = x + text_width + padding
                rect_y2 = y + text_height + padding // 2
                
                draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=background_color)
            
            # Add text with shadow
            shadow_offset = 2
            draw.text((x + shadow_offset, y + shadow_offset), text, fill=(0, 0, 0, 128), font=font)
            draw.text((x, y), text, fill=text_color, font=font)
            
            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"text_overlay_{timestamp}.png"
            output_path = config.OUTPUT_DIR / "images" / filename
            
            image.save(output_path, 'PNG')
            
            logger.info(f"Added text overlay to {image_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Text overlay failed: {e}")
            return image_path
    
    def create_thumbnail(
        self, 
        image_path: Path, 
        title: str, 
        content_type: str = "educational"
    ) -> Path:
        """Create YouTube thumbnail from image."""
        try:
            # Load and resize image
            image = Image.open(image_path).convert('RGB')
            
            # YouTube thumbnail size (16:9 aspect ratio)
            thumb_width, thumb_height = 1280, 720
            
            # Resize and crop image
            image = self._resize_and_crop(image, thumb_width, thumb_height)
            
            # Apply dramatic filter for thumbnail
            image = self._apply_thumbnail_filter(image, content_type)
            
            # Add title overlay
            image = self._add_thumbnail_title(image, title, content_type)
            
            # Save thumbnail
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"thumbnail_{content_type}_{timestamp}.jpg"
            output_path = config.OUTPUT_DIR / "images" / filename
            
            image.save(output_path, 'JPEG', quality=95)
            
            logger.info(f"Created thumbnail: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Thumbnail creation failed: {e}")
            return image_path
    
    def _resize_and_crop(self, image: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """Resize and crop image to target dimensions."""
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
        
        return image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    def _apply_thumbnail_filter(self, image: Image.Image, content_type: str) -> Image.Image:
        """Apply dramatic filter for thumbnail."""
        # Enhanced version of content filter for thumbnails
        base_filter = self.filters.get(content_type, self.filters["educational"])
        
        # Make filter more dramatic for thumbnails
        enhanced_filter = {
            "brightness": base_filter["brightness"] + 0.1,
            "contrast": base_filter["contrast"] + 0.2,
            "saturation": base_filter["saturation"] + 0.3,
            "sharpness": base_filter["sharpness"] + 0.1
        }
        
        return self._apply_enhancements(image, enhanced_filter)
    
    def _add_thumbnail_title(self, image: Image.Image, title: str, content_type: str) -> Image.Image:
        """Add title text to thumbnail."""
        try:
            # Convert to RGBA for text overlay
            image_rgba = image.convert('RGBA')
            
            # Create text overlay
            overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Load font
            font = ImageFont.load_default()
            
            # Split title into lines
            words = title.split()
            lines = []
            current_line = []
            
            for word in words:
                current_line.append(word)
                line_text = ' '.join(current_line).upper()
                bbox = draw.textbbox((0, 0), line_text, font=font)
                if bbox[2] - bbox[0] > image.width - 100:  # Leave margin
                    current_line.pop()
                    lines.append(' '.join(current_line).upper())
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line).upper())
            
            # Limit to 3 lines max
            lines = lines[:3]
            
            # Color scheme based on content type
            color_schemes = {
                "educational": {"text": (255, 255, 255), "bg": (50, 100, 150, 200)},
                "entertainment": {"text": (255, 255, 255), "bg": (255, 100, 50, 200)},
                "news": {"text": (255, 255, 255), "bg": (200, 50, 50, 200)},
                "lifestyle": {"text": (255, 255, 255), "bg": (200, 150, 100, 200)},
                "technology": {"text": (255, 255, 255), "bg": (50, 150, 255, 200)},
                "health": {"text": (255, 255, 255), "bg": (100, 200, 100, 200)},
                "science": {"text": (255, 255, 255), "bg": (150, 100, 255, 200)}
            }
            
            colors = color_schemes.get(content_type, color_schemes["educational"])
            
            # Calculate total text height
            line_height = 60
            total_height = len(lines) * line_height
            start_y = (image.height - total_height) // 2
            
            # Draw background rectangles and text
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = (image.width - text_width) // 2
                y = start_y + i * line_height
                
                # Background rectangle
                rect_padding = 10
                rect_x1 = x - rect_padding
                rect_y1 = y - rect_padding
                rect_x2 = x + text_width + rect_padding
                rect_y2 = y + text_height + rect_padding
                
                draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=colors["bg"])
                
                # Text with shadow
                draw.text((x + 3, y + 3), line, fill=(0, 0, 0, 150), font=font)
                draw.text((x, y), line, fill=colors["text"], font=font)
            
            # Combine with original image
            result = Image.alpha_composite(image_rgba, overlay)
            return result.convert('RGB')
            
        except Exception as e:
            logger.error(f"Thumbnail title overlay failed: {e}")
            return image
    
    def apply_vintage_filter(self, image_path: Path) -> Path:
        """Apply vintage/retro filter to image."""
        try:
            image = Image.open(image_path).convert('RGB')
            
            # Vintage color grading
            # Reduce blue channel
            r, g, b = image.split()
            
            # Apply curves to channels
            r = r.point(lambda x: min(255, int(x * 1.1 + 20)))  # Boost reds
            g = g.point(lambda x: min(255, int(x * 1.05 + 10)))  # Slight green boost
            b = b.point(lambda x: max(0, int(x * 0.8 - 10)))    # Reduce blues
            
            image = Image.merge('RGB', (r, g, b))
            
            # Add slight blur for softness
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # Reduce saturation
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(0.8)
            
            # Add vignette
            image = self._apply_vignette(image, 0.4)
            
            # Save vintage image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vintage_{timestamp}.jpg"
            output_path = config.OUTPUT_DIR / "images" / filename
            
            image.save(output_path, 'JPEG', quality=85)
            
            logger.info(f"Applied vintage filter to {image_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Vintage filter failed: {e}")
            return image_path
    
    def create_collage(self, image_paths: List[Path], layout: str = "grid") -> Path:
        """Create collage from multiple images."""
        try:
            if not image_paths:
                raise ValueError("No images provided for collage")
            
            # Load images
            images = []
            for path in image_paths:
                img = Image.open(path).convert('RGB')
                images.append(img)
            
            # Calculate collage dimensions
            if layout == "grid":
                cols = 2 if len(images) <= 4 else 3
                rows = (len(images) + cols - 1) // cols
            else:  # horizontal
                cols = len(images)
                rows = 1
            
            # Calculate cell size (YouTube Shorts format)
            target_width, target_height = 720, 1280
            cell_width = target_width // cols
            cell_height = target_height // rows
            
            # Create collage canvas
            collage = Image.new('RGB', (target_width, target_height), (255, 255, 255))
            
            # Place images
            for i, img in enumerate(images):
                if i >= cols * rows:
                    break
                
                row = i // cols
                col = i % cols
                
                # Resize image to fit cell
                img_resized = img.resize((cell_width, cell_height), Image.Resampling.LANCZOS)
                
                # Calculate position
                x = col * cell_width
                y = row * cell_height
                
                # Paste image
                collage.paste(img_resized, (x, y))
            
            # Save collage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"collage_{layout}_{timestamp}.jpg"
            output_path = config.OUTPUT_DIR / "images" / filename
            
            collage.save(output_path, 'JPEG', quality=90)
            
            logger.info(f"Created {layout} collage: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Collage creation failed: {e}")
            return image_paths[0] if image_paths else Path()
    
    def optimize_for_platform(self, image_path: Path, platform: str = "youtube_shorts") -> Path:
        """Optimize image for specific platform."""
        try:
            image = Image.open(image_path).convert('RGB')
            
            if platform == "youtube_shorts":
                # 9:16 aspect ratio, 720x1280
                image = self._resize_and_crop(image, 720, 1280)
            elif platform == "youtube_thumbnail":
                # 16:9 aspect ratio, 1280x720
                image = self._resize_and_crop(image, 1280, 720)
            elif platform == "instagram_story":
                # 9:16 aspect ratio, 1080x1920
                image = self._resize_and_crop(image, 1080, 1920)
            elif platform == "tiktok":
                # 9:16 aspect ratio, 1080x1920
                image = self._resize_and_crop(image, 1080, 1920)
            
            # Save optimized image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"optimized_{platform}_{timestamp}.jpg"
            output_path = config.OUTPUT_DIR / "images" / filename
            
            # Platform-specific quality settings
            quality = 95 if platform.endswith("thumbnail") else 90
            image.save(output_path, 'JPEG', quality=quality, optimize=True)
            
            logger.info(f"Optimized image for {platform}: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Platform optimization failed: {e}")
            return image_path

# Example usage
def main():
    """Test image processing functions."""
    processor = ImageProcessor()
    print("Image processor initialized")
    print(f"Available filters: {list(processor.filters.keys())}")

if __name__ == "__main__":
    main()