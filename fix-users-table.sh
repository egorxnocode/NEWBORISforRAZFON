#!/bin/bash

# ============================================================
# Скрипт исправления структуры таблицы users
# ============================================================

echo "🔧 ИСПРАВЛЕНИЕ СТРУКТУРЫ ТАБЛИЦЫ USERS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd /opt/NEWBORISforRAZFON

echo "1️⃣ Выполнение миграции..."
echo ""

# Выполняем миграцию через Docker
docker exec -i supabase-db psql -U postgres -d postgres << 'EOF'
-- Миграция таблицы users - добавление недостающих колонок

ALTER TABLE users ADD COLUMN IF NOT EXISTS penalties INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS current_task INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS course_state VARCHAR(50) DEFAULT 'not_started';

ALTER TABLE users ADD COLUMN IF NOT EXISTS registered_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_task_sent_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reminder_sent_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at TIMESTAMP WITH TIME ZONE;

SELECT 'Миграция завершена! Все колонки добавлены.' as status;
EOF

echo ""
echo "2️⃣ Проверка структуры таблицы..."
echo ""

docker exec supabase-db psql -U postgres -d postgres -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position;"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Теперь можно использовать команду /razgon_stop"
echo ""



