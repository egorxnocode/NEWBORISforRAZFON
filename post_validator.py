# -*- coding: utf-8 -*-
"""
Модуль для проверки ссылок на посты в Telegram
"""

import re
from datetime import datetime, timedelta
from aiogram import Bot
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def parse_post_link(link: str) -> Optional[Tuple[str, int]]:
    """
    Парсит ссылку на пост в Telegram
    
    Args:
        link: Ссылка вида https://t.me/channel_name/post_id
        
    Returns:
        Tuple (channel_username, post_id) или None
    """
    # Паттерн для ссылки: https://t.me/channel_name/123
    pattern = r'https://t\.me/([a-zA-Z0-9_]+)/(\d+)'
    match = re.match(pattern, link.strip())
    
    if match:
        channel_username = match.group(1)
        post_id = int(match.group(2))
        return (channel_username, post_id)
    
    return None


def extract_channel_username(channel_link: str) -> Optional[str]:
    """
    Извлекает username канала из ссылки или @username
    
    Args:
        channel_link: Ссылка вида https://t.me/channel или @channel
        
    Returns:
        Username канала без @ или None
    """
    channel_link = channel_link.strip()
    
    # Если начинается с @
    if channel_link.startswith('@'):
        return channel_link[1:]
    
    # Если это ссылка t.me/...
    match = re.search(r't\.me/([a-zA-Z0-9_]+)', channel_link)
    if match:
        return match.group(1)
    
    return None


async def get_post_date(bot: Bot, channel_username: str, post_id: int, check_age: bool = False) -> Optional[datetime]:
    """
    Получает дату публикации поста
    
    Args:
        bot: Экземпляр бота
        channel_username: Username канала без @
        post_id: ID поста
        check_age: Проверять ли реальный возраст поста (требует прав администратора)
        
    Returns:
        Datetime публикации или None если пост не найден
    """
    # Если проверка возраста отключена, просто возвращаем текущее время
    # (считаем что пост существует и свежий)
    if not check_age:
        logger.info(f"Проверка возраста поста {channel_username}/{post_id} отключена (CHECK_POST_AGE=false)")
        return datetime.now()
    
    # Если проверка включена, пробуем получить реальную дату
    try:
        chat_id = f"@{channel_username}"
        
        # Для получения даты поста бот должен быть администратором канала
        # или использовать метод forward_message
        from aiogram.exceptions import TelegramBadRequest
        
        try:
            # Пересылаем сообщение себе для получения даты
            logger.info(f"Попытка получить дату поста {channel_username}/{post_id}")
            message = await bot.forward_message(
                chat_id=bot.id,
                from_chat_id=chat_id,
                message_id=post_id
            )
            
            post_date = message.date
            
            # Удаляем пересланное сообщение
            try:
                await bot.delete_message(chat_id=bot.id, message_id=message.message_id)
            except:
                pass
            
            return post_date
            
        except TelegramBadRequest as e:
            logger.error(f"Не удалось получить пост {channel_username}/{post_id}: {e}")
            logger.error("Бот должен быть добавлен как администратор в канал для проверки возраста постов")
            return None
        
    except Exception as e:
        logger.error(f"Ошибка при получении даты поста {channel_username}/{post_id}: {e}")
        return None


async def is_post_recent(bot: Bot, channel_username: str, post_id: int, max_hours: int = 23, check_age: bool = False) -> Tuple[bool, Optional[datetime]]:
    """
    Проверяет, опубликован ли пост не более max_hours назад
    
    Args:
        bot: Экземпляр бота
        channel_username: Username канала без @
        post_id: ID поста
        max_hours: Максимальное количество часов (по умолчанию 23)
        check_age: Проверять ли реальный возраст поста (требует прав администратора)
        
    Returns:
        Tuple (is_recent, post_date)
    """
    post_date = await get_post_date(bot, channel_username, post_id, check_age)
    
    if not post_date:
        return (False, None)
    
    # Если проверка возраста отключена, всегда возвращаем True
    if not check_age:
        return (True, post_date)
    
    # Проверяем разницу во времени
    now = datetime.now(post_date.tzinfo)
    time_diff = now - post_date
    
    is_recent = time_diff <= timedelta(hours=max_hours)
    
    return (is_recent, post_date)


async def validate_post_link(
    bot: Bot,
    link: str,
    user_channel: str,
    max_hours: int = 23,
    check_age: bool = False
) -> Tuple[bool, str, Optional[str], Optional[str], Optional[datetime]]:
    """
    Полная валидация ссылки на пост
    
    Args:
        bot: Экземпляр бота
        link: Ссылка на пост
        user_channel: Канал пользователя (из регистрации)
        max_hours: Максимальный возраст поста в часах
        check_age: Проверять ли реальный возраст поста (требует прав администратора)
        
    Returns:
        Tuple (is_valid, error_type, post_channel, user_channel_clean, post_date)
        error_type: 'invalid_link', 'wrong_channel', 'too_old', None (если ОК)
    """
    # Парсим ссылку
    parsed = parse_post_link(link)
    
    if not parsed:
        return (False, 'invalid_link', None, None, None)
    
    post_channel, post_id = parsed
    
    # Извлекаем username канала пользователя
    user_channel_clean = extract_channel_username(user_channel)
    
    if not user_channel_clean:
        logger.error(f"Не удалось извлечь username из {user_channel}")
        return (False, 'invalid_link', None, None, None)
    
    # Проверяем, что пост в канале пользователя
    if post_channel.lower() != user_channel_clean.lower():
        return (False, 'wrong_channel', post_channel, user_channel_clean, None)
    
    # Проверяем возраст поста (если включена проверка)
    is_recent, post_date = await is_post_recent(bot, post_channel, post_id, max_hours, check_age)
    
    if not is_recent:
        return (False, 'too_old', post_channel, user_channel_clean, post_date)
    
    # Все проверки пройдены
    return (True, None, post_channel, user_channel_clean, post_date)

