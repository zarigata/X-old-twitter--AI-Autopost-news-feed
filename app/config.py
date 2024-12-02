from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

class Settings(BaseModel):
    interval_minutes: int  # Posting interval in minutes
    bot_persona: str  # Custom bot persona description
    news_categories: Optional[list[str]] = ["world news", "breaking news", "important events"]
    ai_model: Optional[str] = "mistral"
    last_post_time: Optional[datetime] = None
    next_post_time: Optional[datetime] = None

    def update_post_times(self):
        self.last_post_time = datetime.now()
        self.next_post_time = self.last_post_time + timedelta(minutes=self.interval_minutes)
