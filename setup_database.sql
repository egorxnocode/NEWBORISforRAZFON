-- Скрипт для создания таблицы пользователей в Supabase
-- Скопируйте этот код и выполните в SQL Editor вашего Supabase проекта

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    telegram_id BIGINT UNIQUE,
    first_name VARCHAR(255),
    username VARCHAR(255),
    channel_link VARCHAR(255),
    state VARCHAR(50) DEFAULT 'new',
    
    -- Данные курса
    penalties INTEGER DEFAULT 0,
    current_task INTEGER DEFAULT 0,
    course_state VARCHAR(50) DEFAULT 'not_started',
    
    -- Временные метки
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    registered_at TIMESTAMP WITH TIME ZONE,
    last_task_sent_at TIMESTAMP WITH TIME ZONE,
    last_reminder_sent_at TIMESTAMP WITH TIME ZONE,
    blocked_at TIMESTAMP WITH TIME ZONE,
    
    -- Ссылки на посты заданий (14 колонок)
    post_1 VARCHAR(500),
    post_2 VARCHAR(500),
    post_3 VARCHAR(500),
    post_4 VARCHAR(500),
    post_5 VARCHAR(500),
    post_6 VARCHAR(500),
    post_7 VARCHAR(500),
    post_8 VARCHAR(500),
    post_9 VARCHAR(500),
    post_10 VARCHAR(500),
    post_11 VARCHAR(500),
    post_12 VARCHAR(500),
    post_13 VARCHAR(500),
    post_14 VARCHAR(500)
);

-- Создаем индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_state ON users(state);

-- Создаем функцию для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Создаем триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Комментарии к колонкам
COMMENT ON TABLE users IS 'Таблица пользователей бота';
COMMENT ON COLUMN users.email IS 'Email пользователя (загружается вручную администратором)';
COMMENT ON COLUMN users.telegram_id IS 'Telegram ID пользователя';
COMMENT ON COLUMN users.first_name IS 'Имя пользователя из Telegram';
COMMENT ON COLUMN users.username IS 'Username пользователя из Telegram';
COMMENT ON COLUMN users.channel_link IS 'Ссылка на канал пользователя';
COMMENT ON COLUMN users.state IS 'Текущее состояние пользователя (new, waiting_email, waiting_channel, registered)';

-- Пример добавления разрешенных email для регистрации
-- Раскомментируйте и добавьте реальные email:

-- INSERT INTO users (email) VALUES ('user1@example.com');
-- INSERT INTO users (email) VALUES ('user2@example.com');
-- INSERT INTO users (email) VALUES ('user3@example.com');

