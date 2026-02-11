# Firewall Logs Producer

## Description

Ce Producer Spark lit les logs firewall depuis un fichier CSV et les envoie vers Kafka par batchs. Il utilise un système de sauvegarde d'état pour reprendre l'envoi là où il s'était arrêté en cas de redémarrage.

## Fonctionnalités

- ✅ Lecture du dataset CSV `all_firewall_logs.csv`
- ✅ Envoi par batchs vers Kafka (taille configurable)
- ✅ Sauvegarde de l'état de progression
- ✅ Reprise automatique après redémarrage
- ✅ Utilisation du `timestamp` comme clé Kafka
- ✅ Optimisations Kafka (compression, batching, timeouts)
- ✅ Affichage de la progression en temps réel

## Structure des données

Le Producer lit des logs firewall avec les colonnes suivantes :
- `timestamp` : Horodatage de l'événement (utilisé comme clé Kafka)
- `firewall_id` : Identifiant du firewall (FW-A, FW-B, etc.)
- `src_ip`, `dst_ip` : Adresses IP source et destination
- `src_port`, `dst_port` : Ports source et destination
- `protocol` : Protocole réseau (TCP/UDP/ICMP)
- `action` : Action du firewall (ALLOW/DENY)
- `bytes` : Taille des données transférées
- `duration_ms` : Durée de la session en millisecondes
- `rule_id` : ID de la règle firewall appliquée
- `session_id` : Identifiant unique de session
- `user` : Utilisateur (optionnel)
- `reason` : Raison de l'action (optionnel)
- `status` : Statut de la connexion
- `flags` : Flags TCP/IP (optionnel)

## Architecture

```
┌─────────────────┐
│  CSV Dataset    │
│  all_firewall_  │
│  logs.csv       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Spark Producer │
│  - Read CSV     │
│  - Batch Split  │
│  - JSON Convert │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Kafka Topic    │
│  topic-firewall │
│  -logs          │
└─────────────────┘
```

## Configuration

### Variables d'environnement

- `KAFKA_HOST` : Serveur Kafka (défaut: `localhost:9092`)
- `DATASET_PATH` : Chemin vers le dossier des datasets (défaut: `data/`)
- `BATCH_SIZE` : Nombre de logs par batch (défaut: 500)
- `SPARK_DRIVER_MEMORY` : Mémoire du driver Spark (défaut: 2g)
- `SPARK_EXECUTOR_MEMORY` : Mémoire de l'executor Spark (défaut: 2g)

### Configuration Kafka

Le Producer utilise les paramètres Kafka optimisés :
```scala
// Timeouts
kafka.request.timeout.ms: 300000 (5 minutes)
kafka.delivery.timeout.ms: 360000 (6 minutes)
kafka.max.block.ms: 300000 (5 minutes)

// Retry
kafka.retries: 3
kafka.retry.backoff.ms: 1000

// Performance
kafka.batch.size: 32768 (32KB)
kafka.linger.ms: 100
kafka.buffer.memory: 67108864 (64MB)
kafka.compression.type: snappy
```

## Système de reprise

Le Producer maintient un fichier d'état dans `/app/tmp/kafka_firewall_batch_state.txt` qui contient le numéro du dernier batch envoyé.

### Réinitialiser l'envoi

Pour recommencer depuis le début :

1. **Arrêter Docker Compose** :
```bash
cd /home/artorius/Projects/Perso/Hackhathon/CND/DIRISI_hackaton/backend
docker-compose down
```

2. **Réinitialiser le fichier d'état** :
```bash
rm Producer/tmp/kafka_firewall_batch_state.txt
echo "-1" > Producer/tmp/kafka_firewall_batch_state.txt
```

3. **Redémarrer** :
```bash
docker-compose up -d
```

## Build

### Compilation locale

```bash
cd Producer
sbt clean assembly
```

Le JAR sera créé dans : `target/scala-2.12/Producer-assembly-1.0.0.jar`

### Build Docker

```bash
docker-compose build producer
```

## Exécution

### Avec Docker Compose (recommandé)

```bash
cd /home/artorius/Projects/Perso/Hackhathon/CND/DIRISI_hackaton/backend
docker-compose up producer
```

### Logs en temps réel

```bash
docker-compose logs -f producer
```

### Arrêter

```bash
docker-compose stop producer
```

## Sortie exemple

```
=============================================================================
Nombre total de batchs déjà envoyés, : 0
Nombre total de batchs à envoyer à Kafka, : 6633233
=============================================================================

✔ Batch 0 envoyé dans le topic Kafka 'topic-firewall-logs'
✔ Batch 1 envoyé dans le topic Kafka 'topic-firewall-logs'
✔ Batch 2 envoyé dans le topic Kafka 'topic-firewall-logs'
...
✅ Tous les batchs ont été envoyés à Kafka.
```

## Dépendances

- Apache Spark 3.5.0
- Kafka Client 2.8.1
- Scala 2.12.18

## Schéma des données

Le schéma Spark utilisé est défini dans `Config.scala` :

```scala
val firewallSchema = StructType(Array(
  StructField("timestamp", StringType, nullable = false),
  StructField("firewall_id", StringType, nullable = false),
  // ... autres champs
))
```

## Troubleshooting

### Le Producer ne trouve pas le fichier CSV

**Problème** : `Path does not exist: file:/app/data/all_firewall_logs.csv`

**Solution** : Vérifier que le volume Docker est correctement monté :
```yaml
volumes:
  - ../data:/app/data/
```

### Le Producer redémarre toujours au même batch

**Solution** : Le fichier d'état appartient probablement à `root`. Supprimez-le et recréez-le :
```bash
rm Producer/tmp/kafka_firewall_batch_state.txt
echo "-1" > Producer/tmp/kafka_firewall_batch_state.txt
```

### Kafka timeout errors

**Solution** : Les timeouts sont déjà configurés à 5-6 minutes. Si le problème persiste, vérifiez que Kafka est accessible :
```bash
docker-compose logs kafka
```

## Performance

Pour accélérer, augmentez `BATCH_SIZE` dans `Config.scala` :
```scala
val BATCH_SIZE = 1000  // ou 2000, 5000
```
