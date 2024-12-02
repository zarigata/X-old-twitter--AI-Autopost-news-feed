# AI News Bot Dashboard

An intelligent news aggregation and publishing system that collects news from around the world and publishes summaries on X (Twitter) using AI-powered content generation.

## Features

- Automated news gathering from global sources using DuckDuckGo
- AI-powered news summarization and content generation using Ollama
- Automated X (Twitter) posting with customizable schedule
- Real-time engagement tracking (likes, views, comments)
- Interactive web dashboard
- AI-powered comment generation and interaction
- Customizable bot persona

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Ollama installed locally (for development)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd news-bot
```

2. Build and run with Docker Compose:
```bash
docker-compose up --build
```

3. Access the dashboard:
Open your browser and navigate to `http://localhost:8000`

## Configuration

The bot can be configured through the web interface or by editing the environment variables:

- Posting schedule
- Bot persona
- News sources and categories
- AI model parameters

## Architecture

- FastAPI backend for API endpoints and WebSocket connections
- Ollama for AI processing
- DuckDuckGo for news gathering
- Real-time updates using WebSocket
- Modern web interface with Tailwind CSS

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
