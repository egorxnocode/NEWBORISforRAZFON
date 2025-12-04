-- Миграция для добавления колонок для хранения message_id
-- Это позволяет удалять старые сообщения при отправке новых заданий

-- Добавляем колонку для хранения ID последнего сообщения с заданием
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_task_message_id BIGINT;

-- Добавляем колонку для хранения списка ID сообщений для удаления (через запятую)
ALTER TABLE users ADD COLUMN IF NOT EXISTS messages_to_delete TEXT;

-- Проверяем результат
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('last_task_message_id', 'messages_to_delete');

