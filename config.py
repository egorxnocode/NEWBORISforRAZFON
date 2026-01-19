# -*- coding: utf-8 -*-
"""
Конфигурационный файл бота
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ============================================================
# ПУТИ К МЕДИАФАЙЛАМ - РЕГИСТРАЦИЯ
# ============================================================
# ПРИМЕЧАНИЕ: Все пути определяются автоматически через media_helper.py
# Поддерживаются форматы: .jpg, .jpeg, .png, .webp для изображений
# Для видео: .mp4, .mov, .avi
# Файлы должны находиться в папке media/ с соответствующими именами:
# - welcome.jpg/.png/.jpeg/.webp - приветственная картинка
# - channel_request.jpg/.png/.jpeg/.webp - картинка при запросе канала
# - final_message.jpg/.png/.jpeg/.webp - картинка после регистрации
# - instruction.mp4/.mov/.avi - видео с инструкцией
# - post_accepted.jpg/.png/.jpeg/.webp - картинка принятия поста

# ============================================================
# НАСТРОЙКИ КУРСА
# ============================================================

# ID администраторов (через запятую в .env: ADMIN_IDS=123456789,987654321)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]

# ID чата для курса (откуда исключать пользователей при 3 штрафах)
COURSE_CHAT_ID = os.getenv("COURSE_CHAT_ID", "")
if COURSE_CHAT_ID:
    try:
        COURSE_CHAT_ID = int(COURSE_CHAT_ID)
    except ValueError:
        COURSE_CHAT_ID = None
else:
    COURSE_CHAT_ID = None

# ID чата для мониторинга (куда отправлять отчеты о работе бота)
MONITORING_CHAT_ID = os.getenv("MONITORING_CHAT_ID", "")
if MONITORING_CHAT_ID:
    try:
        MONITORING_CHAT_ID = int(MONITORING_CHAT_ID)
    except ValueError:
        MONITORING_CHAT_ID = None
else:
    MONITORING_CHAT_ID = None

# Временная зона (по умолчанию Москва)
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

# Время рассылки задания (по умолчанию 10:00)
TASK_SEND_TIME = "10:00"

# Время напоминаний
REMINDER_TIMES = ["08:50", "09:20", "09:35"]

# Время проверки выполнения задания
CHECK_TIME = "09:50"

# Количество дней курса
COURSE_DAYS = 14

# Проверка возраста поста (требует прав администратора бота в канале)
CHECK_POST_AGE = os.getenv("CHECK_POST_AGE", "false").lower() == "true"
MAX_POST_AGE_HOURS = int(os.getenv("MAX_POST_AGE_HOURS", "23"))

# Пути к картинкам для курса
TASK_IMAGE_DIR = "media/tasks"  # Директория с картинками заданий (task_1.jpg/.png, task_2.jpg/.png и т.д.)

# ПРИМЕЧАНИЕ: Расширения файлов определяются автоматически
# Поддерживаются форматы: .jpg, .jpeg, .png, .webp
# Бот автоматически найдет файл с любым из этих расширений

# Проверка конфигурации
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env файле!")

if not ADMIN_IDS:
    print("⚠️  ВНИМАНИЕ: ADMIN_IDS не установлен! Команда /razgon_start не будет работать.")
    print("   Добавьте в .env: ADMIN_IDS=ваш_telegram_id")

if not COURSE_CHAT_ID:
    print("⚠️  ВНИМАНИЕ: COURSE_CHAT_ID не установлен! Исключение из чата не будет работать.")
    print("   Добавьте в .env: COURSE_CHAT_ID=id_чата")

if not MONITORING_CHAT_ID:
    print("⚠️  ВНИМАНИЕ: MONITORING_CHAT_ID не установлен! Отчеты не будут отправляться.")
    print("   Добавьте в .env: MONITORING_CHAT_ID=id_чата_для_мониторинга")

# ============================================================
# ИНТЕГРАЦИИ
# ============================================================

# OpenAI API (для транскрибации голосовых сообщений)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# n8n Webhook URL (для генерации постов)
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

# Таймаут ожидания ответа от n8n (в секундах)
N8N_TIMEOUT = int(os.getenv("N8N_TIMEOUT", "300"))  # 5 минут = 300 секунд

# Проверка интеграций
if not OPENAI_API_KEY:
    print("⚠️  ВНИМАНИЕ: OPENAI_API_KEY не установлен! Транскрибация голоса не будет работать.")
    print("   Добавьте в .env: OPENAI_API_KEY=ваш_ключ")

if not N8N_WEBHOOK_URL:
    print("⚠️  ВНИМАНИЕ: N8N_WEBHOOK_URL не установлен! Генерация постов не будет работать.")
    print("   Добавьте в .env: N8N_WEBHOOK_URL=https://your-n8n.com/webhook/...")

# ============================================================
# КАРТИНКИ ДЛЯ ЛОГИКИ ПОСТОВ
# ============================================================
# Используется автоматический поиск через media_helper.py
# Файл: media/post_accepted.jpg/.png/.jpeg/.webp

