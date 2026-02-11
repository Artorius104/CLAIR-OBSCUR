# 🛡️ Système d'Analyse de Logs Firewall en Temps Réel

Projet de traitement et visualisation de logs firewall en temps réel utilisant Apache Spark, Kafka, PostgreSQL et Streamlit.

## 🎯 Objectif

Créer un système complet d'analyse de logs firewall permettant :
- L'ingestion massive de logs en temps réel
- Le traitement et l'agrégation automatique
- La détection de menaces de sécurité
- La visualisation interactive des données
- La proposition de remédiation avec IA
- Un chatbot de discussion

## 🎯 TODO LIST
- Mettre en place des traitements / analyses plus poussés
- Changer le frontend de streamlit vers React
- Organiser les traitements en tables de FAITS pour faciliter les analyses / call API
- Coder le backend API et agents
- Coder la détection d'anomalies avec IA
- Coder le système d'agents
- Modifier le frontend


## 🏗️ Architecture Globale

```
┌─────────────────┐
│   CSV Dataset   │
│   3.3M+ logs    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Spark Producer │
│  - Read CSV     │
│  - Batch (500)  │
│  - Send to      │
│    Kafka        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Kafka Cluster  │
│  topic-firewall │
│  -logs          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Spark Consumer │
│  - Stream       │
│  - Process      │
│  - Save to DB   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  PostgreSQL DB  │────▶│  Streamlit   │
│  - Logs         │     │  Dashboard   │
│  - Stats        │     │  - Analytics │
│  - Aggregates   │     │  - Alerts    │
└─────────────────┘     └──────────────┘
```

## 📦 Composants

### 1. Producer (Spark)
**Rôle** : Ingestion des données CSV vers Kafka

**Fonctionnalités** :
- Lecture du dataset `all_firewall_logs.csv` (3.3M+ logs)
- Envoi par batchs de 500 logs
- Reprise automatique après redémarrage
- Utilisation du `timestamp` comme clé Kafka

**Technologies** : Scala 2.12, Spark 3.5.0, Kafka

📖 [README Producer](backend/Producer/README.md)

### 2. Consumer (Spark Streaming)
**Rôle** : Traitement des flux Kafka et sauvegarde dans PostgreSQL

**Fonctionnalités** :
- Lecture en streaming du topic Kafka
- Parsing et transformation des logs
- Sauvegarde dans PostgreSQL
- Agrégations horaires automatiques
- Statistiques en temps réel

**Technologies** : Scala 2.12, Spark Streaming 3.5.0, PostgreSQL JDBC

📖 [README Consumer](backend/Consumer/README.md)

### 3. PostgreSQL
**Rôle** : Stockage persistant des données

**Base de données** :
- **Tables** : `firewall_logs`, `firewall_stats_hourly`, `firewall_top_ports`, `firewall_suspicious_ips`
- **Index** : Sur timestamp, IPs, actions pour performance
- **Requêtes optimisées** : Directes dans l'application (pas de vues pour éviter les problèmes au démarrage)

📖 [README PostgreSQL](backend/init/README.md)

### 4. Dashboard Streamlit (Frontend)
**Rôle** : Visualisation interactive des données

**Pages** :
- **🏠 Vue d'ensemble** : KPIs, graphiques, top IPs
- **📈 Analyse Temporelle** : Évolution du trafic, heatmaps
- **🔍 Recherche** : Filtres avancés, export CSV
- **⚠️ Alertes Sécurité** : IPs suspectes, blocklists

**Technologies** : Python 3.10, Streamlit, Plotly, Pandas

📖 [README Dashboard](frontend/README.md)

### 5. Kafka
**Rôle** : Bus de messages pour le streaming

**Configuration** :
- Topic: `topic-firewall-logs`
- Partitions: 3
- Réplication: 1

### 6. Zookeeper
**Rôle** : Coordination Kafka

## 🚀 Installation et Démarrage

### Prérequis

- Docker & Docker Compose
- 8 GB RAM minimum
- 20 GB d'espace disque

### Variables d'Environnement

Le fichier `.env` existe déjà dans le dossier `backend/` avec la configuration :

```bash
POSTGRES_USER=divinandretomadam
POSTGRES_PASSWORD=oDAnmvidrTnmeiAa
POSTGRES_DB=spark_streaming_db
KAFKA_HOST=kafka:9092
SPARK_DRIVER_MEMORY=2g
SPARK_EXECUTOR_MEMORY=2g
```

### 🧹 Démarrage via script

Pour redémarrer le système à zéro (supprimer toutes les données et réinitialiser les états) :

```bash
# Depuis la racine du projet
./start.sh clean
```

Cette commande va :
- Arrêter tous les services Docker
- Supprimer tous les volumes (base de données vidée)
- Réinitialiser le state du Producer (batch_state_file)
- Supprimer les checkpoints du Consumer
- Permettre un redémarrage propre

Après le nettoyage, relancez avec :
```bash
./start.sh all
```

### Démarrage Complet

```bash
# Compiler le Producer
cd backend/Producer && sbt clean assembly && cd ../..

# Compiler le Consumer
cd backend/Consumer && sbt clean assembly && cd ../..

# Démarrer tous les services
docker-compose up --build
```

### Démarrage Sélectif

```bash
# Démarrer uniquement Kafka et Zookeeper
docker-compose up zookeeper kafka

# Démarrer le Producer
docker-compose up producer

# Démarrer le Consumer
docker-compose up consumer

# Démarrer le Dashboard
docker-compose up streamlit
```

## 📊 Accès aux Interfaces

| Service | URL | Description |
|---------|-----|-------------|
| **Streamlit Dashboard** | http://localhost:8501 | Interface de visualisation |
| **Spark Producer UI** | http://localhost:4040 | Monitoring Producer |
| **Spark Consumer UI** | http://localhost:4041 | Monitoring Consumer |
| **PostgreSQL** | localhost:5432 | Base de données |

## 🔄 Workflow Complet

### 1. Démarrage Initial

```bash
docker-compose up
```

Ordre de démarrage :
1. Zookeeper (coordination)
2. Kafka (message broker)
3. PostgreSQL (database)
4. Producer (ingestion)
5. Consumer (processing)
6. Streamlit (visualization)

### 2. Ingestion des Données

Le **Producer** lit le CSV et envoie les logs à Kafka :
- Batch 0 : Logs 1-500
- Batch 1 : Logs 501-1000
- ...

Progression sauvegardée dans `backend/Producer/tmp/kafka_firewall_batch_state.txt`

### 3. Traitement en Temps Réel

Le **Consumer** traite chaque batch :
- Parse les messages JSON
- Sauvegarde dans `firewall_logs`
- Calcule les statistiques horaires
- Affiche les métriques dans les logs

### 4. Visualisation

Le **Dashboard Streamlit** affiche :
- KPIs en temps réel
- Graphiques interactifs
- Recherche avancée
- Alertes de sécurité

## 📈 Dataset

### all_firewall_logs.csv

**Taille** : ~3.3 millions de logs  
**Colonnes** : 16 champs

- `timestamp` : 2025-02-01T00:00:00Z
- `firewall_id` : FW-A, FW-B, FW-C
- `src_ip`, `dst_ip` : Adresses IPv4
- `src_port`, `dst_port` : 1-65535
- `protocol` : TCP, UDP, ICMP
- `action` : ALLOW, DENY
- `bytes` : Volume de données
- `duration_ms` : Durée de session
- `rule_id`, `session_id`, `user`, `reason`, `status`, `flags`

## 🛠️ Commandes Utiles

### Docker Compose

```bash
# Voir les logs en temps réel
docker-compose logs -f [service]

# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v

# Rebuilder un service
docker-compose build [service]

# Redémarrer un service
docker-compose restart [service]

# Voir l'état des services
docker-compose ps
```

### PostgreSQL

```bash
# Se connecter à PostgreSQL
docker exec -it test_hackathon-postgres-1 psql -U user -d spark_streaming_db

# Compter les logs
SELECT COUNT(*) FROM firewall_logs;

# Statistiques globales
SELECT * FROM firewall_global_stats;

# Top IPs bloquées
SELECT src_ip, COUNT(*) FROM firewall_logs WHERE action='DENY' GROUP BY src_ip ORDER BY COUNT(*) DESC LIMIT 10;
```

### Kafka

```bash
# Lister les topics
docker exec -it backend-kafka-1 kafka-topics.sh --list --bootstrap-server localhost:9092

# Voir les messages du topic
docker exec -it backend-kafka-1 kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic topic-firewall-logs --from-beginning --max-messages 5
```

### Réinitialiser le Producer

```bash
# Arrêter le Producer
docker-compose stop producer

# Réinitialiser l'état
rm backend/Producer/tmp/kafka_firewall_batch_state.txt
echo "-1" > backend/Producer/tmp/kafka_firewall_batch_state.txt

# Redémarrer
docker-compose up producer
```

## 🐛 Troubleshooting

### Le Producer n'envoie rien

1. Vérifiez que Kafka est démarré : `docker-compose logs kafka`
2. Vérifiez le dataset : `ls -lh data/all_firewall_logs.csv`
3. Vérifiez le volume Docker dans docker-compose.yml

### Le Consumer ne reçoit rien

1. Vérifiez que le Producer envoie : `docker-compose logs producer`
2. Vérifiez la connexion Kafka : `docker-compose logs consumer | grep "Connexion établie"`
3. Vérifiez le topic Kafka (commande ci-dessus)

### Le Dashboard est vide

1. Vérifiez que PostgreSQL contient des données : `SELECT COUNT(*) FROM firewall_logs;`
2. Vérifiez les logs du Consumer : `docker-compose logs consumer | grep "sauvegardé"`
3. Rafraîchissez le dashboard (bouton dans la sidebar)

### Erreurs de mémoire

1. Augmentez la RAM des services dans docker-compose.yml
2. Réduisez `BATCH_SIZE` dans le Producer
3. Ajustez `spark.sql.shuffle.partitions`

## 📚 Documentation

- [Producer README](backend/Producer/README.md)
- [Consumer README](backend/Consumer/README.md)
- [PostgreSQL README](backend/init/README.md)
- [Dashboard README](backend/DataVisualisation/README.md)
