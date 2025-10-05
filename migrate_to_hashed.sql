-- Migration: Hashed IDs only (no username storage)

-- Шаг 1: Удалить старую таблицу (ВНИМАНИЕ: потеряете данные!)
DROP TABLE IF EXISTS subscriptions;

-- Шаг 2: Создать новую таблицу с TEXT для user_id (без username)
CREATE TABLE subscriptions (
    user_id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

-- Шаг 3: Создать индекс для быстрого поиска
CREATE INDEX idx_expires_at ON subscriptions(expires_at);

-- Шаг 4: Дать права пользователю botuser
GRANT ALL PRIVILEGES ON TABLE subscriptions TO botuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO botuser;

-- Готово! Таблица хранит только хеши ID без username
