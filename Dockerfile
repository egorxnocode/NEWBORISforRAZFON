# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Создаем директорию для медиафайлов (если не существует)
RUN mkdir -p /app/media/tasks /app/media/penalties /app/media/reminders

# Создаем директорию для временных аудиофайлов
RUN mkdir -p /app/audio_temp

# Устанавливаем права
RUN chmod -R 755 /app

# Открываем порт для webhook (n8n callback)
EXPOSE 8080

# Команда запуска бота
CMD ["python", "bot.py"]

