# -*- coding: utf-8 -*-
"""
Примеры для тестирования функций бота
Этот файл можно использовать для проверки работы отдельных компонентов
"""

import asyncio
from database import (
    check_email_exists,
    get_user_by_telegram_id,
    update_user_data,
    update_user_channel
)


async def test_email_check():
    """Тестирование проверки email"""
    print("=== Тест проверки email ===")
    
    # Замените на реальный email из вашей БД
    test_email = "test@example.com"
    
    exists = await check_email_exists(test_email)
    print(f"Email {test_email} существует: {exists}")
    

async def test_get_user():
    """Тестирование получения пользователя"""
    print("\n=== Тест получения пользователя ===")
    
    # Замените на реальный telegram_id
    test_telegram_id = 123456789
    
    user = await get_user_by_telegram_id(test_telegram_id)
    if user:
        print(f"Пользователь найден: {user}")
    else:
        print("Пользователь не найден")


async def test_update_user():
    """Тестирование обновления данных пользователя"""
    print("\n=== Тест обновления пользователя ===")
    
    # Замените на данные для теста
    test_email = "test@example.com"
    test_telegram_id = 123456789
    test_name = "Тестовый Пользователь"
    
    success = await update_user_data(
        email=test_email,
        telegram_id=test_telegram_id,
        first_name=test_name,
        username="testuser"
    )
    
    print(f"Обновление прошло успешно: {success}")


async def main():
    """Запуск всех тестов"""
    print("Начало тестирования...\n")
    
    try:
        await test_email_check()
        await test_get_user()
        # await test_update_user()  # Раскомментируйте для теста обновления
        
        print("\n✅ Все тесты завершены!")
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")


if __name__ == "__main__":
    print("⚠️  ВАЖНО: Перед запуском убедитесь, что:")
    print("1. Файл .env настроен правильно")
    print("2. В коде указаны реальные данные для тестирования")
    print("3. В БД есть тестовые данные\n")
    
    asyncio.run(main())

