import tweepy
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class TwitterService:
    def __init__(self, settings_service):
        self.settings_service = settings_service
        self.api: Optional[tweepy.API] = None
        self.client: Optional[tweepy.Client] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Twitter API client with current settings."""
        try:
            settings = self.settings_service.get_settings()
            twitter_settings = settings.get('twitter', {})

            # Check if we have all required credentials
            required_keys = ['api_key', 'api_secret', 'access_token', 'access_token_secret', 'bearer_token']
            if not all(twitter_settings.get(key) for key in required_keys):
                logger.warning("Twitter credentials not fully configured")
                return

            # Initialize v1.1 API (for media upload)
            auth = tweepy.OAuthHandler(
                twitter_settings['api_key'],
                twitter_settings['api_secret']
            )
            auth.set_access_token(
                twitter_settings['access_token'],
                twitter_settings['access_token_secret']
            )
            self.api = tweepy.API(auth)

            # Initialize v2 API
            self.client = tweepy.Client(
                bearer_token=twitter_settings['bearer_token'],
                consumer_key=twitter_settings['api_key'],
                consumer_secret=twitter_settings['api_secret'],
                access_token=twitter_settings['access_token'],
                access_token_secret=twitter_settings['access_token_secret']
            )
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {str(e)}")
            self.api = None
            self.client = None

    def is_configured(self) -> bool:
        """Check if Twitter API is properly configured."""
        settings = self.settings_service.get_settings()
        twitter_settings = settings.get('twitter', {})
        required_keys = ['api_key', 'api_secret', 'access_token', 'access_token_secret', 'bearer_token']
        return all(twitter_settings.get(key) for key in required_keys)

    def validate_credentials(self) -> Dict:
        """Validate Twitter API credentials."""
        if not self.is_configured():
            return {
                "status": "error",
                "message": "Twitter credentials not configured. Please update settings with your Twitter API credentials."
            }

        try:
            if self.client and self.api:
                # Test the API by getting the authenticated user
                user = self.client.get_me()
                if user and user.data:
                    return {
                        "status": "success",
                        "message": f"Connected as @{user.data.username}"
                    }
            return {
                "status": "error",
                "message": "Failed to authenticate with Twitter. Please check your credentials."
            }
        except Exception as e:
            logger.error(f"Error validating Twitter credentials: {str(e)}")
            return {
                "status": "error",
                "message": f"Twitter API error: {str(e)}"
            }

    async def post_tweet(self, text: str) -> Dict:
        """Post a tweet."""
        if not self.is_configured():
            return {
                "status": "error",
                "message": "Twitter credentials not configured. Please update settings with your Twitter API credentials."
            }

        if not self.client:
            return {
                "status": "error",
                "message": "Twitter client not initialized. Please check your credentials."
            }

        try:
            response = self.client.create_tweet(text=text)
            if response and response.data:
                tweet_id = response.data['id']
                return {
                    "status": "success",
                    "message": f"Tweet posted successfully",
                    "tweet_url": f"https://twitter.com/user/status/{tweet_id}"
                }
            return {
                "status": "error",
                "message": "Failed to post tweet. Please try again."
            }
        except Exception as e:
            logger.error(f"Error posting tweet: {str(e)}")
            return {
                "status": "error",
                "message": f"Twitter API error: {str(e)}"
            }
