#!/bin/bash

# Скрипт для ручного исправления current_task

if [ -z "$1" ]; then
    echo "❌ Использование: bash fix-current-task.sh <telegram_id> <task_number>"
    echo "Пример: bash fix-current-task.sh 8098626207 1"
    exit 1
fi

if [ -z "$2" ]; then
    echo "❌ Использование: bash fix-current-task.sh <telegram_id> <task_number>"
    echo "Пример: bash fix-current-task.sh 8098626207 1"
    exit 1
fi

TELEGRAM_ID=$1
TASK_NUMBER=$2

echo "🔧 ИСПРАВЛЕНИЕ CURRENT_TASK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 Текущее состояние пользователя $TELEGRAM_ID:"
docker exec supabase-db psql -U postgres -d postgres -c "SELECT telegram_id, state, course_state, current_task, penalties FROM users WHERE telegram_id = $TELEGRAM_ID;"

echo ""
echo "🔄 Устанавливаем current_task = $TASK_NUMBER..."
docker exec supabase-db psql -U postgres -d postgres -c "UPDATE users SET current_task = $TASK_NUMBER WHERE telegram_id = $TELEGRAM_ID;"

echo ""
echo "✅ Обновленное состояние:"
docker exec supabase-db psql -U postgres -d postgres -c "SELECT telegram_id, state, course_state, current_task, penalties FROM users WHERE telegram_id = $TELEGRAM_ID;"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ГОТОВО! Теперь попробуйте нажать кнопку в боте."



