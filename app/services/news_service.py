from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import httpx
import asyncio
from datetime import datetime, timedelta
import ollama
import os
import time
import random
import logging

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.ddgs = DDGS()
        self.news_cache = []
        self.last_fetch = None
        self.fetch_interval = timedelta(minutes=30)
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://192.168.15.115:11434')
        self.current_model = 'llama2'
        ollama.host = self.ollama_host
        self.last_search_time = 0
        self.min_search_interval = 2  # minimum seconds between searches

    async def search_internet(self, query):
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last_search = current_time - self.last_search_time
            if time_since_last_search < self.min_search_interval:
                await asyncio.sleep(self.min_search_interval - time_since_last_search)
            
            self.last_search_time = time.time()
            
            # Add some randomization to appear more human-like
            results = list(self.ddgs.text(
                query, 
                max_results=5,
                region='wt-wt'
            ))
            
            # Filter and validate results
            filtered_results = []
            for result in results:
                if isinstance(result, dict) and 'body' in result and result['body']:
                    filtered_results.append(result)
            
            return filtered_results
        except Exception as e:
            print(f"Error searching internet: {e}")
            return []

    async def get_combined_response(self, query):
        search_results = []
        try:
            # If it's a summary request and we have cached news, use that directly
            if "Based on these recent news items" in query and self.news_cache:
                search_content = query  # Use the formatted news context directly
            else:
                # Perform internet search
                search_results = await self.search_internet(query)
                if not search_results:
                    return "Unable to fetch news at this time. Please try again later.", []
                search_content = "\n".join([result['body'] for result in search_results])

            # Integrate search results into the AI response
            response = ollama.chat(
                model=self.current_model,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a professional news analyst. Provide clear, concise, and accurate summaries.'
                    },
                    {
                        'role': 'user',
                        'content': search_content
                    }
                ]
            )
            return response['message']['content'], search_results

        except Exception as e:
            print(f"Error in get_combined_response: {e}")
            return "Error processing request. Please try again later.", search_results

    async def get_ollama_models(self):
        try:
            response = httpx.get(f"{self.ollama_host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            return []
        except Exception as e:
            print(f"Error getting Ollama models: {e}")
            return []

    async def fetch_news(self):
        try:
            # Define news categories and regions
            categories = ["world news", "breaking news", "technology", "science", "business"]
            all_news = []

            for category in categories:
                # Add delay between category searches
                await asyncio.sleep(2)
                
                # Search for news in each category
                query = f"latest {category} news today"
                summary, results = await self.get_combined_response(query)
                
                if results:  # Only process if we got results
                    for result in results:
                        news_item = {
                            "title": result["title"],
                            "link": result["href"],
                            "source": result.get("source", "DuckDuckGo"),
                            "published": datetime.now().isoformat(),
                            "excerpt": result["body"],
                            "category": category,
                            "ai_summary": summary
                        }
                        all_news.append(news_item)

            if all_news:  # Only update cache if we got new results
                # Sort by recency (assuming all are from today)
                self.news_cache = sorted(all_news, key=lambda x: x["published"], reverse=True)
                self.last_fetch = datetime.now()
                
            return self.news_cache or []  # Return empty list if no news

        except Exception as e:
            print(f"Error fetching news: {e}")
            return self.news_cache or []  # Return cached news on error, or empty list

    async def get_latest_news(self):
        """Get the latest news from cache or fetch new ones."""
        if not self.news_cache or (
                datetime.now() - self.last_fetch > self.fetch_interval):
            await self.fetch_news()
        return self.news_cache

    async def get_ai_summary(self, news_items):
        """Generate an AI summary of the provided news items."""
        try:
            # Prepare context for AI
            news_context = "\n\n".join([
                f"Title: {item['title']}\n"
                f"Excerpt: {item['excerpt']}"
                for item in news_items[:5]  # Take latest 5 news items
            ])
            
            # Generate summary using Ollama
            headers = {'Content-Type': 'application/json'}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.current_model,
                        "prompt": f"You are a professional news analyst. Based on these recent news items, "
                                f"provide a concise summary of the current major events and their significance "
                                f"in about 2-3 paragraphs:\n\n{news_context}",
                        "stream": False
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    logger.error(f"Ollama API error: Status {response.status_code}, Response: {response.text}")
                    raise Exception(f"Error from Ollama API: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error generating AI summary: {str(e)}")
            raise Exception(f"Failed to generate AI summary: {str(e)}")
