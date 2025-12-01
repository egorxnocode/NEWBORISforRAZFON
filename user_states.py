# -*- coding: utf-8 -*-
"""
Модуль для управления состояниями пользователей в диалоге
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class UserDialogState:
    """Состояние диалога пользователя"""
    state: str = "idle"  # idle, question_1, question_2, question_3, waiting_post_link, generating_post
    current_task: int = 0
    answers: Dict[str, str] = field(default_factory=dict)  # {answer_1: "текст", answer_2: "текст", answer_3: "текст"}
    digest_data: Optional[Dict[str, Any]] = None  # Данные из digest_day_X
    request_id: Optional[str] = None  # ID запроса к n8n


# Глобальный словарь состояний пользователей {telegram_id: UserDialogState}
user_dialog_states: Dict[int, UserDialogState] = {}


def get_user_state(telegram_id: int) -> UserDialogState:
    """Получает состояние пользователя"""
    if telegram_id not in user_dialog_states:
        user_dialog_states[telegram_id] = UserDialogState()
    return user_dialog_states[telegram_id]


def set_user_state(telegram_id: int, state: str, **kwargs):
    """Устанавливает состояние пользователя"""
    user_state = get_user_state(telegram_id)
    user_state.state = state
    
    # Обновляем дополнительные поля
    for key, value in kwargs.items():
        if hasattr(user_state, key):
            setattr(user_state, key, value)


def clear_user_state(telegram_id: int):
    """Очищает состояние пользователя"""
    if telegram_id in user_dialog_states:
        del user_dialog_states[telegram_id]


def save_answer(telegram_id: int, question_num: int, answer: str):
    """Сохраняет ответ пользователя на вопрос"""
    user_state = get_user_state(telegram_id)
    user_state.answers[f"answer_{question_num}"] = answer


def get_answers(telegram_id: int) -> Dict[str, str]:
    """Получает все ответы пользователя"""
    user_state = get_user_state(telegram_id)
    return user_state.answers

