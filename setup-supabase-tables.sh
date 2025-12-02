#!/bin/bash

# ============================================================
# Скрипт создания таблиц в Supabase
# ============================================================

echo "🗄️  СОЗДАНИЕ ТАБЛИЦ В SUPABASE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd /opt/NEWBORISforRAZFON

# Попытка 1: Через psql в контейнере supabase-db
echo "Попытка 1: Через PostgreSQL контейнер..."
if docker exec supabase-db psql -U postgres -d postgres -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ PostgreSQL доступен"
    
    # Выполняем SQL скрипты
    docker exec -i supabase-db psql -U postgres -d postgres < setup_database.sql
    docker exec -i supabase-db psql -U postgres -d postgres < setup_course_database.sql
    
    # Добавляем тестовый email
    docker exec -i supabase-db psql -U postgres -d postgres << 'EOF'
INSERT INTO users (email) VALUES ('admin@yandex.ru') ON CONFLICT DO NOTHING;
SELECT 'Email admin@yandex.ru добавлен!' as status;
EOF
    
    echo ""
    echo "✅ Таблицы созданы!"
    
    # Проверка
    echo ""
    echo "📊 Проверка таблиц:"
    docker exec supabase-db psql -U postgres -d postgres -c "\dt users"
    docker exec supabase-db psql -U postgres -d postgres -c "SELECT * FROM users;"
    
else
    echo "❌ PostgreSQL недоступен через контейнер"
    echo ""
    echo "Альтернатива: Выполните SQL вручную"
    echo ""
    echo "1. Откройте Supabase Studio:"
    echo "   http://ваш-сервер:8009"
    echo ""
    echo "2. Перейдите в SQL Editor"
    echo ""
    echo "3. Выполните содержимое этих файлов:"
    echo "   - setup_database.sql"
    echo "   - setup_course_database.sql"
    echo ""
    echo "4. Добавьте тестовый email:"
    echo "   INSERT INTO users (email) VALUES ('admin@yandex.ru');"
    echo ""
    
    echo "Содержимое setup_database.sql:"
    cat setup_database.sql
    
    echo ""
    echo "Содержимое setup_course_database.sql:"
    cat setup_course_database.sql
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

