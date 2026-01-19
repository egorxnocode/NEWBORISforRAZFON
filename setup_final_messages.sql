-- ============================================================
-- ТАБЛИЦА ДЛЯ ФИНАЛЬНЫХ СООБЩЕНИЙ 15 ДНЯ
-- ============================================================

-- Создаем таблицу для финальных сообщений
CREATE TABLE IF NOT EXISTS final_messages (
    id SERIAL PRIMARY KEY,
    message_number INTEGER UNIQUE NOT NULL, -- 1, 2, 3
    send_time VARCHAR(5) NOT NULL,          -- "10:00", "15:00", "15:55"
    message_text TEXT NOT NULL,
    has_media BOOLEAN DEFAULT false,
    media_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_final_messages_number ON final_messages(message_number);

-- Комментарии
COMMENT ON TABLE final_messages IS 'Финальные сообщения 15 дня курса (после 14 задания)';
COMMENT ON COLUMN final_messages.message_number IS 'Номер сообщения (1, 2, 3)';
COMMENT ON COLUMN final_messages.send_time IS 'Время отправки (10:00, 15:00, 15:55)';
COMMENT ON COLUMN final_messages.message_text IS 'Текст сообщения';
COMMENT ON COLUMN final_messages.has_media IS 'Есть ли медиафайл';
COMMENT ON COLUMN final_messages.media_path IS 'Путь к медиафайлу (если есть)';

-- Вставляем дефолтные значения для 3 финальных сообщений
INSERT INTO final_messages (message_number, send_time, message_text, has_media, media_path)
VALUES 
(1, '10:00', 
'🎉 <b>Поздравляю!</b>

Вы завершили 14-дневный курс! 

Сегодня последний день, и у меня для вас есть важные сообщения.

Следите за обновлениями! 👀', 
false, 
NULL),

(2, '15:00',
'💡 <b>Важное сообщение</b>

Текст второго финального сообщения.

Вы можете изменить этот текст в таблице final_messages.', 
false, 
NULL),

(3, '15:55',
'🏁 <b>Финал курса</b>

Спасибо за участие в курсе!

Это последнее сообщение. Желаем вам успехов! 🚀', 
false, 
NULL)
ON CONFLICT (message_number) DO NOTHING;

-- Триггер для автоматического обновления updated_at
CREATE TRIGGER update_final_messages_updated_at
    BEFORE UPDATE ON final_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

