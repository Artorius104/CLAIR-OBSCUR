#!/bin/bash

# Script de démarrage du système d'analyse de logs firewall
# Usage: ./start.sh [all|backend|frontend|build|clean|stop]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "🛡️  Système d'Analyse de Logs Firewall"
echo "======================================"
echo ""
# Fonction pour vérifier Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker n'est pas installé"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose n'est pas installé"
        exit 1
    fi
    
    echo "✅ Docker et Docker Compose sont installés"
}

# Fonction pour démarrer tous les services
start_all() {
    echo ""
    echo "🚀 Démarrage de tous les services..."
    cd "$PROJECT_ROOT"
    docker-compose up -d
    
    echo ""
    echo "✅ Services démarrés !"
    echo ""
    echo "📊 Accès aux interfaces :"
    echo "  - Frontend Web:         http://localhost:3000"
    echo "  - API Backend:          http://localhost:8000"
    echo "  - API Docs (Swagger):   http://localhost:8000/docs"
    echo "  - AI Agents:            http://localhost:8001"
    echo "  - Spark Producer UI:    http://localhost:4040"
    echo "  - Spark Consumer UI:    http://localhost:4041"
    echo ""
    echo "📝 Voir les logs :"
    echo "  docker-compose logs -f [service]"
    echo ""
    echo "  Services disponibles:"
    echo "  - producer     : Ingestion CSV → Kafka"
    echo "  - consumer     : Kafka → PostgreSQL"
    echo "  - backend_api  : API FastAPI"
    echo "  - agents       : Agent IA (OpenAI)"
    echo "  - frontend     : Interface web Next.js"
    echo "  - postgres     : Base de données"
    echo "  - kafka        : Message broker"
    echo "  - zookeeper    : Coordination Kafka"
}

# Fonction pour démarrer backend uniquement
start_backend() {
    echo ""
    echo "🚀 Démarrage du backend (sans frontend)..."
    cd "$PROJECT_ROOT"
    docker-compose up -d zookeeper kafka postgres producer consumer backend_api agents
    
    echo ""
    echo "✅ Backend démarré !"
    echo "📊 API: http://localhost:8000/docs"
}

# Fonction pour démarrer frontend uniquement
start_frontend() {
    echo ""
    echo "🚀 Démarrage du frontend..."
    cd "$PROJECT_ROOT"
    docker-compose up -d postgres backend_api agents frontend
    
    echo ""
    echo "✅ Frontend démarré !"
    echo "📊 Frontend: http://localhost:3000"
}

# Fonction pour builder les images
build_all() {
    echo ""
    echo "🏗️  Build des images Docker..."
    cd "$PROJECT_ROOT"
    docker-compose build
    
    echo ""
    echo "✅ Images construites !"
}

# Fonction pour nettoyer complètement le système
clean_system() {
    echo ""
    echo "🧹 NETTOYAGE COMPLET DU SYSTÈME"
    echo "================================"
    echo ""
    echo "⚠️  Cette opération va :"
    echo "  - Arrêter tous les services"
    echo "  - Supprimer tous les volumes Docker (base de données)"
    echo "  - Réinitialiser le state du Producer"
    echo "  - Réinitialiser le checkpoint du Consumer"
    echo ""
    read -p "Êtes-vous sûr de vouloir continuer ? (yes/no): " -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "❌ Opération annulée"
        exit 0
    fi
    
    cd "$PROJECT_ROOT"
    
    # 1. Arrêter tous les services
    echo "🛑 Arrêt de tous les services..."
    docker-compose down -v 2>/dev/null || true
    echo "✅ Services arrêtés"
    
    # 2. Réinitialiser le state file du Producer
    echo "🔄 Réinitialisation du state du Producer..."
    PRODUCER_STATE_FILE="$PROJECT_ROOT/backend/Producer/tmp/kafka_firewall_batch_state.txt"
    echo "-1" > "$PRODUCER_STATE_FILE"
    echo "✅ State du Producer réinitialisé"
    
    # 3. Supprimer les checkpoints Spark (au cas où ils persistent)
    echo "🔄 Nettoyage des checkpoints..."
    rm -rf /tmp/kafka-checkpoint-* 2>/dev/null || true
    echo "✅ Checkpoints nettoyés"
    
    echo ""
    echo "✅ NETTOYAGE TERMINÉ !"
    echo ""
    echo "Vous pouvez maintenant relancer le système avec :"
    echo "  ./start.sh all"
}

# Fonction pour arrêter les services sans tout nettoyer
stop_services() {
    echo ""
    echo "🛑 Arrêt des services..."
    cd "$PROJECT_ROOT"
    docker-compose stop
    echo "✅ Services arrêtés (les données sont conservées)"
}

# Main
check_docker

case "${1:-all}" in
    all)
        build_all
        start_all
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    build)
        build_all
        ;;
    clean)
        clean_system
        ;;
    stop)
        stop_services
        ;;
    *)
        echo "Usage: $0 [all|backend|frontend|build|stop|clean]"
        echo ""
        echo "Options:"
        echo "  all       - Compiler, builder et démarrer tous les services (défaut)"
        echo "  backend   - Démarrer uniquement les services backend"
        echo "  frontend  - Démarrer uniquement le frontend (+ API + PostgreSQL)"
        echo "  build     - Builder les images Docker"
        echo "  stop      - Arrêter les services sans supprimer les données"
        echo "  clean     - Nettoyer complètement le système (réinitialiser tout)"
        exit 1
        ;;
esac

