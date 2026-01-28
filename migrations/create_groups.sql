-- ============================================================
-- Создание таблиц для групповой рассылки
-- ============================================================

-- Таблица с текстами для каждой группы (один текст на группу)
CREATE TABLE IF NOT EXISTS group_texts (
    group_number INT PRIMARY KEY CHECK (group_number >= 1 AND group_number <= 10),
    text TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Заполняем начальные значения для 10 групп
INSERT INTO group_texts (group_number, text) VALUES 
    (1, ''),
    (2, ''),
    (3, ''),
    (4, ''),
    (5, ''),
    (6, ''),
    (7, ''),
    (8, ''),
    (9, ''),
    (10, '')
ON CONFLICT (group_number) DO NOTHING;

-- Группа 1 (только telegram_id)
CREATE TABLE IF NOT EXISTS group1 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 2
CREATE TABLE IF NOT EXISTS group2 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 3
CREATE TABLE IF NOT EXISTS group3 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 4
CREATE TABLE IF NOT EXISTS group4 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 5
CREATE TABLE IF NOT EXISTS group5 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Комментарии
COMMENT ON TABLE group_texts IS 'Тексты для групповых рассылок (один текст на группу)';
COMMENT ON TABLE group1 IS 'Список пользователей группы 1';
COMMENT ON TABLE group2 IS 'Список пользователей группы 2';
COMMENT ON TABLE group3 IS 'Список пользователей группы 3';
COMMENT ON TABLE group4 IS 'Список пользователей группы 4';
COMMENT ON TABLE group5 IS 'Список пользователей группы 5';

-- ============================================================
-- ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:
-- ============================================================

-- Установить текст для группы 1:
-- UPDATE group_texts SET text = '<b>Привет!</b> Это сообщение для группы 1' WHERE group_number = 1;

-- Добавить пользователей в группу 1:
-- INSERT INTO group1 (telegram_id) VALUES (123456789), (987654321);

-- Посмотреть текст группы:
-- SELECT text FROM group_texts WHERE group_number = 1;

-- Посмотреть пользователей группы:
-- SELECT telegram_id FROM group1;
