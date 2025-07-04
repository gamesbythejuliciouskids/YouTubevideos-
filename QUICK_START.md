# 🚀 Quick Start Guide - YouTube Shorts Automation

Get your automated YouTube Shorts system running in **5 minutes**!

## 📋 Prerequisites

- Python 3.8+
- ffmpeg installed
- Google Cloud Console account (for YouTube API)
- API keys for content sources

## ⚡ 5-Minute Setup

### 1. Clone & Install (1 minute)
```bash
git clone <repository>
cd youtube-shorts-automation
pip install -r requirements.txt
```

### 2. Basic Configuration (2 minutes)
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys (minimum required)
nano .env
```

**Essential API Keys:**
```bash
# YouTube API (required for uploads)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Content APIs (at least one required)
PEXELS_API_KEY=your_pexels_key      # Free: 200 requests/hour
OPENAI_API_KEY=your_openai_key      # Paid: $0.002/1K tokens

# Optional but recommended
ELEVENLABS_API_KEY=your_elevenlabs_key  # Better voice quality
```

### 3. Setup YouTube Authentication (1 minute)
```bash
python -c "from modules.youtube_upload.auth_manager import setup_youtube_auth; setup_youtube_auth()"
```
Follow the browser prompts to authorize your YouTube channel.

### 4. Test the System (1 minute)
```bash
# Test all components
python main.py --test

# Run one complete video generation
python main.py --run-once --debug
```

## 🎯 Production Setup

### Environment Variables
Add these to your `.env` file for full functionality:

```bash
# Core Configuration
CHANNEL_NAME=YourChannelName
CONTENT_TYPES=educational,technology,science
OUTPUT_DIR=/app/output
LOG_LEVEL=INFO

# API Keys - Content Sources
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
ELEVENLABS_API_KEY=your_elevenlabs_key
PEXELS_API_KEY=your_pexels_key
UNSPLASH_ACCESS_KEY=your_unsplash_key

# API Keys - Trending Topics
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
TWITTER_BEARER_TOKEN=your_twitter_token

# Video Configuration
VIDEO_RESOLUTION_WIDTH=720
VIDEO_RESOLUTION_HEIGHT=1280
VIDEO_RESOLUTION_FPS=30
```

### Docker Deployment (Recommended)
```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

## 🔑 Getting API Keys

### Required APIs

1. **YouTube Data API v3** (Free)
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create project → Enable YouTube Data API v3
   - Create OAuth2 credentials
   - Download client secret JSON

2. **Pexels API** (Free)
   - Sign up at [Pexels](https://www.pexels.com/api/)
   - Get free API key (200 requests/hour)

### Optional APIs (Enhanced Quality)

3. **OpenAI API** (Paid - ~$2/video)
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Add billing, get API key

4. **ElevenLabs API** (Paid - ~$1/video)
   - Sign up at [ElevenLabs](https://elevenlabs.io/)
   - Subscribe to plan, get API key

## 🎬 Usage Examples

### Generate Single Video
```bash
python main.py --run-once
```

### Test Mode (No Upload)
```bash
python main.py --run-once --debug
```

### Validate Setup
```bash
python main.py --validate-config
```

### Module Testing
```bash
python main.py --test
```

## 📁 Output Structure

After running, you'll find:
```
output/
├── videos/          # Final MP4 files
├── audio/           # Generated voiceovers
├── images/          # Downloaded/generated visuals
├── metadata/        # Video metadata & results
└── logs/           # System logs
```

## 🔧 Troubleshooting

### Common Issues

**"ffmpeg not found"**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/
```

**"No API key configured"**
```bash
# Check .env file exists and has correct keys
cat .env | grep API_KEY
```

**"YouTube authentication failed"**
```bash
# Re-run authentication setup
python -c "from modules.youtube_upload.auth_manager import setup_youtube_auth; setup_youtube_auth()"
```

**"No trending topics found"**
```bash
# Check if at least one trending API is configured
python -c "
from modules.trending_topics import TrendingTopicsFetcher
import asyncio
async def test():
    fetcher = TrendingTopicsFetcher()
    topics = await fetcher.fetch_all_trending_topics(limit=5)
    print(f'Found {len(topics)} topics')
asyncio.run(test())
"
```

### Performance Tips

1. **Enable Caching**: Reduces API costs
2. **Use Fallbacks**: Configure multiple API providers
3. **Monitor Quotas**: Check API usage regularly
4. **Optimize Schedule**: Run during off-peak hours

## 🎯 Production Checklist

Before going live:

- [ ] All API keys configured
- [ ] YouTube authentication working
- [ ] Test video generated successfully
- [ ] ffmpeg installed and working
- [ ] Sufficient API quota/credits
- [ ] Monitoring setup (optional)
- [ ] Backup strategy (optional)

## 💡 Pro Tips

### Cost Optimization
- Use Google TTS instead of ElevenLabs for voice (free vs $1/video)
- Use fallback visuals when Pexels quota exhausted
- Enable aggressive caching in production

### Quality Optimization
- Use OpenAI + ElevenLabs for premium quality
- Configure channel-specific voice profiles
- Use multiple visual sources for variety

### Scaling Tips
- Run multiple content types simultaneously
- Use Docker for easy deployment
- Set up monitoring for production use

## 🚀 Ready to Launch!

Your system is now ready to generate automated YouTube Shorts!

```bash
# Start your first automated pipeline
python main.py --run-once

# Check the results
ls output/videos/
ls output/metadata/
```

## 📞 Need Help?

1. Check the logs: `tail -f logs/youtube_shorts.log`
2. Run diagnostics: `python main.py --test`
3. Validate config: `python main.py --validate-config`

**Happy automating!** 🎉