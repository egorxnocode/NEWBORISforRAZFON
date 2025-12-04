#!/bin/bash

# Скрипт для проверки состояния базы данных

echo "🔍 ПРОВЕРКА СОСТОЯНИЯ БАЗЫ ДАННЫХ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1️⃣ Состояние курса:"
docker exec supabase-db psql -U postgres -d postgres -c "SELECT * FROM course_state;"

echo ""
echo "2️⃣ Пользователи в курсе:"
docker exec supabase-db psql -U postgres -d postgres -c "SELECT telegram_id, state, course_state, current_task, penalties FROM users WHERE course_state = 'in_course';"

echo ""
echo "3️⃣ Все пользователи:"
docker exec supabase-db psql -U postgres -d postgres -c "SELECT telegram_id, email, state, course_state, current_task FROM users ORDER BY id;"

echo ""
echo "4️⃣ Задания в digest_day_1:"
docker exec supabase-db psql -U postgres -d postgres -c "SELECT id, substring(zadanie, 1, 50) as zadanie FROM digest_day_1 LIMIT 1;"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"



