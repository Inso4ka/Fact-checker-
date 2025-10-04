# Overview

This is a **Telegram fact-checking bot** that uses AI to verify the truthfulness of claims sent by users. The bot leverages Perplexity's AI API (sonar-pro model) to perform fact-checking with web search capabilities and returns structured responses with conclusions, reasoning, and sources.

The application is built as a **Python-based Telegram bot** (`bot.py`) using:
- **aiogram 3.15.0** - Modern async Telegram Bot framework
- **OpenAI SDK** - For Perplexity API integration
- **Long polling** - Simple and reliable message delivery

The bot accepts text messages from users, processes them through Perplexity's AI fact-checking agent, and returns formatted responses in HTML with clear verdicts, explanations, and source citations.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
**Not applicable** - This is a backend-only application that interfaces with Telegram's messaging platform as the user interface.

## Backend Architecture

### Simple Python Architecture
The application uses a **single-runtime Python architecture**:

**Python Bot (`bot.py`)**
- Clean, simple implementation using aiogram 3.15.0
- Long polling for reliable message delivery
- Direct async integration with Perplexity API via OpenAI SDK
- Stateless fact-checking flow

**Design Decision**: Python chosen for simplicity, maintainability, and ease of deployment. The async architecture with aiogram provides excellent performance without the complexity of multi-service orchestration.

### AI Agent System
- **Model**: Perplexity `sonar-pro` (web-search capable)
- **System Prompt**: Comprehensive OSINT fact-checking methodology loaded from `system_prompt.txt`
- **Operation**: Stateless - each request is independent
- **Configuration**: Temperature 0.2 for consistent, factual responses

**System Prompt Structure** (`system_prompt.txt`):
- Detailed 5-step OSINT verification methodology
- Hypothesis formulation (true/false)
- Verification plan with multi-source checking
- Research across official registries, news aggregators, social media, OSINT tools
- Evidence synthesis and gap analysis
- Concise output formatting for users

**Processing Flow**:
1. User sends message to bot
2. Bot receives via Telegram long polling
3. Sends "⏳ Анализирую ваш запрос..." indicator
4. Loads system prompt from `system_prompt.txt`
5. Calls Perplexity API with comprehensive OSINT prompt + user message
6. AI performs detailed analysis internally, returns concise summary
7. Formats and sends HTML response to user
8. Handles message chunking for long responses (>4096 chars)

**Rationale**: Separating the prompt into an external file allows for easy iteration and improvement of the OSINT methodology without code changes. The prompt instructs the AI to perform thorough analysis internally but present only essential conclusions and sources to users.

### Response Format
The bot enforces strict HTML formatting with **two sections only**:
- **Bold headers** using `<b>` tags (not markdown)
- **Two sections**: 
  - **ВЫВОД** (Conclusion): 2-3 sentences with clear verdict and confidence level
  - **ИСТОЧНИКИ** (Sources): 3-5 URLs with brief descriptions
- **Multilingual**: Responds in user's language (primarily Russian)
- **Concise**: No lengthy explanations - just verdict and sources

**Design Decision**: Removed ОБОСНОВАНИЕ (Justification) section to keep responses brief. Users get the conclusion and can verify sources themselves. HTML formatting chosen because Telegram's Bot API supports it natively.

## Data Storage Solutions

### No Database Required
The bot operates **statelessly** - no database or persistent storage is needed.

**Rationale**: Fact-checking doesn't require conversation history or state. Each request is independent, which simplifies deployment and reduces costs.

## Authentication and Authorization

### API Authentication
- **Telegram Bot**: Token-based (`TELEGRAM_BOT_TOKEN` environment variable)
- **Perplexity AI**: API key authentication (`PERPLEXITY_API_KEY`)
- **Webhook Security**: Telegram's built-in webhook validation (bot token in URL)

### Access Control
**None implemented** - The bot is open to any Telegram user who can message it. No user authentication or rate limiting visible in the codebase.

**Security Consideration**: Production deployment should implement rate limiting and potentially user whitelisting to prevent API quota abuse.

## External Dependencies

### Third-Party APIs
1. **Telegram Bot API**
   - Purpose: Message receiving and sending
   - Integration: Long polling
   - Library: `aiogram` 3.15.0 (Python)

2. **Perplexity AI API**
   - Purpose: AI-powered fact-checking with web search
   - Model: `sonar-pro` (optimized for OSINT and research)
   - Base URL: `https://api.perplexity.ai`
   - SDK: OpenAI-compatible client library (Python `openai` package)

**Rationale**: Perplexity chosen over standard GPT models because it includes real-time web search, which is essential for fact-checking current events and claims.

### Python Packages
- **aiogram** (3.15.0): Modern async Telegram Bot framework
- **openai** (1.58.1): OpenAI SDK (used with Perplexity base URL)
- **python-dotenv** (1.0.1): Environment variable management

### Deployment Platform
**Replit deployment**:
- Simple VM deployment with Python runtime
- Environment variables managed through Replit Secrets
- Continuous running for long polling