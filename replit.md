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
- PostgreSQL database for subscription management
- Admin-controlled subscription system

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
3. Checks user subscription status in database
4. If no subscription: directs user to send their ID to admin, notifies admin with user details
5. If subscription active: Sends "⏳ Анализирую ваш запрос..." indicator
6. Loads system prompt from `system_prompt.txt`
7. Calls Perplexity API with comprehensive OSINT prompt + user message
8. AI performs detailed analysis internally, returns concise summary
9. Formats and sends HTML response to user
10. Handles message chunking for long responses (>4096 chars)

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

### PostgreSQL Database (Replit Neon)
The bot uses **PostgreSQL** for subscription management:

**Schema**:
- `subscriptions` table:
  - `user_id` (BIGINT, PRIMARY KEY): Telegram user ID
  - `username` (VARCHAR): Telegram username
  - `expires_at` (TIMESTAMP): Subscription expiration date/time
  - `created_at` (TIMESTAMP): Subscription creation date/time

**Operations**:
- Subscription checks on every message
- Automatic cleanup of expired subscriptions every 10 minutes
- Admin commands for subscription management

**Rationale**: Subscription system requires persistent storage to track user access. PostgreSQL chosen for reliability and Replit's built-in support. Background cleanup task ensures database stays clean without manual intervention.

## Authentication and Authorization

### API Authentication
- **Telegram Bot**: Token-based (`TELEGRAM_BOT_TOKEN` environment variable)
- **Perplexity AI**: API key authentication (`PERPLEXITY_API_KEY`)
- **Database**: Connection string (`DATABASE_URL`)
- **Admin**: Telegram user ID (`ADMIN_CHAT_ID` environment variable)

### Access Control

**Subscription System**:
- Only users with active subscriptions can use fact-checking functionality
- New users receive their Telegram ID and are directed to send it to admin
- Admin receives automatic notifications with user details (ID, username, name) when unauthorized users attempt to use the bot

**Admin Control** (identified by Telegram IDs in `ADMIN_CHAT_ID`):
- `/grant <user_id> <duration>` - Grant subscription (1m, 1d, 1M, 6M, 1y)
- `/revoke <user_id>` - Revoke subscription
- `/list` - View all active subscriptions

**Multiple Admins Support**:
- `ADMIN_CHAT_ID` can contain one or more Telegram IDs separated by commas
- Example: `123456789` (one admin) or `123456789,987654321,111222333` (multiple admins)
- All admins have equal rights and receive notifications about new users
- To get your Telegram ID: send `/start` to the bot

**User Commands**:
- `/start` - Bot introduction and subscription status
- `/mystatus` - Check own subscription status

**Automatic Expiration**:
- Background task runs every 10 minutes
- Automatically removes expired subscriptions from database
- Users lose access immediately upon expiration

**Rationale**: Subscription system prevents API quota abuse and allows controlled access. Admin identification by Telegram ID (not username) is more secure and reliable since usernames can be changed. Multiple admins support allows team management. Admin-only management ensures proper oversight. Time-based subscriptions provide flexibility for different access levels.

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
- **asyncpg** (0.30.0): Async PostgreSQL driver for subscription management

### Deployment Platform
**Replit deployment**:
- Simple VM deployment with Python runtime
- Environment variables managed through Replit Secrets
- Required secrets: `TELEGRAM_BOT_TOKEN`, `PERPLEXITY_API_KEY`, `DATABASE_URL`, `ADMIN_CHAT_ID`
- Continuous running for long polling