#!/bin/bash

# Скрипт для проверки current_task конкретного пользователя

TELEGRAM_ID=8098626207

echo "🔍 ПРОВЕРКА CURRENT_TASK ДЛЯ ПОЛЬЗОВАТЕЛЯ $TELEGRAM_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 Данные из базы:"
docker exec supabase-db psql -U postgres -d postgres -c "SELECT telegram_id, state, course_state, current_task, penalties FROM users WHERE telegram_id = $TELEGRAM_ID;"

echo ""
echo "🔍 Проверка типа данных current_task:"
docker exec supabase-db psql -U postgres -d postgres -c "SELECT telegram_id, current_task, pg_typeof(current_task) FROM users WHERE telegram_id = $TELEGRAM_ID;"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"



