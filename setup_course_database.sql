-- Скрипт для обновления БД и добавления таблицы заданий курса
-- Выполните этот скрипт в SQL Editor вашего Supabase проекта

-- 1. Добавляем новые колонки в таблицу users для курса
ALTER TABLE users ADD COLUMN IF NOT EXISTS penalties INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS current_task INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS course_state VARCHAR(50) DEFAULT 'not_started';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_task_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE;

-- Добавляем колонки для ссылок на посты заданий
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_1 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_2 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_3 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_4 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_5 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_6 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_7 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_8 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_9 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_10 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_11 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_12 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_13 VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS post_14 VARCHAR(500);

-- Комментарии к новым колонкам
COMMENT ON COLUMN users.penalties IS 'Количество штрафных очков (0-4)';
COMMENT ON COLUMN users.current_task IS 'Номер текущего задания (0-14)';
COMMENT ON COLUMN users.course_state IS 'Состояние курса (not_started, in_progress, waiting_task_X, completed, excluded)';
COMMENT ON COLUMN users.last_task_completed_at IS 'Время последнего выполненного задания';
COMMENT ON COLUMN users.is_blocked IS 'Заблокировал ли пользователь бота';
COMMENT ON COLUMN users.post_1 IS 'Ссылка на пост задания 1';
COMMENT ON COLUMN users.post_2 IS 'Ссылка на пост задания 2';
-- И так далее до post_14

-- 2. Создаем 14 таблиц для каждого дня курса (digest_day_1 ... digest_day_14)
-- Каждая таблица содержит: Задание, Вопрос 1, Вопрос 2, Вопрос 3, Промпт

-- Функция для создания таблицы дня
CREATE OR REPLACE FUNCTION create_digest_day_table(day_num INT) RETURNS VOID AS $$
DECLARE
    table_name TEXT := 'digest_day_' || day_num;
BEGIN
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I (
            id SERIAL PRIMARY KEY,
            zadanie TEXT NOT NULL,
            vopros_1 TEXT,
            vopros_2 TEXT,
            vopros_3 TEXT,
            prompt TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', table_name);
    
    -- Добавляем комментарии
    EXECUTE format('COMMENT ON TABLE %I IS ''Задания для дня %s курса''', table_name, day_num);
    EXECUTE format('COMMENT ON COLUMN %I.zadanie IS ''Текст задания (HTML)''', table_name);
    EXECUTE format('COMMENT ON COLUMN %I.vopros_1 IS ''Первый вопрос''', table_name);
    EXECUTE format('COMMENT ON COLUMN %I.vopros_2 IS ''Второй вопрос''', table_name);
    EXECUTE format('COMMENT ON COLUMN %I.vopros_3 IS ''Третий вопрос''', table_name);
    EXECUTE format('COMMENT ON COLUMN %I.prompt IS ''Промпт для задания''', table_name);
END;
$$ LANGUAGE plpgsql;

-- Создаем 14 таблиц
SELECT create_digest_day_table(1);
SELECT create_digest_day_table(2);
SELECT create_digest_day_table(3);
SELECT create_digest_day_table(4);
SELECT create_digest_day_table(5);
SELECT create_digest_day_table(6);
SELECT create_digest_day_table(7);
SELECT create_digest_day_table(8);
SELECT create_digest_day_table(9);
SELECT create_digest_day_table(10);
SELECT create_digest_day_table(11);
SELECT create_digest_day_table(12);
SELECT create_digest_day_table(13);
SELECT create_digest_day_table(14);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_digest_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Создаем триггеры для всех таблиц
DO $$
DECLARE
    day_num INT;
    table_name TEXT;
BEGIN
    FOR day_num IN 1..14 LOOP
        table_name := 'digest_day_' || day_num;
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION update_digest_updated_at_column();
        ', table_name, table_name, table_name, table_name);
    END LOOP;
END;
$$;

-- 3. Создаем таблицу для хранения глобального состояния курса
CREATE TABLE IF NOT EXISTS course_state (
    id INT PRIMARY KEY DEFAULT 1,
    is_active BOOLEAN DEFAULT FALSE,
    current_day INT DEFAULT 0,
    start_date TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT single_row CHECK (id = 1)
);

-- Вставляем единственную запись состояния курса
INSERT INTO course_state (id, is_active, current_day) 
VALUES (1, FALSE, 0)
ON CONFLICT (id) DO NOTHING;

-- Комментарии к таблице состояния курса
COMMENT ON TABLE course_state IS 'Глобальное состояние курса (только одна запись)';
COMMENT ON COLUMN course_state.is_active IS 'Активен ли курс сейчас';
COMMENT ON COLUMN course_state.current_day IS 'Текущий день курса (0-14)';
COMMENT ON COLUMN course_state.start_date IS 'Дата начала курса';

-- 4. Примеры добавления заданий (раскомментируйте и отредактируйте)
-- Вставьте данные в каждую таблицу вручную через Table Editor или SQL

-- Пример для digest_day_1:
-- INSERT INTO digest_day_1 (zadanie, vopros_1, vopros_2, vopros_3, prompt) VALUES
-- (
--   '<b>Первое задание курса</b><br>Опишите ваш канал и его цели...',
--   'Какая основная тема вашего канала?',
--   'Кто ваша целевая аудитория?',
--   'Какую пользу получат подписчики?',
--   'Создай пост-знакомство для Telegram канала о...'
-- );

-- Повторите для digest_day_2 ... digest_day_14

-- 5. Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_users_course_state ON users(course_state);
CREATE INDEX IF NOT EXISTS idx_users_current_task ON users(current_task);
CREATE INDEX IF NOT EXISTS idx_users_penalties ON users(penalties);

