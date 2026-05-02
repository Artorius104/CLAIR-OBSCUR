# 🛡️ CLAIR OBSCUR API — Backend FastAPI

API REST temps-réel pour l'analyse de logs firewall. Fournit les endpoints de consultation, d'analytique et de chat IA au frontend **Hackathon CND**.

## 📁 Structure du projet

```
backend_fastapi/
├── app/
│   ├── main.py                  # Point d'entrée FastAPI, CORS, routeurs
│   ├── api/
│   │   └── endpoints/
│   │       ├── logs.py          # CRUD & recherche de logs firewall
│   │       ├── analytics.py     # Statistiques & timeline
│   │       └── chat.py          # Proxy vers le service d'agents IA
│   ├── core/
│   │   ├── config.py            # Configuration (Pydantic Settings)
│   │   └── database.py          # Connexion SQLAlchemy / PostgreSQL
│   ├── models/
│   │   └── log.py               # Modèles ORM (FirewallLog, StatsHourly, …)
│   ├── schemas/
│   │   └── log.py               # Schémas Pydantic (requête / réponse)
│   └── services/
│       └── analyzer.py          # Moteur de détection (attaques, bugs, sévérité)
├── Dockerfile
├── requirements.txt
└── test_api.py                  # Tests de base de l'API
```

## ⚙️ Stack technique

| Composant  | Version                      |
| ---------- | ---------------------------- |
| Python     | 3.11                         |
| FastAPI    | 0.115.0                      |
| Uvicorn    | 0.34.0                       |
| SQLAlchemy | 2.0.46                       |
| Pydantic   | 2.10.6                       |
| PostgreSQL | via `psycopg2-binary` 2.9.10 |
| HTTPX      | 0.28.1                       |

## 🚀 Démarrage rapide

### Pré-requis

- Python 3.11+
- PostgreSQL accessible (ou le service Docker Compose du projet)

### Installation locale

```bash
cd backend_fastapi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Variables d'environnement

Créer un fichier `.env` à la racine du dossier (ou définir les variables d'environnement) :

| Variable            | Défaut               | Description                |
| ------------------- | -------------------- | -------------------------- |
| `POSTGRES_USER`     | `divinandretomadam`  | Utilisateur PostgreSQL     |
| `POSTGRES_PASSWORD` | `oDAnmvidrTnmeiAa`   | Mot de passe PostgreSQL    |
| `POSTGRES_DB`       | `spark_streaming_db` | Nom de la base de données  |
| `DATABASE_HOST`     | `localhost`          | Hôte de la base de données |
| `DATABASE_PORT`     | `5432`               | Port de la base de données |
| `AGENTS_URL`        | `http://agents:8001` | URL du service d'agents IA |

### Lancer le serveur

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker build -t clair-obscur-api .
docker run -p 8000:8000 --env-file .env clair-obscur-api
```

## 📡 Endpoints de l'API

Base URL : `/api/v1`

### Logs (`/api/v1/logs`)

| Méthode | Route             | Description                                                                     |
| ------- | ----------------- | ------------------------------------------------------------------------------- |
| `GET`   | `/`               | Liste les logs (pagination, filtres `severity`, `action`, `protocol`, `search`) |
| `GET`   | `/count`          | Nombre total de logs                                                            |
| `GET`   | `/suspicious-ips` | IPs suspectes classées par nombre de blocages                                   |
| `GET`   | `/top-ports`      | Ports les plus sollicités                                                       |

### Analytics (`/api/v1/analytics`)

| Méthode | Route        | Description                                     |
| ------- | ------------ | ----------------------------------------------- |
| `GET`   | `/overview`  | Vue d'ensemble (totaux, sévérités, IPs uniques) |
| `GET`   | `/timeline`  | Nombre d'événements par heure (7 jours max)     |
| `GET`   | `/actions`   | Répartition par action (ALLOW, DENY, DROP…)     |
| `GET`   | `/protocols` | Répartition par protocole (TCP, UDP…)           |
| `GET`   | `/severity`  | Répartition par sévérité (High, Medium, Low)    |

### Chat IA (`/api/v1/chat`)

| Méthode | Route | Description                                             |
| ------- | ----- | ------------------------------------------------------- |
| `POST`  | `/`   | Envoie un message au service d'agents IA (`AGENTS_URL`) |

> La documentation interactive Swagger est disponible sur `http://localhost:8000/api/v1/openapi.json` et via Swagger UI sur `http://localhost:8000/docs`.

## 🔍 Moteur d'analyse (`LogAnalyzer`)

Le service `analyzer.py` porte la logique de classification des logs :

1. **Détection de bugs** — timestamps corrompus, IPs invalides, champs manquants
2. **Détection d'attaques** — patterns dans `reason` et `flags` (SQL injection, brute force, DDoS, XSS, malware…)
3. **Classification** — chaque log est catégorisé : `Normal`, `Attack` ou `Bug`
4. **Scoring de sévérité** — `High`, `Medium` ou `Low` selon le type et le contexte

## 🗄️ Modèles de données

| Table                     | Description                                                                |
| ------------------------- | -------------------------------------------------------------------------- |
| `firewall_logs`           | Logs bruts du firewall (source, destination, protocole, action, sévérité…) |
| `firewall_stats_hourly`   | Statistiques agrégées par heure et par firewall                            |
| `firewall_top_ports`      | Ports les plus utilisés                                                    |
| `firewall_suspicious_ips` | IPs suspectes avec niveau de risque                                        |

## 🧪 Tests

```bash
python test_api.py
```

Le script `test_api.py` vérifie la création de logs avec détection d'attaque et le endpoint de statistiques.
