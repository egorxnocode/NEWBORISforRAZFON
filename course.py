# -*- coding: utf-8 -*-
"""
Модуль для работы с курсом "Разгон"
"""

import logging
import os
from datetime import datetime
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

import config
import messages
from database import (
    get_global_course_state,
    update_global_course_state,
    start_course_for_users,
    get_task_by_number,
    get_users_by_current_task,
    get_all_registered_users,
    add_penalty,
    get_user_by_telegram_id,
    get_user_course_state,
    CourseState,
    mark_task_completed,
    get_user_current_task,
    complete_course_for_user,
    get_user_penalties
)
from monitoring import monitor

logger = logging.getLogger(__name__)


def get_task_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками для задания"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=messages.BTN_WRITE_POST,
                callback_data="write_post"
            )
        ],
        [
            InlineKeyboardButton(
                text=messages.BTN_SUBMIT_TASK,
                callback_data="submit_task"
            )
        ]
    ])
    return keyboard


async def stop_course(bot: Bot, admin_id: int) -> dict:
    """
    Останавливает курс и очищает все данные
    
    Args:
        bot: Экземпляр бота
        admin_id: ID админа, остановившего курс
        
    Returns:
        Словарь с результатом: {'success': bool, 'message': str, 'users_count': int}
    """
    try:
        # Проверяем, активен ли курс
        course_state = await get_global_course_state()
        
        if not course_state or not course_state.get("is_active"):
            return {
                'success': False,
                'message': messages.MSG_ADMIN_STOP_NO_ACTIVE_COURSE,
                'users_count': 0
            }
        
        # Получаем всех пользователей в курсе
        from database import get_all_active_users_in_course, supabase, TABLE_NAME
        users = await get_all_active_users_in_course()
        
        # Очищаем данные пользователей
        for user in users:
            telegram_id = user.get('telegram_id')
            if telegram_id:
                try:
                    # Формируем данные для обновления только с существующими полями
                    update_data = {
                        'state': 'registered',
                        'post_1': None,
                        'post_2': None,
                        'post_3': None,
                        'post_4': None,
                        'post_5': None,
                        'post_6': None,
                        'post_7': None,
                        'post_8': None,
                        'post_9': None,
                        'post_10': None,
                        'post_11': None,
                        'post_12': None,
                        'post_13': None,
                        'post_14': None,
                    }
                    
                    # Добавляем дополнительные поля если они есть в схеме
                    # Используем безопасное обновление - если колонки нет, она будет проигнорирована
                    if 'penalties' in user:
                        update_data['penalties'] = 0
                    if 'current_task' in user:
                        update_data['current_task'] = 0
                    if 'course_state' in user:
                        update_data['course_state'] = 'registered'
                    if 'last_task_sent_at' in user:
                        update_data['last_task_sent_at'] = None
                    if 'last_reminder_sent_at' in user:
                        update_data['last_reminder_sent_at'] = None
                    
                    # Сбрасываем данные курса
                    supabase.table(TABLE_NAME).update(update_data).eq('telegram_id', telegram_id).execute()
                except Exception as e:
                    logger.warning(f"Не удалось обновить пользователя {telegram_id}: {e}")
                    # Продолжаем со следующим пользователем
        
        # Деактивируем курс
        await update_global_course_state(is_active=False, current_day=0)
        
        logger.info(f"Курс остановлен администратором {admin_id}. Очищено пользователей: {len(users)}")
        
        return {
            'success': True,
            'message': messages.MSG_ADMIN_STOP_COURSE_SUCCESS.format(users_count=len(users)),
            'users_count': len(users)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при остановке курса: {e}")
        return {
            'success': False,
            'message': f"❌ Ошибка при остановке курса: {e}",
            'users_count': 0
        }


async def start_course(bot: Bot, admin_id: int) -> str:
    """
    Запускает курс
    
    ВАЖНО: current_day = 0 означает "курс активен, ждём 10:00 для первой рассылки"
    В 10:00 scheduled_send_task() увеличит day до 1 и отправит первое задание
    
    Args:
        bot: Экземпляр бота
        admin_id: ID админа, запустившего курс
        
    Returns:
        Сообщение о результате
    """
    try:
        # Проверяем, не запущен ли курс уже
        course_state = await get_global_course_state()
        
        if course_state and course_state.get("is_active"):
            current_day = course_state.get("current_day", 0)
            return messages.MSG_COURSE_ALREADY_ACTIVE.format(current_day=current_day)
        
        # Запускаем курс с current_day = 0 (ждём первую рассылку в 10:00)
        now = datetime.now().isoformat()
        await update_global_course_state(is_active=True, current_day=0, start_date=now)
        
        # Обновляем состояние пользователей
        await start_course_for_users()
        
        # НЕ отправляем первое задание сразу!
        # В 10:00 scheduled_send_task() увеличит day до 1 и отправит задание 1
        
        logger.info(f"Курс запущен администратором {admin_id}. current_day=0, ожидаем 10:00 для первой рассылки.")
        
        return messages.MSG_COURSE_STARTED
        
    except Exception as e:
        logger.error(f"Ошибка при запуске курса: {e}")
        return f"❌ Ошибка при запуске курса: {e}"


async def send_task_to_users(bot: Bot, task_number: int):
    """
    Отправляет задание пользователям
    
    Args:
        bot: Экземпляр бота
        task_number: Номер задания (1-14)
    """
    try:
        # Получаем задание из БД (из таблицы digest_day_X)
        task = await get_task_by_number(task_number)
        
        if not task:
            logger.error(f"Задание {task_number} не найдено в БД (таблица digest_day_{task_number})!")
            return
        
        # Получаем ВСЕХ активных пользователей в курсе (не только на текущем задании!)
        from database import get_all_active_users_in_course
        users = await get_all_active_users_in_course()
        
        logger.info(f"📊 Получено пользователей для задания {task_number}: {len(users)}")
        if users:
            logger.info(f"📋 Список telegram_id: {[u.get('telegram_id') for u in users]}")
        
        if not users:
            logger.warning(f"❌ Нет пользователей для задания {task_number}")
            return
        
        # Получаем текст задания из колонки "zadanie"
        zadanie_text = task.get("zadanie", "")
        
        # Формируем сообщение
        message_text = messages.MSG_NEW_TASK.format(
            day=task_number,
            zadanie=zadanie_text
        )
        
        # Клавиатура
        keyboard = get_task_keyboard()
        
        # Путь к картинке задания
        image_path = f"{config.TASK_IMAGE_DIR}/task_{task_number}.jpg"
        
        # Отправляем каждому пользователю
        success_count = 0
        failed_count = 0
        
        for user in users:
            telegram_id = user.get("telegram_id")
            if not telegram_id:
                continue
            
            try:
                # Отправляем картинку с заданием
                if os.path.exists(image_path):
                    photo = FSInputFile(image_path)
                    await bot.send_photo(
                        chat_id=telegram_id,
                        photo=photo,
                        caption=message_text,
                        reply_markup=keyboard
                    )
                else:
                    # Если картинки нет, отправляем просто текст
                    logger.warning(f"Картинка не найдена: {image_path}")
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=message_text,
                        reply_markup=keyboard
                    )
                
                # Обновляем current_task у пользователя
                from database import supabase, TABLE_NAME
                try:
                    logger.info(f"Обновляем current_task={task_number} для пользователя {telegram_id}")
                    response = supabase.table(TABLE_NAME).update({
                        'current_task': task_number
                    }).eq('telegram_id', telegram_id).execute()
                    logger.info(f"✅ current_task обновлен для {telegram_id}: {response.data}")
                except Exception as update_error:
                    logger.error(f"❌ Не удалось обновить current_task для {telegram_id}: {update_error}")
                
                success_count += 1
                logger.info(f"Задание {task_number} отправлено пользователю {telegram_id}")
                
            except Exception as e:
                failed_count += 1
                # Если пользователь заблокировал бота
                if "bot was blocked" in str(e).lower() or "user is deactivated" in str(e).lower() or "chat not found" in str(e).lower():
                    logger.warning(f"Пользователь {telegram_id} заблокировал бота")
                    from database import mark_user_as_blocked
                    await mark_user_as_blocked(telegram_id)
                else:
                    logger.error(f"Ошибка при отправке задания пользователю {telegram_id}: {e}")
        
        logger.info(f"Задание {task_number} разослано: успешно={success_count}, ошибок={failed_count}")
        
        # Отправляем отчет в мониторинг
        await monitor.report_task_sent(bot, task_number, success_count, failed_count)
        
    except Exception as e:
        logger.error(f"Ошибка при рассылке задания: {e}")


async def send_reminder(bot: Bot, reminder_type: str):
    """
    Отправляет напоминание пользователям
    
    Args:
        bot: Экземпляр бота
        reminder_type: Тип напоминания (для логирования)
    """
    try:
        # Получаем текущий день курса
        course_state = await get_global_course_state()
        
        if not course_state or not course_state.get("is_active"):
            return
        
        current_day = course_state.get("current_day", 0)
        
        if current_day < 1 or current_day > config.COURSE_DAYS:
            return
        
        # Получаем задание из таблицы digest_day_X
        task = await get_task_by_number(current_day)
        
        if not task:
            logger.error(f"Задание {current_day} не найдено в таблице digest_day_{current_day}!")
            return
        
        # Получаем пользователей, которые еще не выполнили задание
        # (те, у кого current_task == current_day)
        users = await get_users_by_current_task(current_day)
        
        if not users:
            logger.info(f"Нет пользователей для напоминания (все выполнили задание {current_day})")
            return
        
        # Вычисляем время до проверки
        now = datetime.now()
        check_time_parts = config.CHECK_TIME.split(":")
        check_hour = int(check_time_parts[0])
        check_minute = int(check_time_parts[1])
        
        time_diff_minutes = (check_hour * 60 + check_minute) - (now.hour * 60 + now.minute)
        time_left = f"{time_diff_minutes} минут"
        
        # Формируем сообщение
        message_text = messages.MSG_REMINDER.format(
            day=current_day,
            time_left=time_left
        )
        
        # Клавиатура
        keyboard = get_task_keyboard()
        
        # Выбираем картинку в зависимости от типа напоминания
        if reminder_type == "reminder_1":
            reminder_image = config.REMINDER_1_IMAGE
        elif reminder_type == "reminder_2":
            reminder_image = config.REMINDER_2_IMAGE
        else:
            reminder_image = config.REMINDER_3_IMAGE
        
        # Отправляем каждому
        success_count = 0
        failed_count = 0
        
        for user in users:
            telegram_id = user.get("telegram_id")
            if not telegram_id:
                continue
            
            try:
                if os.path.exists(reminder_image):
                    photo = FSInputFile(reminder_image)
                    await bot.send_photo(
                        chat_id=telegram_id,
                        photo=photo,
                        caption=message_text,
                        reply_markup=keyboard
                    )
                else:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=message_text,
                        reply_markup=keyboard
                    )
                
                success_count += 1
                logger.info(f"Напоминание отправлено пользователю {telegram_id}")
                
            except Exception as e:
                failed_count += 1
                # Если пользователь заблокировал бота
                if "bot was blocked" in str(e).lower() or "user is deactivated" in str(e).lower() or "chat not found" in str(e).lower():
                    logger.warning(f"Пользователь {telegram_id} заблокировал бота")
                    from database import mark_user_as_blocked
                    await mark_user_as_blocked(telegram_id)
                else:
                    logger.error(f"Ошибка при отправке напоминания пользователю {telegram_id}: {e}")
        
        logger.info(f"Напоминание ({reminder_type}) отправлено: успешно={success_count}, ошибок={failed_count}")
        
        # Определяем номер и время напоминания для отчета
        reminder_mapping = {
            "reminder_1": (1, "8:50"),
            "reminder_2": (2, "9:20"),
            "reminder_3": (3, "9:35")
        }
        reminder_num, reminder_time = reminder_mapping.get(reminder_type, (1, ""))
        
        # Отправляем отчет в мониторинг
        await monitor.report_reminder_sent(bot, reminder_num, reminder_time, success_count, failed_count)
        
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминаний: {e}")


async def check_tasks_completion(bot: Bot):
    """
    Проверяет выполнение заданий и выдает штрафы
    
    Логика (все пользователи либо сдают, либо получают штраф):
    - current_task == current_day → НЕ сдал → ШТРАФ + перевод на следующий день
    - current_task > current_day → уже сдал → ничего не делаем
    - current_task == 0 → не получал задание (курс только запущен) → перевод без штрафа
    """
    try:
        # Получаем текущий день курса
        course_state = await get_global_course_state()
        
        if not course_state or not course_state.get("is_active"):
            logger.info("⏭️ Проверка пропущена: курс не активен")
            return
        
        current_day = course_state.get("current_day", 0)
        
        logger.info(f"🔍 Проверка выполнения заданий. Текущий день курса: {current_day}")
        
        if current_day < 1 or current_day > config.COURSE_DAYS:
            logger.info(f"⏭️ Проверка пропущена: current_day={current_day} вне диапазона 1-{config.COURSE_DAYS}")
            return
        
        # Получаем ВСЕХ активных пользователей в курсе
        from database import get_all_active_users_in_course
        all_users = await get_all_active_users_in_course()
        
        if not all_users:
            logger.info(f"⏭️ Нет активных пользователей в курсе")
            return
        
        logger.info(f"👥 Найдено {len(all_users)} активных пользователей для проверки")
        
        # Словарь для сбора статистики штрафов: {1: [user_ids], 2: [user_ids], ...}
        penalties_by_count = {1: [], 2: [], 3: [], 4: []}
        
        # Проверяем каждого пользователя
        for user in all_users:
            telegram_id = user.get("telegram_id")
            user_current_task = user.get("current_task", 0)
            
            if not telegram_id:
                continue
            
            logger.info(f"👤 Пользователь {telegram_id}: current_task={user_current_task}, current_day={current_day}")
            
            try:
                # Случай 1: НЕ сдал задание (current_task == current_day) → ШТРАФ
                if user_current_task == current_day:
                    penalties = await add_penalty(telegram_id)
                    
                    logger.info(f"🚫 Пользователь {telegram_id} НЕ сдал задание {current_day}. Штраф #{penalties}")
                    
                    # Статистика для мониторинга
                    if penalties <= 4:
                        penalties_by_count[penalties].append(telegram_id)
                    else:
                        penalties_by_count[4].append(telegram_id)
                    
                    # Отправляем сообщение о штрафе
                    await send_penalty_message(bot, telegram_id, penalties)
                    
                    # Если 3 штрафа - исключаем из чата
                    if penalties == 3 and config.COURSE_CHAT_ID:
                        try:
                            await bot.ban_chat_member(
                                chat_id=config.COURSE_CHAT_ID,
                                user_id=telegram_id
                            )
                            logger.info(f"Пользователь {telegram_id} исключен из чата")
                        except Exception as e:
                            logger.error(f"Ошибка при исключении из чата: {e}")
                    
                    # Переводим на следующее задание
                    from database import supabase, TABLE_NAME
                    next_task = current_day + 1
                    supabase.table(TABLE_NAME).update({
                        "current_task": next_task
                    }).eq("telegram_id", telegram_id).execute()
                    
                    logger.info(f"➡️ Переведен на задание {next_task}")
                
                # Случай 2: Уже сдал (current_task > current_day) → ничего не делаем
                elif user_current_task > current_day:
                    logger.info(f"✅ Пользователь {telegram_id} уже сдал задание {current_day}")
                
                # Случай 3: Не получал задание (current_task == 0) → перевод без штрафа
                elif user_current_task == 0:
                    logger.warning(f"⚠️ Пользователь {telegram_id} не получал задание (current_task=0). Перевод без штрафа.")
                    
                    from database import supabase, TABLE_NAME
                    next_task = current_day + 1
                    supabase.table(TABLE_NAME).update({
                        "current_task": next_task
                    }).eq("telegram_id", telegram_id).execute()
                    
                    logger.info(f"➡️ Переведен на задание {next_task} (без штрафа)")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке пользователя {telegram_id}: {e}")
        
        logger.info(f"✅ Проверка завершена. Обработано: {len(all_users)} пользователей")
        
        # Отправляем отчет о штрафах в мониторинг
        await monitor.report_penalties(bot, penalties_by_count)
        
    except Exception as e:
        logger.error(f"Ошибка при проверке выполнения заданий: {e}")


async def send_penalty_message(bot: Bot, telegram_id: int, penalties: int):
    """Отправляет сообщение о штрафе"""
    try:
        # Выбираем сообщение в зависимости от количества штрафов
        if penalties == 1:
            message_text = messages.MSG_PENALTY_1
        elif penalties == 2:
            message_text = messages.MSG_PENALTY_2
        elif penalties == 3:
            message_text = messages.MSG_PENALTY_3
        else:
            message_text = messages.MSG_PENALTY_4
        
        # Используем одну картинку для всех штрафов
        image_path = config.PENALTY_IMAGE
        
        # Отправляем
        if os.path.exists(image_path):
            photo = FSInputFile(image_path)
            await bot.send_photo(
                chat_id=telegram_id,
                photo=photo,
                caption=message_text
            )
        else:
            await bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )
        
        logger.info(f"Сообщение о штрафе {penalties} отправлено пользователю {telegram_id}")
        
    except Exception as e:
        # Если пользователь заблокировал бота
        if "bot was blocked" in str(e).lower() or "user is deactivated" in str(e).lower() or "chat not found" in str(e).lower():
            logger.warning(f"Пользователь {telegram_id} заблокировал бота при отправке штрафа")
            from database import mark_user_as_blocked
            await mark_user_as_blocked(telegram_id)
        else:
            logger.error(f"Ошибка при отправке сообщения о штрафе: {e}")


async def advance_course_day(bot: Bot):
    """
    Переходит к следующему дню курса.
    
    ВАЖНО: Эта функция вызывается в 9:50 после проверки и штрафов.
    Она только увеличивает current_day - задания отправляются в 10:00 через scheduled_send_task()!
    """
    try:
        course_state = await get_global_course_state()
        
        if not course_state or not course_state.get("is_active"):
            return
        
        current_day = course_state.get("current_day", 0)
        next_day = current_day + 1
        
        if next_day > config.COURSE_DAYS:
            # Курс завершен
            await update_global_course_state(is_active=False, current_day=config.COURSE_DAYS)
            logger.info("🏁 Курс завершен! Все 14 дней пройдены.")
            
            # Отправляем поздравления всем, кто завершил курс
            await send_completion_messages(bot)
            
            return
        
        # Переходим к следующему дню
        await update_global_course_state(is_active=True, current_day=next_day)
        
        logger.info(f"📅 Курс перешел на день {next_day}. Рассылка задания будет в 10:00")
        
        # НЕ отправляем задание здесь!
        # Задания отправляются ТОЛЬКО в 10:00 через scheduled_send_task()
        
    except Exception as e:
        logger.error(f"Ошибка при переходе к следующему дню: {e}")


async def send_completion_messages(bot: Bot):
    """Отправляет сообщения о завершении курса"""
    try:
        # Получаем всех пользователей, которые завершили курс
        from database import supabase, TABLE_NAME
        
        response = supabase.table(TABLE_NAME).select("*").eq("course_state", CourseState.COMPLETED).execute()
        users = response.data if response.data else []
        
        for user in users:
            telegram_id = user.get("telegram_id")
            penalties = user.get("penalties", 0)
            
            if not telegram_id:
                continue
            
            try:
                message_text = messages.MSG_COURSE_COMPLETED.format(penalties=penalties)
                await bot.send_message(
                    chat_id=telegram_id,
                    text=message_text
                )
                
                logger.info(f"Сообщение о завершении отправлено пользователю {telegram_id}")
                
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения о завершении: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщений о завершении: {e}")

