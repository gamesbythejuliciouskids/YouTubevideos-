#!/usr/bin/env python3
"""
Setup script for YouTube Shorts Automation System.
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess
import json

def print_banner():
    """Print setup banner."""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║         YouTube Shorts Automation System          ║
    ║                    Setup Script                   ║
    ╚═══════════════════════════════════════════════════╝
    """)

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required. You have:", sys.version)
        sys.exit(1)
    print("✅ Python version:", sys.version.split()[0])

def check_dependencies():
    """Check if required system dependencies are installed."""
    print("\n🔍 Checking system dependencies...")
    
    # Check ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ ffmpeg is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ffmpeg is not installed")
        print("   Please install ffmpeg:")
        print("   - Ubuntu/Debian: sudo apt install ffmpeg")
        print("   - macOS: brew install ffmpeg")
        print("   - Windows: Download from https://ffmpeg.org/")
        return False
    
    return True

def setup_virtual_environment():
    """Set up virtual environment."""
    print("\n🐍 Setting up virtual environment...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    try:
        subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
        print("✅ Virtual environment created")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create virtual environment")
        return False

def install_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing Python dependencies...")
    
    # Determine pip path
    if os.name == 'nt':  # Windows
        pip_path = Path("venv/Scripts/pip")
    else:  # Unix-like
        pip_path = Path("venv/bin/pip")
    
    try:
        subprocess.run([str(pip_path), 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def create_env_file():
    """Create .env file from template."""
    print("\n🔧 Setting up environment configuration...")
    
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("⚠️  Please edit .env file with your API keys")
        return True
    else:
        print("❌ .env.example file not found")
        return False

def create_sample_channel_configs():
    """Create sample channel configurations."""
    print("\n📺 Creating sample channel configurations...")
    
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # AI Facts Channel
    ai_facts_config = {
        "name": "ai_facts",
        "niche": "technology",
        "language": "en",
        "target_audience": "tech enthusiasts",
        "upload_frequency": "daily",
        "preferred_topics": ["AI", "machine learning", "technology", "science", "future"],
        "content_style": "educational",
        "voice_settings": {
            "voice_id": "default",
            "stability": 0.5,
            "similarity_boost": 0.5,
            "speed": 1.0
        }
    }
    
    # Health Tips Channel
    health_tips_config = {
        "name": "health_tips",
        "niche": "health",
        "language": "en",
        "target_audience": "health conscious",
        "upload_frequency": "daily",
        "preferred_topics": ["health", "fitness", "nutrition", "wellness", "lifestyle"],
        "content_style": "informative",
        "voice_settings": {
            "voice_id": "default",
            "stability": 0.6,
            "similarity_boost": 0.6,
            "speed": 0.9
        }
    }
    
    # Science Facts Channel
    science_facts_config = {
        "name": "science_facts",
        "niche": "science",
        "language": "en",
        "target_audience": "science lovers",
        "upload_frequency": "daily",
        "preferred_topics": ["science", "physics", "chemistry", "biology", "space", "research"],
        "content_style": "educational",
        "voice_settings": {
            "voice_id": "default",
            "stability": 0.7,
            "similarity_boost": 0.5,
            "speed": 1.1
        }
    }
    
    configs = [
        ("ai_facts_channel.json", ai_facts_config),
        ("health_tips_channel.json", health_tips_config),
        ("science_facts_channel.json", science_facts_config)
    ]
    
    for filename, config in configs:
        filepath = config_dir / filename
        if not filepath.exists():
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Created {filename}")
        else:
            print(f"✅ {filename} already exists")

def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating directories...")
    
    directories = [
        "output/videos",
        "output/audio", 
        "output/images",
        "output/metadata",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {directory}")

def run_validation():
    """Run configuration validation."""
    print("\n✅ Running system validation...")
    
    # Determine python path
    if os.name == 'nt':  # Windows
        python_path = Path("venv/Scripts/python")
    else:  # Unix-like
        python_path = Path("venv/bin/python")
    
    try:
        result = subprocess.run([str(python_path), 'main.py', '--validate-config'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Configuration validation passed")
            return True
        else:
            print("⚠️  Configuration validation failed:")
            print(result.stderr)
            print("Please configure your API keys in .env file")
            return False
    except Exception as e:
        print(f"❌ Failed to run validation: {e}")
        return False

def print_next_steps():
    """Print next steps for the user."""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║                   Setup Complete!                 ║
    ╚═══════════════════════════════════════════════════╝
    
    🎉 Your YouTube Shorts Automation System is ready!
    
    📋 Next Steps:
    
    1. Configure API Keys:
       - Edit .env file with your API keys
       - Required: OPENAI_API_KEY, YOUTUBE_API_KEY
       - Optional: ELEVENLABS_API_KEY, REDDIT_CLIENT_ID, etc.
    
    2. Test the System:
       - python main.py --validate-config
       - python main.py --test
       - python main.py --run-once --debug
    
    3. Production Run:
       - python main.py --run-once
       - Set up cron for daily automation
    
    4. Customize:
       - Edit channel configs in config/ directory
       - Adjust settings in .env file
       - Add your own content sources
    
    📚 Documentation:
       - Read README.md for detailed instructions
       - Check logs/ directory for system logs
       - View output/ directory for generated content
    
    💡 Pro Tips:
       - Start with --debug mode for testing
       - Monitor logs for troubleshooting
       - Use multiple channel configs for different niches
    
    🚀 Happy automating!
    """)

def main():
    """Main setup function."""
    print_banner()
    
    # Check system requirements
    check_python_version()
    
    if not check_dependencies():
        print("\n❌ Please install required dependencies before continuing")
        sys.exit(1)
    
    # Setup environment
    if not setup_virtual_environment():
        print("\n❌ Failed to set up virtual environment")
        sys.exit(1)
    
    if not install_dependencies():
        print("\n❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Create configuration
    create_env_file()
    create_sample_channel_configs()
    create_directories()
    
    # Validate setup
    run_validation()
    
    # Show next steps
    print_next_steps()

if __name__ == "__main__":
    main()