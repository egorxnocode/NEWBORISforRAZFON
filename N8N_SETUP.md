# Настройка n8n для генерации постов

## Что такое n8n?

n8n - это инструмент автоматизации workflow с открытым исходным кодом.  
Бот использует n8n для генерации текстов постов с помощью AI (например, ChatGPT).

## Схема работы

1. Бот собирает ответы пользователя на 3 вопроса
2. Подставляет ответы в промпт из таблицы digest_day_X
3. Отправляет POST запрос на n8n webhook с данными:
   - `prompt` - готовый промпт с ответами
   - `chat_id` - ID чата пользователя
   - `request_id` - уникальный ID запроса
4. n8n обрабатывает промпт через AI (OpenAI, Claude, и т.д.)
5. n8n отправляет POST запрос обратно боту с данными:
   - `request_id` - тот же ID запроса
   - `generated_text` - сгенерированный текст поста
6. Бот отдает текст пользователю

## Настройка n8n workflow

### 1. Создайте workflow в n8n

**Узлы (nodes):**

1. **Webhook (Trigger)**
   - Method: POST
   - Path: `/generate-post`
   - Response: Immediately
   
2. **OpenAI Node** (или другой AI провайдер)
   - Model: gpt-4 или gpt-3.5-turbo
   - Prompt: `{{ $json.prompt }}`
   
3. **HTTP Request Node** (отправка ответа обратно боту)
   - Method: POST
   - URL: `http://your-bot-server:8080/webhook/n8n`
   - Body (JSON):
   ```json
   {
     "request_id": "{{ $('Webhook').item.json.request_id }}",
     "generated_text": "{{ $json.choices[0].message.content }}"
   }
   ```

### 2. Пример workflow (JSON)

```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "webhookId": "generate-post",
      "parameters": {
        "path": "generate-post",
        "method": "POST",
        "responseMode": "immediately"
      }
    },
    {
      "name": "OpenAI",
      "type": "n8n-nodes-base.openAi",
      "position": [450, 300],
      "parameters": {
        "operation": "message",
        "model": "gpt-4",
        "messages": {
          "values": [
            {
              "role": "user",
              "content": "={{ $json.prompt }}"
            }
          ]
        }
      }
    },
    {
      "name": "Send to Bot",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300],
      "parameters": {
        "method": "POST",
        "url": "http://YOUR_BOT_IP:8080/webhook/n8n",
        "jsonParameters": true,
        "options": {},
        "bodyParametersJson": "={\n  \"request_id\": \"{{ $('Webhook').item.json.request_id }}\",\n  \"generated_text\": \"{{ $json.choices[0].message.content }}\"\n}"
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "OpenAI", "type": "main", "index": 0 }]]
    },
    "OpenAI": {
      "main": [[{ "node": "Send to Bot", "type": "main", "index": 0 }]]
    }
  }
}
```

### 3. Получите Webhook URL

После создания workflow, n8n выдаст URL вида:
```
https://your-n8n-instance.com/webhook/generate-post
```

Скопируйте этот URL и добавьте в `.env` файл бота:
```
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/generate-post
```

### 4. Настройте URL бота в n8n

В узле "Send to Bot" укажите URL вашего бота:
```
http://your-bot-server-ip:8080/webhook/n8n
```

**Важно:** Бот запускает webhook сервер на порту 8080.  
Убедитесь, что порт открыт в файрволе.

## Альтернативные AI провайдеры

Вместо OpenAI можно использовать:
- **Anthropic Claude** (узел Anthropic)
- **Google Gemini** (узел Google)
- **Local LLM** (Ollama, LM Studio)
- Любой другой через HTTP Request

Просто замените узел OpenAI на нужный провайдер.

## Тестирование

### Тест вебхука n8n:

```bash
curl -X POST https://your-n8n-instance.com/webhook/generate-post \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Напиши короткий пост о программировании",
    "chat_id": 123456789,
    "request_id": "test-123"
  }'
```

### Тест ответа боту:

```bash
curl -X POST http://your-bot-ip:8080/webhook/n8n \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-123",
    "generated_text": "Вот ваш пост о программировании..."
  }'
```

## Решение проблем

### Бот не получает ответ от n8n

1. Проверьте, что порт 8080 открыт
2. Проверьте URL в n8n (должен быть доступен из интернета)
3. Проверьте логи n8n workflow
4. Убедитесь, что `request_id` совпадает

### Таймаут 5 минут

Если генерация занимает > 5 минут:
- Увеличьте `N8N_TIMEOUT` в `.env`
- Используйте более быструю модель AI
- Оптимизируйте промпты

### n8n недоступен

- Используйте n8n Cloud (n8n.io)
- Или разверните свой instance на VPS
- Или используйте Docker: `docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n`

## Безопасность

1. **Используйте HTTPS** для n8n webhook
2. **Добавьте аутентификацию** в n8n webhook (Basic Auth или API Key)
3. **Ограничьте доступ** к порту 8080 бота (только для n8n IP)
4. **Не храните API ключи** в workflow - используйте Credentials в n8n

## Полезные ссылки

- [Документация n8n](https://docs.n8n.io/)
- [n8n Community](https://community.n8n.io/)
- [OpenAI Node](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.openai/)

