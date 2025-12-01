# -*- coding: utf-8 -*-
"""
Веб-сервер для приема вебхуков от n8n
"""

import logging
from aiohttp import web
from ai_helper import handle_n8n_response

logger = logging.getLogger(__name__)


async def handle_n8n_webhook(request):
    """
    Обработчик вебхука от n8n
    
    Ожидаемый формат JSON:
    {
        "request_id": "uuid",
        "generated_text": "текст поста"
    }
    """
    try:
        data = await request.json()
        
        request_id = data.get('request_id')
        generated_text = data.get('generated_text')
        
        if not request_id or not generated_text:
            logger.error("Неверный формат данных от n8n")
            return web.Response(text="Invalid data", status=400)
        
        # Обрабатываем ответ
        success = handle_n8n_response(request_id, generated_text)
        
        if success:
            return web.Response(text="OK", status=200)
        else:
            return web.Response(text="Request ID not found", status=404)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука от n8n: {e}")
        return web.Response(text="Internal error", status=500)


async def start_webhook_server(host='0.0.0.0', port=8080):
    """
    Запускает веб-сервер для приема вебхуков
    
    Args:
        host: Хост для прослушивания
        port: Порт для прослушивания
    """
    app = web.Application()
    app.router.add_post('/webhook/n8n', handle_n8n_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Webhook сервер запущен на http://{host}:{port}/webhook/n8n")
    
    return runner


# Можно запустить отдельно для тестирования
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    import asyncio
    
    async def main():
        runner = await start_webhook_server()
        
        # Ждем бесконечно
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
    
    asyncio.run(main())

