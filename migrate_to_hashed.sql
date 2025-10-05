-- Migration: Change user_id from BIGINT to TEXT for hashed IDs

-- Шаг 1: Удалить старую таблицу (ВНИМАНИЕ: потеряете данные!)
DROP TABLE IF EXISTS subscriptions;

-- Шаг 2: Создать новую таблицу с TEXT для user_id
CREATE TABLE subscriptions (
    user_id TEXT PRIMARY KEY,
    username VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

-- Шаг 3: Создать индекс для быстрого поиска
CREATE INDEX idx_expires_at ON subscriptions(expires_at);

-- Шаг 4: Дать права пользователю botuser
GRANT ALL PRIVILEGES ON TABLE subscriptions TO botuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO botuser;

-- Готово! Теперь user_id хранит SHA256 хеши вместо чистых ID
