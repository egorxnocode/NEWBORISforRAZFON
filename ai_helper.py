# -*- coding: utf-8 -*-
"""
Модуль для работы с OpenAI (транскрибация голосовых сообщений)
и n8n (генерация постов)
"""

import os
import logging
import aiohttp
import asyncio
import uuid
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

# Инициализация OpenAI клиента
openai_client = None
if config.OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


# Словарь для хранения ожидающих запросов к n8n
pending_requests: Dict[str, Dict[str, Any]] = {}


async def transcribe_voice(voice_file_path: str) -> Optional[str]:
    """
    Транскрибирует голосовое сообщение с помощью OpenAI Whisper
    
    Args:
        voice_file_path: Путь к аудиофайлу
        
    Returns:
        Распознанный текст или None
    """
    if not openai_client:
        logger.error("OpenAI клиент не инициализирован")
        return None
    
    try:
        with open(voice_file_path, "rb") as audio_file:
            transcript = await openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"
            )
        
        return transcript.text
        
    except Exception as e:
        logger.error(f"Ошибка при транскрибации: {e}")
        return None


async def send_to_n8n(
    prompt: str,
    chat_id: int,
    request_id: str
) -> bool:
    """
    Отправляет запрос в n8n для генерации поста
    
    Args:
        prompt: Промпт с подставленными ответами
        chat_id: ID чата пользователя
        request_id: Уникальный ID запроса
        
    Returns:
        True если запрос отправлен успешно
    """
    if not config.N8N_WEBHOOK_URL:
        logger.error("N8N_WEBHOOK_URL не установлен")
        return False
    
    try:
        # Данные для отправки
        payload = {
            "prompt": prompt,
            "chat_id": chat_id,
            "request_id": request_id
        }
        
        # Отправляем POST запрос
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config.N8N_WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Запрос {request_id} отправлен в n8n")
                    return True
                else:
                    logger.error(f"n8n вернул статус {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"Ошибка при отправке в n8n: {e}")
        return False


def generate_request_id() -> str:
    """Генерирует уникальный ID запроса"""
    return str(uuid.uuid4())


async def wait_for_n8n_response(request_id: str, timeout: int = None) -> Optional[str]:
    """
    Ожидает ответ от n8n
    
    Args:
        request_id: ID запроса
        timeout: Таймаут в секундах (по умолчанию из config)
        
    Returns:
        Сгенерированный текст или None
    """
    if timeout is None:
        timeout = config.N8N_TIMEOUT
    
    # Создаем Future для ожидания
    future = asyncio.Future()
    pending_requests[request_id] = {
        'future': future,
        'created_at': asyncio.get_event_loop().time()
    }
    
    try:
        # Ждем ответ с таймаутом
        result = await asyncio.wait_for(future, timeout=timeout)
        return result
        
    except asyncio.TimeoutError:
        logger.warning(f"Таймаут ожидания ответа от n8n для {request_id}")
        return None
        
    finally:
        # Удаляем из словаря
        if request_id in pending_requests:
            del pending_requests[request_id]


def handle_n8n_response(request_id: str, generated_text: str) -> bool:
    """
    Обрабатывает ответ от n8n
    
    Args:
        request_id: ID запроса
        generated_text: Сгенерированный текст
        
    Returns:
        True если запрос был найден и обработан
    """
    if request_id in pending_requests:
        future = pending_requests[request_id]['future']
        if not future.done():
            future.set_result(generated_text)
            logger.info(f"Ответ от n8n получен для {request_id}")
            return True
    
    logger.warning(f"Запрос {request_id} не найден в pending_requests")
    return False


async def generate_post_with_ai(
    digest_data: Dict[str, Any],
    answer_1: str,
    answer_2: str,
    answer_3: str,
    chat_id: int,
    task_number: int = 0
) -> Optional[str]:
    """
    Генерирует пост с помощью AI через n8n
    
    Args:
        digest_data: Данные из таблицы digest_day_X
        answer_1: Ответ на вопрос 1
        answer_2: Ответ на вопрос 2
        answer_3: Ответ на вопрос 3
        chat_id: ID чата пользователя
        task_number: Номер задания (для мониторинга)
        
    Returns:
        Сгенерированный текст поста или None
    """
    # Берем промпт из данных
    prompt_template = digest_data.get('prompt', '')
    
    if not prompt_template:
        logger.error("Промпт не найден в digest_data")
        return None
    
    # Подставляем ответы в промпт
    # Можно использовать простую замену или форматирование
    prompt = prompt_template.format(
        answer_1=answer_1,
        answer_2=answer_2,
        answer_3=answer_3,
        vopros_1=answer_1,
        vopros_2=answer_2,
        vopros_3=answer_3
    )
    
    # Генерируем уникальный ID запроса
    request_id = generate_request_id()
    
    # Отправляем в n8n
    success = await send_to_n8n(prompt, chat_id, request_id)
    
    if not success:
        return None
    
    # Ждем ответ
    generated_text = await wait_for_n8n_response(request_id)
    
    # Если таймаут - отправляем отчет в мониторинг
    if generated_text is None and task_number > 0:
        from monitoring import monitor
        # Импортируем bot из главного модуля
        from bot import bot
        await monitor.report_n8n_timeout(bot, chat_id, task_number)
    
    return generated_text

