-- Telegram Fact Checker Bot - Database Schema
-- PostgreSQL Database Schema

-- Таблица подписок пользователей
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

-- Индекс для быстрого поиска истекших подписок
CREATE INDEX IF NOT EXISTS idx_expires_at ON subscriptions(expires_at);

-- Проверка созданных таблиц
\dt
