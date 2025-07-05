"""
Auth Manager - handles OAuth2 authentication for YouTube API access.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
import json
import pickle
import os

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

from config.config import config

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages OAuth2 authentication for YouTube API."""
    
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube',
            'https://www.googleapis.com/auth/youtube.readonly'
        ]
        
        # Paths for credential files
        self.credentials_path = config.CONFIG_DIR / "youtube_credentials.json"
        self.token_path = config.CONFIG_DIR / "youtube_token.pickle"
        
        # Ensure config directory exists
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
    def get_credentials(self) -> Optional[Credentials]:
        """Get valid credentials for YouTube API."""
        if not GOOGLE_AUTH_AVAILABLE:
            logger.error("Google auth libraries not available")
            return None
        
        try:
            credentials = None
            
            # Load existing credentials
            if self.token_path.exists():
                credentials = self._load_credentials()
            
            # If credentials are invalid or don't exist, create new ones
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    # Refresh expired credentials
                    credentials = self._refresh_credentials(credentials)
                else:
                    # Run OAuth flow
                    credentials = self._run_oauth_flow()
                
                # Save credentials
                if credentials:
                    self._save_credentials(credentials)
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to get credentials: {e}")
            return None
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from token file."""
        try:
            with open(self.token_path, 'rb') as token_file:
                credentials = pickle.load(token_file)
                logger.info("Loaded existing credentials")
                return credentials
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None
    
    def _save_credentials(self, credentials: Credentials) -> bool:
        """Save credentials to token file."""
        try:
            with open(self.token_path, 'wb') as token_file:
                pickle.dump(credentials, token_file)
                logger.info("Credentials saved successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            return False
    
    def _refresh_credentials(self, credentials: Credentials) -> Optional[Credentials]:
        """Refresh expired credentials."""
        try:
            credentials.refresh(Request())
            logger.info("Credentials refreshed successfully")
            return credentials
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            return None
    
    def _run_oauth_flow(self) -> Optional[Credentials]:
        """Run OAuth2 flow to get new credentials."""
        try:
            if not self.credentials_path.exists():
                logger.error(f"Client credentials file not found: {self.credentials_path}")
                logger.info("Please download the OAuth2 client credentials from Google Cloud Console")
                return None
            
            # Create OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                self.scopes
            )
            
            # Run local server flow
            credentials = flow.run_local_server(
                port=8080,
                prompt='consent',
                authorization_prompt_message='Please visit this URL to authorize the application: {url}',
                success_message='The auth flow is complete; you may close this window.',
                open_browser=True
            )
            
            logger.info("OAuth flow completed successfully")
            return credentials
            
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            return None
    
    def setup_credentials_file(self, client_secret_content: str) -> bool:
        """Setup credentials file from client secret JSON content."""
        try:
            # Validate JSON content
            client_config = json.loads(client_secret_content)
            
            # Ensure it has the required structure
            if "installed" not in client_config and "web" not in client_config:
                logger.error("Invalid client secret format")
                return False
            
            # Save to credentials file
            with open(self.credentials_path, 'w') as f:
                json.dump(client_config, f, indent=2)
            
            logger.info(f"Client credentials saved to: {self.credentials_path}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to setup credentials file: {e}")
            return False
    
    def create_credentials_from_env(self) -> bool:
        """Create credentials file from environment variables."""
        try:
            # Get credentials from environment
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                logger.error("Google OAuth credentials not found in environment variables")
                logger.info("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables")
                return False
            
            # Create client config
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost:8080/"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }
            }
            
            # Save to file
            with open(self.credentials_path, 'w') as f:
                json.dump(client_config, f, indent=2)
            
            logger.info("Client credentials created from environment variables")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create credentials from environment: {e}")
            return False
    
    def revoke_credentials(self) -> bool:
        """Revoke and delete stored credentials."""
        try:
            # Load existing credentials
            credentials = self._load_credentials()
            
            if credentials and credentials.valid:
                # Revoke the credentials
                try:
                    from google.oauth2 import utils
                    revoke_url = 'https://oauth2.googleapis.com/revoke'
                    utils.revoke_credentials(credentials, revoke_url)
                    logger.info("Credentials revoked successfully")
                except Exception as e:
                    logger.warning(f"Failed to revoke credentials: {e}")
            
            # Delete token file
            if self.token_path.exists():
                self.token_path.unlink()
                logger.info("Token file deleted")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return False
    
    def get_credentials_status(self) -> Dict[str, Any]:
        """Get status of stored credentials."""
        status = {
            "credentials_file_exists": self.credentials_path.exists(),
            "token_file_exists": self.token_path.exists(),
            "credentials_valid": False,
            "needs_refresh": False,
            "scopes": self.scopes
        }
        
        try:
            if status["token_file_exists"]:
                credentials = self._load_credentials()
                if credentials:
                    status["credentials_valid"] = credentials.valid
                    status["needs_refresh"] = credentials.expired and credentials.refresh_token is not None
                    status["expiry"] = credentials.expiry.isoformat() if credentials.expiry else None
        except Exception as e:
            logger.error(f"Failed to check credentials status: {e}")
        
        return status
    
    def test_credentials(self) -> bool:
        """Test if credentials are working."""
        try:
            credentials = self.get_credentials()
            
            if not credentials:
                logger.error("No credentials available")
                return False
            
            if not credentials.valid:
                logger.error("Credentials are not valid")
                return False
            
            # Test with a simple API call
            from googleapiclient.discovery import build
            service = build('youtube', 'v3', credentials=credentials)
            
            # Make a test call
            response = service.channels().list(part='snippet', mine=True).execute()
            
            if response.get('items'):
                logger.info("✅ Credentials test successful")
                return True
            else:
                logger.error("❌ No channel found with these credentials")
                return False
                
        except Exception as e:
            logger.error(f"❌ Credentials test failed: {e}")
            return False
    
    def setup_service_account(self, service_account_path: Path) -> bool:
        """Setup service account credentials (for server environments)."""
        try:
            if not service_account_path.exists():
                logger.error(f"Service account file not found: {service_account_path}")
                return False
            
            # Copy service account file to config directory
            target_path = config.CONFIG_DIR / "service_account.json"
            
            import shutil
            shutil.copy2(service_account_path, target_path)
            
            logger.info(f"Service account file copied to: {target_path}")
            logger.warning("Note: Service accounts have limited YouTube API access")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup service account: {e}")
            return False
    
    def get_authorization_url(self) -> Optional[str]:
        """Get authorization URL for manual OAuth flow."""
        try:
            if not self.credentials_path.exists():
                logger.error("Client credentials file not found")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                self.scopes
            )
            
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to get authorization URL: {e}")
            return None
    
    def exchange_code_for_credentials(self, authorization_code: str) -> bool:
        """Exchange authorization code for credentials."""
        try:
            if not self.credentials_path.exists():
                logger.error("Client credentials file not found")
                return False
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                self.scopes
            )
            
            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
            
            # Exchange code for credentials
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Save credentials
            self._save_credentials(credentials)
            
            logger.info("Credentials obtained successfully from authorization code")
            return True
            
        except Exception as e:
            logger.error(f"Failed to exchange authorization code: {e}")
            return False

def setup_youtube_auth():
    """Interactive setup for YouTube authentication."""
    auth_manager = AuthManager()
    
    print("🔧 Setting up YouTube API authentication...")
    print()
    
    # Check if credentials file exists
    if not auth_manager.credentials_path.exists():
        print("❌ Client credentials file not found")
        print()
        print("Please choose an option:")
        print("1. Create from environment variables (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)")
        print("2. Manual setup (provide client secret JSON)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            if auth_manager.create_credentials_from_env():
                print("✅ Credentials file created from environment variables")
            else:
                print("❌ Failed to create credentials from environment")
                return False
                
        elif choice == "2":
            print("\n📝 Please paste your client secret JSON content:")
            print("(This is the JSON file downloaded from Google Cloud Console)")
            client_secret = input().strip()
            
            if auth_manager.setup_credentials_file(client_secret):
                print("✅ Credentials file created successfully")
            else:
                print("❌ Failed to create credentials file")
                return False
        else:
            print("Setup cancelled")
            return False
    
    # Test credentials
    print("\n🔐 Testing authentication...")
    if auth_manager.test_credentials():
        print("✅ Authentication setup complete!")
        return True
    else:
        print("❌ Authentication test failed")
        return False

# Example usage
def main():
    """Test auth manager."""
    auth_manager = AuthManager()
    
    # Check status
    status = auth_manager.get_credentials_status()
    print("Credentials status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Test credentials
    if auth_manager.test_credentials():
        print("✅ Authentication working")
    else:
        print("❌ Authentication not working")

if __name__ == "__main__":
    main()