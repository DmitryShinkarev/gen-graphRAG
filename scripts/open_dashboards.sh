#!/bin/bash
# Открыть все UI дашборды баз данных

echo "🌐 Открываем UI интерфейсы..."
echo ""

# Проверка что Docker запущен
if ! docker ps | grep -q "memgraph"; then
    echo "❌ Memgraph не запущен!"
    echo "Запустите: docker compose up -d memgraph"
    exit 1
fi

echo "✅ Открываем дашборды..."
echo ""

# Открываем браузер с каждым UI
open "http://localhost:3000"  # Memgraph Lab
sleep 1
open "http://localhost:6333/dashboard"  # Qdrant Dashboard
sleep 1
open "http://localhost:8000/docs"  # API Docs
sleep 1
open "http://localhost:3001"  # Grafana

echo "✅ Все дашборды открыты!"
echo ""
echo "📋 Учетные данные:"
echo ""
echo "  🔴 Memgraph Lab (3000):"
echo "     URL:      bolt://localhost:7687"
echo "     Auth:     Не требуется"
echo ""
echo "  🟣 Qdrant Dashboard (6333):"
echo "     Auth:     Не требуется"
echo ""
echo "  📊 Grafana (3001):"
echo "     User:     admin"
echo "     Password: admin"
echo ""
echo "  📚 API Docs (8000):"
echo "     Auth:     Не требуется"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Примеры Cypher запросов в Memgraph Lab:"
echo ""
echo "  // Показать все узлы по типам"
echo "  MATCH (n) RETURN labels(n)[0], count(n)"
echo ""
echo "  // Показать методы класса"
echo "  MATCH (c:Class)-[:CONTAINS]->(m:Method)"
echo "  WHERE c.name = 'BetaChecker'"
echo "  RETURN m.name, m.complexity"
echo ""
echo "  // Граф вызовов методов"
echo "  MATCH path = (m1:Method)-[:CALLS*1..2]->(m2:Method)"
echo "  RETURN path LIMIT 25"
echo ""

