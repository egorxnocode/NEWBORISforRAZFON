# -*- coding: utf-8 -*-
"""
Основной файл телеграм-бота
"""

import asyncio
import logging
import re
import os
from datetime import datetime, timedelta
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
from media_helper import (
    find_image, 
    get_task_image_path,
    get_welcome_image_path,
    get_channel_request_image_path,
    get_final_image_path,
    get_instruction_video_path
)
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
    get_task_by_number,
    fix_users_after_task_2
)
from course import (
    start_course,
    stop_course,
    send_task_to_users,
    send_task_to_single_user,
    send_task_to_limited_user,
    send_reminder,
    check_tasks_completion,
    advance_course_day,
    get_task_keyboard
)
from database import get_global_course_state
from post_handlers import (
    handle_submit_task_button,
    handle_write_post_button,
    handle_post_link,
    handle_question_answer
)
from user_states import get_user_state as get_dialog_state, clear_user_state as clear_dialog_state
from ai_helper import handle_n8n_response
from monitoring import monitor
from final_messages_handlers import (
    send_final_message_to_all,
    should_ignore_user_input,
    mark_course_finished
)

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

# Кэш для проверки публичности каналов (защита от флуд-контроля)
# Структура: {channel_username: {"is_public": bool, "expires_at": datetime}}
channel_cache = {}
CHANNEL_CACHE_TTL = 300  # 5 минут кэширования

# Rate limiting для API запросов к Telegram (защита от флуд-контроля)
last_channel_check_time = None
MIN_DELAY_BETWEEN_CHECKS = 1.5  # Минимальная задержка между проверками каналов (секунды)


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
    Проверяет, является ли канал публичным (с кэшированием и rate limiting для защиты от флуд-контроля)
    
    Args:
        channel_username: Username канала без @
        
    Returns:
        True если канал публичный, False если приватный или не существует
    """
    global last_channel_check_time
    
    # Проверяем кэш
    if channel_username in channel_cache:
        cached = channel_cache[channel_username]
        # Если кэш не истек, возвращаем закэшированный результат
        if datetime.now() < cached["expires_at"]:
            logger.debug(f"✅ Канал @{channel_username} найден в кэше: {cached['is_public']}")
            return cached["is_public"]
        else:
            # Кэш истек, удаляем
            del channel_cache[channel_username]
            logger.debug(f"🗑️ Кэш для @{channel_username} истек, удален")
    
    # Rate limiting: проверяем, прошло ли достаточно времени с последней проверки
    if last_channel_check_time:
        time_since_last_check = (datetime.now() - last_channel_check_time).total_seconds()
        if time_since_last_check < MIN_DELAY_BETWEEN_CHECKS:
            delay = MIN_DELAY_BETWEEN_CHECKS - time_since_last_check
            logger.info(f"⏱️ Rate limiting: ожидание {delay:.1f}с перед проверкой @{channel_username}")
            await asyncio.sleep(delay)
    
    # Обновляем время последней проверки
    last_channel_check_time = datetime.now()
    
    # Кэша нет или он истек, делаем запрос к API
    try:
        logger.debug(f"🔍 Проверяю канал @{channel_username} через API...")
        chat = await bot.get_chat(f"@{channel_username}")
        is_public = True
        logger.info(f"✅ Канал @{channel_username} публичный")
    except Exception as e:
        is_public = False
        logger.error(f"❌ Ошибка при проверке канала @{channel_username}: {e}")
    
    # Сохраняем результат в кэш
    channel_cache[channel_username] = {
        "is_public": is_public,
        "expires_at": datetime.now() + timedelta(seconds=CHANNEL_CACHE_TTL)
    }
    logger.debug(f"💾 Результат для @{channel_username} сохранен в кэш на {CHANNEL_CACHE_TTL}с")
    
    return is_public


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in config.ADMIN_IDS


# ============================================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    # Игнорируем сообщения из групповых чатов
    if message.chat.type != "private":
        return
    
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
    
    # Отправляем приветственную картинку с текстом (универсальный поиск)
    welcome_image = get_welcome_image_path()
    if welcome_image:
        try:
            photo = FSInputFile(welcome_image)
            await message.answer_photo(photo, caption=messages.MSG_ASK_EMAIL)
        except Exception as e:
            logger.error(f"Ошибка при отправке приветственной картинки: {e}")
            # Если картинка не отправилась, отправляем только текст
            await message.answer(messages.MSG_ASK_EMAIL)
    else:
        logger.warning(f"Приветственная картинка не найдена в папке media/")
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


@dp.message(Command("fix_excluded"))
async def cmd_fix_excluded(message: Message):
    """
    Команда /fix_excluded - переводит пользователей со статусом excluded обратно в in_progress
    
    Используется для исправления пользователей, которые были исключены из чата,
    но должны продолжать получать задания.
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    from database import supabase, TABLE_NAME, CourseState
    
    try:
        # Находим всех excluded пользователей
        response = supabase.table(TABLE_NAME).select("telegram_id, penalties").eq("course_state", "excluded").execute()
        excluded_users = response.data if response.data else []
        
        if not excluded_users:
            await monitor.send_admin_report(bot, "ℹ️ /fix_excluded\n\nНет пользователей со статусом excluded")
            return
        
        # Переводим их в in_progress
        fixed_count = 0
        for user in excluded_users:
            tid = user.get("telegram_id")
            penalties = user.get("penalties", 0)
            try:
                supabase.table(TABLE_NAME).update({
                    "course_state": CourseState.IN_PROGRESS
                }).eq("telegram_id", tid).execute()
                fixed_count += 1
                logger.info(f"✅ Пользователь {tid} переведён из excluded в in_progress (штрафов: {penalties})")
            except Exception as e:
                logger.error(f"❌ Ошибка при исправлении {tid}: {e}")
        
        report = f"""✅ /fix_excluded

Исправлено пользователей: {fixed_count}
Они продолжат получать задания."""
        
        await monitor.send_admin_report(bot, report)
        logger.info(f"Админ {user_id} исправил {fixed_count} excluded пользователей")
        
    except Exception as e:
        logger.error(f"Ошибка в /fix_excluded: {e}")
        await monitor.send_admin_report(bot, f"❌ /fix_excluded\n\nОшибка: {e}")


@dp.message(Command("final1"))
async def handle_final1_command(message: Message):
    """Админ команда: отправить финальное сообщение 1 вручную"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await message.answer("📤 Отправляю финальное сообщение 1...")
    
    from final_messages_handlers import send_final_message_to_all
    await send_final_message_to_all(bot, message_number=1)
    
    await message.answer("✅ Финальное сообщение 1 отправлено!")
    
    # Отчёт в мониторинговый чат
    await monitor.send_admin_report(bot, "📧 Админ отправил финальное сообщение 1 вручную")
    logger.info(f"Админ {user_id} отправил финальное сообщение 1 вручную")


@dp.message(Command("final2"))
async def handle_final2_command(message: Message):
    """Админ команда: отправить финальное сообщение 2 вручную"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await message.answer("📤 Отправляю финальное сообщение 2...")
    
    from final_messages_handlers import send_final_message_to_all
    await send_final_message_to_all(bot, message_number=2)
    
    await message.answer("✅ Финальное сообщение 2 отправлено!")
    
    # Отчёт в мониторинговый чат
    await monitor.send_admin_report(bot, "📧 Админ отправил финальное сообщение 2 вручную")
    logger.info(f"Админ {user_id} отправил финальное сообщение 2 вручную")


@dp.message(Command("final3"))
async def handle_final3_command(message: Message):
    """Админ команда: отправить финальное сообщение 3 вручную"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await message.answer("📤 Отправляю финальное сообщение 3...")
    
    from final_messages_handlers import send_final_message_to_all
    await send_final_message_to_all(bot, message_number=3)
    
    await message.answer("✅ Финальное сообщение 3 отправлено!")
    
    # Отчёт в мониторинговый чат
    await monitor.send_admin_report(bot, "📧 Админ отправил финальное сообщение 3 вручную")
    logger.info(f"Админ {user_id} отправил финальное сообщение 3 вручную")


@dp.message(Command("fix26"))
async def handle_fix26_command(message: Message):
    """Админ-команда: исправление пользователей с current_task > 2"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    logger.info(f"🔧 Админ {user_id} запустил команду /fix26")
    
    await message.answer("🔧 Запускаю исправление пользователей...")
    
    # Выполняем исправление
    fixed_count, fixed_ids = await fix_users_after_task_2()
    
    if fixed_count == 0:
        await message.answer("✅ Пользователей для исправления не найдено.\nВсе пользователи имеют current_task не больше 2.")
        logger.info("✅ /fix26: пользователей для исправления не найдено")
    else:
        # Отправляем сообщение всем исправленным пользователям
        await message.answer(f"📤 Отправляю сообщение {fixed_count} пользователям...")
        
        fix_message = """Сегодня я лихорадил, но мне уже лучше!

Не переживай, я записал твой пост, просто забыл об этом сказать.

Завтра в 10:00 жди новое задание, постараюсь больше не болеть!"""
        
        sent_count = 0
        error_count = 0
        
        for telegram_id in fixed_ids:
            try:
                await bot.send_message(chat_id=telegram_id, text=fix_message)
                sent_count += 1
                await asyncio.sleep(0.05)  # Небольшая задержка между отправками
            except Exception as e:
                error_count += 1
                logger.warning(f"Не удалось отправить сообщение пользователю {telegram_id}: {e}")
        
        # Формируем отчет
        report = f"""✅ <b>Исправление завершено!</b>

📊 Исправлено пользователей: <b>{fixed_count}</b>

🔧 Выполнено:
• current_task = 2
• course_state = waiting_task_2
• Обнулены post_2...post_14 (post_1 сохранен)

📤 Отправлено сообщений: <b>{sent_count}</b>
❌ Ошибок отправки: <b>{error_count}</b>

👥 Telegram ID исправленных пользователей:
{', '.join(map(str, fixed_ids[:10]))}"""
        
        if fixed_count > 10:
            report += f"\n... и еще {fixed_count - 10} пользователей"
        
        await message.answer(report)
        logger.info(f"✅ /fix26: исправлено {fixed_count} пользователей, отправлено {sent_count} сообщений")
        
        # Отчёт в мониторинговый чат
        await monitor.send_admin_report(bot, f"🔧 /fix26: исправлено {fixed_count} пользователей, отправлено {sent_count} сообщений")


@dp.message(Command("group"))
async def cmd_group(message: Message):
    """
    Команда /group N - рассылка сообщения группе N (1-10)
    
    Использование:
        /group 1 - рассылка группе 1
        /group 2 - рассылка группе 2
        ...
        /group 10 - рассылка группе 10
    """
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом
    if not is_admin(user_id):
        return
    
    # Парсим аргументы команды
    text = message.text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        # Неверный формат - отправляем подсказку в мониторинг
        await monitor.send_admin_report(bot, "❌ /group\n\nИспользование: /group N (где N = 1-10)")
        return
    
    # Получаем номер группы
    try:
        group_number = int(parts[1])
    except ValueError:
        await monitor.send_admin_report(bot, f"❌ /group {parts[1]}\n\nНомер группы должен быть числом от 1 до 10")
        return
    
    if group_number < 1 or group_number > 10:
        await monitor.send_admin_report(bot, f"❌ /group {group_number}\n\nНомер группы должен быть от 1 до 10")
        return
    
    # Получаем данные группы из БД
    from database import get_group_data
    telegram_ids, group_text = await get_group_data(group_number)
    
    if not telegram_ids:
        await monitor.send_admin_report(bot, f"⚠️ /group {group_number}\n\nГруппа {group_number} пуста (нет пользователей)")
        return
    
    if not group_text:
        await monitor.send_admin_report(bot, f"⚠️ /group {group_number}\n\nТекст для группы {group_number} не задан")
        return
    
    # Отправляем сообщение всем пользователям группы
    success_count = 0
    error_count = 0
    
    for tid in telegram_ids:
        try:
            await bot.send_message(chat_id=tid, text=group_text)
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки группе {group_number} пользователю {tid}: {e}")
            error_count += 1
    
    # Отчёт в мониторинговый чат
    report = f"""📨 /group {group_number}

✅ Успешно: {success_count}
❌ Ошибок: {error_count}
📊 Всего в группе: {len(telegram_ids)}"""
    
    await monitor.send_admin_report(bot, report)
    logger.info(f"Админ {user_id} выполнил /group {group_number}: успешно={success_count}, ошибок={error_count}")


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
    
    # Проверяем, не завершил ли пользователь 14 задание (игнорируем до конца 15 дня)
    if await should_ignore_user_input(user_id):
        try:
            await callback.answer("Курс завершен. Ожидайте финальные сообщения.", show_alert=True)
        except Exception:
            pass
        return
    
    # Проверяем, не заблокирован ли пользователь
    from database import is_user_blocked
    if await is_user_blocked(user_id):
        try:
            await callback.answer(messages.MSG_USER_BLOCKED, show_alert=True)
        except Exception:
            pass
        return
    
    # Проверяем, участвует ли пользователь в курсе
    course_state = await get_user_course_state(user_id)
    
    if course_state not in [CourseState.IN_PROGRESS] and not course_state.startswith("waiting_task"):
        try:
            await callback.answer(messages.MSG_NOT_IN_COURSE, show_alert=True)
        except Exception:
            pass
        return
    
    try:
        await callback.answer()
    except Exception:
        pass  # Игнорируем ошибку "query is too old"
    await handle_write_post_button(user_id, callback.message, bot)


@dp.callback_query(F.data == "submit_task")
async def callback_submit_task(callback: CallbackQuery):
    """Обработчик кнопки 'Сдать задание'"""
    user_id = callback.from_user.id
    
    # Проверяем, не завершил ли пользователь 14 задание (игнорируем до конца 15 дня)
    if await should_ignore_user_input(user_id):
        try:
            await callback.answer("Курс завершен. Ожидайте финальные сообщения.", show_alert=True)
        except Exception:
            pass
        return
    
    # Проверяем, не заблокирован ли пользователь
    from database import is_user_blocked
    if await is_user_blocked(user_id):
        try:
            await callback.answer(messages.MSG_USER_BLOCKED, show_alert=True)
        except Exception:
            pass  # Игнорируем ошибку "query is too old"
        return
    
    # Проверяем, участвует ли пользователь в курсе И находится в активном состоянии
    course_state = await get_user_course_state(user_id)
    
    # Кнопки работают:
    # - В состоянии IN_PROGRESS (все пользователи)
    # - В состоянии LIMITED (опоздавшие могут писать посты всегда)
    if course_state == CourseState.LIMITED:
        # Опоздавшие могут писать посты в любое время
        pass
    elif course_state != CourseState.IN_PROGRESS:
        # Обычные пользователи только в IN_PROGRESS
        try:
            if course_state.startswith("waiting_task"):
                await callback.answer("⏳ Ожидайте следующее задание. Кнопки станут активны после получения задания.", show_alert=True)
            else:
                await callback.answer(messages.MSG_NOT_IN_COURSE, show_alert=True)
        except Exception:
            pass
        return
    
    try:
        await callback.answer()
    except Exception:
        pass  # Игнорируем ошибку "query is too old" при перезапуске бота
    await handle_submit_task_button(user_id, callback.message, bot)


# ============================================================
# ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ
# ============================================================

@dp.message(F.text)
async def handle_text_message(message: Message):
    """Обработчик всех текстовых сообщений"""
    # Игнорируем сообщения из групповых чатов
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Проверяем, не завершил ли пользователь 14 задание (игнорируем до конца 15 дня)
    if await should_ignore_user_input(user_id):
        # Игнорируем сообщения, не отвечаем
        return
    
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
        # Пользователь ПОЛУЧИЛ задание и ещё НЕ сдал - отправляем задание заново
        from course import get_task_keyboard, send_task_to_single_user
        user_current_task = await get_user_current_task(user_id)
        
        # Отправляем задание текущего дня
        await send_task_to_single_user(bot, user_id, user_current_task)
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
    # Игнорируем сообщения из групповых чатов
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    
    # Проверяем, не завершил ли пользователь 14 задание (игнорируем до конца 15 дня)
    if await should_ignore_user_input(user_id):
        # Игнорируем сообщения, не отвечаем
        return
    
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
    # Игнорируем сообщения из групповых чатов
    if message.chat.type != "private":
        return
    # Игнорируем медиа (можно расширить функциональность при необходимости)
    pass


async def handle_email_input(message: Message, email: str):
    """Обработка ввода email"""
    user_id = message.from_user.id
    
    # Приводим email к нижнему регистру (в БД хранятся в lowercase)
    email = email.lower().strip()
    
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
        # Отправляем картинку (если есть) и сообщение с запросом канала (универсальный поиск)
        channel_image = get_channel_request_image_path()
        if channel_image:
            try:
                photo = FSInputFile(channel_image)
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
    # ВРЕМЕННО ОТКЛЮЧЕНО из-за флуд-контроля (можно включить через 30 минут)
    # is_public = await is_channel_public(channel_username)
    # 
    # if not is_public:
    #     await message.answer(messages.MSG_CHANNEL_PRIVATE)
    #     return
    
    # Временно пропускаем проверку (принимаем любые каналы)
    logger.warning(f"⚠️ Проверка публичности канала отключена (флуд-контроль)")
    
    # Канал публичный, сохраняем его
    channel_link = f"@{channel_username}"
    success = await update_user_channel(user_id, channel_link)
    
    if success:
        # ============================================================
        # СИСТЕМА ДЛЯ ОПОЗДАВШИХ
        # ============================================================
        course_state = await get_global_course_state()
        is_course_active = course_state and course_state.get("is_active")
        current_day = course_state.get("current_day", 0) if course_state else 0
        
        # Определяем тип участника
        # current_day >= 2 → ОГРАНИЧЕННЫЙ участник (limited)
        # current_day == 1 → полноценный опоздавший (успел на первый день)
        # current_day == 0 или курс не активен → обычный участник
        is_limited_user = is_course_active and current_day >= 2
        is_late_first_day = is_course_active and current_day == 1
        
        if is_limited_user:
            # ============================================================
            # ОГРАНИЧЕННЫЙ УЧАСТНИК (опоздал на день 2+)
            # НЕ получает информацию о чате/канале, только пишет посты
            # ============================================================
            logger.info(f"📥 LIMITED участник {user_id}: курс на дне {current_day}")
            
            # Отправляем специальное приветствие для limited
            await message.answer(messages.MSG_LIMITED_REGISTRATION)
            
            # Устанавливаем статус LIMITED
            from database import supabase, TABLE_NAME, CourseState
            try:
                supabase.table(TABLE_NAME).update({
                    'course_state': CourseState.LIMITED,
                    'current_task': current_day  # Текущий день курса
                }).eq('telegram_id', user_id).execute()
                logger.info(f"✅ Установлен статус LIMITED для {user_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка установки LIMITED статуса: {e}")
            
            await asyncio.sleep(1)
            
            # Отправляем ТЕКУЩЕЕ задание (с ограниченной клавиатурой)
            from course import send_task_to_limited_user
            task_sent = await send_task_to_limited_user(bot, user_id, current_day)
            
            if task_sent:
                logger.info(f"✅ LIMITED {user_id}: отправлено задание дня {current_day}")
            else:
                logger.error(f"❌ Не удалось отправить задание LIMITED {user_id}")
        
        else:
            # ============================================================
            # ОБЫЧНЫЙ ИЛИ ПОЛНОЦЕННЫЙ ОПОЗДАВШИЙ
            # Получает всю информацию о чате/канале
            # ============================================================
            
            # Отправляем финальную картинку с текстом об успехе (универсальный поиск)
            final_image = get_final_image_path()
            if final_image:
                try:
                    photo = FSInputFile(final_image)
                    await message.answer_photo(photo=photo, caption=messages.MSG_CHANNEL_SUCCESS)
                except Exception as e:
                    logger.error(f"Ошибка при отправке финальной картинки: {e}")
                    await message.answer(messages.MSG_CHANNEL_SUCCESS)
            else:
                await message.answer(messages.MSG_CHANNEL_SUCCESS)
            
            # Отправляем видео с инструкцией (формат 1920x1080) (универсальный поиск)
            instruction_video = get_instruction_video_path()
            if instruction_video:
                try:
                    video = FSInputFile(instruction_video)
                    await message.answer_video(
                        video=video,
                        width=1920,
                        height=1080,
                        supports_streaming=True
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке видео: {e}")
            else:
                logger.warning(f"Видео с инструкцией не найдено в папке media/")
            
            # Если опоздал на первый день - отправляем первое задание
            if is_late_first_day:
                logger.info(f"📥 Опоздавший {user_id}: курс на дне 1, отправляем задание 1")
                
                await message.answer(messages.MSG_LATE_REGISTRATION)
                await asyncio.sleep(1)
                
                task_sent = await send_task_to_single_user(bot, user_id, task_number=1)
                
                if task_sent:
                    logger.info(f"✅ Опоздавшему {user_id} отправлено первое задание")
                else:
                    logger.error(f"❌ Не удалось отправить задание опоздавшему {user_id}")
            else:
                logger.info(f"📝 Пользователь {user_id} зарегистрировался до старта курса")
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


async def scheduled_final_message_1():
    """Финальное сообщение 1 в 10:00 (15 день)"""
    logger.info("=" * 50)
    logger.info("⏰ ПЛАНИРОВЩИК: Финальное сообщение 1 (10:00)")
    logger.info("=" * 50)
    
    from database import get_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state:
        logger.warning("❌ course_state не найден в БД!")
        return
    
    # Проверяем, активен ли курс
    if not course_state.get("is_active"):
        logger.info("⏸️ Курс не активен (/razgon_stop), финальное сообщение 1 пропущено")
        return
    
    current_day = course_state.get("current_day", 0)
    
    # Проверяем, что это 15-й день (после 14 задания)
    if current_day >= 15:
        logger.info(f"📤 Отправляем финальное сообщение 1 (день {current_day})...")
        await send_final_message_to_all(bot, message_number=1)
        logger.info("✅ Финальное сообщение 1 отправлено")
    else:
        logger.info(f"⏸️ Текущий день {current_day}, финальные сообщения не отправляются")


async def scheduled_final_message_2():
    """Финальное сообщение 2 в 15:00 (15 день)"""
    logger.info("=" * 50)
    logger.info("⏰ ПЛАНИРОВЩИК: Финальное сообщение 2 (15:00)")
    logger.info("=" * 50)
    
    from database import get_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state:
        logger.warning("❌ course_state не найден в БД!")
        return
    
    # Проверяем, активен ли курс
    if not course_state.get("is_active"):
        logger.info("⏸️ Курс не активен (/razgon_stop), финальное сообщение 2 пропущено")
        return
    
    current_day = course_state.get("current_day", 0)
    
    if current_day >= 15:
        logger.info(f"📤 Отправляем финальное сообщение 2 (день {current_day})...")
        await send_final_message_to_all(bot, message_number=2)
        logger.info("✅ Финальное сообщение 2 отправлено")
    else:
        logger.info(f"⏸️ Текущий день {current_day}, финальные сообщения не отправляются")


async def scheduled_final_message_3():
    """Финальное сообщение 3 в 15:55 (15 день)"""
    logger.info("=" * 50)
    logger.info("⏰ ПЛАНИРОВЩИК: Финальное сообщение 3 (15:55)")
    logger.info("=" * 50)
    
    from database import get_global_course_state
    course_state = await get_global_course_state()
    
    if not course_state:
        logger.warning("❌ course_state не найден в БД!")
        return
    
    # Проверяем, активен ли курс
    if not course_state.get("is_active"):
        logger.info("⏸️ Курс не активен (/razgon_stop), финальное сообщение 3 пропущено")
        return
    
    current_day = course_state.get("current_day", 0)
    
    if current_day >= 15:
        logger.info(f"📤 Отправляем финальное сообщение 3 (день {current_day})...")
        await send_final_message_to_all(bot, message_number=3)
        logger.info("✅ Финальное сообщение 3 отправлено")
    else:
        logger.info(f"⏸️ Текущий день {current_day}, финальные сообщения не отправляются")


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
    
    # Финальные сообщения 15 дня
    # Сообщение 1 - 10:00 (отправляется в тот же час, что и обычные задания)
    scheduler.add_job(
        scheduled_final_message_1,
        CronTrigger(hour=10, minute=0, timezone=config.TIMEZONE),
        id="final_message_1"
    )
    logger.info("Планировщик: финальное сообщение 1 в 10:00")
    
    # Сообщение 2 - 15:00
    scheduler.add_job(
        scheduled_final_message_2,
        CronTrigger(hour=15, minute=0, timezone=config.TIMEZONE),
        id="final_message_2"
    )
    logger.info("Планировщик: финальное сообщение 2 в 15:00")
    
    # Сообщение 3 - 15:55
    scheduler.add_job(
        scheduled_final_message_3,
        CronTrigger(hour=15, minute=55, timezone=config.TIMEZONE),
        id="final_message_3"
    )
    logger.info("Планировщик: финальное сообщение 3 в 15:55")
    
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
