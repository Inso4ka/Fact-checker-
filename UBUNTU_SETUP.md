# Инструкция по настройке PostgreSQL на Ubuntu

Эта инструкция поможет настроить PostgreSQL для работы с ботом на Ubuntu Server.

## 📋 Требования

- Ubuntu 20.04 / 22.04 / 24.04
- Root доступ или sudo права
- Python 3.10+

---

## 1️⃣ Установка PostgreSQL

### Обновите систему
```bash
sudo apt update
```

### Установите PostgreSQL
```bash
sudo apt install postgresql postgresql-contrib -y
```

### Проверьте статус
```bash
sudo systemctl status postgresql
```

Если не запущен, запустите:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

## 2️⃣ Создание базы данных и пользователя

### Войдите в PostgreSQL
```bash
sudo -u postgres psql
```

### Выполните команды (в psql консоли):

```sql
-- Создайте пользователя для бота
CREATE USER botuser WITH ENCRYPTED PASSWORD 'ВАШ_НАДЕЖНЫЙ_ПАРОЛЬ';

-- Создайте базу данных
CREATE DATABASE factchecker OWNER botuser;

-- Выйдите из psql
\q
```

---

## 3️⃣ Создание таблиц

### Загрузите схему базы данных

Используйте файл `migrate_to_hashed.sql` из проекта:

```bash
# Скачайте проект (если еще не скачали)
git clone ваш_репозиторий
cd факт-чекер-бот

# Примените миграцию
sudo -u postgres psql -d factchecker -f migrate_to_hashed.sql
```

### Вручную (альтернатива):

```bash
sudo -u postgres psql -d factchecker
```

Затем в psql:
```sql
-- Создать таблицу подписок с хешированными ID
CREATE TABLE subscriptions (
    user_id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

-- Индекс для производительности
CREATE INDEX idx_expires_at ON subscriptions(expires_at);

-- Права для пользователя
GRANT ALL PRIVILEGES ON TABLE subscriptions TO botuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO botuser;

-- Выход
\q
```

---

## 4️⃣ Настройка подключения

### Получите строку подключения

Формат:
```
postgresql://botuser:ВАШ_ПАРОЛЬ@localhost:5432/factchecker
```

Пример:
```
postgresql://botuser:SuperSecret123@localhost:5432/factchecker
```

### Где использовать:

**Вариант А: .env файл (локальный запуск)**
```bash
# Создайте .env файл
nano .env
```

Добавьте:
```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
PERPLEXITY_API_KEY=ваш_perplexity_api_key
ADMIN_CHAT_ID=ваш_telegram_id
DATABASE_URL=postgresql://botuser:ВАШ_ПАРОЛЬ@localhost:5432/factchecker
HASH_SALT=длинная_случайная_строка_минимум_32_символа
```

**Вариант Б: Переменные окружения (production)**
```bash
export DATABASE_URL="postgresql://botuser:ВАШ_ПАРОЛЬ@localhost:5432/factchecker"
```

---

## 5️⃣ Установка зависимостей Python

```bash
# Установите pip
sudo apt install python3-pip python3-venv -y

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

---

## 6️⃣ Запуск бота

```bash
# Активируйте окружение
source venv/bin/activate

# Запустите бота
python bot.py
```

---

## 🔧 Проверка подключения к БД

### Проверьте что база работает:
```bash
psql -U botuser -d factchecker -h localhost
```

Введите пароль. Если вошли - всё работает!

### Посмотрите таблицы:
```sql
\dt
```

Должна быть таблица `subscriptions`.

### Выход:
```sql
\q
```

---

## 🔐 Безопасность (для production)

### Настройте файрвол
```bash
# Разрешите только локальные подключения к PostgreSQL
sudo ufw allow from 127.0.0.1 to any port 5432
```

### Ограничьте доступ в pg_hba.conf
```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Убедитесь что есть строка:
```
local   all    botuser    scram-sha-256
```

### Перезапустите PostgreSQL
```bash
sudo systemctl restart postgresql
```

---

## 🚀 Автозапуск бота (systemd)

Создайте сервис для автоматического запуска:

```bash
sudo nano /etc/systemd/system/factchecker-bot.service
```

Содержимое:
```ini
[Unit]
Description=Telegram Fact Checker Bot
After=network.target postgresql.service

[Service]
Type=simple
User=ваш_пользователь
WorkingDirectory=/путь/к/боту
Environment="DATABASE_URL=postgresql://botuser:ПАРОЛЬ@localhost:5432/factchecker"
Environment="TELEGRAM_BOT_TOKEN=ваш_токен"
Environment="PERPLEXITY_API_KEY=ваш_ключ"
Environment="ADMIN_CHAT_ID=ваш_id"
Environment="HASH_SALT=ваша_соль"
ExecStart=/путь/к/боту/venv/bin/python /путь/к/боту/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активируйте:
```bash
sudo systemctl daemon-reload
sudo systemctl enable factchecker-bot
sudo systemctl start factchecker-bot
sudo systemctl status factchecker-bot
```

---

## 📊 Полезные команды

### PostgreSQL
```bash
# Статус
sudo systemctl status postgresql

# Перезапуск
sudo systemctl restart postgresql

# Логи
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### База данных
```bash
# Войти в psql
sudo -u postgres psql

# Список баз
\l

# Подключиться к БД
\c factchecker

# Список таблиц
\dt

# Посмотреть подписки
SELECT * FROM subscriptions;
```

### Бот
```bash
# Логи бота
journalctl -u factchecker-bot -f

# Остановить
sudo systemctl stop factchecker-bot

# Перезапустить
sudo systemctl restart factchecker-bot
```

---

## ❓ Частые проблемы

### "connection refused"
```bash
# Проверьте что PostgreSQL запущен
sudo systemctl status postgresql
sudo systemctl start postgresql
```

### "password authentication failed"
```bash
# Сбросьте пароль
sudo -u postgres psql
ALTER USER botuser WITH PASSWORD 'новый_пароль';
\q
```

### "relation does not exist"
```bash
# Создайте таблицы заново
sudo -u postgres psql -d factchecker -f migrate_to_hashed.sql
```

---

## ✅ Готово!

Теперь ваш бот работает на Ubuntu с PostgreSQL базой данных! 🎉
