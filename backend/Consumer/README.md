# Firewall Logs Consumer

## Description

Ce Consumer Spark Streaming récupère les logs firewall depuis Kafka et les sauvegarde dans PostgreSQL avec des agrégations en temps réel.

## Fonctionnalités

- ✅ Connexion au topic Kafka `topic-firewall-logs`
- ✅ Parsing des messages JSON avec le schéma firewall
- ✅ **Sauvegarde dans PostgreSQL** (table `firewall_logs`)
- ✅ **Génération de statistiques horaires** (table `firewall_stats_hourly`)
- A FAIRE - Détection d'anomalies avec machine learning
- ✅ Affichage des statistiques par batch :
  - Nombre de messages reçus
  - Distribution par action (ALLOW/DENY)
  - Distribution par protocole (TCP/UDP/ICMP)
  - Distribution par firewall
  - Échantillon des données

## Structure des données

### Lecture depuis Kafka

Le Consumer lit des logs firewall avec 16 colonnes + métadonnées ajoutées par le Producer.

## Architecture

```
┌─────────────────┐
│  Kafka Topic    │
│  topic-firewall │
│  -logs          │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Spark Consumer     │
│  - Read Stream      │
│  - Parse JSON       │
│  - Transform        │
│  - Detect anomalies │
└────────┬────────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL DB  │
│  - firewall_    │
│    logs         │
│  - stats_hourly │
└─────────────────┘
```

## Configuration

### Variables d'environnement

- `KAFKA_HOST` : Serveur Kafka (défaut: `localhost:9092`)
- `DATABASE_HOST` : Serveur PostgreSQL (défaut: `localhost`)
- `DATABASE_PORT` : Port PostgreSQL (défaut: 5432)
- `DATABASE_USER` : Utilisateur de la base de données
- `DATABASE_PASSWORD` : Mot de passe de la base de données
- `DATABASE_NAME` : Nom de la base de données
- `SPARK_DRIVER_MEMORY` : Mémoire du driver Spark (défaut: 4g)
- `SPARK_EXECUTOR_MEMORY` : Mémoire de l'executor Spark (défaut: 2g)

### Configuration Spark Streaming

```scala
// Checkpoint pour la récupération en cas de panne
checkpointLocation: "/tmp/kafka-checkpoint-consumer"
```

## Build

### Compilation locale

```bash
cd Consumer
sbt clean assembly
```

Le JAR sera créé dans : `target/scala-2.12/Consumer-assembly-1.0.0.jar`

### Build Docker

```bash
docker-compose build consumer
```

## Exécution

### Avec Docker Compose

```bash
cd /home/artorius/Projects/Perso/Hackhathon/CND/DIRISI_hackaton/backend
docker-compose up consumer
```

### Logs en temps réel

```bash
docker-compose logs -f consumer
```

### Arrêter

```bash
docker-compose stop consumer
```

## Sortie exemple

```
=============================================================================
  Firewall Logs Consumer - Démarrage
=============================================================================

🔄 Tentative 1/15 de connexion au topic Kafka 'topic-firewall-logs'...
✅ Connexion établie avec le topic Kafka 'topic-firewall-logs'
✅ Connexion Kafka établie. Lecture du topic 'topic-firewall-logs'...

=============================================================================
  📦 Batch #0 reçu - 500 messages
=============================================================================

💾 Sauvegarde du batch #0 dans PostgreSQL...
✅ Batch #0 sauvegardé dans PostgreSQL (500 lignes)
✅ Statistiques horaires mises à jour

📊 Statistiques du batch:

🔹 Actions:
+------+-----+
|action|count|
+------+-----+
|ALLOW |  380|
|DENY  |  120|
+------+-----+

🔹 Protocols:
+--------+-----+
|protocol|count|
+--------+-----+
|TCP     |  425|
|UDP     |   65|
|ICMP    |   10|
+--------+-----+

✅ Batch #0 traité avec succès
```

## Dépendances

- Apache Spark 3.5.0
- Kafka Client 2.8.1
- PostgreSQL JDBC 42.7.1
- Scala 2.12.18

## Traitement des Données

### Pipeline de Traitement

1. **Lecture depuis Kafka** : Stream continu des messages
2. **Parsing JSON** : Conversion en DataFrame Spark
3. **Transformation** : Renommage de colonnes, conversion de types
4. **Sauvegarde Principale** : Insert dans `firewall_logs`
5. **Agrégation** : Calcul des statistiques horaires
6. **Sauvegarde Agrégations** : Insert dans `firewall_stats_hourly`

### Gestion des Erreurs

- Retry automatique de connexion Kafka (15 tentatives)
- Logging des erreurs PostgreSQL
- Continuation du traitement en cas d'erreur d'agrégation

## Troubleshooting

### Le Consumer ne reçoit pas de messages

**Problème** : Aucun batch reçu

**Solution** :
1. Vérifiez que le Producer fonctionne : `docker-compose logs producer`
2. Vérifiez Kafka : `docker-compose logs kafka`
3. Vérifiez le topic : `docker exec -it backend-kafka-1 kafka-topics.sh --list --bootstrap-server localhost:9092`

### Erreur de connexion PostgreSQL

**Problème** : `Connection refused` ou `Authentication failed`

**Solution** :
1. Vérifiez les variables d'environnement dans docker-compose.yml
2. Vérifiez que PostgreSQL est démarré : `docker-compose ps postgres`
3. Testez la connexion : `docker exec -it backend-postgres-1 psql -U user -d dbname`

### Duplicate key errors

**Problème** : Erreurs `UNIQUE constraint` sur `firewall_stats_hourly`

**Solution** :
- C'est normal si des données d'une même heure arrivent dans des batchs différents
- Le Consumer continue à fonctionner malgré ces erreurs non-critiques
- Pour éviter : utiliser un UPSERT (ON CONFLICT DO UPDATE) dans une version future

### Checkpoint errors

**Problème** : Erreurs de checkpoint Spark

**Solution** :
```bash
# Supprimer le checkpoint et recommencer
docker exec -it backend-consumer-1 rm -rf /tmp/kafka-checkpoint-consumer
docker-compose restart consumer
```

## Monitoring

### Vérifier l'insertion dans PostgreSQL

```sql
-- Nombre total de logs
SELECT COUNT(*) FROM firewall_logs;

-- Derniers logs insérés
SELECT * FROM firewall_logs ORDER BY created_at DESC LIMIT 10;

-- Statistiques horaires
SELECT * FROM firewall_stats_hourly ORDER BY hour_timestamp DESC LIMIT 10;
```

### Métriques Spark

Accédez à l'interface Spark UI : `http://localhost:4041`
