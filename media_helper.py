# -*- coding: utf-8 -*-
"""
Вспомогательные функции для работы с медиафайлами
Автоматический поиск файлов с разными расширениями
"""

import os
from pathlib import Path
from typing import Optional


def find_image(base_path: str, extensions: list = None) -> Optional[str]:
    """
    Ищет изображение с указанным базовым путём и разными расширениями
    
    Args:
        base_path: Путь без расширения, например "media/tasks/task_1"
        extensions: Список расширений для проверки. По умолчанию ['.jpg', '.jpeg', '.png', '.webp']
        
    Returns:
        Полный путь к найденному файлу или None
        
    Examples:
        >>> find_image("media/tasks/task_1")
        "media/tasks/task_1.png"  # если task_1.png существует
        
        >>> find_image("media/tasks/task_2")
        "media/tasks/task_2.jpg"  # если task_2.jpg существует
    """
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.webp', '.JPG', '.JPEG', '.PNG', '.WEBP']
    
    # Проверяем каждое расширение
    for ext in extensions:
        full_path = f"{base_path}{ext}"
        if os.path.exists(full_path):
            return full_path
    
    # Если ничего не найдено, возвращаем None
    return None


def find_media_file(base_path: str, extensions: list = None) -> Optional[str]:
    """
    Универсальный поиск медиафайла (изображения или видео)
    
    Args:
        base_path: Путь без расширения
        extensions: Список расширений. По умолчанию включает изображения и видео
        
    Returns:
        Полный путь к найденному файлу или None
    """
    if extensions is None:
        extensions = [
            '.jpg', '.jpeg', '.png', '.webp', '.gif',
            '.JPG', '.JPEG', '.PNG', '.WEBP', '.GIF',
            '.mp4', '.mov', '.avi', '.MP4', '.MOV', '.AVI'
        ]
    
    return find_image(base_path, extensions)


def get_task_image_path(task_number: int, task_dir: str = "media/tasks") -> Optional[str]:
    """
    Получает путь к картинке задания
    
    Args:
        task_number: Номер задания (1-14)
        task_dir: Директория с заданиями
        
    Returns:
        Полный путь к картинке или None если не найдена
    """
    base_path = f"{task_dir}/task_{task_number}"
    return find_image(base_path)


def get_reminder_image_path(reminder_number: int, reminder_dir: str = "media/reminders") -> Optional[str]:
    """
    Получает путь к картинке напоминания
    
    Args:
        reminder_number: Номер напоминания (1, 2, 3)
        reminder_dir: Директория с напоминаниями
        
    Returns:
        Полный путь к картинке или None если не найдена
    """
    base_path = f"{reminder_dir}/reminder_{reminder_number}"
    return find_image(base_path)


def get_penalty_image_path(penalty_dir: str = "media/penalties") -> Optional[str]:
    """
    Получает путь к картинке штрафа
    
    Args:
        penalty_dir: Директория со штрафами
        
    Returns:
        Полный путь к картинке или None если не найдена
    """
    base_path = f"{penalty_dir}/penalty"
    return find_image(base_path)


def get_welcome_image_path(media_dir: str = "media") -> Optional[str]:
    """
    Получает путь к приветственной картинке
    
    Args:
        media_dir: Директория с медиафайлами
        
    Returns:
        Полный путь к картинке или None если не найдена
    """
    base_path = f"{media_dir}/welcome"
    return find_image(base_path)


def get_channel_request_image_path(media_dir: str = "media") -> Optional[str]:
    """
    Получает путь к картинке запроса канала
    
    Args:
        media_dir: Директория с медиафайлами
        
    Returns:
        Полный путь к картинке или None если не найдена
    """
    base_path = f"{media_dir}/channel_request"
    return find_image(base_path)


def get_final_image_path(media_dir: str = "media") -> Optional[str]:
    """
    Получает путь к финальной картинке (после регистрации)
    
    Args:
        media_dir: Директория с медиафайлами
        
    Returns:
        Полный путь к картинке или None если не найдена
    """
    base_path = f"{media_dir}/final_message"
    return find_image(base_path)


def get_instruction_video_path(media_dir: str = "media") -> Optional[str]:
    """
    Получает путь к видео с инструкцией
    
    Args:
        media_dir: Директория с медиафайлами
        
    Returns:
        Полный путь к видео или None если не найдено
    """
    base_path = f"{media_dir}/instruction"
    return find_media_file(base_path)


def get_post_accepted_image_path(media_dir: str = "media") -> Optional[str]:
    """
    Получает путь к картинке принятия поста
    
    Args:
        media_dir: Директория с медиафайлами
        
    Returns:
        Полный путь к картинке или None если не найдена
    """
    base_path = f"{media_dir}/post_accepted"
    return find_image(base_path)
