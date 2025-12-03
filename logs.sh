#!/bin/bash

# ============================================================
# 📊 СИСТЕМА ЛОГИРОВАНИЯ БОТА "РАЗГОН"
# ============================================================
# Использование:
#   ./logs.sh                    - показать меню
#   ./logs.sh user 123456789     - логи пользователя
#   ./logs.sh errors             - только ошибки
#   ./logs.sh warnings           - только предупреждения
#   ./logs.sh mailings           - все рассылки
#   ./logs.sh n8n                - взаимодействие с n8n
#   ./logs.sh penalties          - штрафы
#   ./logs.sh blocks             - блокировки
#   ./logs.sh scheduler          - планировщик
#   ./logs.sh today              - всё за сегодня
#   ./logs.sh live               - живые логи
# ============================================================

CONTAINER="telegram-bot"
LINES=200

# Цвета для вывода
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

show_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  📊 $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

show_menu() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║          📊 СИСТЕМА ЛОГИРОВАНИЯ БОТА \"РАЗГОН\"           ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║                                                          ║"
    echo "║  1) 👤 Логи пользователя (по telegram_id)                ║"
    echo "║  2) ❌ Только ERROR                                      ║"
    echo "║  3) ⚠️  Только WARNING                                   ║"
    echo "║  4) 📤 Все рассылки                                      ║"
    echo "║  5) 🤖 Взаимодействие с n8n                              ║"
    echo "║  6) 🚫 Штрафы                                            ║"
    echo "║  7) 🔒 Блокировки пользователей                          ║"
    echo "║  8) ⏰ Планировщик (scheduler)                           ║"
    echo "║  9) 📅 Всё за сегодня                                    ║"
    echo "║  10) 🔴 Живые логи (Ctrl+C для выхода)                   ║"
    echo "║  11) 📈 Статистика курса                                 ║"
    echo "║  12) 🔍 Поиск по тексту                                  ║"
    echo "║                                                          ║"
    echo "║  0) Выход                                                ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -n "Выберите опцию: "
}

# 1. Логи конкретного пользователя
logs_user() {
    local user_id=$1
    
    if [ -z "$user_id" ]; then
        echo -n "Введите telegram_id пользователя: "
        read user_id
    fi
    
    show_header "ЛОГИ ПОЛЬЗОВАТЕЛЯ $user_id"
    
    echo -e "${BLUE}📋 Данные из базы:${NC}"
    docker exec -it supabase-db psql -U postgres -d postgres -c \
        "SELECT telegram_id, first_name, username, state, course_state, current_task, penalties, channel_link FROM users WHERE telegram_id = $user_id;" 2>/dev/null
    
    echo ""
    echo -e "${BLUE}📜 Последние действия в логах:${NC}"
    docker logs --tail=$LINES $CONTAINER 2>&1 | grep -E "$user_id" | tail -50
}

# 2. Только ошибки
logs_errors() {
    show_header "ОШИБКИ (ERROR)"
    docker logs --tail=500 $CONTAINER 2>&1 | grep -E "ERROR|Error|error|Exception|Traceback" --color=always | tail -100
}

# 3. Только предупреждения
logs_warnings() {
    show_header "ПРЕДУПРЕЖДЕНИЯ (WARNING)"
    docker logs --tail=500 $CONTAINER 2>&1 | grep -E "WARNING|Warning|warning|⚠️" --color=always | tail -100
}

# 4. Все рассылки
logs_mailings() {
    show_header "ВСЕ РАССЫЛКИ"
    docker logs --tail=500 $CONTAINER 2>&1 | grep -E "рассылк|Рассылка|отправлен|разослано|Задание.*отправлено|📤|Напоминание|reminder|ПЛАНИРОВЩИК" --color=always | tail -100
}

# 5. Взаимодействие с n8n
logs_n8n() {
    show_header "ВЗАИМОДЕЙСТВИЕ С N8N"
    docker logs --tail=500 $CONTAINER 2>&1 | grep -E "n8n|N8N|webhook|Webhook|generated_text|request_id|Промпт|prompt" --color=always | tail -100
}

# 6. Штрафы
logs_penalties() {
    show_header "ШТРАФЫ"
    docker logs --tail=500 $CONTAINER 2>&1 | grep -E "штраф|Штраф|penalty|Penalty|penalties|исключен|ban" --color=always | tail -100
    
    echo ""
    echo -e "${BLUE}📊 Пользователи со штрафами:${NC}"
    docker exec -it supabase-db psql -U postgres -d postgres -c \
        "SELECT telegram_id, first_name, username, penalties, course_state FROM users WHERE penalties > 0 ORDER BY penalties DESC;" 2>/dev/null
}

# 7. Блокировки
logs_blocks() {
    show_header "БЛОКИРОВКИ ПОЛЬЗОВАТЕЛЕЙ"
    docker logs --tail=500 $CONTAINER 2>&1 | grep -E "block|Block|заблокиров|Заблокиров|is_blocked|blocked_at|deactivated" --color=always | tail -100
    
    echo ""
    echo -e "${BLUE}📊 Заблокированные пользователи:${NC}"
    docker exec -it supabase-db psql -U postgres -d postgres -c \
        "SELECT telegram_id, first_name, username, is_blocked FROM users WHERE is_blocked = true;" 2>/dev/null
}

# 8. Планировщик
logs_scheduler() {
    show_header "ПЛАНИРОВЩИК (SCHEDULER)"
    docker logs --tail=500 $CONTAINER 2>&1 | grep -E "ПЛАНИРОВЩИК|Планировщик|scheduler|Scheduler|10:00|08:50|09:20|09:35|09:50|CronTrigger|scheduled_" --color=always | tail -100
}

# 9. Логи за сегодня
logs_today() {
    local today=$(date +%Y-%m-%d)
    show_header "ВСЕ ЛОГИ ЗА $today"
    docker logs --since="24h" $CONTAINER 2>&1 | tail -200
}

# 10. Живые логи
logs_live() {
    show_header "ЖИВЫЕ ЛОГИ (Ctrl+C для выхода)"
    docker logs -f $CONTAINER
}

# 11. Статистика курса
logs_stats() {
    show_header "СТАТИСТИКА КУРСА"
    
    echo -e "${BLUE}📊 Состояние курса:${NC}"
    docker exec -it supabase-db psql -U postgres -d postgres -c \
        "SELECT * FROM course_state WHERE id = 1;" 2>/dev/null
    
    echo ""
    echo -e "${BLUE}👥 Пользователи по состояниям:${NC}"
    docker exec -it supabase-db psql -U postgres -d postgres -c \
        "SELECT course_state, COUNT(*) as count FROM users GROUP BY course_state;" 2>/dev/null
    
    echo ""
    echo -e "${BLUE}📈 Пользователи по текущему заданию:${NC}"
    docker exec -it supabase-db psql -U postgres -d postgres -c \
        "SELECT current_task, COUNT(*) as count FROM users WHERE course_state = 'in_progress' GROUP BY current_task ORDER BY current_task;" 2>/dev/null
    
    echo ""
    echo -e "${BLUE}🚫 Штрафы:${NC}"
    docker exec -it supabase-db psql -U postgres -d postgres -c \
        "SELECT penalties, COUNT(*) as count FROM users WHERE penalties > 0 GROUP BY penalties ORDER BY penalties;" 2>/dev/null
    
    echo ""
    echo -e "${BLUE}📝 Сданные посты:${NC}"
    docker exec -it supabase-db psql -U postgres -d postgres -c \
        "SELECT 
            SUM(CASE WHEN post_1 IS NOT NULL THEN 1 ELSE 0 END) as day_1,
            SUM(CASE WHEN post_2 IS NOT NULL THEN 1 ELSE 0 END) as day_2,
            SUM(CASE WHEN post_3 IS NOT NULL THEN 1 ELSE 0 END) as day_3,
            SUM(CASE WHEN post_4 IS NOT NULL THEN 1 ELSE 0 END) as day_4,
            SUM(CASE WHEN post_5 IS NOT NULL THEN 1 ELSE 0 END) as day_5
        FROM users;" 2>/dev/null
}

# 12. Поиск по тексту
logs_search() {
    local search_text=$1
    
    if [ -z "$search_text" ]; then
        echo -n "Введите текст для поиска: "
        read search_text
    fi
    
    show_header "ПОИСК: $search_text"
    docker logs --tail=1000 $CONTAINER 2>&1 | grep -i "$search_text" --color=always | tail -100
}

# Главная логика
case "$1" in
    user)
        logs_user "$2"
        ;;
    errors)
        logs_errors
        ;;
    warnings)
        logs_warnings
        ;;
    mailings)
        logs_mailings
        ;;
    n8n)
        logs_n8n
        ;;
    penalties)
        logs_penalties
        ;;
    blocks)
        logs_blocks
        ;;
    scheduler)
        logs_scheduler
        ;;
    today)
        logs_today
        ;;
    live)
        logs_live
        ;;
    stats)
        logs_stats
        ;;
    search)
        logs_search "$2"
        ;;
    *)
        # Интерактивное меню
        while true; do
            show_menu
            read choice
            
            case $choice in
                1) logs_user ;;
                2) logs_errors ;;
                3) logs_warnings ;;
                4) logs_mailings ;;
                5) logs_n8n ;;
                6) logs_penalties ;;
                7) logs_blocks ;;
                8) logs_scheduler ;;
                9) logs_today ;;
                10) logs_live ;;
                11) logs_stats ;;
                12) logs_search ;;
                0) echo "До свидания!"; exit 0 ;;
                *) echo -e "${RED}Неверный выбор${NC}" ;;
            esac
            
            echo ""
            echo -n "Нажмите Enter для продолжения..."
            read
        done
        ;;
esac

