-- ============================================================
-- ОБНОВЛЕНИЕ ТАБЛИЦЫ USERS ДЛЯ ФИНАЛЬНЫХ СООБЩЕНИЙ
-- ============================================================

-- Добавляем поля для отслеживания отправки финальных сообщений
-- День 15: одно сообщение (final_message_15_sent)
-- День 16: три сообщения (final_message_1_sent, _2_sent, _3_sent)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS final_message_15_sent BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS final_message_1_sent BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS final_message_2_sent BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS final_message_3_sent BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS course_finished_at TIMESTAMP WITH TIME ZONE;

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_users_final_message_1 ON users(final_message_1_sent);
CREATE INDEX IF NOT EXISTS idx_users_final_message_2 ON users(final_message_2_sent);
CREATE INDEX IF NOT EXISTS idx_users_final_message_3 ON users(final_message_3_sent);

-- Комментарии
COMMENT ON COLUMN users.final_message_15_sent IS 'Отправлено ли единственное финальное сообщение 15 дня (10:00)';
COMMENT ON COLUMN users.final_message_1_sent IS 'Отправлено ли финальное сообщение дня 16 №1 (10:00)';
COMMENT ON COLUMN users.final_message_2_sent IS 'Отправлено ли финальное сообщение дня 16 №2 (15:00)';
COMMENT ON COLUMN users.final_message_3_sent IS 'Отправлено ли финальное сообщение дня 16 №3 (15:55)';
COMMENT ON COLUMN users.course_finished_at IS 'Время завершения 14 задания';

