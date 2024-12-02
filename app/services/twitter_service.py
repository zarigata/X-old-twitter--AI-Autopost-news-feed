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
        return self.client is not None and self.api is not None

    async def post_tweet(self, text: str) -> Dict:
        """Post a tweet with the given text."""
        if not self.is_configured():
            return {"error": "Twitter API not configured"}

        try:
            # Create tweet
            response = self.client.create_tweet(text=text)
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/user/status/{tweet_id}"
            
            return {
                "success": True,
                "tweet_id": tweet_id,
                "tweet_url": tweet_url
            }
        except Exception as e:
            error_msg = f"Error posting tweet: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def validate_credentials(self) -> Dict:
        """Validate Twitter API credentials."""
        try:
            if not self.is_configured():
                return {"error": "Twitter API not configured"}

            # Try to verify credentials
            self.api.verify_credentials()
            return {"success": True, "message": "Twitter credentials are valid"}
        except Exception as e:
            error_msg = f"Invalid Twitter credentials: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}