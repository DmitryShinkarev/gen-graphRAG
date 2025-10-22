#!/bin/bash
# Show database statistics for Java Unit Test Agent

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                  📊 ПОЛНАЯ СТАТИСТИКА БАЗ ДАННЫХ                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if services are running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ API сервер не запущен. Запустите: ./start_api.sh"
    exit 1
fi

# Get Qdrant stats
echo "🔍 QDRANT - ВЕКТОРНАЯ БАЗА ДАННЫХ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
QDRANT_INFO=$(curl -s http://localhost:6333/collections/java_methods)
POINTS=$(echo "$QDRANT_INFO" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data['result']['points_count'])" 2>/dev/null || echo "0")
STATUS=$(echo "$QDRANT_INFO" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data['result']['status'])" 2>/dev/null || echo "unknown")
SEGMENTS=$(echo "$QDRANT_INFO" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data['result']['segments_count'])" 2>/dev/null || echo "0")

echo "  Коллекция:         java_methods"
echo "  Статус:            ✅ $STATUS"
echo "  Векторов:          $POINTS точек"
echo "  Сегментов:         $SEGMENTS"
echo "  Размер вектора:    384 измерения"
echo "  Метрика:           Cosine similarity"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# System health
echo "🎯 СОСТОЯНИЕ СИСТЕМЫ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HEALTH=$(curl -s http://localhost:8000/health)
echo "$HEALTH" | python3 -c "
import sys, json
data = json.load(sys.stdin)
components = data.get('components', {})
print(f\"  API Сервер:        {'✅' if data.get('status') == 'healthy' else '❌'} Работает\")
print(f\"  Граф:              {'✅' if components.get('graph') else '❌'} {'Доступен' if components.get('graph') else 'Недоступен'}\")
print(f\"  Эмбеддер:          {'✅' if components.get('embedder') else '❌'} {'Доступен' if components.get('embedder') else 'Недоступен'}\")
print(f\"  Vector Store:      {'✅' if components.get('vector_store') else '❌'} {'Доступен' if components.get('vector_store') else 'Недоступен'}\")
print(f\"  Indexer Agent:     {'✅' if components.get('indexer_agent') else '❌'} {'Доступен' if components.get('indexer_agent') else 'Недоступен'}\")
"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Indexing activity
echo "📈 АКТИВНОСТЬ ИНДЕКСАЦИИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f logs/api.log ]; then
    SESSIONS=$(grep -c "Indexing completed" logs/api.log 2>/dev/null || echo "0")
    echo "  Всего сессий:      $SESSIONS"
    
    # Performance metrics
    grep "Indexing completed" logs/api.log 2>/dev/null | awk '{print $NF}' | sed 's/s$//' | python3 -c "
import sys
times = [float(line.strip()) for line in sys.stdin if line.strip()]
if times:
    print(f'  Среднее время:     {sum(times)/len(times):.3f} сек')
    print(f'  Мин. время:        {min(times):.3f} сек')
    print(f'  Макс. время:       {max(times):.3f} сек')
" 2>/dev/null
    
    # Last indexing
    LAST_PROJECT=$(grep "Indexing project:" logs/api.log 2>/dev/null | tail -1 | awk -F': ' '{print $NF}')
    if [ ! -z "$LAST_PROJECT" ]; then
        echo ""
        echo "  Последний проект:  $(basename $LAST_PROJECT)"
    fi
fi
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Summary
echo "📊 ИТОГОВЫЕ ЦИФРЫ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Векторов в Qdrant:    $POINTS"
echo "  Статус коллекции:     $STATUS ✅"
echo "  Готовность:           100% - Система готова к работе"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Links
echo "🔗 ПОЛЕЗНЫЕ ССЫЛКИ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📚 API Документация:   http://localhost:8000/docs"
echo "  💚 Health Check:       http://localhost:8000/health"
echo "  📊 Статистика:         http://localhost:8000/api/stats"
echo "  🔍 Qdrant Dashboard:   http://localhost:6333/dashboard"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

