#!/bin/bash

# ============================================================
# Скрипт автоматического развертывания бота на сервере
# ============================================================

set -e  # Остановить при ошибке

echo "🚀 Начинаем развертывание бота в Docker..."
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    exit 1
fi

echo "✅ Docker установлен"

# Проверка существующих контейнеров
echo ""
echo "📊 Проверка существующих контейнеров:"
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'

echo ""
echo "🔍 Проверка Docker сетей:"
docker network ls

# Ищем n8n контейнер
echo ""
echo "🔍 Поиск n8n контейнера..."
N8N_CONTAINER=$(docker ps --filter "name=n8n" --format "{{.Names}}" | head -1)
if [ -z "$N8N_CONTAINER" ]; then
    echo "⚠️  n8n контейнер не найден. Ищу по образу..."
    N8N_CONTAINER=$(docker ps --filter "ancestor=n8nio/n8n" --format "{{.Names}}" | head -1)
fi

if [ -n "$N8N_CONTAINER" ]; then
    echo "✅ Найден n8n контейнер: $N8N_CONTAINER"
    N8N_NETWORK=$(docker inspect $N8N_CONTAINER --format='{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')
    echo "   Сеть: $N8N_NETWORK"
else
    echo "⚠️  n8n контейнер не найден"
fi

# Ищем Supabase контейнер
echo ""
echo "🔍 Поиск Supabase контейнера..."
SUPABASE_CONTAINER=$(docker ps --filter "name=supabase" --format "{{.Names}}" | head -1)
if [ -z "$SUPABASE_CONTAINER" ]; then
    echo "⚠️  Supabase контейнер не найден. Ищу по портам..."
    SUPABASE_CONTAINER=$(docker ps --filter "publish=8000" --format "{{.Names}}" | head -1)
fi

if [ -n "$SUPABASE_CONTAINER" ]; then
    echo "✅ Найден Supabase контейнер: $SUPABASE_CONTAINER"
    SUPABASE_NETWORK=$(docker inspect $SUPABASE_CONTAINER --format='{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')
    echo "   Сеть: $SUPABASE_NETWORK"
else
    echo "⚠️  Supabase контейнер не найден"
fi

# Определяем общую сеть
echo ""
echo "🔗 Определение Docker сети..."
if [ -n "$N8N_NETWORK" ]; then
    DOCKER_NETWORK=$N8N_NETWORK
elif [ -n "$SUPABASE_NETWORK" ]; then
    DOCKER_NETWORK=$SUPABASE_NETWORK
else
    echo "⚠️  Не найдена сеть. Создаем новую..."
    DOCKER_NETWORK="bot-network"
    docker network create $DOCKER_NETWORK 2>/dev/null || echo "Сеть уже существует"
fi

echo "✅ Используем сеть: $DOCKER_NETWORK"

# Клонирование репозитория
echo ""
echo "📥 Клонирование репозитория..."
cd /opt
if [ -d "NEWBORISforRAZFON" ]; then
    echo "📂 Репозиторий уже существует, обновляем..."
    cd NEWBORISforRAZFON
    git pull
else
    git clone https://github.com/egorxnocode/NEWBORISforRAZFON.git
    cd NEWBORISforRAZFON
fi

echo "✅ Репозиторий готов"

# Создание .env файла
echo ""
echo "⚙️  Создание .env файла..."

if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# ============================================================
# TELEGRAM BOT CONFIGURATION
# ============================================================

BOT_TOKEN=ЗАМЕНИТЕ_НА_ВАШ_ТОКЕН

# ============================================================
# SUPABASE (Docker internal)
# ============================================================
SUPABASE_URL=http://supabase:8000
SUPABASE_KEY=ЗАМЕНИТЕ_НА_ВАШ_КЛЮЧ

# ============================================================
# N8N (Docker internal)
# ============================================================
N8N_WEBHOOK_URL=http://n8n:5678/webhook/generate-post
N8N_TIMEOUT=300

# ============================================================
# ADMIN SETTINGS
# ============================================================
ADMIN_IDS=ЗАМЕНИТЕ_НА_ВАШ_TELEGRAM_ID
COURSE_CHAT_ID=-1001234567890
MONITORING_CHAT_ID=-1001234567891

# ============================================================
# OPENAI
# ============================================================
OPENAI_API_KEY=ЗАМЕНИТЕ_НА_ВАШ_КЛЮЧ

# ============================================================
# OTHER
# ============================================================
TIMEZONE=Europe/Moscow
EOF
    echo "✅ Создан .env файл (ТРЕБУЕТ НАСТРОЙКИ!)"
    echo ""
    echo "⚠️  ВАЖНО: Отредактируйте файл .env перед запуском!"
    echo "   nano /opt/NEWBORISforRAZFON/.env"
    echo ""
else
    echo "✅ .env файл уже существует"
fi

# Обновление docker-compose с правильной сетью
echo ""
echo "⚙️  Настройка docker-compose..."

cat > docker-compose.production.yml << EOF
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
      - ${DOCKER_NETWORK}
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  ${DOCKER_NETWORK}:
    external: true
EOF

echo "✅ docker-compose настроен для сети: $DOCKER_NETWORK"

# Создание директорий для медиа
echo ""
echo "📁 Создание директорий для медиафайлов..."
mkdir -p media/tasks media/penalties media/reminders audio_temp logs
chmod -R 755 media audio_temp logs
echo "✅ Директории созданы"

# Проверка портов
echo ""
echo "🔍 Проверка порта 8080..."
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Порт 8080 занят! Изменяем на 8081..."
    sed -i 's/"8080:8080"/"8081:8080"/' docker-compose.production.yml
    echo "✅ Порт изменен на 8081"
else
    echo "✅ Порт 8080 свободен"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ПОДГОТОВКА ЗАВЕРШЕНА!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1️⃣  Отредактируйте .env файл:"
echo "   nano /opt/NEWBORISforRAZFON/.env"
echo ""
echo "2️⃣  Загрузите медиафайлы в:"
echo "   /opt/NEWBORISforRAZFON/media/"
echo ""
echo "3️⃣  Запустите бота:"
echo "   cd /opt/NEWBORISforRAZFON"
echo "   docker-compose -f docker-compose.production.yml up -d --build"
echo ""
echo "4️⃣  Проверьте логи:"
echo "   docker logs -f telegram-bot"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

