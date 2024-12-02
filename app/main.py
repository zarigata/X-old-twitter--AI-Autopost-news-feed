from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import asyncio
from datetime import datetime
import json
from services.news_service import NewsService
from services.ai_service import AIService
from services.twitter_service import TwitterService
from services.settings_service import SettingsService
from database import AsyncSessionLocal, init_db
from config import Settings
import os
import httpx
import logging

logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="/app/static"), name="static")
templates = Jinja2Templates(directory="/app/templates")

# Services initialization
settings_service = SettingsService()
news_service = NewsService(settings_service)
ai_service = AIService()
twitter_service = TwitterService(settings_service)

# Global settings
current_settings = None

# Global variables for WebSocket connections
terminal_connections = []

class TerminalLogHandler(logging.Handler):
    async def emit(self, record):
        message = self.format(record)
        for connection in terminal_connections:
            try:
                await connection.send_json({"content": message})
            except:
                terminal_connections.remove(connection)

# Add terminal handler to logger
terminal_handler = TerminalLogHandler()
terminal_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(terminal_handler)

async def news_bot_loop():
    global current_settings
    while True:
        try:
            if current_settings and current_settings.next_post_time:
                now = datetime.now()
                if now >= current_settings.next_post_time:
                    # Fetch latest news
                    news_items = await news_service.get_latest_news()
                    if news_items:
                        # Generate summary with custom persona
                        prompt = f"""As a {current_settings.bot_persona}, summarize the following news:
                        {news_items[0]['title']}
                        {news_items[0]['excerpt']}
                        """
                        summary = await ai_service.generate_summary(news_items)
                        
                        # Post to Twitter
                        tweet = await twitter_service.post_tweet(summary, news_items[0]["link"])
                        if tweet:
                            print(f"Posted tweet: {summary}")
                            current_settings.update_post_times()
                    
                    # Check for new comments and generate responses
                    if twitter_service.last_tweet_id:
                        comments = await twitter_service.get_comments(twitter_service.last_tweet_id)
                        for comment in comments:
                            response = await ai_service.generate_comment(
                                tweet_content=summary,
                                existing_comments=[c["text"] for c in comments]
                            )
                            await twitter_service.reply_to_tweet(comment["id"], response)
            
            # Check every minute
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Error in news bot loop: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send real-time updates about news and Twitter stats
            stats = await twitter_service.get_latest_stats()
            await websocket.send_json({
                "type": "stats_update",
                "data": stats
            })
            
            # Send next post time if available
            if current_settings and current_settings.next_post_time:
                await websocket.send_json({
                    "type": "next_post_update",
                    "data": {
                        "next_post": current_settings.next_post_time.isoformat(),
                        "last_post": current_settings.last_post_time.isoformat() if current_settings.last_post_time else None
                    }
                })
            
            await asyncio.sleep(30)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.get("/api/news")
async def get_news():
    return await news_service.get_latest_news()

@app.get("/api/twitter/stats")
async def get_twitter_stats():
    return await twitter_service.get_latest_stats()

@app.get("/api/settings")
async def get_settings():
    """Get all settings."""
    return settings_service.get_all_settings()

@app.post("/api/settings")
async def update_settings(settings: dict):
    """Update settings."""
    if settings_service.save_settings(settings):
        return {"status": "success", "settings": settings}
    return {"status": "error", "message": "Failed to save settings"}

@app.post("/api/twitter/validate")
async def validate_twitter_credentials():
    """Validate Twitter API credentials."""
    return twitter_service.validate_credentials()

@app.post("/api/twitter/tweet")
async def post_tweet(request: Request):
    try:
        data = await request.json()
        text = data.get("text")
        if not text:
            return JSONResponse({"error": "Tweet text is required"}, status_code=400)
        
        result = await twitter_service.post_tweet(text)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error posting tweet: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/ai_summary")
async def get_ai_summary(query: str = ''):
    """Get AI-generated summary of news articles."""
    try:
        # Fetch news based on query
        news_items = await news_service.fetch_news(query)
        
        if not news_items:
            return JSONResponse({
                "error": f"No news found for query: {query}" if query else "No news found"
            }, status_code=404)

        # Generate prompt for AI
        news_text = "\n\n".join([
            f"Title: {item['title']}\n{item['body']}"
            for item in news_items
        ])
        
        prompt = f"""Here are some news articles{' about ' + query if query else ''}:

{news_text}

Please provide a concise summary of these articles, highlighting the key points and trends."""

        # Get AI summary
        response = await ai_service.get_completion(prompt)
        
        return JSONResponse({
            "summary": response,
            "news_items": news_items
        })
    except Exception as e:
        logger.error(f"Error getting AI summary: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/models")
async def get_available_models():
    """Get available models from Ollama server."""
    try:
        models = await settings_service.fetch_available_models()
        return {"models": models}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch models: {str(e)}"}
        )

@app.websocket("/api/terminal_updates")
async def terminal_updates(websocket: WebSocket):
    await websocket.accept()
    terminal_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
    finally:
        terminal_connections.remove(websocket)
        await websocket.close()

# Background task for news gathering and posting
@app.on_event("startup")
async def start_news_bot():
    asyncio.create_task(news_bot_loop())
