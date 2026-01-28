-- ============================================================
-- Добавление групп 6-10 для групповой рассылки
-- ============================================================

-- Обновляем ограничение в group_texts (1-10 вместо 1-5)
ALTER TABLE group_texts DROP CONSTRAINT IF EXISTS group_texts_group_number_check;
ALTER TABLE group_texts ADD CONSTRAINT group_texts_group_number_check CHECK (group_number >= 1 AND group_number <= 10);

-- Добавляем тексты для групп 6-10
INSERT INTO group_texts (group_number, text) VALUES 
    (6, ''),
    (7, ''),
    (8, ''),
    (9, ''),
    (10, '')
ON CONFLICT (group_number) DO NOTHING;

-- Группа 6
CREATE TABLE IF NOT EXISTS group6 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 7
CREATE TABLE IF NOT EXISTS group7 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 8
CREATE TABLE IF NOT EXISTS group8 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 9
CREATE TABLE IF NOT EXISTS group9 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Группа 10
CREATE TABLE IF NOT EXISTS group10 (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Комментарии
COMMENT ON TABLE group6 IS 'Список пользователей группы 6';
COMMENT ON TABLE group7 IS 'Список пользователей группы 7';
COMMENT ON TABLE group8 IS 'Список пользователей группы 8';
COMMENT ON TABLE group9 IS 'Список пользователей группы 9';
COMMENT ON TABLE group10 IS 'Список пользователей группы 10';

-- ============================================================
-- ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:
-- ============================================================

-- Установить текст для группы 6:
-- UPDATE group_texts SET text = '<b>Привет!</b> Это сообщение для группы 6' WHERE group_number = 6;

-- Добавить пользователей в группу 6:
-- INSERT INTO group6 (telegram_id) VALUES (123456789), (987654321);

-- Посмотреть текст группы:
-- SELECT text FROM group_texts WHERE group_number = 6;

-- Посмотреть пользователей группы:
-- SELECT telegram_id FROM group6;

-- Посмотреть все группы и их заполненность:
-- SELECT 
--     gt.group_number,
--     LENGTH(gt.text) as text_length,
--     (SELECT COUNT(*) FROM group6 WHERE gt.group_number = 6) as users_count_6,
--     (SELECT COUNT(*) FROM group7 WHERE gt.group_number = 7) as users_count_7,
--     (SELECT COUNT(*) FROM group8 WHERE gt.group_number = 8) as users_count_8,
--     (SELECT COUNT(*) FROM group9 WHERE gt.group_number = 9) as users_count_9,
--     (SELECT COUNT(*) FROM group10 WHERE gt.group_number = 10) as users_count_10
-- FROM group_texts gt
-- WHERE gt.group_number >= 6 AND gt.group_number <= 10;
