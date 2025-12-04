#!/bin/bash

# ============================================================
# ⚡ БЫСТРЫЕ КОМАНДЫ ДЛЯ ЛОГОВ
# ============================================================
# Использование:
#   ./quick-logs.sh               - последние 50 строк
#   ./quick-logs.sh -e            - только ошибки
#   ./quick-logs.sh -w            - только предупреждения
#   ./quick-logs.sh -u 123456     - логи пользователя
#   ./quick-logs.sh -f            - живые логи
#   ./quick-logs.sh -p            - проблемы (errors + warnings)
# ============================================================

CONTAINER="telegram-bot"

case "$1" in
    -e|--errors)
        echo "❌ ОШИБКИ:"
        docker logs --tail=300 $CONTAINER 2>&1 | grep -E "ERROR|Exception|Traceback" --color=always | tail -30
        ;;
    -w|--warnings)
        echo "⚠️ ПРЕДУПРЕЖДЕНИЯ:"
        docker logs --tail=300 $CONTAINER 2>&1 | grep -E "WARNING" --color=always | tail -30
        ;;
    -u|--user)
        if [ -z "$2" ]; then
            echo "Использование: ./quick-logs.sh -u TELEGRAM_ID"
            exit 1
        fi
        echo "👤 ЛОГИ ПОЛЬЗОВАТЕЛЯ $2:"
        docker logs --tail=500 $CONTAINER 2>&1 | grep "$2" | tail -30
        ;;
    -f|--follow)
        echo "🔴 ЖИВЫЕ ЛОГИ (Ctrl+C для выхода):"
        docker logs -f $CONTAINER
        ;;
    -p|--problems)
        echo "🚨 ПРОБЛЕМЫ (ERROR + WARNING):"
        docker logs --tail=500 $CONTAINER 2>&1 | grep -E "ERROR|WARNING|Exception" --color=always | tail -50
        ;;
    -m|--mailings)
        echo "📤 РАССЫЛКИ:"
        docker logs --tail=300 $CONTAINER 2>&1 | grep -E "ПЛАНИРОВЩИК|отправлен|разослано" --color=always | tail -30
        ;;
    -s|--stats)
        echo "📊 СТАТИСТИКА:"
        docker exec -it supabase-db psql -U postgres -d postgres -c \
            "SELECT course_state, COUNT(*) FROM users GROUP BY course_state;"
        ;;
    -h|--help)
        echo "⚡ Быстрые команды для логов:"
        echo ""
        echo "  ./quick-logs.sh           - последние 50 строк"
        echo "  ./quick-logs.sh -e        - только ошибки (ERROR)"
        echo "  ./quick-logs.sh -w        - только предупреждения (WARNING)"
        echo "  ./quick-logs.sh -p        - все проблемы (ERROR + WARNING)"
        echo "  ./quick-logs.sh -u ID     - логи пользователя по telegram_id"
        echo "  ./quick-logs.sh -m        - рассылки"
        echo "  ./quick-logs.sh -s        - статистика курса"
        echo "  ./quick-logs.sh -f        - живые логи"
        echo ""
        ;;
    *)
        docker logs --tail=50 $CONTAINER
        ;;
esac


