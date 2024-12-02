from duckduckgo_search import AsyncDDGS
import logging
from datetime import datetime
from typing import List, Dict, Optional
import asyncio
import time
import httpx

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self, settings_service):
        self.settings_service = settings_service
        self.last_search_time = 0
        self.min_search_interval = 1  # minimum seconds between searches

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
            
            # Get news from DuckDuckGo
            async with AsyncDDGS() as ddgs:
                results = []
                async for r in ddgs.news(
                    search_query,
                    max_results=10,  # Increased max results
                    region="wt-wt",
                    safesearch="off",
                    timelimit="d"
                ):
                    results.append(r)

            if not results:
                logger.warning(f"No results found for query: {search_query}")
                return []

            # Format the results
            articles = []
            for result in results:
                try:
                    # Parse and format the date
                    published = result.get('date')
                    if published:
                        try:
                            # Try to parse the date in different formats
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                try:
                                    date_obj = datetime.strptime(published, fmt)
                                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
                                    break
                                except ValueError:
                                    continue
                            else:
                                formatted_date = published
                        except:
                            formatted_date = published
                    else:
                        formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M")

                    articles.append({
                        "title": result["title"],
                        "body": result["body"],
                        "link": result["link"],
                        "date": formatted_date,
                        "source": result.get("source", "")
                    })
                except Exception as e:
                    logger.error(f"Error parsing article: {str(e)}")
                    continue

            if not articles:
                logger.warning("No articles could be parsed from the results")
                return []

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
