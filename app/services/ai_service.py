import httpx
import json
from typing import List, Dict

class AIService:
    def __init__(self):
        self.ollama_url = "http://ollama:11434"
        self.model = "mistral"  # You can change this to any model you have in Ollama

    async def generate_summary(self, news_items: List[Dict]) -> str:
        try:
            # Prepare the news items for summarization
            news_text = "\n\n".join([
                f"Title: {item['title']}\n"
                f"Source: {item['source']}\n"
                f"Content: {item['excerpt']}"
                for item in news_items
            ])

            prompt = (
                "Summarize the following news items into a concise Twitter post "
                "(max 280 characters) that captures the most important information:\n\n"
                f"{news_text}\n\n"
                "Include a brief commentary on the most significant story."
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                result = response.json()
                return result['response'].strip()

        except Exception as e:
            print(f"Error generating summary: {e}")
            return ""

    async def generate_comment(self, tweet_content: str, existing_comments: List[str]) -> str:
        try:
            prompt = (
                "Generate a thoughtful and engaging comment for this Twitter post:\n\n"
                f"Post: {tweet_content}\n\n"
                "Existing comments:\n"
                f"{chr(10).join(existing_comments)}\n\n"
                "Generate a unique perspective that adds value to the discussion.\n"
                "Keep it concise and respectful."
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                result = response.json()
                return result['response'].strip()

        except Exception as e:
            print(f"Error generating comment: {e}")
            return ""

    async def analyze_sentiment(self, text: str) -> Dict:
        try:
            prompt = (
                "Analyze the sentiment of this text and return JSON with "
                "'sentiment' (positive/negative/neutral) and 'confidence' (0-1):\n\n"
                f"{text}"
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                result = response.json()
                return json.loads(result['response'])

        except Exception as e:
            print(f"Error analyzing sentiment: {e}")
            return {"sentiment": "neutral", "confidence": 0.0}
