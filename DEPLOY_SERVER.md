# 🖥️ Инструкция по развертыванию на сервере

## Требования к серверу

- **ОС**: Ubuntu 20.04+ / Debian 11+
- **RAM**: минимум 512 MB (рекомендуется 1 GB+)
- **Disk**: минимум 2 GB свободного места
- **Python**: 3.8+
- **Порты**: 8080 (для webhook от n8n)

---

## 🚀 Автоматическое развертывание

### Способ 1: Скрипт развертывания (рекомендуется)

1. **Подключитесь к серверу:**

```bash
ssh user@your-server-ip
```

2. **Скачайте и запустите скрипт:**

```bash
# Скачайте репозиторий временно
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git /tmp/bot-deploy
cd /tmp/bot-deploy

# Отредактируйте deploy.sh (замените YOUR_USERNAME и YOUR_REPO)
nano deploy.sh

# Сделайте скрипт исполняемым
chmod +x deploy.sh

# Запустите скрипт
./deploy.sh
```

3. **Настройте .env:**

```bash
nano /opt/telegram-bot/.env
```

Заполните все переменные:

```env
BOT_TOKEN=your_bot_token
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_key
ADMIN_IDS=123456789
COURSE_CHAT_ID=-1001234567890
MONITORING_CHAT_ID=-1001234567891
OPENAI_API_KEY=sk-your_key
N8N_WEBHOOK_URL=https://your-n8n.com/webhook
TIMEZONE=Europe/Moscow
```

4. **Загрузите медиафайлы:**

```bash
# Через SCP (с вашего компьютера)
scp -r media/* user@your-server-ip:/opt/telegram-bot/media/

# Или создайте вручную на сервере
cd /opt/telegram-bot/media
# ... загрузите файлы
```

5. **Запустите бота:**

```bash
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

---

## 🔧 Ручное развертывание

### Шаг 1: Подключение к серверу

```bash
ssh user@your-server-ip
```

### Шаг 2: Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
```

### Шаг 3: Установка зависимостей

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

### Шаг 4: Клонирование репозитория

```bash
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git telegram-bot
cd telegram-bot
sudo chown -R $USER:$USER /opt/telegram-bot
```

### Шаг 5: Виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Шаг 6: Настройка .env

```bash
cp ENV_EXAMPLE.txt .env
nano .env
```

### Шаг 7: Создание systemd сервиса

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Вставьте:

```ini
[Unit]
Description=Telegram Course Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/telegram-bot
Environment="PATH=/opt/telegram-bot/venv/bin"
ExecStart=/opt/telegram-bot/venv/bin/python /opt/telegram-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Замените `YOUR_USERNAME` на ваше имя пользователя!**

### Шаг 8: Активация сервиса

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

---

## 📁 Загрузка медиафайлов

### Через SCP (с вашего компьютера)

```bash
# Загрузка всех медиафайлов
scp -r /path/to/local/media/* user@server-ip:/opt/telegram-bot/media/

# Загрузка конкретной директории
scp /path/to/welcome_video.mp4 user@server-ip:/opt/telegram-bot/media/
scp -r /path/to/tasks/* user@server-ip:/opt/telegram-bot/media/tasks/
```

### Через SFTP (GUI)

Используйте FileZilla или WinSCP:
1. Подключитесь к серверу
2. Перейдите в `/opt/telegram-bot/media/`
3. Загрузите файлы

---

## 🔥 Настройка Firewall (опционально)

```bash
# Открыть порт 8080 для n8n webhook
sudo ufw allow 8080/tcp

# Если используете ufw
sudo ufw enable
sudo ufw status
```

---

## 📊 Управление ботом

### Запуск

```bash
sudo systemctl start telegram-bot
```

### Остановка

```bash
sudo systemctl stop telegram-bot
```

### Перезапуск

```bash
sudo systemctl restart telegram-bot
```

### Статус

```bash
sudo systemctl status telegram-bot
```

### Логи

```bash
# Просмотр логов в реальном времени
sudo journalctl -u telegram-bot -f

# Последние 100 строк
sudo journalctl -u telegram-bot -n 100

# Логи за сегодня
sudo journalctl -u telegram-bot --since today
```

---

## 🔄 Обновление бота

```bash
cd /opt/telegram-bot

# Остановить бота
sudo systemctl stop telegram-bot

# Обновить код
git pull

# Обновить зависимости (если изменились)
source venv/bin/activate
pip install -r requirements.txt

# Запустить бота
sudo systemctl start telegram-bot

# Проверить статус
sudo systemctl status telegram-bot
```

---

## 🐛 Устранение неполадок

### Бот не запускается

```bash
# Проверьте логи
sudo journalctl -u telegram-bot -n 50

# Проверьте .env файл
cat /opt/telegram-bot/.env

# Проверьте права на файлы
ls -la /opt/telegram-bot/
```

### Бот работает, но не отвечает

```bash
# Проверьте токен бота
# Проверьте подключение к Supabase
# Проверьте медиафайлы

# Перезапустите
sudo systemctl restart telegram-bot
```

### Ошибки с медиафайлами

```bash
# Проверьте наличие файлов
ls -la /opt/telegram-bot/media/
ls -la /opt/telegram-bot/media/tasks/

# Проверьте права
chmod -R 755 /opt/telegram-bot/media/
```

---

## 🔐 Безопасность

1. **Не коммитьте .env в Git** (уже в .gitignore)
2. **Используйте firewall** (ufw)
3. **Регулярно обновляйте систему**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
4. **Используйте SSH ключи вместо паролей**
5. **Ограничьте доступ к порту 8080** (только для n8n IP)

---

## 📝 Чеклист развертывания

- [ ] Сервер с Ubuntu/Debian
- [ ] Python 3.8+ установлен
- [ ] Репозиторий клонирован
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] .env настроен
- [ ] Supabase настроен (таблицы созданы)
- [ ] Медиафайлы загружены
- [ ] Systemd сервис создан
- [ ] Бот запущен
- [ ] Логи проверены
- [ ] Тестовая команда /start работает

---

## 🎯 После развертывания

1. **Проверьте работу бота:**
   - Отправьте `/start`
   - Проверьте регистрацию
   - Проверьте команды админа

2. **Настройте мониторинг:**
   - Создайте чат для мониторинга
   - Добавьте бота в чат
   - Проверьте отчеты

3. **Проверьте планировщик:**
   ```bash
   # Логи планировщика
   sudo journalctl -u telegram-bot | grep "Планировщик"
   ```

4. **Настройте резервное копирование** (рекомендуется)

---

**Бот готов к работе! 🚀**

Для получения помощи смотрите:
- БЫСТРЫЙ_СТАРТ.txt
- ИНСТРУКЦИЯ.md
- МОНИТОРИНГ.md

