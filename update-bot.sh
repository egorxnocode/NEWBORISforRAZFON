#!/bin/bash

# ============================================================
# Скрипт быстрого обновления бота на сервере
# ============================================================

set -e

echo "🔄 ОБНОВЛЕНИЕ БОТА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd /opt/NEWBORISforRAZFON

# 1. Получаем последние изменения
echo "1️⃣ Получение обновлений из GitHub..."
git pull origin main
echo "✅ Код обновлен"
echo ""

# 2. Останавливаем контейнер
echo "2️⃣ Остановка контейнера..."
docker stop telegram-bot 2>/dev/null || echo "Контейнер уже остановлен"
echo "✅ Контейнер остановлен"
echo ""

# 3. Пересборка образа без кэша
echo "3️⃣ Пересборка образа (это займет 1-2 минуты)..."
if [ -f "docker-compose.fixed.yml" ]; then
    docker-compose -f docker-compose.fixed.yml build --no-cache
else
    docker-compose -f docker-compose.production.yml build --no-cache 2>/dev/null || docker build --no-cache -t telegram-bot .
fi
echo "✅ Образ пересобран"
echo ""

# 4. Запуск контейнера
echo "4️⃣ Запуск контейнера..."
if [ -f "docker-compose.fixed.yml" ]; then
    docker-compose -f docker-compose.fixed.yml up -d
elif [ -f "docker-compose.production.yml" ]; then
    docker-compose -f docker-compose.production.yml up -d
else
    docker run -d \
        --name telegram-bot \
        --restart unless-stopped \
        --env-file .env \
        -v $(pwd)/media:/app/media \
        -v $(pwd)/audio_temp:/app/audio_temp \
        -v $(pwd)/logs:/app/logs \
        -p 8080:8080 \
        --network n8n_default \
        telegram-bot
    docker network connect supabase_default telegram-bot
fi
echo "✅ Контейнер запущен"
echo ""

# 5. Ожидание запуска
echo "5️⃣ Ожидание запуска (10 секунд)..."
sleep 10
echo ""

# 6. Проверка логов
echo "6️⃣ Проверка логов:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs --tail=30 telegram-bot
echo ""

# 7. Статус
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Статус контейнера:"
docker ps --filter name=telegram-bot --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ""
echo "📝 Для просмотра логов в реальном времени:"
echo "   docker logs -f telegram-bot"
echo ""

