# 🎯 Guide de Démarrage Complet - Pipeline Polymarket

## Architecture Complète

```
┌─────────────────────────────────────────────────────────────────────┐
│                    POLYMARKET PIPELINE v2.0                         │
│              Spark Streaming pour le nettoyage temps réel          │
└─────────────────────────────────────────────────────────────────────┘

                    📡 API Polymarket
                           ↓
                    🚀 Producer.py
                           ↓
              🔥 Kafka (polymarket-events)
                      ↙        ↘
                     ↙          ↘
         [RAW PATH]              [CLEANED PATH]
              ↓                       ↓
    👨‍💻 Consumer.py          ⚡ Spark Consumer
              ↓                  (Filtrage + Nettoyage)
    🗄️ MongoDB                        ↓
    polymarket.polymarket    🗄️ PostgreSQL
    [RAW DATA]              polymarket_cleaned
         ↓                    [CLEANED DATA]
         ↓                         ↓
         └─────────→ 📊 Grafana ←──┘
                  [COMPARISON]
```

### 🔑 Points Clés de l'Architecture

- **2 chemins parallèles** depuis Kafka
- **MongoDB**: Stockage des données brutes (PRE-Spark)
- **Spark Streaming**: Nettoyage et transformation en temps réel
- **PostgreSQL**: Stockage des données nettoyées (POST-Spark)
- **Grafana**: Comparaison RAW vs CLEANED

## 🚀 Démarrage Rapide

### 1. Configuration Initiale

```powershell
# Cloner ou naviguer vers le dossier du projet
cd "C:\Users\Bradlley GANGNOU\OneDrive\Desktop\ArchBigDatA"

# Créer le fichier .env avec vos credentials MongoDB
# Éditer .env et remplacer MONGO_URI par votre vraie URI MongoDB Atlas
```

### 2. Démarrer tous les services

```powershell
# Démarrer l'infrastructure complète
docker-compose up -d

# Vérifier que tous les containers sont démarrés
docker-compose ps
```

### 3. Vérifier les Services

| Service | URL | Credentials |
|---------|-----|-------------|
| 🌬️ Airflow | http://localhost:8081 | admin / admin |
| 📊 Grafana | http://localhost:3000 | admin / admin |
| 🔥 Spark Master | http://localhost:8082 | - |
| 🗄️ PostgreSQL | localhost:5433 | polymarket / polymarket123 |
| 🧩 Kafka | localhost:9092 | - |

### 4. Lancer le Pipeline

#### Option A: Via Airflow (Recommandé)

1. Ouvrir http://localhost:8081
2. Se connecter (admin/admin)
3. Activer le DAG `polymarket_data_pipeline`
4. Cliquer sur "Trigger DAG" pour le lancer manuellement

Le pipeline s'exécutera automatiquement toutes les heures.

#### Option B: Scripts manuels

```powershell
# 1. Récupérer les données de l'API et envoyer à Kafka
python producer.py

# 2. Consommer Kafka et insérer dans MongoDB (RAW)
python kafka/actors/consumer.py

# 3. Traiter avec Spark et insérer dans PostgreSQL (CLEANED)
docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.1 \
  /opt/spark-apps/spark_consumer.py
```

**⚠️ Note**: Les scripts `CleaningPolymarket.py` et `mongo_to_postgres.py` sont **obsolètes** et remplacés par le Spark Consumer.

### 5. Visualiser avec Grafana

1. Ouvrir http://localhost:3000
2. Se connecter (admin/admin)
3. Aller dans **Dashboards**
4. Sélectionner:
   - **Polymarket - Cleaned Data Analysis** (données PostgreSQL)
   - **Polymarket - Cleaned vs Raw Data Comparison** (comparaison)

## 📦 Structure du Projet

```
ArchBigDatA/
├── 📄 Docker-compose.yaml           # Orchestration des services
├── 📄 .env                           # Variables d'environnement
├── 📄 requirements.txt               # Dépendances Python
│
├── 📁 dags/                          # DAGs Airflow
│   └── polymarket_pipeline_dag.py   # Pipeline principal
│
├── 📁 grafana/                       # Configuration Grafana
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── datasources.yml      # PostgreSQL & MongoDB
│   │   └── dashboards/
│   │       └── dashboards.yml
│   └── dashboards/
│       ├── polymarket-cleaned-dashboard.json
│       └── polymarket-comparison-dashboard.json
│
├── 📁 postgres-init/                 # Scripts SQL PostgreSQL
│   ├── 01-init.sql                  # Tables de monitoring
│   └── 02-polymarket-schema.sql     # Schéma Polymarket
│
├── 📁 spark-apps/                    # Applications Spark
│   └── spark_consumer.py            # ⚡ Kafka → Cleaning → PostgreSQL
│
├── 📁 kafka/actors/                  # Scripts Kafka
│   ├── producer.py                  # Producteur Kafka
│   └── consumer.py                  # Consommateur Kafka → MongoDB
│
├── 🐍 CleaningPolymarket.py         # ⚠️ OBSOLÈTE (remplacé par Spark)
├── 🐍 mongo_to_postgres.py          # ⚠️ OBSOLÈTE (remplacé par Spark)
├── 🐍 collect_mongo_stats.py        # Collecte stats MongoDB
├── 🐍 monitoring.py                 # Service de monitoring
│
└── 📚 Documentation/
    ├── README.md
    ├── POSTGRES_README.md
    └── GRAFANA_README.md
```

## 🔄 Flux de Données Détaillé

### Étape 1: Collecte (API → Kafka)
- **Script**: `kafka/actors/producer.py` ou DAG task `fetch_api_send_kafka`
- **Source**: https://gamma-api.polymarket.com/events
- **Destination**: Topic Kafka `polymarket-events`
- **Fréquence**: Toutes les heures (via Airflow) ou toutes les 5 min (via `kafka_producer_consumer` DAG)

### Étape 2A: Ingestion RAW (Kafka → MongoDB)
- **Script**: `kafka/actors/consumer.py` ou DAG task `consume_kafka_insert_mongo`
- **Source**: Topic Kafka `polymarket-events`
- **Destination**: MongoDB `Polymarket.polymarket`
- **Type**: Données brutes, non filtrées
- **Usage**: Comparaison dans Grafana (données RAW)
- **Déduplication**: Index unique sur le champ `id`

### Étape 2B: Traitement CLEANED (Kafka → Spark → PostgreSQL)
- **Script**: `spark-apps/spark_consumer.py` ou DAG task `spark_processing`
- **Source**: Topic Kafka `polymarket-events` (streaming)
- **Destination**: PostgreSQL `polymarket.polymarket_cleaned`
- **Traitement Spark**:
  - ✅ **Filtrage**: image, icon, seriesSlug, resolutionSource non vides
  - ✅ **Suppression**: 28 champs inutiles (liquidity, archived, new, etc.)
  - ✅ **Transformation**: Renommage colonnes (id→mongo_id, conditionId→condition_id)
  - ✅ **Conversion dates**: Timestamps vers format PostgreSQL
  - ✅ **JSON preservation**: outcomes et outcomePrices en JSONB
- **Mode**: Streaming temps réel (pas de batch)
- **Avantages**:
  - 🔍 Requêtes SQL performantes
  - 📊 Jointures et agrégations avancées
  - 🎯 Indexation optimisée (9 index dont unique sur mongo_id)
  - ⚡ Traitement distribué scalable

### Étape 3: Visualisation (MongoDB + PostgreSQL → Grafana)
- **Datasource RAW**: Table `mongodb_stats` (stats collectées depuis MongoDB)
- **Datasource CLEANED**: Table PostgreSQL `polymarket_cleaned`
- **Dashboards**: 
  - Cleaned Data Analysis (métriques PostgreSQL)
  - Comparison RAW vs CLEANED (impact du filtrage Spark)
- **Métriques**: Count, qualité, complétude, distribution par catégorie
- **Refresh**: 30s - 1m

### 📊 Comparaison Architecture v1 vs v2

| Aspect | v1 (Ancien) | v2 (Actuel) |
|--------|-------------|-------------|
| **Nettoyage** | Python batch (CleaningPolymarket.py) | Spark Streaming temps réel |
| **Transfert** | Python batch (mongo_to_postgres.py) | Spark JDBC direct |
| **MongoDB cleaned** | Existe (intermédiaire) | ⚠️ N'existe plus |
| **Latence** | Batch horaire | Streaming continu |
| **Scalabilité** | Limitée | Distribuée (Spark) |
| **Étapes** | 4 scripts séquentiels | 2 chemins parallèles |

## 🎛️ Commandes Utiles

### Docker

```powershell
# Démarrer tous les services
docker-compose up -d

# Démarrer un service spécifique
docker-compose up -d grafana

# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v

# Voir les logs d'un service
docker-compose logs -f grafana

# Redémarrer un service
docker-compose restart airflow-webserver

# Voir l'état des services
docker-compose ps
```

### PostgreSQL

```powershell
# Se connecter à PostgreSQL
docker exec -it postgres-polymarket psql -U polymarket -d polymarket

# Ou depuis Windows (si psql installé)
psql -h localhost -p 5433 -U polymarket -d polymarket

# Requêtes utiles
SELECT COUNT(*) FROM polymarket_cleaned;
SELECT * FROM polymarket_active_events LIMIT 10;
SELECT * FROM polymarket_stats_by_category;
```

### MongoDB

```powershell
# Vérifier le nombre de documents RAW
# Via Python
python -c "from pymongo import MongoClient; import os; from dotenv import load_dotenv; load_dotenv(); client = MongoClient(os.getenv('MONGO_URI')); print('Raw:', client['Polymarket']['polymarket'].count_documents({}))"

# Note: MongoDB 'cleaned' collection n'existe plus (remplacée par Spark → PostgreSQL direct)
```

### Kafka

```powershell
# Lister les topics (depuis le container)
docker exec broker kafka-topics.sh --bootstrap-server localhost:9092 --list

# Voir les messages d'un topic
docker exec broker kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic polymarket-events --from-beginning --max-messages 10
```

## 📊 Monitoring

### 1. Pipeline Airflow

- **URL**: http://localhost:8081
- **DAG**: `polymarket_data_pipeline`
- **Monitoring**: Graph View, Task Duration, Logs

### 2. Grafana Dashboards

- **URL**: http://localhost:3000
- **Dashboards**: Cleaned Analysis, Comparison
- **Metrics**: Count, Quality, Distribution

### 3. PostgreSQL Monitoring

```sql
-- Taille de la base
SELECT pg_size_pretty(pg_database_size('polymarket'));

-- Activité récente
SELECT * FROM pipeline_runs ORDER BY start_time DESC LIMIT 10;

-- Métriques Kafka
SELECT * FROM kafka_metrics ORDER BY timestamp DESC LIMIT 10;

-- Logs d'erreurs
SELECT * FROM error_logs ORDER BY timestamp DESC LIMIT 10;
```

## 🐛 Dépannage

### Problème: Airflow ne démarre pas

```powershell
# Vérifier les logs
docker-compose logs airflow-init
docker-compose logs airflow-webserver

# Réinitialiser Airflow
docker-compose down
docker volume rm archbigdata_postgres-db-volume
docker-compose up -d
```

### Problème: Grafana ne trouve pas PostgreSQL

```powershell
# Vérifier que PostgreSQL est démarré
docker-compose ps postgres-polymarket

# Tester la connexion
docker exec grafana ping -c 3 postgres-polymarket

# Vérifier les datasources
docker exec grafana cat /etc/grafana/provisioning/datasources/datasources.yml
```

### Problème: Données non transférées vers PostgreSQL

```powershell
# 1. Vérifier que Kafka reçoit les messages
docker exec broker kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic polymarket-events --max-messages 5

# 2. Vérifier les logs Spark
docker-compose logs spark-master
docker-compose logs spark-worker-1

# 3. Vérifier PostgreSQL
docker exec postgres-polymarket psql -U polymarket -d polymarket -c "SELECT COUNT(*) FROM polymarket_cleaned;"

# 4. Relancer le Spark Consumer manuellement
docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.1 \
  /opt/spark-apps/spark_consumer.py
```

### Problème: Kafka ne reçoit pas de messages

```powershell
# Vérifier que Kafka est prêt
docker-compose logs broker

# Tester avec le producteur
python producer.py

# Vérifier les messages
docker exec broker kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic polymarket-events --max-messages 5
```

## 🔐 Sécurité

### Credentials par défaut (à changer en production)

```env
# Airflow
AIRFLOW_USER=admin
AIRFLOW_PASSWORD=admin

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# PostgreSQL
POSTGRES_USER=polymarket
POSTGRES_PASSWORD=polymarket123

# MongoDB
MONGO_URI=mongodb+srv://votre_vrai_uri
```

