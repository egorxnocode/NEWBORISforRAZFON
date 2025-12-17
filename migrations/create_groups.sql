-- ============================================================
-- Создание таблиц для групповой рассылки
-- Таблицы group1, group2, group3, group4, group5
-- ============================================================

-- Группа 1
CREATE TABLE IF NOT EXISTS group1 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    text TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 2
CREATE TABLE IF NOT EXISTS group2 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    text TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 3
CREATE TABLE IF NOT EXISTS group3 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    text TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 4
CREATE TABLE IF NOT EXISTS group4 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    text TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 5
CREATE TABLE IF NOT EXISTS group5 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    text TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Комментарии к таблицам
COMMENT ON TABLE group1 IS 'Группа 1 для рассылки';
COMMENT ON TABLE group2 IS 'Группа 2 для рассылки';
COMMENT ON TABLE group3 IS 'Группа 3 для рассылки';
COMMENT ON TABLE group4 IS 'Группа 4 для рассылки';
COMMENT ON TABLE group5 IS 'Группа 5 для рассылки';

-- Комментарии к колонкам
COMMENT ON COLUMN group1.telegram_id IS 'Telegram ID пользователя';
COMMENT ON COLUMN group1.text IS 'Текст сообщения для рассылки этой группе';

-- ============================================================
-- Пример заполнения:
-- 
-- INSERT INTO group1 (telegram_id, text) VALUES 
--   (123456789, 'Привет! Это сообщение для группы 1');
-- 
-- UPDATE group1 SET text = 'Новый текст' WHERE 1=1;
-- ============================================================

