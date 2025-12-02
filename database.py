# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных Supabase
"""

import os
from supabase import create_client, Client
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Инициализация клиента Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Названия таблиц
TABLE_NAME = "users"
COURSE_STATE_TABLE = "course_state"
DIGEST_TABLE_PREFIX = "digest_day_"  # digest_day_1, digest_day_2, etc.

# Возможные состояния пользователя
class UserState:
    NEW = "new"
    WAITING_EMAIL = "waiting_email"
    WAITING_CHANNEL = "waiting_channel"
    REGISTERED = "registered"

# Состояния курса
class CourseState:
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WAITING_TASK = "waiting_task_{}"  # waiting_task_1, waiting_task_2 и т.д.
    COMPLETED = "completed"
    EXCLUDED = "excluded"


async def check_email_exists(email: str) -> bool:
    """
    Проверяет, существует ли email в базе данных
    
    Args:
        email: Email для проверки
        
    Returns:
        True если email существует, False если нет
    """
    try:
        response = supabase.table(TABLE_NAME).select("email").eq("email", email).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Ошибка при проверке email: {e}")
        return False


async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает данные пользователя по Telegram ID
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        Словарь с данными пользователя или None
    """
    try:
        response = supabase.table(TABLE_NAME).select("*").eq("telegram_id", telegram_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Ошибка при получении пользователя: {e}")
        return None


async def update_user_data(
    email: str,
    telegram_id: int,
    first_name: str,
    username: Optional[str] = None,
    state: str = UserState.WAITING_CHANNEL
) -> bool:
    """
    Обновляет данные пользователя после ввода email
    
    Args:
        email: Email пользователя
        telegram_id: Telegram ID
        first_name: Имя пользователя
        username: Username пользователя (опционально)
        state: Состояние пользователя
        
    Returns:
        True если обновление прошло успешно
    """
    try:
        response = supabase.table(TABLE_NAME).update({
            "telegram_id": telegram_id,
            "first_name": first_name,
            "username": username,
            "state": state
        }).eq("email", email).execute()
        return True
    except Exception as e:
        print(f"Ошибка при обновлении данных пользователя: {e}")
        return False


async def update_user_channel(telegram_id: int, channel_link: str) -> bool:
    """
    Обновляет ссылку на канал пользователя и меняет статус на зарегистрирован
    
    Args:
        telegram_id: Telegram ID пользователя
        channel_link: Ссылка на канал
        
    Returns:
        True если обновление прошло успешно
    """
    try:
        response = supabase.table(TABLE_NAME).update({
            "channel_link": channel_link,
            "state": UserState.REGISTERED
        }).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        print(f"Ошибка при обновлении канала: {e}")
        return False


async def get_user_state(telegram_id: int) -> Optional[str]:
    """
    Получает текущее состояние пользователя
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        Состояние пользователя или None
    """
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        return user.get("state", UserState.NEW)
    return UserState.NEW


async def update_user_state(telegram_id: int, state: str) -> bool:
    """
    Обновляет состояние пользователя
    
    Args:
        telegram_id: Telegram ID пользователя
        state: Новое состояние
        
    Returns:
        True если обновление прошло успешно
    """
    try:
        response = supabase.table(TABLE_NAME).update({
            "state": state
        }).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        print(f"Ошибка при обновлении состояния: {e}")
        return False


# ============================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С КУРСОМ
# ============================================================

async def get_all_registered_users() -> list:
    """Получает всех зарегистрированных пользователей"""
    try:
        response = supabase.table(TABLE_NAME).select("*").eq("state", UserState.REGISTERED).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Ошибка при получении зарегистрированных пользователей: {e}")
        return []


async def start_course_for_users() -> bool:
    """Запускает курс для всех зарегистрированных пользователей"""
    try:
        # Обновляем состояние всех зарегистрированных пользователей
        # current_task НЕ устанавливаем сразу - будет установлен при отправке первого задания
        response = supabase.table(TABLE_NAME).update({
            "course_state": CourseState.IN_PROGRESS,
            "current_task": 0,
            "penalties": 0
        }).eq("state", UserState.REGISTERED).execute()
        return True
    except Exception as e:
        print(f"Ошибка при запуске курса: {e}")
        return False


async def get_global_course_state() -> Optional[Dict[str, Any]]:
    """Получает глобальное состояние курса"""
    try:
        response = supabase.table(COURSE_STATE_TABLE).select("*").eq("id", 1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Ошибка при получении состояния курса: {e}")
        return None


async def update_global_course_state(is_active: bool, current_day: int, start_date: str = None) -> bool:
    """Обновляет глобальное состояние курса"""
    try:
        data = {
            "is_active": is_active,
            "current_day": current_day
        }
        if start_date:
            data["start_date"] = start_date
        
        response = supabase.table(COURSE_STATE_TABLE).update(data).eq("id", 1).execute()
        return True
    except Exception as e:
        print(f"Ошибка при обновлении состояния курса: {e}")
        return False


async def get_task_by_number(task_number: int) -> Optional[Dict[str, Any]]:
    """
    Получает задание по номеру из таблицы digest_day_X
    
    Args:
        task_number: Номер дня (1-14)
        
    Returns:
        Словарь с полями: zadanie, vopros_1, vopros_2, vopros_3, prompt
    """
    try:
        table_name = f"{DIGEST_TABLE_PREFIX}{task_number}"
        response = supabase.table(table_name).select("*").execute()
        
        if response.data and len(response.data) > 0:
            # Возвращаем первую запись из таблицы
            return response.data[0]
        return None
    except Exception as e:
        print(f"Ошибка при получении задания из {table_name}: {e}")
        return None


async def get_users_in_course() -> list:
    """Получает всех пользователей, участвующих в курсе (любое состояние кроме not_started, excluded, completed)"""
    try:
        # Получаем всех, кто в курсе (in_progress или waiting_task_X)
        response = supabase.table(TABLE_NAME).select("*").neq("course_state", CourseState.NOT_STARTED).neq("course_state", CourseState.EXCLUDED).neq("course_state", CourseState.COMPLETED).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Ошибка при получении пользователей курса: {e}")
        return []


async def get_users_by_current_task(task_number: int) -> list:
    """Получает пользователей на определенном задании"""
    try:
        response = supabase.table(TABLE_NAME).select("*").eq("current_task", task_number).eq("course_state", CourseState.IN_PROGRESS).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Ошибка при получении пользователей по заданию: {e}")
        return []


async def mark_task_completed(telegram_id: int, task_number: int) -> bool:
    """Отмечает задание как выполненное"""
    try:
        from datetime import datetime
        
        # Обновляем текущее задание и время выполнения
        response = supabase.table(TABLE_NAME).update({
            "current_task": task_number + 1,
            "last_task_completed_at": datetime.now().isoformat(),
            "course_state": CourseState.WAITING_TASK.format(task_number + 1) if task_number < 14 else CourseState.COMPLETED
        }).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        print(f"Ошибка при отметке задания: {e}")
        return False


async def add_penalty(telegram_id: int) -> int:
    """
    Добавляет штраф пользователю
    
    Returns:
        Количество штрафов после добавления
    """
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user:
            return 0
        
        new_penalties = user.get("penalties", 0) + 1
        
        # Обновляем штрафы и состояние
        update_data = {"penalties": new_penalties}
        
        # Если 3+ штрафа, исключаем из курса
        if new_penalties >= 3:
            update_data["course_state"] = CourseState.EXCLUDED
        
        response = supabase.table(TABLE_NAME).update(update_data).eq("telegram_id", telegram_id).execute()
        
        return new_penalties
    except Exception as e:
        print(f"Ошибка при добавлении штрафа: {e}")
        return 0


async def get_user_penalties(telegram_id: int) -> int:
    """Получает количество штрафов пользователя"""
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        return user.get("penalties", 0)
    return 0


async def get_user_current_task(telegram_id: int) -> int:
    """Получает номер текущего задания пользователя"""
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        return user.get("current_task", 0)
    return 0


async def get_user_course_state(telegram_id: int) -> str:
    """Получает состояние курса пользователя"""
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        return user.get("course_state", CourseState.NOT_STARTED)
    return CourseState.NOT_STARTED


async def complete_course_for_user(telegram_id: int) -> bool:
    """Завершает курс для пользователя"""
    try:
        response = supabase.table(TABLE_NAME).update({
            "course_state": CourseState.COMPLETED
        }).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        print(f"Ошибка при завершении курса: {e}")
        return False


async def save_post_link(telegram_id: int, task_number: int, post_link: str) -> bool:
    """
    Сохраняет ссылку на пост в соответствующую колонку post_X
    
    Args:
        telegram_id: Telegram ID пользователя
        task_number: Номер задания (1-14)
        post_link: Ссылка на пост
        
    Returns:
        True если успешно
    """
    try:
        column_name = f"post_{task_number}"
        
        response = supabase.table(TABLE_NAME).update({
            column_name: post_link
        }).eq("telegram_id", telegram_id).execute()
        
        return True
    except Exception as e:
        print(f"Ошибка при сохранении ссылки на пост: {e}")
        return False


async def get_user_post_link(telegram_id: int, task_number: int) -> Optional[str]:
    """
    Получает ссылку на пост пользователя для определенного задания
    
    Args:
        telegram_id: Telegram ID пользователя
        task_number: Номер задания (1-14)
        
    Returns:
        Ссылка на пост или None
    """
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if user:
            column_name = f"post_{task_number}"
            return user.get(column_name)
        return None
    except Exception as e:
        print(f"Ошибка при получении ссылки на пост: {e}")
        return None


async def mark_user_as_blocked(telegram_id: int) -> bool:
    """
    Отмечает пользователя как заблокировавшего бота
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        True если успешно
    """
    try:
        response = supabase.table(TABLE_NAME).update({
            "is_blocked": True
        }).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        print(f"Ошибка при отметке пользователя как заблокированного: {e}")
        return False


async def is_user_blocked(telegram_id: int) -> bool:
    """
    Проверяет, заблокирован ли пользователь
    
    Args:
        telegram_id: Telegram ID пользователя
        
    Returns:
        True если пользователь заблокирован
    """
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if user:
            return user.get("is_blocked", False)
        return False
    except Exception as e:
        print(f"Ошибка при проверке блокировки: {e}")
        return False


async def get_all_active_users_in_course() -> list:
    """
    Получает ВСЕХ активных пользователей в курсе (для рассылки в 10:00)
    Включая тех, кто не сдал предыдущее задание
    """
    try:
        # Получаем всех, кто in_progress
        response = supabase.table(TABLE_NAME).select("*").eq("course_state", CourseState.IN_PROGRESS).execute()
        
        # Фильтруем заблокированных вручную (если колонка blocked_at существует)
        if response.data:
            users = []
            for user in response.data:
                # Пропускаем если пользователь заблокирован
                if user.get('blocked_at') is None:
                    users.append(user)
            return users
        return []
    except Exception as e:
        print(f"Ошибка при получении активных пользователей: {e}")
        return []

