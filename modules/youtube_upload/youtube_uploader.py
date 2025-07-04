"""
YouTube Uploader - handles video uploads to YouTube using YouTube Data API v3.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
from dataclasses import dataclass
import time

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

from config.config import config
from modules.metadata_generator.metadata_generator import VideoMetadata
from modules.video_stitching.video_stitcher import VideoProject

logger = logging.getLogger(__name__)

@dataclass
class UploadResult:
    """Result of video upload."""
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    title: str = ""
    upload_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "video_id": self.video_id,
            "video_url": self.video_url,
            "title": self.title,
            "upload_time": self.upload_time.isoformat() if self.upload_time else None,
            "error_message": self.error_message
        }

class YouTubeUploader:
    """Handles YouTube video uploads using YouTube Data API v3."""
    
    def __init__(self):
        self.youtube_service = None
        self.auth_manager = None
        self.setup_youtube_service()
        
        # Upload retry settings
        self.max_retries = 3
        self.retry_delay = 60  # seconds
        
        # Valid privacy statuses
        self.privacy_statuses = ["private", "public", "unlisted"]
        
        # YouTube Shorts requirements
        self.shorts_requirements = {
            "max_duration": 60,  # seconds
            "aspect_ratio": "vertical",  # 9:16
            "max_file_size": 256 * 1024 * 1024,  # 256MB for Shorts
            "required_tags": ["#Shorts"]
        }
    
    def setup_youtube_service(self):
        """Set up YouTube Data API service."""
        try:
            if not GOOGLE_API_AVAILABLE:
                logger.error("Google API client not available. Install google-api-python-client")
                return
            
            from .auth_manager import AuthManager
            self.auth_manager = AuthManager()
            
            credentials = self.auth_manager.get_credentials()
            if credentials:
                self.youtube_service = build('youtube', 'v3', credentials=credentials)
                logger.info("YouTube service initialized successfully")
            else:
                logger.warning("YouTube credentials not available")
                
        except Exception as e:
            logger.error(f"Failed to setup YouTube service: {e}")
    
    async def upload_video(
        self, 
        video_project: VideoProject, 
        metadata: VideoMetadata,
        schedule_time: Optional[datetime] = None
    ) -> UploadResult:
        """Upload video to YouTube."""
        if not self.youtube_service:
            return UploadResult(
                success=False,
                error_message="YouTube service not available"
            )
        
        if not video_project.video_path or not video_project.video_path.exists():
            return UploadResult(
                success=False,
                error_message="Video file not found"
            )
        
        try:
            logger.info(f"Starting upload: {metadata.title}")
            
            # Validate video for YouTube Shorts
            validation_result = await self._validate_shorts_requirements(video_project)
            if not validation_result["valid"]:
                logger.warning(f"Video validation warnings: {validation_result['warnings']}")
            
            # Prepare upload request
            request_body = self._prepare_upload_request(metadata, schedule_time)
            media_upload = MediaFileUpload(
                str(video_project.video_path),
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )
            
            # Execute upload with retries
            upload_result = await self._execute_upload_with_retry(
                request_body, media_upload, metadata.title
            )
            
            if upload_result.success and upload_result.video_id:
                # Upload thumbnail if available
                if video_project.thumbnail_path and video_project.thumbnail_path.exists():
                    await self._upload_thumbnail(upload_result.video_id, video_project.thumbnail_path)
                
                # Set as YouTube Short
                await self._mark_as_short(upload_result.video_id)
                
                logger.info(f"Upload completed successfully: {upload_result.video_url}")
            
            return upload_result
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return UploadResult(
                success=False,
                title=metadata.title,
                error_message=str(e)
            )
    
    def _prepare_upload_request(self, metadata: VideoMetadata, schedule_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Prepare YouTube upload request body."""
        # Ensure tags include #Shorts
        tags = metadata.tags.copy()
        if "shorts" not in [tag.lower() for tag in tags]:
            tags.append("Shorts")
        
        # Limit tags to 500 characters total
        tags_str = ",".join(tags)
        if len(tags_str) > 500:
            # Truncate tags to fit limit
            truncated_tags = []
            current_length = 0
            for tag in tags:
                if current_length + len(tag) + 1 <= 500:
                    truncated_tags.append(tag)
                    current_length += len(tag) + 1
                else:
                    break
            tags = truncated_tags
        
        # Privacy status
        privacy_status = metadata.privacy if metadata.privacy in self.privacy_statuses else "public"
        
        # Schedule time
        publish_at = None
        if schedule_time and privacy_status == "private":
            publish_at = schedule_time.isoformat() + "Z"
        
        request_body = {
            "snippet": {
                "title": metadata.title[:100],  # YouTube title limit
                "description": metadata.description[:5000],  # YouTube description limit
                "tags": tags,
                "categoryId": metadata.category,
                "defaultLanguage": metadata.language,
                "defaultAudioLanguage": metadata.default_audio_language
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
                "embeddable": True
            }
        }
        
        if publish_at:
            request_body["status"]["publishAt"] = publish_at
        
        return request_body
    
    async def _execute_upload_with_retry(
        self, 
        request_body: Dict[str, Any], 
        media_upload: MediaFileUpload, 
        title: str
    ) -> UploadResult:
        """Execute upload with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Upload attempt {attempt + 1}/{self.max_retries}")
                
                # Create upload request
                request = self.youtube_service.videos().insert(
                    part=",".join(request_body.keys()),
                    body=request_body,
                    media_body=media_upload
                )
                
                # Execute upload
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        logger.info(f"Upload progress: {int(status.progress() * 100)}%")
                
                # Extract video information
                video_id = response["id"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                return UploadResult(
                    success=True,
                    video_id=video_id,
                    video_url=video_url,
                    title=title,
                    upload_time=datetime.now()
                )
                
            except HttpError as e:
                last_error = e
                error_code = e.resp.status
                
                if error_code in [500, 502, 503, 504]:
                    # Temporary server errors - retry
                    logger.warning(f"Temporary error {error_code}, retrying in {self.retry_delay}s")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                else:
                    # Permanent error - don't retry
                    logger.error(f"Permanent error {error_code}: {e}")
                    break
                    
            except Exception as e:
                last_error = e
                logger.error(f"Upload attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
        
        return UploadResult(
            success=False,
            title=title,
            error_message=str(last_error) if last_error else "Upload failed after all retries"
        )
    
    async def _upload_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """Upload custom thumbnail for video."""
        try:
            if not thumbnail_path.exists():
                logger.warning(f"Thumbnail file not found: {thumbnail_path}")
                return False
            
            media_upload = MediaFileUpload(
                str(thumbnail_path),
                mimetype='image/jpeg'
            )
            
            request = self.youtube_service.thumbnails().set(
                videoId=video_id,
                media_body=media_upload
            )
            
            response = request.execute()
            logger.info(f"Thumbnail uploaded successfully for video {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Thumbnail upload failed: {e}")
            return False
    
    async def _mark_as_short(self, video_id: str) -> bool:
        """Mark video as YouTube Short."""
        try:
            # YouTube Shorts are automatically detected by YouTube based on:
            # 1. Vertical aspect ratio (9:16)
            # 2. Duration under 60 seconds
            # 3. #Shorts in title/description
            
            # We'll add #Shorts to the description if not present
            video_response = self.youtube_service.videos().list(
                part="snippet",
                id=video_id
            ).execute()
            
            if video_response["items"]:
                snippet = video_response["items"][0]["snippet"]
                description = snippet.get("description", "")
                
                # Add #Shorts hashtag if not present
                if "#Shorts" not in description and "#shorts" not in description:
                    updated_description = f"{description}\n\n#Shorts"
                    
                    # Update video description
                    self.youtube_service.videos().update(
                        part="snippet",
                        body={
                            "id": video_id,
                            "snippet": {
                                "title": snippet["title"],
                                "description": updated_description,
                                "categoryId": snippet.get("categoryId", "22"),
                                "tags": snippet.get("tags", [])
                            }
                        }
                    ).execute()
                    
                    logger.info(f"Added #Shorts to video {video_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark as Short: {e}")
            return False
    
    async def _validate_shorts_requirements(self, video_project: VideoProject) -> Dict[str, Any]:
        """Validate video meets YouTube Shorts requirements."""
        result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        try:
            # Check file exists
            if not video_project.video_path.exists():
                result["errors"].append("Video file not found")
                result["valid"] = False
                return result
            
            # Check file size
            file_size = video_project.video_path.stat().st_size
            if file_size > self.shorts_requirements["max_file_size"]:
                result["warnings"].append(f"File size ({file_size/1024/1024:.1f}MB) exceeds recommended limit for Shorts")
            
            # Check duration
            if video_project.duration > self.shorts_requirements["max_duration"]:
                result["warnings"].append(f"Duration ({video_project.duration:.1f}s) exceeds Shorts limit of 60s")
            
            # Check aspect ratio
            width, height = video_project.resolution
            aspect_ratio = width / height
            expected_ratio = 9 / 16  # 0.5625
            
            if abs(aspect_ratio - expected_ratio) > 0.1:
                result["warnings"].append(f"Aspect ratio ({aspect_ratio:.3f}) not optimal for Shorts (9:16)")
            
            return result
            
        except Exception as e:
            result["errors"].append(f"Validation failed: {e}")
            result["valid"] = False
            return result
    
    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """Get video upload and processing status."""
        try:
            response = self.youtube_service.videos().list(
                part="status,processingDetails,statistics",
                id=video_id
            ).execute()
            
            if not response["items"]:
                return {"error": "Video not found"}
            
            video = response["items"][0]
            
            return {
                "upload_status": video["status"].get("uploadStatus"),
                "privacy_status": video["status"].get("privacyStatus"),
                "processing_status": video.get("processingDetails", {}).get("processingStatus"),
                "view_count": video.get("statistics", {}).get("viewCount", 0),
                "like_count": video.get("statistics", {}).get("likeCount", 0),
                "comment_count": video.get("statistics", {}).get("commentCount", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get video status: {e}")
            return {"error": str(e)}
    
    async def update_video_metadata(self, video_id: str, metadata: VideoMetadata) -> bool:
        """Update video metadata after upload."""
        try:
            request_body = {
                "id": video_id,
                "snippet": {
                    "title": metadata.title[:100],
                    "description": metadata.description[:5000],
                    "tags": metadata.tags,
                    "categoryId": metadata.category
                }
            }
            
            self.youtube_service.videos().update(
                part="snippet",
                body=request_body
            ).execute()
            
            logger.info(f"Video metadata updated for {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update video metadata: {e}")
            return False
    
    async def delete_video(self, video_id: str) -> bool:
        """Delete video from YouTube."""
        try:
            self.youtube_service.videos().delete(id=video_id).execute()
            logger.info(f"Video {video_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete video {video_id}: {e}")
            return False
    
    async def get_channel_info(self) -> Dict[str, Any]:
        """Get authenticated channel information."""
        try:
            response = self.youtube_service.channels().list(
                part="snippet,statistics,brandingSettings",
                mine=True
            ).execute()
            
            if not response["items"]:
                return {"error": "No channel found"}
            
            channel = response["items"][0]
            
            return {
                "channel_id": channel["id"],
                "title": channel["snippet"]["title"],
                "description": channel["snippet"]["description"],
                "subscriber_count": channel["statistics"].get("subscriberCount", 0),
                "video_count": channel["statistics"].get("videoCount", 0),
                "view_count": channel["statistics"].get("viewCount", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return {"error": str(e)}
    
    async def list_uploaded_videos(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """List recently uploaded videos."""
        try:
            # Get channel's upload playlist
            channel_response = self.youtube_service.channels().list(
                part="contentDetails",
                mine=True
            ).execute()
            
            if not channel_response["items"]:
                return []
            
            upload_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get videos from upload playlist
            playlist_response = self.youtube_service.playlistItems().list(
                part="snippet",
                playlistId=upload_playlist_id,
                maxResults=max_results
            ).execute()
            
            videos = []
            for item in playlist_response["items"]:
                videos.append({
                    "video_id": item["snippet"]["resourceId"]["videoId"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "published_at": item["snippet"]["publishedAt"],
                    "thumbnail": item["snippet"]["thumbnails"]["default"]["url"]
                })
            
            return videos
            
        except Exception as e:
            logger.error(f"Failed to list videos: {e}")
            return []
    
    def save_upload_result(self, result: UploadResult, filename: str = None) -> Path:
        """Save upload result to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"upload_result_{timestamp}.json"
        
        filepath = config.OUTPUT_DIR / "metadata" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        logger.info(f"Upload result saved to: {filepath}")
        return filepath
    
    async def test_authentication(self) -> bool:
        """Test YouTube API authentication."""
        try:
            if not self.youtube_service:
                logger.error("YouTube service not available")
                return False
            
            # Simple API call to test authentication
            response = self.youtube_service.channels().list(
                part="snippet",
                mine=True
            ).execute()
            
            if response["items"]:
                channel_title = response["items"][0]["snippet"]["title"]
                logger.info(f"✅ Authentication successful for channel: {channel_title}")
                return True
            else:
                logger.error("❌ No channel found for authenticated user")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication test failed: {e}")
            return False

# Example usage and testing
async def main():
    """Test the YouTube uploader."""
    uploader = YouTubeUploader()
    
    # Test authentication
    auth_success = await uploader.test_authentication()
    print(f"Authentication test: {'✅ PASSED' if auth_success else '❌ FAILED'}")
    
    if auth_success:
        # Get channel info
        channel_info = await uploader.get_channel_info()
        print(f"Channel: {channel_info.get('title', 'Unknown')}")

if __name__ == "__main__":
    asyncio.run(main())