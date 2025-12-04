#!/bin/bash

# ============================================================
# 🏥 ПРОВЕРКА ЗДОРОВЬЯ БОТА
# ============================================================
# Запускайте этот скрипт для быстрой диагностики проблем
# ============================================================

CONTAINER="telegram-bot"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            🏥 ПРОВЕРКА ЗДОРОВЬЯ БОТА                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 1. Статус контейнера
echo "1️⃣ СТАТУС КОНТЕЙНЕРА:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
STATUS=$(docker ps --filter "name=$CONTAINER" --format "{{.Status}}")
if [ -z "$STATUS" ]; then
    echo "   ❌ Контейнер НЕ ЗАПУЩЕН!"
else
    echo "   ✅ $STATUS"
fi
echo ""

# 2. Состояние курса
echo "2️⃣ СОСТОЯНИЕ КУРСА:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec -it supabase-db psql -U postgres -d postgres -t -c \
    "SELECT 'Активен: ' || is_active || ', День: ' || current_day FROM course_state WHERE id = 1;" 2>/dev/null || echo "   ❌ Не удалось получить данные"
echo ""

# 3. Последние ошибки
echo "3️⃣ ПОСЛЕДНИЕ ОШИБКИ (за 1 час):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ERRORS=$(docker logs --since=1h $CONTAINER 2>&1 | grep -c "ERROR")
if [ "$ERRORS" -gt 0 ]; then
    echo "   ⚠️ Найдено $ERRORS ошибок!"
    echo ""
    docker logs --since=1h $CONTAINER 2>&1 | grep "ERROR" | tail -5
else
    echo "   ✅ Ошибок нет"
fi
echo ""

# 4. Пользователи с проблемами
echo "4️⃣ ПОЛЬЗОВАТЕЛИ С 3+ ШТРАФАМИ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec -it supabase-db psql -U postgres -d postgres -c \
    "SELECT telegram_id, first_name, penalties FROM users WHERE penalties >= 3;" 2>/dev/null || echo "   Нет данных"
echo ""

# 5. Заблокированные пользователи
echo "5️⃣ ЗАБЛОКИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
BLOCKED=$(docker exec -it supabase-db psql -U postgres -d postgres -t -c \
    "SELECT COUNT(*) FROM users WHERE is_blocked = true;" 2>/dev/null | tr -d ' ')
echo "   Заблокировано: $BLOCKED"
echo ""

# 6. Статистика пользователей
echo "6️⃣ СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker exec -it supabase-db psql -U postgres -d postgres -c \
    "SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN course_state = 'in_progress' THEN 1 ELSE 0 END) as in_course,
        SUM(CASE WHEN penalties > 0 THEN 1 ELSE 0 END) as with_penalties
    FROM users;" 2>/dev/null || echo "   Нет данных"
echo ""

# 7. Последняя активность планировщика
echo "7️⃣ ПОСЛЕДНЯЯ АКТИВНОСТЬ ПЛАНИРОВЩИКА:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs --since=24h $CONTAINER 2>&1 | grep "ПЛАНИРОВЩИК" | tail -5
echo ""

# 8. n8n взаимодействия
echo "8️⃣ N8N ТАЙМАУТЫ (за 24ч):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
N8N_ERRORS=$(docker logs --since=24h $CONTAINER 2>&1 | grep -c "n8n.*timeout\|n8n.*404\|Таймаут")
if [ "$N8N_ERRORS" -gt 0 ]; then
    echo "   ⚠️ Найдено $N8N_ERRORS проблем с n8n"
else
    echo "   ✅ Проблем с n8n нет"
fi
echo ""

# 9. Текущее время сервера
echo "9️⃣ ВРЕМЯ СЕРВЕРА:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   $(date)"
echo ""

echo "╔══════════════════════════════════════════════════════════╗"
echo "║            ✅ ПРОВЕРКА ЗАВЕРШЕНА                         ║"
echo "╚══════════════════════════════════════════════════════════╝"


