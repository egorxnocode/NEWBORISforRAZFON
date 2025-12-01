# -*- coding: utf-8 -*-
"""
Обработчики для логики выполнения заданий (посты)
"""

import logging
import os
from datetime import datetime
from aiogram import Bot
from aiogram.types import Message, FSInputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import messages
from database import (
    get_user_by_telegram_id,
    get_task_by_number,
    get_user_current_task,
    mark_task_completed,
    save_post_link,
    get_user_post_link
)
from post_validator import validate_post_link
from ai_helper import transcribe_voice, generate_post_with_ai
from user_states import (
    get_user_state,
    set_user_state,
    clear_user_state,
    save_answer,
    get_answers
)

logger = logging.getLogger(__name__)


async def handle_submit_task_button(message: Message, bot: Bot):
    """
    Обработчик кнопки "Сдать задание"
    """
    user_id = message.from_user.id
    
    # Получаем текущее задание пользователя
    current_task = await get_user_current_task(user_id)
    
    if current_task < 1 or current_task > 14:
        await message.answer(messages.MSG_NO_ACTIVE_TASK)
        return
    
    # Получаем канал пользователя
    user = await get_user_by_telegram_id(user_id)
    if not user or not user.get('channel_link'):
        await message.answer("❌ Ошибка: канал не найден. Обратитесь к администратору.")
        return
    
    user_channel = user.get('channel_link')
    
    # Устанавливаем состояние ожидания ссылки
    set_user_state(user_id, "waiting_post_link", current_task=current_task)
    
    # Просим ссылку
    await message.answer(
        messages.MSG_SUBMIT_POST_LINK.format(channel=user_channel)
    )


async def handle_post_link(message: Message, bot: Bot):
    """
    Обработчик получения ссылки на пост
    """
    user_id = message.from_user.id
    link = message.text.strip()
    
    # Получаем состояние пользователя
    user_state = get_user_state(user_id)
    current_task = user_state.current_task
    
    # Получаем канал пользователя
    user = await get_user_by_telegram_id(user_id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден.")
        return
    
    user_channel = user.get('channel_link', '')
    
    # Валидируем ссылку
    is_valid, error_type, post_channel, user_channel_clean, post_date = await validate_post_link(
        bot, link, user_channel, max_hours=23
    )
    
    if not is_valid:
        # Обрабатываем ошибки
        if error_type == 'invalid_link':
            await message.answer(messages.MSG_INVALID_POST_LINK)
        elif error_type == 'wrong_channel':
            await message.answer(
                messages.MSG_WRONG_CHANNEL.format(
                    your_channel=user_channel_clean,
                    post_channel=post_channel
                )
            )
        elif error_type == 'too_old':
            now_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            post_time = post_date.strftime("%d.%m.%Y %H:%M") if post_date else "неизвестно"
            await message.answer(
                messages.MSG_POST_TOO_OLD.format(
                    post_time=post_time,
                    now_time=now_time
                )
            )
        return
    
    # Ссылка валидна, сохраняем
    success = await save_post_link(user_id, current_task, link)
    
    if not success:
        await message.answer("❌ Ошибка при сохранении ссылки. Попробуйте еще раз.")
        return
    
    # Отмечаем задание как выполненное
    await mark_task_completed(user_id, current_task)
    
    # Очищаем состояние
    clear_user_state(user_id)
    
    # Отправляем подтверждение с картинкой
    if os.path.exists(config.POST_ACCEPTED_IMAGE):
        try:
            photo = FSInputFile(config.POST_ACCEPTED_IMAGE)
            await message.answer_photo(
                photo=photo,
                caption=messages.MSG_POST_ACCEPTED
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке картинки: {e}")
            await message.answer(messages.MSG_POST_ACCEPTED)
    else:
        await message.answer(messages.MSG_POST_ACCEPTED)


async def handle_write_post_button(message: Message, bot: Bot):
    """
    Обработчик кнопки "Напиши пост"
    """
    user_id = message.from_user.id
    
    # Получаем текущее задание
    current_task = await get_user_current_task(user_id)
    
    if current_task < 1 or current_task > 14:
        await message.answer(messages.MSG_NO_ACTIVE_TASK)
        return
    
    # Получаем данные задания из digest_day_X
    digest_data = await get_task_by_number(current_task)
    
    if not digest_data:
        await message.answer("❌ Ошибка: задание не найдено в базе данных.")
        return
    
    # Сохраняем данные в состоянии пользователя
    set_user_state(
        user_id,
        "question_1",
        current_task=current_task,
        digest_data=digest_data
    )
    
    # Отправляем приветственное сообщение
    await message.answer(messages.MSG_WRITE_POST_START)
    
    # Задаем первый вопрос
    question_1 = digest_data.get('vopros_1', 'Вопрос не найден')
    await message.answer(
        messages.MSG_QUESTION_1.format(question=question_1)
    )


async def handle_question_answer(message: Message, bot: Bot):
    """
    Обработчик ответов на вопросы (текст или голосовое)
    """
    user_id = message.from_user.id
    user_state = get_user_state(user_id)
    
    # Определяем, на каком вопросе мы
    if user_state.state not in ["question_1", "question_2", "question_3"]:
        return
    
    # Получаем ответ
    answer_text = None
    
    if message.text:
        answer_text = message.text
    elif message.voice:
        # Голосовое сообщение - транскрибируем
        await message.answer(messages.MSG_VOICE_TRANSCRIBING)
        
        # Скачиваем голосовое сообщение
        voice_file = await bot.get_file(message.voice.file_id)
        voice_path = f"/tmp/voice_{user_id}_{message.voice.file_id}.ogg"
        await bot.download_file(voice_file.file_path, voice_path)
        
        # Транскрибируем
        answer_text = await transcribe_voice(voice_path)
        
        # Удаляем файл
        try:
            os.remove(voice_path)
        except:
            pass
        
        if not answer_text:
            await message.answer(messages.MSG_VOICE_TRANSCRIPTION_ERROR)
            return
    
    if not answer_text:
        return
    
    # Сохраняем ответ
    question_num = int(user_state.state.split("_")[1])
    save_answer(user_id, question_num, answer_text)
    
    # Переходим к следующему вопросу
    if question_num < 3:
        await message.answer(messages.MSG_ANSWER_ACCEPTED)
        
        next_question_num = question_num + 1
        set_user_state(user_id, f"question_{next_question_num}")
        
        # Задаем следующий вопрос
        digest_data = user_state.digest_data
        question_key = f"vopros_{next_question_num}"
        question = digest_data.get(question_key, 'Вопрос не найден')
        
        if next_question_num == 2:
            await message.answer(messages.MSG_QUESTION_2.format(question=question))
        else:
            await message.answer(messages.MSG_QUESTION_3.format(question=question))
    else:
        # Все вопросы заданы, генерируем пост
        await generate_post(message, bot)


async def generate_post(message: Message, bot: Bot):
    """
    Генерирует пост с помощью AI
    """
    user_id = message.from_user.id
    user_state = get_user_state(user_id)
    
    # Получаем все ответы
    answers = get_answers(user_id)
    answer_1 = answers.get('answer_1', '')
    answer_2 = answers.get('answer_2', '')
    answer_3 = answers.get('answer_3', '')
    
    # Устанавливаем состояние генерации
    set_user_state(user_id, "generating_post")
    
    # Сообщаем пользователю
    await message.answer(messages.MSG_GENERATING_POST)
    
    # Генерируем пост
    generated_text = await generate_post_with_ai(
        digest_data=user_state.digest_data,
        answer_1=answer_1,
        answer_2=answer_2,
        answer_3=answer_3,
        chat_id=user_id,
        task_number=user_state.current_task or 0
    )
    
    if not generated_text:
        # Ошибка или таймаут
        clear_user_state(user_id)
        await message.answer(messages.MSG_GENERATION_TIMEOUT)
        
        # Предлагаем попробовать снова
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=messages.BTN_WRITE_POST, callback_data="write_post")]
        ])
        await message.answer("Попробуйте еще раз:", reply_markup=keyboard)
        return
    
    # Отправляем готовый пост
    await message.answer(
        messages.MSG_POST_GENERATED.format(post_text=generated_text)
    )
    
    # Предлагаем сдать задание
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=messages.BTN_SUBMIT_TASK, callback_data="submit_task")]
    ])
    await message.answer(
        "Опубликуйте этот пост в своем канале и нажмите кнопку:",
        reply_markup=keyboard
    )
    
    # Очищаем состояние (но оставляем в ожидании ссылки)
    clear_user_state(user_id)

