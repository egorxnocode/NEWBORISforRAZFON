#!/bin/bash

# ============================================================
# Скрипт исправления проблем на сервере
# ============================================================

set -e

echo "🔧 ИСПРАВЛЕНИЕ ПРОБЛЕМ БОТА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd /opt/NEWBORISforRAZFON

# 1. Остановка контейнера
echo "1️⃣ Остановка контейнера..."
docker stop telegram-bot 2>/dev/null || echo "Контейнер уже остановлен"
docker rm telegram-bot 2>/dev/null || echo "Контейнер удален"
echo "✅ Контейнер остановлен"
echo ""

# 2. Подключение к сетям
echo "2️⃣ Проверка Docker сетей..."
if docker network inspect supabase_default >/dev/null 2>&1; then
    echo "✅ Сеть supabase_default найдена"
else
    echo "❌ Сеть supabase_default не найдена!"
    echo "Список сетей:"
    docker network ls
    exit 1
fi

if docker network inspect n8n_default >/dev/null 2>&1; then
    echo "✅ Сеть n8n_default найдена"
else
    echo "❌ Сеть n8n_default не найдена!"
    exit 1
fi
echo ""

# 3. Обновление .env
echo "3️⃣ Обновление .env файла..."
if [ -f ".env" ]; then
    # Исправляем URL Supabase (используем внутренний порт 8000)
    sed -i 's|SUPABASE_URL=http://supabase:8009|SUPABASE_URL=http://supabase-kong:8000|g' .env
    sed -i 's|SUPABASE_URL=http://supabase:8000|SUPABASE_URL=http://supabase-kong:8000|g' .env
    
    echo "✅ .env обновлен"
    echo ""
    echo "Текущие настройки:"
    grep -E "SUPABASE_URL|N8N_WEBHOOK_URL" .env
else
    echo "❌ .env файл не найден!"
    exit 1
fi
echo ""

# 4. Обновление requirements.txt
echo "4️⃣ Обновление requirements.txt (исправление конфликта версий)..."
cat > requirements.txt << 'EOF'
aiogram==3.3.0
python-dotenv==1.0.0
supabase==2.9.1
httpx==0.27.2
aiohttp==3.9.1
validators==0.22.0
apscheduler==3.10.4
pytz==2023.3
openai==1.6.1
pydub==0.25.1
EOF
echo "✅ requirements.txt обновлен"
echo ""

# 5. Обновление docker-compose
echo "5️⃣ Создание docker-compose для двух сетей..."
cat > docker-compose.fixed.yml << 'EOF'
version: '3.8'

services:
  telegram-bot:
    build: .
    container_name: telegram-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./media:/app/media
      - ./audio_temp:/app/audio_temp
      - ./logs:/app/logs
    ports:
      - "8080:8080"
    networks:
      - n8n_default
      - supabase_default
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  n8n_default:
    external: true
  supabase_default:
    external: true
EOF
echo "✅ docker-compose.fixed.yml создан"
echo ""

# 6. Пересборка и запуск
echo "6️⃣ Пересборка и запуск контейнера..."
docker-compose -f docker-compose.fixed.yml build --no-cache
docker-compose -f docker-compose.fixed.yml up -d
echo "✅ Контейнер запущен"
echo ""

# 7. Проверка
echo "7️⃣ Проверка логов (10 секунд)..."
sleep 10
docker logs --tail=30 telegram-bot
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Проверка сетей:"
docker inspect telegram-bot --format='Сети: {{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
echo ""
echo "📝 Для просмотра логов:"
echo "   docker logs -f telegram-bot"

