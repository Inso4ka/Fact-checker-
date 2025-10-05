# Overview

This is a **Telegram fact-checking bot** that uses AI to verify the truthfulness of claims sent by users. The bot leverages Perplexity's AI API (sonar-pro model) to perform fact-checking with web search capabilities and returns structured responses with conclusions, reasoning, and sources.

The application is built as a **Python-based Telegram bot** (`bot.py`) using:
- **aiogram 3.15.0** - Modern async Telegram Bot framework
- **OpenAI SDK** - For Perplexity API integration
- **Long polling** - Simple and reliable message delivery

The bot accepts text messages from users, processes them through Perplexity's AI fact-checking agent, and returns formatted responses in HTML with clear verdicts, explanations, and source citations.

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes (2025-10-05)

## SHA256 ID Hashing Implementation
- **Security Enhancement**: User IDs are now hashed using SHA256 + salt before storage
- **Database**: Changed `user_id` from BIGINT to TEXT to store 64-character hashes
- **Username Removed**: Deleted `username` field from database for maximum privacy
- **Environment Variable**: Added `HASH_SALT` (required, minimum 32 characters)
- **Privacy**: Real Telegram IDs never stored in database - only hashes visible
- **Admin Commands**: Work transparently - `/grant 123456789 1M` auto-hashes the ID
- **Migration**: `migrate_to_hashed.sql` recreates table with TEXT user_id (no username)

# System Architecture

## Frontend Architecture
**Not applicable** - This is a backend-only application that interfaces with Telegram's messaging platform as the user interface.

## Backend Architecture

### Modular Python Architecture
The application uses a **modular Python package architecture** with clean separation of concerns:

**Project Structure**:
```
app/
├── config.py              # Configuration with Pydantic validation
├── constants.py           # Shared constants (timezones, durations)
├── models/
│   └── subscription.py    # TypedDict models for type safety
├── db/
│   ├── pool.py           # Database connection pool management
│   └── repositories/
│       └── subscriptions.py  # Data access layer (CRUD operations)
├── clients/
│   └── perplexity.py     # Perplexity AI client wrapper
├── services/
│   ├── subscriptions.py  # Business logic for subscriptions
│   └── notifications.py  # User notification service
├── handlers/
│   ├── admin.py          # Admin command handlers (Router-based)
│   └── user.py           # User command handlers (Router-based)
├── background/
│   └── cleanup.py        # Background task for expired subscriptions
├── utils/
│   └── text.py          # Text utilities (message chunking)
└── main.py              # Application entry point
bot.py                    # Compatibility wrapper for workflow
```

**Architecture Benefits**:
- **Separation of Concerns**: Each module has single responsibility
- **Type Safety**: Pydantic config validation, TypedDict models, comprehensive type hints
- **Testability**: Modular design enables easy unit testing
- **Maintainability**: Clear structure makes code easy to navigate and modify
- **Scalability**: Easy to add new features without touching existing code
- **Async Best Practices**: Proper resource management, graceful shutdown handling

**Design Decision**: Refactored from monolithic 464-line bot.py to modular architecture for better maintainability, type safety, and scalability. Uses dependency injection pattern with routers for handlers. Proper async lifecycle management with graceful shutdown support.

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
- Automatic cleanup of expired subscriptions every 1 minute
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
- Users without subscription see admin contact (@kroove) in all related messages
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
- Background task runs every 1 minute
- Automatically notifies users and admins when subscription expires
- Users receive notification with admin contacts for renewal
- Admins receive notification with user details and quick /grant command
- Removes expired subscriptions from database after notification
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