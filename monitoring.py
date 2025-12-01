# -*- coding: utf-8 -*-
"""
Модуль для мониторинга работы бота и отправки отчетов в админский чат
"""

import logging
from datetime import datetime
from aiogram import Bot
from typing import Dict, Any

import config
import monitoring_messages as mon_msg

logger = logging.getLogger(__name__)


class BotMonitor:
    """Класс для сбора и отправки статистики работы бота"""
    
    def __init__(self):
        self.daily_stats = {
            'task_sent': 0,
            'task_failed': 0,
            'reminder_1_sent': 0,
            'reminder_1_failed': 0,
            'reminder_2_sent': 0,
            'reminder_2_failed': 0,
            'reminder_3_sent': 0,
            'reminder_3_failed': 0,
            'penalties_1': 0,
            'penalties_2': 0,
            'penalties_3': 0,  # Важно!
            'penalties_4': 0,
            'n8n_timeouts': [],  # Список telegram_id пользователей
            'n8n_errors': [],
        }
        self.last_reset = datetime.now()
    
    def reset_daily_stats(self):
        """Сбрасывает дневную статистику"""
        self.daily_stats = {
            'task_sent': 0,
            'task_failed': 0,
            'reminder_1_sent': 0,
            'reminder_1_failed': 0,
            'reminder_2_sent': 0,
            'reminder_2_failed': 0,
            'reminder_3_sent': 0,
            'reminder_3_failed': 0,
            'penalties_1': 0,
            'penalties_2': 0,
            'penalties_3': 0,
            'penalties_4': 0,
            'n8n_timeouts': [],
            'n8n_errors': [],
        }
        self.last_reset = datetime.now()
    
    async def report_task_sent(self, bot: Bot, day: int, success_count: int, failed_count: int):
        """Отчет о рассылке задания"""
        self.daily_stats['task_sent'] += success_count
        self.daily_stats['task_failed'] += failed_count
        
        if config.MONITORING_CHAT_ID:
            try:
                message = mon_msg.MSG_REPORT_TASK_SENT.format(
                    day=day,
                    success=success_count,
                    failed=failed_count,
                    time=datetime.now().strftime("%H:%M")
                )
                await bot.send_message(chat_id=config.MONITORING_CHAT_ID, text=message)
            except Exception as e:
                logger.error(f"Ошибка отправки отчета о рассылке: {e}")
    
    async def report_reminder_sent(self, bot: Bot, reminder_num: int, time: str, success_count: int, failed_count: int):
        """Отчет о рассылке напоминания"""
        self.daily_stats[f'reminder_{reminder_num}_sent'] += success_count
        self.daily_stats[f'reminder_{reminder_num}_failed'] += failed_count
        
        if config.MONITORING_CHAT_ID:
            try:
                message = mon_msg.MSG_REPORT_REMINDER_SENT.format(
                    number=reminder_num,
                    time=time,
                    success=success_count,
                    failed=failed_count,
                    actual_time=datetime.now().strftime("%H:%M")
                )
                await bot.send_message(chat_id=config.MONITORING_CHAT_ID, text=message)
            except Exception as e:
                logger.error(f"Ошибка отправки отчета о напоминании: {e}")
    
    async def report_penalties(self, bot: Bot, penalties_by_count: Dict[int, list]):
        """
        Отчет о штрафах
        
        Args:
            penalties_by_count: {1: [user_ids], 2: [user_ids], 3: [user_ids], 4: [user_ids]}
        """
        for penalty_count, user_ids in penalties_by_count.items():
            count = len(user_ids)
            self.daily_stats[f'penalties_{penalty_count}'] += count
        
        if config.MONITORING_CHAT_ID:
            try:
                # Подсчитываем общее количество
                total_penalties = sum(len(users) for users in penalties_by_count.values())
                
                # Особое внимание к 3-му штрафу
                excluded_count = len(penalties_by_count.get(3, []))
                excluded_users = penalties_by_count.get(3, [])
                
                message = mon_msg.MSG_REPORT_PENALTIES.format(
                    total=total_penalties,
                    penalty_1=len(penalties_by_count.get(1, [])),
                    penalty_2=len(penalties_by_count.get(2, [])),
                    penalty_3=excluded_count,
                    penalty_4=len(penalties_by_count.get(4, [])),
                    excluded_list=", ".join(map(str, excluded_users)) if excluded_users else "нет",
                    time=datetime.now().strftime("%H:%M")
                )
                await bot.send_message(chat_id=config.MONITORING_CHAT_ID, text=message)
            except Exception as e:
                logger.error(f"Ошибка отправки отчета о штрафах: {e}")
    
    async def report_n8n_timeout(self, bot: Bot, user_id: int, task_number: int):
        """Отчет о таймауте n8n"""
        self.daily_stats['n8n_timeouts'].append(user_id)
        
        if config.MONITORING_CHAT_ID:
            try:
                message = mon_msg.MSG_REPORT_N8N_TIMEOUT.format(
                    user_id=user_id,
                    task=task_number,
                    time=datetime.now().strftime("%H:%M")
                )
                await bot.send_message(chat_id=config.MONITORING_CHAT_ID, text=message)
            except Exception as e:
                logger.error(f"Ошибка отправки отчета о таймауте n8n: {e}")
    
    async def report_n8n_error(self, bot: Bot, user_id: int, task_number: int, error: str):
        """Отчет об ошибке n8n"""
        self.daily_stats['n8n_errors'].append(user_id)
        
        if config.MONITORING_CHAT_ID:
            try:
                message = mon_msg.MSG_REPORT_N8N_ERROR.format(
                    user_id=user_id,
                    task=task_number,
                    error=error,
                    time=datetime.now().strftime("%H:%M")
                )
                await bot.send_message(chat_id=config.MONITORING_CHAT_ID, text=message)
            except Exception as e:
                logger.error(f"Ошибка отправки отчета об ошибке n8n: {e}")
    
    async def send_daily_summary(self, bot: Bot):
        """Отправляет ежедневную сводку"""
        if config.MONITORING_CHAT_ID:
            try:
                message = mon_msg.MSG_DAILY_SUMMARY.format(
                    date=datetime.now().strftime("%d.%m.%Y"),
                    task_sent=self.daily_stats['task_sent'],
                    task_failed=self.daily_stats['task_failed'],
                    reminder_1_sent=self.daily_stats['reminder_1_sent'],
                    reminder_2_sent=self.daily_stats['reminder_2_sent'],
                    reminder_3_sent=self.daily_stats['reminder_3_sent'],
                    total_penalties=sum([
                        self.daily_stats['penalties_1'],
                        self.daily_stats['penalties_2'],
                        self.daily_stats['penalties_3'],
                        self.daily_stats['penalties_4']
                    ]),
                    penalty_1=self.daily_stats['penalties_1'],
                    penalty_2=self.daily_stats['penalties_2'],
                    penalty_3=self.daily_stats['penalties_3'],
                    penalty_4=self.daily_stats['penalties_4'],
                    n8n_timeouts=len(self.daily_stats['n8n_timeouts']),
                    n8n_errors=len(self.daily_stats['n8n_errors'])
                )
                await bot.send_message(chat_id=config.MONITORING_CHAT_ID, text=message)
            except Exception as e:
                logger.error(f"Ошибка отправки дневной сводки: {e}")


# Глобальный экземпляр монитора
monitor = BotMonitor()

