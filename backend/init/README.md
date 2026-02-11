# PostgreSQL Database Initialization

Ce dossier contient les scripts d'initialisation de la base de données PostgreSQL pour le projet d'analyse des logs firewall.

## Tables

### `firewall_logs`
Table principale contenant tous les logs firewall reçus de Kafka.

**Colonnes :**
- `id` : Identifiant unique auto-incrémenté
- `timestamp` : Horodatage de l'événement
- `firewall_id` : Identifiant du firewall
- `src_ip`, `dst_ip` : Adresses IP source et destination
- `src_port`, `dst_port` : Ports source et destination
- `protocol` : Protocole (TCP/UDP/ICMP)
- `action` : Action (ALLOW/DENY)
- `bytes` : Taille des données transférées
- `duration_ms` : Durée de la session
- `rule_id` : ID de la règle appliquée
- `session_id` : ID de session unique
- `user_name` : Utilisateur (optionnel)
- `reason` : Raison de l'action (optionnel)
- `status` : Statut de la connexion
- `flags` : Flags TCP/IP (optionnel)
- `created_at` : Date d'insertion dans la base

### `firewall_stats_hourly`
Statistiques agrégées par heure pour analyse temporelle.

### `firewall_top_ports`
Top des ports les plus utilisés (source et destination).

### `firewall_suspicious_ips`
Liste des IPs suspectes avec niveau de risque.

## Vues

### `firewall_global_stats`
Statistiques globales sur l'ensemble des logs.

### `firewall_stats_by_firewall`
Statistiques par firewall.

### `firewall_stats_by_protocol`
Statistiques par protocole réseau.

## Utilisation

### Commandes PostgreSQL de base

| Commande      | Description                                        |
| ------------- | -------------------------------------------------- |
| `\l`          | Lister toutes les bases de données                 |
| `\c <dbname>` | Se connecter à une autre base de données           |
| `\dt`         | Lister toutes les tables dans la base courante     |
| `\d <table>`  | Afficher la structure d'une table                  |
| `\dv`         | Lister toutes les vues                             |
| `\q`          | Quitter le client `psql`                           |
| `\du`         | Lister les rôles (utilisateurs PostgreSQL)         |

### Connexion

```bash
# Se connecter à PostgreSQL
sudo -u postgres psql

# Se connecter à la base de données
psql -U <user> -h localhost -d spark_streaming_db
```

### Initialisation manuelle

```bash
# Exécuter le script d'initialisation
psql -U postgres -d spark_streaming_db -f init.sql
```

### Avec Docker Compose

Le script `init.sql` est automatiquement exécuté au premier démarrage du conteneur PostgreSQL grâce au volume :

```yaml
volumes:
  - ./init:/docker-entrypoint-initdb.d
```
