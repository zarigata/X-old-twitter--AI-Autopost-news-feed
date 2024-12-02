import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio
import time
import json
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self, settings_service):
        self.settings_service = settings_service
        self.last_search_time = 0
        self.min_search_interval = 2  # minimum seconds between searches
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    async def get_session(self):
        if self.session is None:
            self.session = httpx.AsyncClient(headers=self.headers, follow_redirects=True)
        return self.session

    async def fetch_news_from_newsdata(self, query: str) -> List[Dict]:
        """Fetch news from NewsData.io API"""
        try:
            api_key = "pub_35192abcad89186b7dd5dad4faa389516e123"  # Free API key
            base_url = "https://newsdata.io/api/1/news"
            
            params = {
                'apikey': api_key,
                'q': query,
                'language': 'en',
                'size': 10
            }
            
            session = await self.get_session()
            response = await session.get(base_url, params=params)
            data = response.json()
            
            if response.status_code != 200:
                logger.error(f"NewsData API error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = []
            for result in data.get('results', []):
                try:
                    published_date = datetime.fromisoformat(result['pubDate'].replace('Z', '+00:00'))
                    articles.append({
                        "title": result['title'],
                        "body": result['description'] or result['title'],
                        "link": result['link'],
                        "date": published_date.strftime("%Y-%m-%d %H:%M"),
                        "source": result['source_id']
                    })
                except Exception as e:
                    logger.error(f"Error parsing NewsData article: {str(e)}")
                    continue
                    
            return articles
        except Exception as e:
            logger.error(f"Error fetching from NewsData: {str(e)}")
            return []

    async def fetch_news_from_gnews(self, query: str) -> List[Dict]:
        """Fetch news from Gnews RSS feed"""
        try:
            base_url = "https://news.google.com/rss/search"
            params = {'q': query, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'}
            
            session = await self.get_session()
            response = await session.get(base_url, params=params)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')
            
            articles = []
            for item in items[:10]:  # Limit to 10 articles
                try:
                    pub_date = datetime.strptime(item.pubDate.text, '%a, %d %b %Y %H:%M:%S %Z')
                    articles.append({
                        "title": item.title.text,
                        "body": item.description.text,
                        "link": item.link.text,
                        "date": pub_date.strftime("%Y-%m-%d %H:%M"),
                        "source": "Google News"
                    })
                except Exception as e:
                    logger.error(f"Error parsing GNews article: {str(e)}")
                    continue
            
            return articles
        except Exception as e:
            logger.error(f"Error fetching from GNews: {str(e)}")
            return []

    async def fetch_news(self, query: Optional[str] = None) -> List[Dict]:
        """Fetch news articles based on search query."""
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last_search = current_time - self.last_search_time
            if time_since_last_search < self.min_search_interval:
                await asyncio.sleep(self.min_search_interval - time_since_last_search)
            
            self.last_search_time = time.time()

            # Build search query
            search_query = query if query else "latest breaking news today"
            
            # Try different news sources in order
            articles = []
            
            # Try NewsData.io first
            articles = await self.fetch_news_from_newsdata(search_query)
            
            # If NewsData fails, try GNews
            if not articles:
                articles = await self.fetch_news_from_gnews(search_query)
            
            if not articles:
                logger.warning(f"No articles found for query: {search_query}")
                return []

            return articles

        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            return []

    async def search_internet(self, query):
        """Legacy method - now redirects to fetch_news"""
        return await self.fetch_news(query)

    async def __del__(self):
        if self.session:
            await self.session.aclose()
