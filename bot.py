# -*- coding: utf-8 -*-
"""
Основной файл телеграм-бота
"""

import asyncio
import logging
import re
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import validators

import config
import messages
from database import (
    check_email_exists,
    get_user_by_telegram_id,
    update_user_data,
    update_user_channel,
    get_user_state,
    update_user_state,
    UserState,
    get_user_current_task,
    mark_task_completed,
    get_user_course_state,
    CourseState,
    get_task_by_number
)
from course import (
    start_course,
    stop_course,
    send_task_to_users,
    send_reminder,
    check_tasks_completion,
    advance_course_day,
    get_task_keyboard
)
from post_handlers import (
    handle_submit_task_button,
    handle_write_post_button,
    handle_post_link,
    handle_question_answer
)
from user_states import get_user_state as get_dialog_state, clear_user_state as clear_dialog_state
from ai_helper import handle_n8n_response
from monitoring import monitor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Планировщик задач
scheduler = AsyncIOScheduler(timezone=pytz.timezone(config.TIMEZONE))


def is_valid_email(email: str) -> bool:
    """Проверяет валидность email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def extract_channel_username(text: str) -> str | None:
    """
    Извлекает username канала из ссылки или @username
    
    Args:
        text: Текст со ссылкой или username
        
    Returns:
        Username канала без @ или None
    """
    # Убираем пробелы
    text = text.strip()
    
    # Если начинается с @
    if text.startswith('@'):
        return text[1:]
    
    # Если это ссылка t.me/...
    match = re.search(r't\.me/([a-zA-Z0-9_]+)', text)
    if match:
        return match.group(1)
    
    return None


async def is_channel_public(channel_username: str) -> bool:
    """
    Проверяет, является ли канал публичным
    
    Args:
        channel_username: Username канала без @
        
    Returns:
        True если канал публичный, False если приватный или не существует
    """
    try:
        # Пробуем получить информацию о канале
        chat = await bot.get_chat(f"@{channel_username}")
        # Если получили информацию, значит канал публичный
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке канала @{channel_username}: {e}")
        return False


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in config.ADMIN_IDS


# ============================================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    from database import is_user_blocked
    if await is_user_blocked(user_id):
        await message.answer(messages.MSG_USER_BLOCKED)
        return
    
    # Проверяем, зарегистрирован ли уже пользователь
    user = await get_user_by_telegram_id(user_id)
    
    if user and user.get("state") == UserState.REGISTERED:
        await message.answer(messages.MSG_ALREADY_REGISTERED)
        return
    
    # Отправляем приветственную картинку с текстом
    if os.path.exists(config.WELCOME_IMAGE_PATH):
        try:
            photo = FSInputFile(config.WELCOME_IMAGE_PATH)
            await message.answer_photo(photo, caption=messages.MSG_ASK_EMAIL)
        except Exception as e:
            logger.error(f"Ошибка при отправке приветственной картинки: {e}")
            # Если картинка не отправилась, отправляем только текст
            await message.answer(messages.MSG_ASK_EMAIL)
    else:
        logger.warning(f"Приветственная картинка не найдена: {config.WELCOME_IMAGE_PATH}")
        # Отправляем только текст
        await message.answer(messages.MSG_ASK_EMAIL)
    
    # Устанавливаем состояние ожидания email
    if user:
        await update_user_state(user_id, UserState.WAITING_EMAIL)


@dp.message(Command("razgon_start"))
async def cmd_razgon_start(message: Message):
    """Обработчик команды /razgon_start - запуск курса (только для админов)"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом (молча игнорируем если нет)
    if not is_admin(user_id):
        return
    
    # Запускаем курс (без отправки заданий - только активация рассылки)
    result_message = await start_course(bot, user_id)
    
    # Отчёт в мониторинговый чат
    await monitor.send_admin_report(bot, f"🚀 /razgon_start\n\n{result_message}")
    logger.info(f"Админ {user_id} выполнил /razgon_start")


@dp.message(Command("razgon_stop"))
async def cmd_razgon_stop(message: Message):
    """Обработчик команды /razgon_stop - остановка курса и очистка данных (только для админов)"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом (молча игнорируем если нет)
    if not is_admin(user_id):
        return
    
    # Проверяем подтверждение
    text = message.text.strip()
    
    if text == "/razgon_stop CONFIRM":
        # Выполняем остановку курса
        result = await stop_course(bot, user_id)
        # Отчёт в мониторинговый чат
        await monitor.send_admin_report(bot, f"🛑 /razgon_stop CONFIRM\n\n{result['message']}")
        logger.info(f"Админ {user_id} остановил курс")
    # Без CONFIRM - ничего не делаем (защита от случайного нажатия)


@dp.message(Command("send_digest"))
async def cmd_send_digest(message: Message):
    """
    Обработчик команды /send_digest - отправка задания (только для админов)
    
    ВАЖНО: Работает ИДЕНТИЧНО рассылке в 10:00!
    - Если current_day=0 → увеличивает до 1 и отправляет задание 1
    - Обновляет current_task у пользователей
    """
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом (молча игнорируем если нет)
    if not is_admin(user_id):
        return
    
    # Парсим аргументы команды
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        # Неверный формат - игнорируем
        return
    
    argument = parts[1].strip()
    
    # Проверяем, активен ли курс
    from database import get_global_course_state, update_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state or not course_state.get("is_active"):
        # Курс не активен - игнорируем
        return
    
    current_day = course_state.get("current_day", 0)
    
    # ВАЖНО: Если current_day=0, увеличиваем до 1 (как в scheduled_send_task)
    if current_day == 0:
        logger.info("🚀 /send_digest: current_day=0, увеличиваем до 1")
        current_day = 1
        await update_global_course_state(is_active=True, current_day=1)
    
    if argument.lower() == "all":
        # Отправка всем пользователям в курсе
        await handle_send_digest_all(message, current_day)
    else:
        # Пробуем распарсить как telegram_id
        try:
            target_user_id = int(argument)
            await handle_send_digest_one(message, current_day, target_user_id)
        except ValueError:
            pass  # Неверный формат - игнорируем


# ============================================================
# ТЕСТОВЫЕ КОМАНДЫ ДЛЯ АДМИНОВ
# ============================================================

@dp.message(Command("850"))
async def cmd_test_reminder_850(message: Message):
    """Тестовая команда: напоминание в 8:50"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    # Проверяем, активен ли курс
    from database import get_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state or not course_state.get("is_active"):
        return
    
    # Отправляем напоминание
    await send_reminder(bot, "reminder_1")
    logger.info(f"Админ {user_id} запустил тест напоминания 8:50")


@dp.message(Command("920"))
async def cmd_test_reminder_920(message: Message):
    """Тестовая команда: напоминание в 9:20"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    # Проверяем, активен ли курс
    from database import get_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state or not course_state.get("is_active"):
        return
    
    # Отправляем напоминание
    await send_reminder(bot, "reminder_2")
    logger.info(f"Админ {user_id} запустил тест напоминания 9:20")


@dp.message(Command("935"))
async def cmd_test_reminder_935(message: Message):
    """Тестовая команда: напоминание в 9:35"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    # Проверяем, активен ли курс
    from database import get_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state or not course_state.get("is_active"):
        return
    
    # Отправляем напоминание
    await send_reminder(bot, "reminder_3")
    logger.info(f"Админ {user_id} запустил тест напоминания 9:35")


@dp.message(Command("950"))
async def cmd_test_check_950(message: Message):
    """Тестовая команда: проверка и штрафы в 9:50 + переход на следующий день"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    # Проверяем, активен ли курс
    from database import get_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state or not course_state.get("is_active"):
        return
    
    # Получаем статистику до проверки
    from database import get_all_active_users_in_course, get_users_by_current_task
    current_day = course_state.get("current_day", 0)
    all_users_before = await get_all_active_users_in_course()
    users_not_completed = await get_users_by_current_task(current_day)
    
    # Выполняем проверку и выдачу штрафов (как в 9:50)
    await check_tasks_completion(bot)
    
    # ВАЖНО: Переходим к следующему дню (как делает планировщик в 9:50)
    await advance_course_day(bot)
    
    # Получаем новый день после перехода
    new_course_state = await get_global_course_state()
    new_day = new_course_state.get("current_day", 0) if new_course_state else current_day
    
    # Отчёт в мониторинговый чат
    report = f"""⚡ /950 (тест проверки)

📊 Обработано: {len(all_users_before)} пользователей
🚫 Штрафов: {len(users_not_completed)}
📅 Курс перешёл на день {new_day}"""
    await monitor.send_admin_report(bot, report)
    logger.info(f"Админ {user_id} запустил тест проверки 9:50. Курс перешёл на день {new_day}")


async def handle_send_digest_all(message: Message, current_day: int):
    """Отправка задания всем пользователям в курсе"""
    from database import get_users_in_course
    
    # Получаем всех пользователей в курсе
    users = await get_users_in_course()
    
    if not users:
        return
    
    # Отчёт в мониторинговый чат (до рассылки)
    await monitor.send_admin_report(bot, f"📤 /send_digest all\n\nЗапущена рассылка задания {current_day} для {len(users)} пользователей...")
    
    # Отправляем задание (отчёт о результатах отправится через monitoring.py)
    await send_task_to_users(bot, current_day)
    
    logger.info(f"Админ {message.from_user.id} отправил задание дня {current_day} всем ({len(users)} чел.)")


async def handle_send_digest_one(message: Message, current_day: int, target_user_id: int):
    """
    Отправка задания одному пользователю
    
    ВАЖНО: Работает как send_task_to_users, но для одного пользователя
    - Обновляет current_task пользователя
    """
    from database import get_user_by_telegram_id, get_user_course_state, get_task_by_number, supabase, TABLE_NAME
    from course import get_task_keyboard
    
    # Проверяем, существует ли пользователь
    user = await get_user_by_telegram_id(target_user_id)
    
    if not user:
        return
    
    # Проверяем, участвует ли в курсе
    course_state = await get_user_course_state(target_user_id)
    
    if course_state not in [CourseState.IN_PROGRESS] and not course_state.startswith("waiting_task"):
        return
    
    # Получаем задание
    task = await get_task_by_number(current_day)
    
    if not task:
        return
    
    # Формируем сообщение
    zadanie_text = task.get("zadanie", "")
    message_text = messages.MSG_NEW_TASK.format(
        day=current_day,
        zadanie=zadanie_text
    )
    
    # Клавиатура
    keyboard = get_task_keyboard()
    
    # Путь к картинке
    image_path = f"{config.TASK_IMAGE_DIR}/task_{current_day}.jpg"
    
    # Отправляем пользователю
    try:
        if os.path.exists(image_path):
            photo = FSInputFile(image_path)
            await bot.send_photo(
                chat_id=target_user_id,
                photo=photo,
                caption=message_text,
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=target_user_id,
                text=message_text,
                reply_markup=keyboard
            )
        
        # ВАЖНО: Обновляем current_task и course_state (как в send_task_to_users)
        supabase.table(TABLE_NAME).update({
            'current_task': current_day,
            'course_state': CourseState.IN_PROGRESS  # Пользователь получил задание
        }).eq('telegram_id', target_user_id).execute()
        
        # Отчёт в мониторинговый чат
        await monitor.send_admin_report(bot, f"📤 /send_digest {target_user_id}\n\nЗадание {current_day} отправлено пользователю {target_user_id}")
        logger.info(f"✅ Задание {current_day} отправлено пользователю {target_user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке задания пользователю {target_user_id}: {e}")


# ============================================================
# ОБРАБОТЧИКИ CALLBACK'ОВ (КНОПОК)
# ============================================================

@dp.callback_query(F.data == "write_post")
async def callback_write_post(callback: CallbackQuery):
    """Обработчик кнопки 'Напиши пост'"""
    user_id = callback.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    from database import is_user_blocked
    if await is_user_blocked(user_id):
        await callback.answer(messages.MSG_USER_BLOCKED, show_alert=True)
        return
    
    # Проверяем, участвует ли пользователь в курсе
    course_state = await get_user_course_state(user_id)
    
    if course_state not in [CourseState.IN_PROGRESS] and not course_state.startswith("waiting_task"):
        await callback.answer(messages.MSG_NOT_IN_COURSE, show_alert=True)
        return
    
    await callback.answer()
    await handle_write_post_button(user_id, callback.message, bot)


@dp.callback_query(F.data == "submit_task")
async def callback_submit_task(callback: CallbackQuery):
    """Обработчик кнопки 'Сдать задание'"""
    user_id = callback.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    from database import is_user_blocked
    if await is_user_blocked(user_id):
        await callback.answer(messages.MSG_USER_BLOCKED, show_alert=True)
        return
    
    # Проверяем, участвует ли пользователь в курсе
    course_state = await get_user_course_state(user_id)
    
    if course_state not in [CourseState.IN_PROGRESS] and not course_state.startswith("waiting_task"):
        await callback.answer(messages.MSG_NOT_IN_COURSE, show_alert=True)
        return
    
    await callback.answer()
    await handle_submit_task_button(user_id, callback.message, bot)


# ============================================================
# ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ
# ============================================================

@dp.message(F.text)
async def handle_text_message(message: Message):
    """Обработчик всех текстовых сообщений"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Проверяем, не заблокирован ли пользователь
    from database import is_user_blocked
    if await is_user_blocked(user_id):
        await message.answer(messages.MSG_USER_BLOCKED)
        return
    
    # Проверяем состояние диалога (вопросы или ожидание ссылки на пост)
    dialog_state = get_dialog_state(user_id)
    
    if dialog_state.state in ["question_1", "question_2", "question_3"]:
        # Пользователь отвечает на вопрос
        await handle_question_answer(message, bot)
        return
    elif dialog_state.state == "waiting_post_link":
        # Пользователь отправляет ссылку на пост
        await handle_post_link(message, bot)
        return
    
    # Проверяем, не пытается ли пользователь отправить ссылку на пост без нажатия кнопки
    if text.startswith("https://t.me/") and "/" in text[13:]:
        # Похоже на ссылку на пост
        course_state = await get_user_course_state(user_id)
        if course_state == CourseState.IN_PROGRESS or course_state.startswith("waiting_task"):
            # Пользователь в курсе, но не нажал кнопку
            from course import get_task_keyboard
            keyboard = get_task_keyboard()
            await message.answer(messages.MSG_NEED_PRESS_BUTTON, reply_markup=keyboard)
            return
    
    # Получаем текущее состояние пользователя из БД (регистрация)
    state = await get_user_state(user_id)
    
    if state == UserState.NEW or state == UserState.WAITING_EMAIL:
        # Ожидаем email
        await handle_email_input(message, text)
    elif state == UserState.WAITING_CHANNEL:
        # Ожидаем ссылку на канал
        await handle_channel_input(message, text)
    elif state == UserState.REGISTERED:
        # Пользователь зарегистрирован - проверяем состояние курса
        await handle_registered_user_message(message, user_id)


async def handle_registered_user_message(message: Message, user_id: int):
    """
    Обработка сообщений от зарегистрированных пользователей
    Отвечает в зависимости от состояния курса
    
    Логика:
    - course_state = in_progress → получил задание, не сдал → "используйте кнопки"
    - course_state = waiting_task_X → сдал задание, ждёт следующее → "ждите 10:00"
    """
    from database import get_global_course_state, get_user_course_state, get_user_current_task
    
    # Проверяем глобальное состояние курса
    global_state = await get_global_course_state()
    
    if not global_state or not global_state.get("is_active"):
        # Курс не активен - ждём старта
        await message.answer(messages.MSG_STATE_WAITING_COURSE_START)
        return
    
    current_day = global_state.get("current_day", 0)
    
    if current_day == 0:
        # Курс запущен, но ждём первую рассылку в 10:00
        await message.answer(messages.MSG_STATE_WAITING_COURSE_START)
        return
    
    # Проверяем состояние пользователя в курсе
    user_course_state = await get_user_course_state(user_id)
    
    if user_course_state == CourseState.EXCLUDED:
        # Пользователь исключён
        await message.answer(messages.MSG_STATE_EXCLUDED)
        return
    
    if user_course_state == CourseState.COMPLETED:
        # Пользователь завершил курс
        await message.answer(messages.MSG_STATE_COURSE_FINISHED)
        return
    
    if user_course_state == CourseState.NOT_STARTED:
        # Пользователь не участвует в курсе
        await message.answer(messages.MSG_STATE_WAITING_COURSE_START)
        return
    
    # Проверяем course_state для определения статуса задания
    if user_course_state == CourseState.IN_PROGRESS:
        # Пользователь ПОЛУЧИЛ задание и ещё НЕ сдал - напоминаем про кнопки
        from course import get_task_keyboard
        keyboard = get_task_keyboard()
        user_current_task = await get_user_current_task(user_id)
        await message.answer(
            messages.MSG_STATE_HAS_TASK_NOT_STARTED.format(day=user_current_task),
            reply_markup=keyboard
        )
    elif user_course_state.startswith("waiting_task"):
        # Пользователь СДАЛ задание и ЖДЁТ следующее в 10:00
        # Извлекаем номер выполненного задания
        completed_day = current_day if current_day > 0 else 1
        await message.answer(
            messages.MSG_STATE_TASK_COMPLETED.format(day=completed_day)
        )
    else:
        # Что-то странное
        await message.answer(messages.MSG_STATE_WAITING_COURSE_START)


@dp.message(F.voice)
async def handle_voice_message(message: Message):
    """Обработчик голосовых сообщений"""
    user_id = message.from_user.id
    
    # Проверяем, не заблокирован ли пользователь
    from database import is_user_blocked
    if await is_user_blocked(user_id):
        await message.answer(messages.MSG_USER_BLOCKED)
        return
    
    # Проверяем, отвечает ли пользователь на вопрос
    dialog_state = get_dialog_state(user_id)
    
    if dialog_state.state in ["question_1", "question_2", "question_3"]:
        await handle_question_answer(message, bot)
        return


@dp.message(F.photo | F.video | F.document)
async def handle_media_message(message: Message):
    """Обработчик медиафайлов"""
    # Игнорируем медиа (можно расширить функциональность при необходимости)
    pass


async def handle_email_input(message: Message, email: str):
    """Обработка ввода email"""
    user_id = message.from_user.id
    
    # Проверяем валидность email
    if not is_valid_email(email):
        await message.answer(messages.MSG_INVALID_EMAIL)
        return
    
    # Проверяем, есть ли email в базе
    email_exists = await check_email_exists(email)
    
    if not email_exists:
        await message.answer(messages.MSG_EMAIL_NOT_FOUND)
        return
    
    # Email найден, обновляем данные пользователя
    first_name = message.from_user.first_name or "Пользователь"
    username = message.from_user.username
    
    success = await update_user_data(
        email=email,
        telegram_id=user_id,
        first_name=first_name,
        username=username,
        state=UserState.WAITING_CHANNEL
    )
    
    if success:
        # Отправляем картинку (если есть) и сообщение с запросом канала
        if os.path.exists(config.CHANNEL_REQUEST_IMAGE_PATH):
            try:
                photo = FSInputFile(config.CHANNEL_REQUEST_IMAGE_PATH)
                await message.answer_photo(
                    photo=photo,
                    caption=messages.MSG_EMAIL_SUCCESS
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке картинки: {e}")
                await message.answer(messages.MSG_EMAIL_SUCCESS)
        else:
            await message.answer(messages.MSG_EMAIL_SUCCESS)
    else:
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


async def handle_channel_input(message: Message, text: str):
    """Обработка ввода ссылки на канал"""
    user_id = message.from_user.id
    
    # Извлекаем username канала
    channel_username = extract_channel_username(text)
    
    if not channel_username:
        await message.answer(messages.MSG_INVALID_CHANNEL_LINK)
        return
    
    # Проверяем, является ли канал публичным
    is_public = await is_channel_public(channel_username)
    
    if not is_public:
        await message.answer(messages.MSG_CHANNEL_PRIVATE)
        return
    
    # Канал публичный, сохраняем его
    channel_link = f"@{channel_username}"
    success = await update_user_channel(user_id, channel_link)
    
    if success:
        # Отправляем финальную картинку с текстом об успехе
        if os.path.exists(config.FINAL_IMAGE_PATH):
            try:
                photo = FSInputFile(config.FINAL_IMAGE_PATH)
                await message.answer_photo(photo=photo, caption=messages.MSG_CHANNEL_SUCCESS)
            except Exception as e:
                logger.error(f"Ошибка при отправке финальной картинки: {e}")
                # Если картинка не отправилась, отправляем только текст
                await message.answer(messages.MSG_CHANNEL_SUCCESS)
        else:
            # Если картинки нет, отправляем только текст
            await message.answer(messages.MSG_CHANNEL_SUCCESS)
        
        # Отправляем видео с инструкцией
        if os.path.exists(config.INSTRUCTION_VIDEO_PATH):
            try:
                video = FSInputFile(config.INSTRUCTION_VIDEO_PATH)
                await message.answer_video(video=video)
            except Exception as e:
                logger.error(f"Ошибка при отправке видео: {e}")
        else:
            logger.warning(f"Видео с инструкцией не найдено: {config.INSTRUCTION_VIDEO_PATH}")
    else:
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


# Старые функции удалены, логика перенесена в post_handlers.py


# ============================================================
# ПЛАНИРОВЩИК ЗАДАЧ
# ============================================================

async def scheduled_send_task():
    """Отправка задания в 10:00"""
    logger.info("=" * 50)
    logger.info("⏰ ПЛАНИРОВЩИК: Запуск рассылки задания (10:00)")
    logger.info("=" * 50)
    
    from database import get_global_course_state, update_global_course_state
    
    course_state = await get_global_course_state()
    
    if not course_state:
        logger.warning("❌ course_state не найден в БД!")
        return
    
    logger.info(f"📊 Состояние курса: is_active={course_state.get('is_active')}, current_day={course_state.get('current_day')}")
    
    if not course_state.get("is_active"):
        logger.info("⏸️ Курс не активен, рассылка пропущена")
        return
    
    current_day = course_state.get("current_day", 0)
    
    # Если current_day = 0, это первый день после /razgon_start
    # Увеличиваем до 1 и отправляем первое задание
    if current_day == 0:
        logger.info("🚀 Первая рассылка после /razgon_start! Устанавливаем current_day=1")
        current_day = 1
        await update_global_course_state(is_active=True, current_day=1)
    
    if current_day > config.COURSE_DAYS:
        logger.warning(f"⚠️ current_day={current_day} > {config.COURSE_DAYS}, курс завершен")
        return
    
    logger.info(f"📤 Отправляем задание дня {current_day}...")
    await send_task_to_users(bot, current_day)
    logger.info(f"✅ Рассылка задания {current_day} завершена")


async def scheduled_reminder_1():
    """Напоминание в 8:50"""
    logger.info("=" * 50)
    logger.info("⏰ ПЛАНИРОВЩИК: Напоминание 1 (8:50)")
    logger.info("=" * 50)
    await send_reminder(bot, "reminder_1")


async def scheduled_reminder_2():
    """Напоминание в 9:20"""
    logger.info("=" * 50)
    logger.info("⏰ ПЛАНИРОВЩИК: Напоминание 2 (9:20)")
    logger.info("=" * 50)
    await send_reminder(bot, "reminder_2")


async def scheduled_reminder_3():
    """Напоминание в 9:35"""
    logger.info("=" * 50)
    logger.info("⏰ ПЛАНИРОВЩИК: Напоминание 3 (9:35)")
    logger.info("=" * 50)
    await send_reminder(bot, "reminder_3")


async def scheduled_check_completion():
    """Проверка выполнения в 9:50"""
    logger.info("=" * 50)
    logger.info("⏰ ПЛАНИРОВЩИК: Проверка выполнения и штрафы (9:50)")
    logger.info("=" * 50)
    
    # Проверяем состояние курса
    from database import get_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state or not course_state.get("is_active"):
        logger.info("⏸️ Курс не активен, проверка пропущена")
        return
    
    current_day = course_state.get("current_day", 0)
    
    # Если current_day = 0, это значит курс только что запущен и первое задание ещё не отправлялось
    # Проверку и advance_course_day делать НЕ нужно!
    if current_day == 0:
        logger.info("⏸️ current_day=0 (ожидаем первую рассылку в 10:00), проверка пропущена")
        return
    
    logger.info(f"🔍 Проверка для дня {current_day}...")
    await check_tasks_completion(bot)
    
    # После проверки переходим к следующему дню (БЕЗ отправки заданий!)
    # Задания отправятся в 10:00 через scheduled_send_task()
    await advance_course_day(bot)


async def scheduled_daily_summary():
    """Планировщик: ежедневная сводка в мониторинговый чат"""
    logger.info("⏰ Планировщик: отправка ежедневной сводки")
    await monitor.send_daily_summary(bot)
    # Сбрасываем статистику
    monitor.reset_daily_stats()
    logger.info("📊 Статистика сброшена для нового дня")


def setup_scheduler():
    """Настройка планировщика задач"""
    
    logger.info("=" * 50)
    logger.info("🔧 НАСТРОЙКА ПЛАНИРОВЩИКА")
    logger.info(f"📍 Временная зона: {config.TIMEZONE}")
    logger.info("=" * 50)
    
    # Время рассылки задания (10:00)
    task_hour, task_minute = map(int, config.TASK_SEND_TIME.split(":"))
    scheduler.add_job(
        scheduled_send_task,
        CronTrigger(hour=task_hour, minute=task_minute, timezone=config.TIMEZONE),
        id="send_task"
    )
    logger.info(f"📤 Рассылка заданий: {config.TASK_SEND_TIME} (час={task_hour}, мин={task_minute})")
    
    # Напоминания
    for i, reminder_time in enumerate(config.REMINDER_TIMES, 1):
        hour, minute = map(int, reminder_time.split(":"))
        
        if i == 1:
            func = scheduled_reminder_1
        elif i == 2:
            func = scheduled_reminder_2
        else:
            func = scheduled_reminder_3
        
        scheduler.add_job(
            func,
            CronTrigger(hour=hour, minute=minute, timezone=config.TIMEZONE),
            id=f"reminder_{i}"
        )
        logger.info(f"Планировщик: напоминание {i} в {reminder_time}")
    
    # Проверка выполнения (9:50)
    check_hour, check_minute = map(int, config.CHECK_TIME.split(":"))
    scheduler.add_job(
        scheduled_check_completion,
        CronTrigger(hour=check_hour, minute=check_minute, timezone=config.TIMEZONE),
        id="check_completion"
    )
    logger.info(f"Планировщик: проверка выполнения в {config.CHECK_TIME}")
    
    # Ежедневная сводка (23:59)
    scheduler.add_job(
        scheduled_daily_summary,
        CronTrigger(hour=23, minute=59, timezone=config.TIMEZONE),
        id="daily_summary"
    )
    logger.info("Планировщик: ежедневная сводка в 23:59")
    
    scheduler.start()
    logger.info("Планировщик запущен!")


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

async def main():
    """Главная функция запуска бота"""
    logger.info("=" * 50)
    logger.info("Бот запущен!")
    logger.info(f"Временная зона: {config.TIMEZONE}")
    logger.info(f"Администраторы: {config.ADMIN_IDS}")
    logger.info("=" * 50)
    
    # Проверяем и восстанавливаем состояние курса из БД
    from database import ensure_course_state_exists, get_global_course_state
    await ensure_course_state_exists()
    
    # Логируем текущее состояние курса
    course_state = await get_global_course_state()
    if course_state:
        is_active = course_state.get("is_active", False)
        current_day = course_state.get("current_day", 0)
        logger.info("=" * 50)
        logger.info(f"📊 СОСТОЯНИЕ КУРСА ИЗ БД:")
        logger.info(f"   is_active: {is_active}")
        logger.info(f"   current_day: {current_day}")
        if is_active:
            logger.info(f"   ✅ Курс АКТИВЕН, продолжаем с дня {current_day}")
        else:
            logger.info(f"   ⏸️ Курс НЕ активен")
        logger.info("=" * 50)
    
    # Настраиваем планировщик
    setup_scheduler()
    
    # Запускаем webhook сервер для n8n (если настроен)
    webhook_runner = None
    if config.N8N_WEBHOOK_URL:
        from webhook_server import start_webhook_server
        webhook_runner = await start_webhook_server(host='0.0.0.0', port=8080)
        logger.info("Webhook сервер для n8n запущен на порту 8080")
    
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        if webhook_runner:
            await webhook_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
