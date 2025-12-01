#!/bin/bash

# ============================================================
# Скрипт развертывания бота на сервере
# ============================================================

set -e  # Остановить при ошибке

echo "🚀 Начинаем развертывание бота..."

# Обновление системы
echo "📦 Обновление системы..."
sudo apt update
sudo apt upgrade -y

# Установка Python 3.10+ и зависимостей
echo "🐍 Установка Python и зависимостей..."
sudo apt install -y python3 python3-pip python3-venv git

# Проверка версии Python
python3 --version

# Создание директории для проекта
echo "📁 Создание директории проекта..."
PROJECT_DIR="/opt/telegram-bot"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Клонирование репозитория
echo "📥 Клонирование репозитория..."
cd /opt
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "Репозиторий уже существует, обновляем..."
    cd $PROJECT_DIR
    git pull
else
    echo "Клонируем новый репозиторий..."
    # Замените на ваш репозиторий
    git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git telegram-bot
    cd $PROJECT_DIR
fi

# Создание виртуального окружения
echo "🔧 Создание виртуального окружения..."
python3 -m venv venv

# Активация виртуального окружения и установка зависимостей
echo "📚 Установка зависимостей..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Создание директорий для медиа
echo "📂 Создание директорий для медиафайлов..."
mkdir -p media/tasks
mkdir -p media/penalties
mkdir -p media/reminders

# Создание .env файла (если не существует)
if [ ! -f ".env" ]; then
    echo "⚙️  Создание .env файла..."
    cp ENV_EXAMPLE.txt .env
    echo ""
    echo "⚠️  ВАЖНО: Отредактируйте файл .env и добавьте свои настройки!"
    echo "   Файл находится здесь: $PROJECT_DIR/.env"
    echo ""
fi

# Создание systemd сервиса
echo "⚙️  Создание systemd сервиса..."
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Telegram Course Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
echo "🔄 Перезагрузка systemd..."
sudo systemctl daemon-reload

# Включение автозапуска
echo "✅ Включение автозапуска бота..."
sudo systemctl enable telegram-bot.service

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1. Отредактируйте .env файл:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Загрузите медиафайлы в директории:"
echo "   $PROJECT_DIR/media/"
echo "   $PROJECT_DIR/media/tasks/"
echo "   $PROJECT_DIR/media/penalties/"
echo "   $PROJECT_DIR/media/reminders/"
echo ""
echo "3. Запустите бота:"
echo "   sudo systemctl start telegram-bot"
echo ""
echo "4. Проверьте статус:"
echo "   sudo systemctl status telegram-bot"
echo ""
echo "5. Просмотр логов:"
echo "   sudo journalctl -u telegram-bot -f"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

