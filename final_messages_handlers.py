# -*- coding: utf-8 -*-
"""
Модуль для обработки финальных сообщений 15 дня
После 14 задания бот отправляет 3 финальных сообщения всем пользователям
"""

import logging
from datetime import datetime
from aiogram import Bot
from aiogram.types import FSInputFile
from database import supabase, TABLE_NAME
import os

logger = logging.getLogger(__name__)

# Название таблицы финальных сообщений
FINAL_MESSAGES_TABLE = "final_messages"


async def get_final_message(message_number: int) -> dict:
    """
    Получает финальное сообщение из БД
    
    Args:
        message_number: Номер сообщения (1, 2, 3)
        
    Returns:
        Словарь с данными сообщения
    """
    try:
        response = supabase.table(FINAL_MESSAGES_TABLE).select("*").eq("message_number", message_number).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        logger.error(f"Финальное сообщение {message_number} не найдено в БД")
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при получении финального сообщения {message_number}: {e}")
        return None


async def get_users_for_final_message(message_number: int) -> list:
    """
    Получает пользователей, которым нужно отправить финальное сообщение
    
    Args:
        message_number: Номер сообщения (1, 2, 3)
        
    Returns:
        Список пользователей
    """
    try:
        # Получаем всех пользователей, которые:
        # 1. Завершили 14 задание (current_task >= 14)
        # 2. Ещё не получили это финальное сообщение
        column_name = f"final_message_{message_number}_sent"
        
        response = supabase.table(TABLE_NAME).select("*").gte("current_task", 14).eq(column_name, False).execute()
        
        if response.data:
            logger.info(f"Найдено {len(response.data)} пользователей для финального сообщения {message_number}")
            return response.data
        
        logger.info(f"Нет пользователей для финального сообщения {message_number}")
        return []
        
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей для финального сообщения {message_number}: {e}")
        return []


async def mark_final_message_sent(telegram_id: int, message_number: int) -> bool:
    """
    Отмечает финальное сообщение как отправленное
    
    Args:
        telegram_id: Telegram ID пользователя
        message_number: Номер сообщения (1, 2, 3)
        
    Returns:
        True если успешно
    """
    try:
        column_name = f"final_message_{message_number}_sent"
        
        supabase.table(TABLE_NAME).update({
            column_name: True
        }).eq("telegram_id", telegram_id).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отметке финального сообщения {message_number} для {telegram_id}: {e}")
        return False


async def send_final_message_to_user(bot: Bot, user: dict, message_data: dict, message_number: int) -> bool:
    """
    Отправляет финальное сообщение пользователю
    
    Args:
        bot: Экземпляр бота
        user: Данные пользователя из БД
        message_data: Данные сообщения из БД
        message_number: Номер сообщения
        
    Returns:
        True если успешно отправлено
    """
    telegram_id = user.get("telegram_id")
    
    try:
        message_text = message_data.get("message_text", "")
        
        # Отправляем сообщение (только текст, без медиафайлов)
        await bot.send_message(
            chat_id=telegram_id,
            text=message_text
        )
        
        # Отмечаем как отправленное
        await mark_final_message_sent(telegram_id, message_number)
        
        logger.info(f"✅ Финальное сообщение {message_number} отправлено пользователю {telegram_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке финального сообщения {message_number} пользователю {telegram_id}: {e}")
        return False


async def send_final_message_to_all(bot: Bot, message_number: int):
    """
    Отправляет финальное сообщение всем пользователям
    
    Args:
        bot: Экземпляр бота
        message_number: Номер сообщения (1, 2, 3)
    """
    logger.info(f"🚀 Начинаем отправку финального сообщения {message_number}")
    
    # Получаем данные сообщения
    message_data = await get_final_message(message_number)
    if not message_data:
        logger.error(f"Не удалось получить данные финального сообщения {message_number}")
        return
    
    # Получаем пользователей
    users = await get_users_for_final_message(message_number)
    if not users:
        logger.info(f"Нет пользователей для отправки финального сообщения {message_number}")
        return
    
    # Отправляем сообщения
    sent_count = 0
    failed_count = 0
    
    for user in users:
        success = await send_final_message_to_user(bot, user, message_data, message_number)
        if success:
            sent_count += 1
        else:
            failed_count += 1
    
    logger.info(f"✅ Финальное сообщение {message_number} отправлено: {sent_count} успешно, {failed_count} ошибок")


async def is_course_day_15(current_day: int) -> bool:
    """
    Проверяет, настал ли 15-й день курса
    
    Args:
        current_day: Текущий день курса из course_state
        
    Returns:
        True если 15-й день
    """
    return current_day >= 15


async def should_ignore_user_input(telegram_id: int) -> bool:
    """
    Проверяет, нужно ли игнорировать ввод пользователя
    После 14 задания бот не реагирует на пользователей до конца 15 дня
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        True если нужно игнорировать
    """
    try:
        response = supabase.table(TABLE_NAME).select("current_task, final_message_3_sent").eq("telegram_id", telegram_id).execute()
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            current_task = user.get("current_task", 0)
            final_message_3_sent = user.get("final_message_3_sent", False)
            
            # Игнорируем, если завершил 14 задание, но ещё не получил все финальные сообщения
            if current_task >= 14 and not final_message_3_sent:
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при проверке should_ignore_user_input для {telegram_id}: {e}")
        return False


async def mark_course_finished(telegram_id: int) -> bool:
    """
    Отмечает время завершения курса (после 14 задания)
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        True если успешно
    """
    try:
        supabase.table(TABLE_NAME).update({
            "course_finished_at": datetime.now().isoformat()
        }).eq("telegram_id", telegram_id).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отметке завершения курса для {telegram_id}: {e}")
        return False
