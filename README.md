# 🛡️ CLAIR OBSCUR — Plateforme NDR (Network Detection & Response)

Système d'analyse de logs firewall en temps réel avec détection de menaces, analytics avancés et assistant IA.

## 🏗️ Architecture

```
CSV Dataset (3.3M+ logs)
       │
       ▼
┌───────────────┐      ┌──────────────┐
│   Producer    │────▶│    Kafka     │
│  (Spark/Scala)│      │  (Streaming) │
└───────────────┘      └──────┬───────┘
                              │
                              ▼
                       ┌─────────────┐
                       │  Consumer   │
                       │  (Spark)    │
                       └──────┬──────┘
                              │
                              ▼
    ┌──────────┐     ┌─────────────────┐      ┌─────────────┐
    │ Agents   │────▶│   PostgreSQL    │◀────│ Backend API │
    │ (OpenAI) │     │   (Storage)     │      │ (FastAPI)   │
    └──────────┘     └─────────────────┘      └─────┬───────┘
                                                    │
                                                    ▼
                                              ┌────────────┐
                                              │  Frontend  │
                                              │  (Next.js) │
                                              └────────────┘
```

## 📦 Stack Technique

| Composant       | Technologies                                   |
| --------------- | ---------------------------------------------- |
| **Producer**    | Scala 2.12, Spark 3.5, Kafka                   |
| **Consumer**    | Scala 2.12, Spark Streaming, PostgreSQL JDBC   |
| **Backend API** | Python 3.11, FastAPI, SQLAlchemy, psycopg2     |
| **Agents IA**   | Python 3.11, OpenAI API (GPT-4o-mini)          |
| **Frontend**    | Next.js 15, React 19, TypeScript, Tailwind CSS |
| **Database**    | PostgreSQL 15                                  |
| **Messaging**   | Apache Kafka + Zookeeper                       |

## 🚀 Démarrage Rapide

### Prérequis

- Docker & Docker Compose
- 8 GB RAM minimum
- Une clé API OpenAI (pour le chatbot IA)

### Configuration

Modifiez les variables d'environnements et ajoutez votre clé API vers votre LLM préféré dans le fichier `.env` à la racine :

```bash
LLM_API_KEY=sk-...
```

### Lancement

```bash
# Démarrer tous les services
./start.sh all

# Démarrer uniquement le backend
./start.sh backend

# Démarrer uniquement le frontend (+ API + DB)
./start.sh frontend

# Arrêter les services (données conservées)
./start.sh stop

# Nettoyage complet (reset)
./start.sh clean
```

## 📊 Interfaces

| Service            | URL                        | Description                         |
| ------------------ | -------------------------- | ----------------------------------- |
| **Frontend**       | http://localhost:3000      | Dashboard, Analytics, Logs, Chat IA |
| **API Docs**       | http://localhost:8000/docs | Swagger / OpenAPI                   |
| **API Backend**    | http://localhost:8000      | REST API                            |
| **Agents IA**      | http://localhost:8001      | Service chatbot                     |
| **Spark Producer** | http://localhost:4040      | Monitoring ingestion                |
| **Spark Consumer** | http://localhost:4041      | Monitoring traitement               |

## 📄 Pages Frontend

| Page                | Description                                              |
| ------------------- | -------------------------------------------------------- |
| **Anomaly Tickets** | Logs en temps réel avec sévérité, actions, IPs           |
| **Analytics**       | Vue d'ensemble, timeline, répartition actions/protocoles |
| **Log Search**      | Recherche full-text, filtres sévérité/action, pagination |
| **Network Map**     | IPs suspectes, ports les plus actifs                     |
| **AI Assistant**    | Chatbot IA avec contexte base de données en temps réel   |

## 🔌 API Endpoints

```
GET  /api/v1/logs                   # Logs avec filtres (severity, action, search)
GET  /api/v1/logs/count             # Nombre total de logs
GET  /api/v1/logs/suspicious-ips    # IPs suspectes
GET  /api/v1/logs/top-ports         # Ports les plus actifs
GET  /api/v1/analytics/overview     # Stats globales
GET  /api/v1/analytics/timeline     # Timeline horaire
GET  /api/v1/analytics/actions      # Répartition des actions
GET  /api/v1/analytics/protocols    # Répartition des protocoles
GET  /api/v1/analytics/severity     # Répartition des sévérités
POST /api/v1/chat                   # Chat avec l'agent IA
```

## 📈 Dataset

**Fichier** : `data/all_firewall_logs.csv` (~3.3M logs, 16 colonnes)

Colonnes : `timestamp`, `firewall_id`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`, `action`, `bytes`, `duration_ms`, `rule_id`, `session_id`, `user`, `reason`, `status`, `flags`

## 🛠️ Commandes Utiles

```bash
# Logs en temps réel d'un service
docker-compose logs -f [service]

# Services : producer, consumer, backend_api, agents, frontend, postgres, kafka

# Se connecter à PostgreSQL
docker exec -it clair-obscur-postgres-1 psql -U divinandretomadam -d spark_streaming_db

# Voir les topics Kafka
docker exec -it clair-obscur-kafka-1 kafka-topics.sh --list --bootstrap-server localhost:9092
```

## 🐛 Troubleshooting

| Problème              | Solution                                                                           |
| --------------------- | ---------------------------------------------------------------------------------- |
| Dashboard vide        | Vérifier que le Producer/Consumer tournent : `docker-compose logs consumer`        |
| Chat IA ne répond pas | Vérifier `LLM_API_KEY` dans `.env` et redémarrer : `docker-compose restart agents` |
| Erreur mémoire        | Augmenter la RAM Docker ou réduire `BATCH_SIZE` dans le Producer                   |
| API inaccessible      | `docker-compose logs backend_api` pour voir les erreurs                            |

## 📚 Documentation détaillée

- [Producer (Spark/Scala)](backend/Producer/README.md)
- [Consumer (Spark Streaming)](backend/Consumer/README.md)
- [PostgreSQL (Schéma)](backend/init/README.md)
- [Frontend (Next.js)](frontend/README.md)
