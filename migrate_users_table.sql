-- Миграция таблицы users - добавление недостающих колонок
-- Выполните этот скрипт если таблица users уже существует

-- Добавляем колонки для курса (если их нет)
ALTER TABLE users ADD COLUMN IF NOT EXISTS penalties INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS current_task INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS course_state VARCHAR(50) DEFAULT 'not_started';

-- Добавляем временные метки (если их нет)
ALTER TABLE users ADD COLUMN IF NOT EXISTS registered_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_task_sent_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reminder_sent_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at TIMESTAMP WITH TIME ZONE;

-- Проверка структуры таблицы
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;

-- Сообщение об успехе
SELECT 'Миграция завершена! Все колонки добавлены.' as status;



