# 🚀 Docker - Быстрый старт

## Развертывание бота с существующими n8n и Supabase

---

## 📋 Шаг за шагом (5 минут)

### 1️⃣ На сервере: Клонируйте репозиторий

```bash
cd /opt
git clone https://github.com/egorxnocode/NEWBORISforRAZFON.git
cd NEWBORISforRAZFON
```

### 2️⃣ Узнайте имя Docker сети

```bash
# Посмотрите все сети
docker network ls

# Узнайте сеть n8n
docker inspect n8n | grep NetworkMode

# Или так
docker network inspect $(docker inspect n8n --format='{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}')
```

**Запомните имя сети!** Например: `n8n_default` или `supabase_network`

### 3️⃣ Отредактируйте docker-compose

```bash
nano docker-compose.existing.yml
```

Найдите строки в конце файла и замените имя сети:

```yaml
networks:
  existing-network:
    external: true
    name: n8n_default  # <-- Замените на имя вашей сети
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### 4️⃣ Создайте .env

```bash
cp ENV_DOCKER_EXAMPLE.txt .env
nano .env
```

**Заполните обязательные поля:**

```env
BOT_TOKEN=ваш_токен_от_BotFather

# Имена контейнеров в Docker (НЕ localhost!)
SUPABASE_URL=http://supabase:8000
SUPABASE_KEY=ваш_service_role_ключ

N8N_WEBHOOK_URL=http://n8n:5678/webhook/generate-post

ADMIN_IDS=ваш_telegram_id
COURSE_CHAT_ID=-1001234567890
MONITORING_CHAT_ID=-1001234567891
OPENAI_API_KEY=sk-ваш_ключ
TIMEZONE=Europe/Moscow
```

**Важно:** Если ваши контейнеры называются по-другому, проверьте:

```bash
docker ps | grep supabase
docker ps | grep n8n
```

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### 5️⃣ Создайте директории для медиа

```bash
mkdir -p media/tasks media/penalties media/reminders
```

### 6️⃣ Запустите бота

```bash
docker-compose -f docker-compose.existing.yml up -d --build
```

### 7️⃣ Проверьте логи

```bash
docker logs -f telegram-bot
```

**Вы должны увидеть:**

```
Бот запущен!
Временная зона: Europe/Moscow
Администраторы: [ваш_id]
Планировщик запущен!
```

---

## ✅ Проверка

### Проверьте, что бот в той же сети

```bash
docker network inspect имя-вашей-сети | grep telegram-bot
```

### Проверьте связь с Supabase

```bash
docker exec telegram-bot ping -c 2 supabase
```

### Проверьте связь с n8n

```bash
docker exec telegram-bot curl http://n8n:5678
```

---

## 📁 Загрузка медиафайлов

### Вариант 1: SCP (с вашего компьютера)

```bash
scp -r /path/to/local/media/* user@server:/opt/NEWBORISforRAZFON/media/
```

### Вариант 2: Прямо на сервере

```bash
cd /opt/NEWBORISforRAZFON/media

# Загрузите файлы через wget, curl или FileZilla
# Структура:
# media/
# ├── welcome_video.mp4
# ├── channel_request.jpg
# ├── final_message.jpg
# ├── instruction.mp4
# ├── tasks/task_1.jpg ... task_14.jpg
# ├── penalties/penalty.jpg
# └── reminders/reminder_1.jpg, reminder_2.jpg, reminder_3.jpg
```

---

## 🛠️ Управление

```bash
# Остановить
docker-compose -f docker-compose.existing.yml down

# Перезапустить
docker-compose -f docker-compose.existing.yml restart telegram-bot

# Обновить код
git pull
docker-compose -f docker-compose.existing.yml up -d --build

# Логи
docker logs -f telegram-bot

# Статус
docker ps | grep telegram-bot

# Зайти в контейнер
docker exec -it telegram-bot bash
```

---

## 🐛 Troubleshooting

### Ошибка: Cannot resolve host 'supabase'

**Проблема:** Контейнеры не в одной сети

**Решение:**

1. Проверьте имя сети в docker-compose.existing.yml
2. Убедитесь, что сеть существует: `docker network ls`
3. Проверьте, что n8n и supabase в этой сети

### Ошибка: Port 8080 already in use

**Решение:** Измените порт в docker-compose.existing.yml:

```yaml
ports:
  - "8081:8080"  # Используйте другой внешний порт
```

### Бот запускается, но не отвечает

1. Проверьте токен в .env
2. Проверьте подключение к Supabase
3. Проверьте таблицы в Supabase (setup_database.sql)
4. Проверьте медиафайлы

---

## 📊 После запуска

1. **Настройте Supabase:**
   - Выполните SQL из setup_database.sql
   - Выполните SQL из setup_course_database.sql
   - Добавьте email'ы в таблицу users
   - Заполните задания в digest_day_1 ... digest_day_14

2. **Проверьте бота:**
   - Отправьте `/start`
   - Проверьте регистрацию

3. **Тестовые команды:**
   ```
   /razgon_start   - Запустить курс
   /850            - Тест напоминания
   ```

---

## 🔗 Ссылки

- **Полная документация:** DOCKER_DEPLOY.md
- **Обычная установка:** ИНСТРУКЦИЯ.md
- **Настройка:** БЫСТРЫЙ_СТАРТ.txt
- **Мониторинг:** МОНИТОРИНГ.md

---

**Готово! Бот в Docker готов к работе! 🐳**

Любые вопросы - смотрите DOCKER_DEPLOY.md

