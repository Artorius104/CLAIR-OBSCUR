# Firewall Logs - Dashboard Streamlit

## Description

Dashboard interactif pour visualiser et analyser les logs firewall en temps réel. Construit avec Streamlit et connecté à PostgreSQL.

## Fonctionnalités

### 🏠 Page Principale (FirewallDashboard.py)
- **KPIs Globaux** : Total des logs, connexions autorisées/bloquées, IPs uniques, volume de données
- **Graphiques** : Distribution des actions, protocoles, statistiques par firewall
- **Top IPs** : Sources les plus actives et les plus bloquées
- **Logs Récents** : Tableau filtrable des derniers événements

### 📈 Analyse Temporelle
- **Évolution du Trafic** : Graphiques temporels des événements
- **Volume de Données** : Analyse du trafic en GB dans le temps
- **Répartition par Protocole** : Timeline et distribution
- **Heatmap d'Activité** : Visualisation par jour et heure
- **Statistiques Horaires** : Tableau détaillé des métriques agrégées

### 🔍 Recherche de Logs
- **Recherche Avancée** : Filtres multiples (IP, port, protocole, action, période)
- **Résultats Détaillés** : Tableau avec mise en forme conditionnelle
- **Graphiques Rapides** : Visualisation instantanée des résultats
- **Export** : Téléchargement en CSV (complet ou DENY uniquement)

### ⚠️ Alertes Sécurité
- **IPs Suspectes** : Top des IPs les plus bloquées
- **Niveaux de Risque** : Classification automatique (LOW, MEDIUM, HIGH, CRITICAL)
- **Analyse des Ports** : Ports ciblés par les attaques
- **Blocklist** : Export de liste d'IPs à bloquer
- **Recommandations** : Conseils de sécurité

## Installation

### Prérequis

- Python 3.8+
- PostgreSQL avec les données de logs
- Variables d'environnement configurées

### Dépendances

```bash
pip install -r requirements.txt
```

**requirements.txt :**
```
streamlit
plotly
pandas
sqlalchemy
psycopg2-binary
```

## Configuration

### Variables d'Environnement

```bash
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_NAME=spark_streaming_db
export DATABASE_USER=your_user
export DATABASE_PASSWORD=your_password
```

### Avec Docker Compose

Les variables sont automatiquement configurées via docker-compose.yml :

```yaml
environment:
  DATABASE_HOST: postgres
  DATABASE_PORT: 5432
  DATABASE_USER: ${POSTGRES_USER}
  DATABASE_NAME: ${POSTGRES_DB}
  DATABASE_PASSWORD: ${POSTGRES_PASSWORD}
```

## Utilisation

### Lancement Local

```bash
cd src
streamlit run FirewallDashboard.py
```

L'application sera accessible sur `http://localhost:8501`

### Avec Docker

```bash
docker-compose up streamlit
```

L'application sera accessible sur `http://localhost:8501`

## Structure du Projet

```
DataVisualisation/
├── src/
│   ├── FirewallDashboard.py          # Page principale
│   ├── database/
│   │   ├── __init__.py
│   │   └── getDataFromDatabase.py    # Connexion PostgreSQL
│   └── pages/
│       ├── 1_📈_Analyse_Temporelle.py
│       ├── 2_🔍_Recherche_Logs.py
│       └── 3_⚠️_Alertes_Sécurité.py
├── Dockerfile
├── requirements.txt
└── README.md
```

## Fonctionnalités Avancées

### Rafraîchissement Automatique

Dans la sidebar, activez "Rafraîchissement automatique" et configurez l'intervalle.

### Filtres Interactifs

Chaque page propose des filtres pour affiner les visualisations :
- Période d'analyse
- Firewall ID
- Protocole
- Action (ALLOW/DENY)
- Niveau de risque

### Export de Données

Téléchargez les données aux formats :
- **CSV** : Pour analyse dans Excel, Python, etc.
- **TXT** : Blocklist d'IPs pour configuration firewall

### Mise en Forme Conditionnelle

Les tableaux utilisent des couleurs pour identifier rapidement :
- 🔴 **Rouge** : Connexions DENY
- 🟢 **Vert** : Connexions ALLOW
- 🟠 **Orange** : Risque élevé

## Analyse des Données

### Métriques Disponibles

- Nombre total de logs
- Connexions autorisées vs bloquées
- IPs sources/destinations uniques
- Volume de données transférées
- Durée moyenne des sessions
- Distribution par protocole
- Statistiques par firewall

### Vues PostgreSQL Utilisées

- `firewall_global_stats` : Statistiques globales
- `firewall_stats_by_firewall` : Métriques par firewall
- `firewall_stats_by_protocol` : Métriques par protocole

### Tables PostgreSQL

- `firewall_logs` : Logs bruts
- `firewall_stats_hourly` : Agrégations horaires
- `firewall_top_ports` : Ports populaires
- `firewall_suspicious_ips` : IPs suspectes

## Personnalisation

### Modifier les Couleurs

Dans chaque fichier Python, vous pouvez modifier les palettes de couleurs :

```python
risk_colors = {
    'CRITICAL': '#d32f2f',
    'HIGH': '#f57c00',
    'MEDIUM': '#fbc02d',
    'LOW': '#388e3c'
}
```

### Ajouter des Pages

Créez un nouveau fichier dans `src/pages/` avec le format :
```
4_🆕_Ma_Nouvelle_Page.py
```

Streamlit détectera automatiquement la nouvelle page.

### Modifier les Requêtes

Éditez `database/getDataFromDatabase.py` pour ajouter de nouvelles fonctions de requête.

## Troubleshooting

### Erreur de Connexion PostgreSQL

**Problème** : `Connection refused`

**Solution** :
- Vérifiez que PostgreSQL est démarré
- Vérifiez les variables d'environnement
- Testez la connexion : `psql -U user -h host -d dbname`

### Aucune Donnée Affichée

**Problème** : Dashboard vide

**Solution** :
- Vérifiez que le Consumer insère des données
- Vérifiez les tables PostgreSQL : `SELECT COUNT(*) FROM firewall_logs;`
- Consultez les logs du Consumer

### Erreur de Cache Streamlit

**Problème** : Données obsolètes

**Solution** :
- Cliquez sur "Rafraîchir" dans la sidebar
- Ou appuyez sur `C` dans l'interface Streamlit
- Ou redémarrez l'application

## Performance

### Optimisations

- **Cache Streamlit** : TTL de 60 secondes pour les requêtes fréquentes
- **Index PostgreSQL** : Sur timestamp, firewall_id, action, src_ip, dst_ip
- **Limites de Requêtes** : Max 10,000 résultats par défaut

### Recommandations

- Pour de grandes quantités de données, augmentez les ressources Docker
- Utilisez les filtres de période pour limiter le volume de données
- Archivez régulièrement les anciennes données

## Sécurité

- Les mots de passe sont stockés dans des variables d'environnement
- Aucune donnée sensible dans le code source
- Connexions PostgreSQL sécurisées via SQLAlchemy

## Intégration

Le dashboard s'intègre avec :
- **Producer** : Envoie les logs à Kafka
- **Consumer** : Lit Kafka et écrit dans PostgreSQL
- **PostgreSQL** : Stockage des données
- **Streamlit** : Visualisation (ce dashboard)

## Support

Pour toute question ou problème :
1. Vérifiez les logs Docker : `docker-compose logs streamlit`
2. Consultez la documentation Streamlit : https://docs.streamlit.io
3. Vérifiez la connexion PostgreSQL

## Licence

Projet Hackathon DIRISI
