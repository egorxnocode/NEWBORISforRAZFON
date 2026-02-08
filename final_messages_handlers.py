# -*- coding: utf-8 -*-
"""
Модуль для обработки финальных сообщений 15 и 16 дня
- День 15: одно сообщение в 10:00
- День 16: три сообщения в 10:00, 15:00, 15:55
"""

import logging
from datetime import datetime
from aiogram import Bot
from database import supabase, TABLE_NAME

logger = logging.getLogger(__name__)

FINAL_MESSAGES_TABLE = "final_messages"


def _sent_column(course_day: int, message_number: int) -> str:
    """Имя колонки в users для отметки отправки."""
    if course_day == 15:
        return "final_message_15_sent"
    return f"final_message_{message_number}_sent"


async def get_final_message(course_day: int, message_number: int) -> dict:
    """
    Получает финальное сообщение из БД по дню и номеру.
    
    Args:
        course_day: 15 или 16
        message_number: номер сообщения (для дня 15 всегда 1, для дня 16 — 1, 2, 3)
    """
    try:
        response = (
            supabase.table(FINAL_MESSAGES_TABLE)
            .select("*")
            .eq("course_day", course_day)
            .eq("message_number", message_number)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
        logger.error(f"Финальное сообщение day={course_day} num={message_number} не найдено в БД")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении финального сообщения ({course_day}, {message_number}): {e}")
        return None


async def get_users_for_final_message(course_day: int, message_number: int) -> list:
    """
    Получает пользователей, которым нужно отправить финальное сообщение.
    Условия: current_task >= 15 и ещё не отправлено это сообщение.
    """
    try:
        col = _sent_column(course_day, message_number)
        response = (
            supabase.table(TABLE_NAME)
            .select("*")
            .gte("current_task", 15)
            .eq(col, False)
            .execute()
        )
        if response.data:
            logger.info(f"Найдено {len(response.data)} пользователей для финального сообщения day={course_day} num={message_number}")
            return response.data
        logger.info(f"Нет пользователей для финального сообщения day={course_day} num={message_number}")
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей для финального сообщения ({course_day}, {message_number}): {e}")
        return []


async def mark_final_message_sent(telegram_id: int, course_day: int, message_number: int) -> bool:
    """Отмечает финальное сообщение как отправленное."""
    try:
        col = _sent_column(course_day, message_number)
        supabase.table(TABLE_NAME).update({col: True}).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка при отметке финального сообщения ({course_day}, {message_number}) для {telegram_id}: {e}")
        return False


async def send_final_message_to_user(
    bot: Bot, user: dict, message_data: dict, course_day: int, message_number: int
) -> bool:
    """Отправляет финальное сообщение пользователю (только текст)."""
    telegram_id = user.get("telegram_id")
    try:
        message_text = message_data.get("message_text", "")
        await bot.send_message(chat_id=telegram_id, text=message_text)
        await mark_final_message_sent(telegram_id, course_day, message_number)
        logger.info(f"✅ Финальное сообщение day={course_day} num={message_number} отправлено пользователю {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке финального сообщения day={course_day} num={message_number} пользователю {telegram_id}: {e}")
        return False


async def send_final_message_to_all(bot: Bot, course_day: int, message_number: int):
    """
    Отправляет финальное сообщение всем подходящим пользователям.
    
    Args:
        bot: экземпляр бота
        course_day: 15 или 16
        message_number: 1 для дня 15; 1, 2, 3 для дня 16
    """
    logger.info(f"🚀 Начинаем отправку финального сообщения day={course_day} num={message_number}")
    
    message_data = await get_final_message(course_day, message_number)
    if not message_data:
        logger.error(f"Не удалось получить данные финального сообщения day={course_day} num={message_number}")
        return
    
    users = await get_users_for_final_message(course_day, message_number)
    if not users:
        logger.info(f"Нет пользователей для отправки финального сообщения day={course_day} num={message_number}")
        return
    
    sent_count = 0
    failed_count = 0
    for user in users:
        success = await send_final_message_to_user(bot, user, message_data, course_day, message_number)
        if success:
            sent_count += 1
        else:
            failed_count += 1
    
    logger.info(f"✅ Финальное сообщение day={course_day} num={message_number}: отправлено {sent_count}, ошибок {failed_count}")


async def is_course_day_15(current_day: int) -> bool:
    """Проверяет, настал ли 15-й день курса."""
    return current_day >= 15


async def should_ignore_user_input(telegram_id: int) -> bool:
    """
    Игнорировать ввод, если пользователь завершил 14 задание (current_task >= 15),
    но ещё не получил все финальные сообщения 16 дня (третье сообщение в 15:55).
    """
    try:
        response = (
            supabase.table(TABLE_NAME)
            .select("current_task, final_message_3_sent")
            .eq("telegram_id", telegram_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            user = response.data[0]
            current_task = user.get("current_task", 0)
            final_message_3_sent = user.get("final_message_3_sent", False)
            if current_task >= 15 and not final_message_3_sent:
                return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке should_ignore_user_input для {telegram_id}: {e}")
        return False


async def mark_course_finished(telegram_id: int) -> bool:
    """Отмечает время завершения курса (после 14 задания)."""
    try:
        supabase.table(TABLE_NAME).update({
            "course_finished_at": datetime.now().isoformat()
        }).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        logger.error(f"Ошибка при отметке завершения курса для {telegram_id}: {e}")
        return False
