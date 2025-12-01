# 🐳 Развертывание бота через Docker

## 📋 Содержание

1. [Вариант 1: Все в одной сети (новые контейнеры)](#вариант-1-все-в-одной-сети)
2. [Вариант 2: Подключение к существующим n8n и Supabase](#вариант-2-подключение-к-существующим-сервисам)
3. [Настройка .env для Docker](#настройка-env-для-docker)
4. [Управление контейнерами](#управление-контейнерами)
5. [Troubleshooting](#troubleshooting)

---

## 🎯 Вариант 1: Все в одной сети

Если вы хотите запустить бота вместе с новыми контейнерами n8n и Supabase.

### Шаг 1: Подготовка

```bash
# Клонируйте репозиторий
git clone https://github.com/egorxnocode/NEWBORISforRAZFON.git
cd NEWBORISforRAZFON

# Создайте .env файл
cp .env.docker .env
nano .env
```

### Шаг 2: Настройте .env

```env
BOT_TOKEN=your_bot_token

# Внутренние Docker URLs (контейнеры в одной сети)
SUPABASE_URL=http://supabase:8000
SUPABASE_KEY=your_key

N8N_WEBHOOK_URL=http://n8n:5678/webhook/generate-post

ADMIN_IDS=123456789
COURSE_CHAT_ID=-1001234567890
MONITORING_CHAT_ID=-1001234567891
OPENAI_API_KEY=sk-your_key
TIMEZONE=Europe/Moscow
```

### Шаг 3: Загрузите медиафайлы

```bash
# Создайте директории
mkdir -p media/tasks media/penalties media/reminders

# Загрузите ваши файлы в:
# media/welcome_video.mp4
# media/channel_request.jpg
# media/final_message.jpg
# media/instruction.mp4
# media/tasks/task_1.jpg ... task_14.jpg
# media/penalties/penalty.jpg
# media/reminders/reminder_1.jpg, reminder_2.jpg, reminder_3.jpg
```

### Шаг 4: Запустите контейнеры

```bash
# Соберите и запустите
docker-compose up -d --build

# Проверьте статус
docker-compose ps

# Смотрите логи
docker-compose logs -f telegram-bot
```

### Шаг 5: Настройте Supabase

1. Откройте http://localhost:8000
2. Выполните SQL из `setup_database.sql`
3. Выполните SQL из `setup_course_database.sql`
4. Заполните таблицы заданиями

---

## 🔗 Вариант 2: Подключение к существующим сервисам

Если у вас уже запущены n8n и Supabase в Docker.

### Шаг 1: Узнайте имя Docker сети

```bash
# Посмотрите все сети
docker network ls

# Узнайте к какой сети подключены n8n и supabase
docker inspect n8n | grep NetworkMode
docker inspect supabase | grep NetworkMode
```

Или:

```bash
# Посмотрите детали контейнера
docker inspect n8n | grep -A 5 Networks
```

### Шаг 2: Отредактируйте docker-compose.existing.yml

```bash
nano docker-compose.existing.yml
```

Замените в секции networks:

```yaml
networks:
  existing-network:
    external: true
    name: ваша-сеть  # Например: n8n_default или supabase_network
```

### Шаг 3: Настройте .env

```env
BOT_TOKEN=your_bot_token

# Используйте имена контейнеров из вашей существующей сети
SUPABASE_URL=http://supabase:8000
# Или если контейнер называется по-другому:
# SUPABASE_URL=http://supabase-kong:8000

SUPABASE_KEY=your_key

N8N_WEBHOOK_URL=http://n8n:5678/webhook/generate-post
# Или если контейнер называется по-другому:
# N8N_WEBHOOK_URL=http://n8n-container:5678/webhook/generate-post

ADMIN_IDS=123456789
COURSE_CHAT_ID=-1001234567890
MONITORING_CHAT_ID=-1001234567891
OPENAI_API_KEY=sk-your_key
TIMEZONE=Europe/Moscow
```

### Шаг 4: Запустите бота

```bash
# Соберите образ
docker build -t telegram-bot .

# Запустите через docker-compose
docker-compose -f docker-compose.existing.yml up -d

# Или через docker run (если не хотите использовать compose)
docker run -d \
  --name telegram-bot \
  --network ваша-сеть \
  --env-file .env \
  -v $(pwd)/media:/app/media \
  -v $(pwd)/audio_temp:/app/audio_temp \
  -p 8080:8080 \
  telegram-bot
```

### Шаг 5: Проверьте подключение

```bash
# Проверьте, что бот в той же сети
docker network inspect ваша-сеть

# Проверьте логи
docker logs -f telegram-bot

# Проверьте, что бот видит другие контейнеры
docker exec telegram-bot ping -c 2 supabase
docker exec telegram-bot ping -c 2 n8n
```

---

## ⚙️ Настройка .env для Docker

### Основные отличия от обычного .env:

1. **SUPABASE_URL** - используйте имя контейнера вместо localhost:
   ```env
   # ❌ Неправильно (из контейнера localhost - это сам контейнер)
   SUPABASE_URL=http://localhost:8000
   
   # ✅ Правильно (имя контейнера в Docker сети)
   SUPABASE_URL=http://supabase:8000
   ```

2. **N8N_WEBHOOK_URL** - аналогично:
   ```env
   # ❌ Неправильно
   N8N_WEBHOOK_URL=http://localhost:5678/webhook
   
   # ✅ Правильно
   N8N_WEBHOOK_URL=http://n8n:5678/webhook/generate-post
   ```

3. **host.docker.internal** - если сервис на хосте (вне Docker):
   ```env
   # Если Supabase НЕ в Docker, а на хосте
   SUPABASE_URL=http://host.docker.internal:8000
   ```

---

## 🛠️ Управление контейнерами

### Основные команды

```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart telegram-bot

# Пересборка после изменений кода
docker-compose up -d --build

# Логи
docker-compose logs -f telegram-bot

# Последние 100 строк логов
docker-compose logs --tail=100 telegram-bot

# Выполнить команду внутри контейнера
docker-compose exec telegram-bot bash

# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats telegram-bot
```

### Обновление кода

```bash
# Остановите контейнер
docker-compose down

# Обновите код
git pull

# Пересоберите и запустите
docker-compose up -d --build

# Проверьте логи
docker-compose logs -f telegram-bot
```

### Резервное копирование

```bash
# Backup медиафайлов
tar -czf media-backup.tar.gz media/

# Backup .env
cp .env .env.backup

# Backup логов
tar -czf logs-backup.tar.gz logs/
```

---

## 🔍 Troubleshooting

### Бот не может подключиться к Supabase

**Проблема:** `Connection refused` или `Cannot resolve host`

**Решение:**

1. Проверьте, что контейнеры в одной сети:
   ```bash
   docker network inspect имя-сети
   ```

2. Проверьте имя контейнера Supabase:
   ```bash
   docker ps | grep supabase
   ```

3. Используйте правильное имя в .env:
   ```env
   SUPABASE_URL=http://имя-контейнера:8000
   ```

4. Проверьте связь:
   ```bash
   docker exec telegram-bot curl http://supabase:8000
   ```

### Бот не может подключиться к n8n

**Проблема:** Webhook не работает

**Решение:**

1. Проверьте имя контейнера n8n:
   ```bash
   docker ps | grep n8n
   ```

2. Проверьте URL в .env:
   ```env
   N8N_WEBHOOK_URL=http://n8n:5678/webhook/generate-post
   ```

3. Убедитесь, что n8n может достучаться до бота:
   - Бот должен быть доступен на порту 8080
   - n8n должен отправлять callback на `http://telegram-bot:8080/webhook/n8n`

### Порт 8080 уже занят

**Проблема:** `Port is already allocated`

**Решение:**

Измените порт в docker-compose.yml:

```yaml
ports:
  - "8081:8080"  # Внешний порт 8081 вместо 8080
```

### Медиафайлы не найдены

**Проблема:** `File not found: media/welcome_video.mp4`

**Решение:**

1. Проверьте наличие файлов:
   ```bash
   ls -la media/
   ```

2. Проверьте права:
   ```bash
   chmod -R 755 media/
   ```

3. Проверьте volume в docker-compose.yml:
   ```yaml
   volumes:
     - ./media:/app/media
   ```

### Логи не пишутся

**Решение:**

Создайте директорию logs:

```bash
mkdir -p logs
chmod 777 logs
```

---

## 🔐 Безопасность

1. **Не коммитьте .env в git**
   - Уже в .gitignore

2. **Используйте secrets для production:**
   ```yaml
   services:
     telegram-bot:
       secrets:
         - bot_token
         - supabase_key
   secrets:
     bot_token:
       external: true
     supabase_key:
       external: true
   ```

3. **Ограничьте доступ к портам:**
   ```yaml
   ports:
     - "127.0.0.1:8080:8080"  # Только localhost
   ```

4. **Используйте read-only volumes где возможно:**
   ```yaml
   volumes:
     - ./media:/app/media:ro  # Read-only
   ```

---

## 📊 Мониторинг

### Проверка здоровья контейнера

```bash
# Healthcheck статус
docker inspect telegram-bot | grep -A 5 Health

# Логи healthcheck
docker events --filter container=telegram-bot
```

### Метрики

```bash
# Использование CPU и RAM
docker stats telegram-bot

# Размер логов
docker logs telegram-bot 2>&1 | wc -l

# Размер образа
docker images telegram-bot
```

---

## 🎯 Production рекомендации

1. **Используйте docker-compose с restart policies:**
   ```yaml
   restart: unless-stopped
   ```

2. **Настройте логирование:**
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

3. **Используйте healthchecks:**
   ```yaml
   healthcheck:
     test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
     interval: 30s
     timeout: 10s
     retries: 3
   ```

4. **Backup volumes регулярно**

5. **Мониторьте логи через Loki/Grafana**

---

**Готово! Бот в Docker готов к развертыванию! 🐳**

Для дополнительной информации смотрите:
- БЫСТРЫЙ_СТАРТ.txt
- ИНСТРУКЦИЯ.md
- МОНИТОРИНГ.md

