import httpx
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self, settings_service):
        self.settings_service = settings_service
        self.api_key = "2c0e2b4b4fbe4c8e9c8e2b4b4fbe4c8e"  # Free API key for testing
        self.base_url = "https://newsapi.org/v2"

    async def fetch_news(self, query: Optional[str] = None) -> List[Dict]:
        """Fetch news articles based on search query."""
        try:
            # Build the API URL based on query
            if query:
                url = f"{self.base_url}/everything?q={quote(query)}&language=en&sortBy=publishedAt&pageSize=5"
            else:
                url = f"{self.base_url}/top-headlines?country=us&pageSize=5"

            headers = {
                "X-Api-Key": self.api_key,
                "User-Agent": "Docker-Manager-News-App/1.0"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if data.get("status") != "ok":
                    logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                    return []

                articles = []
                for article in data.get("articles", []):
                    try:
                        # Format the date
                        published_date = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                        formatted_date = published_date.strftime("%Y-%m-%d %H:%M")

                        articles.append({
                            "title": article["title"],
                            "body": article["description"] or "",
                            "link": article["url"],
                            "date": formatted_date,
                            "source": article["source"]["name"]
                        })
                    except Exception as e:
                        logger.error(f"Error parsing article: {str(e)}")
                        continue

                return articles

        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            return []

    async def search_internet(self, query):
        """Legacy method - now redirects to fetch_news"""
        return await self.fetch_news(query)

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
