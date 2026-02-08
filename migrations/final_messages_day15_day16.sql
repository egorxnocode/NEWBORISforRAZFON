-- ============================================================
-- ФИНАЛЬНЫЕ СООБЩЕНИЯ: ДЕНЬ 15 (1 сообщение) + ДЕНЬ 16 (3 сообщения)
-- ============================================================
--
-- Новая структура:
-- День 15: одно сообщение в 10:00
-- День 16: три сообщения в 10:00, 15:00, 15:55
--
-- ============================================================

-- 1. Таблица final_messages: добавляем колонку course_day (15 или 16)
ALTER TABLE final_messages ADD COLUMN IF NOT EXISTS course_day INTEGER NOT NULL DEFAULT 16;

-- Уникальность по (course_day, message_number). Снимаем старый unique с message_number.
ALTER TABLE final_messages DROP CONSTRAINT IF EXISTS final_messages_message_number_key;
ALTER TABLE final_messages DROP CONSTRAINT IF EXISTS final_messages_message_number_unique;
CREATE UNIQUE INDEX IF NOT EXISTS idx_final_messages_course_day_number 
ON final_messages(course_day, message_number);

-- Все существующие строки уже получили course_day = 16 через DEFAULT

-- Вставляем единственное сообщение дня 15 (10:00)
INSERT INTO final_messages (course_day, message_number, send_time, message_text, has_media, media_path)
VALUES (
    15,
    1,
    '10:00',
    '🎉 <b>Поздравляю!</b>

Вы завершили 14-дневный курс!

Сегодня для вас одно важное сообщение. Завтра в 10:00, 15:00 и 15:55 ждите ещё три финальных сообщения — не пропустите! 👀',
    false,
    NULL
)
ON CONFLICT (course_day, message_number) DO NOTHING;

COMMENT ON COLUMN final_messages.course_day IS 'День курса: 15 (одно сообщение в 10:00) или 16 (три сообщения 10:00, 15:00, 15:55)';

-- 2. Таблица users: флаг для единственного сообщения дня 15
ALTER TABLE users ADD COLUMN IF NOT EXISTS final_message_15_sent BOOLEAN DEFAULT FALSE;
COMMENT ON COLUMN users.final_message_15_sent IS 'Отправлено ли единственное финальное сообщение 15 дня (10:00)';
CREATE INDEX IF NOT EXISTS idx_users_final_message_15 ON users(final_message_15_sent);

-- final_message_1_sent, final_message_2_sent, final_message_3_sent — используются для дня 16

-- Проверка
SELECT course_day, message_number, send_time, LEFT(message_text, 40) AS text_preview 
FROM final_messages 
ORDER BY course_day, message_number;
