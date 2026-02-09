# 🔑 Accès Rapide - URLs et Credentials

## 🌐 Interfaces Web

### 🌬️ Apache Airflow
- **URL**: http://localhost:8081
- **Username**: `admin`
- **Password**: `admin`
- **Description**: Orchestration du pipeline, monitoring des tâches

### 📊 Grafana
- **URL**: http://localhost:3000
- **Username**: `admin`
- **Password**: `admin`
- **Description**: Dashboards de visualisation et comparaison des données

### 🔥 Spark Master
- **URL**: http://localhost:8082
- **Username**: (pas d'authentification)
- **Description**: Monitoring des jobs Spark

## 🗄️ Bases de Données

### PostgreSQL - Données Polymarket
- **Host**: `localhost`
- **Port**: `5433`
- **Database**: `polymarket_db`
- **Username**: `polymarket`
- **Password**: `polymarket123`

**Connexion via psql**:
```bash
psql -h localhost -p 5433 -U polymarket -d polymarket_db
```

**Connexion via DBeaver/pgAdmin**:
```
Host: localhost
Port: 5433
Database: polymarket_db
Username: polymarket
Password: polymarket123
```

### PostgreSQL - Airflow (Métadonnées)
- **Host**: `localhost` (non exposé)
- **Port**: `5432` (interne Docker)
- **Database**: `airflow`
- **Username**: `airflow`
- **Password**: `airflow`
- **Note**: Utilisé uniquement par Airflow pour ses métadonnées

### MongoDB Atlas
- **URI**: Configurer dans `.env`
- **Database**: `polymarket_db`
- **Collections**:
  - `polymarket` - Données brutes (raw)
  - `cleaned` - Données nettoyées
  - `monitoring` - Logs de monitoring

## 🔌 Services Backend

### Kafka Broker
- **Host**: `localhost`
- **Port**: `9092`
- **Topic**: `polymarket-events`

**Test de connexion**:
```bash
docker exec broker kafka-topics.sh --bootstrap-server localhost:9092 --list
```

## 📁 Dashboards Grafana Pré-configurés

1. **Polymarket - Cleaned Data Analysis**
   - URL: http://localhost:3000/d/polymarket-cleaned
   - Focus: Données PostgreSQL nettoyées uniquement

2. **Polymarket - Cleaned vs Raw Data Comparison**
   - URL: http://localhost:3000/d/polymarket-comparison
   - Focus: Comparaison qualité cleaned vs raw

## 🛠️ Datasources Grafana

### PostgreSQL - Polymarket Cleaned (Par défaut)
- **Name**: `PostgreSQL - Polymarket Cleaned`
- **Type**: PostgreSQL
- **Host**: `postgres-polymarket:5432`
- **Database**: `polymarket_db`
- **User**: `polymarket`
- **Status**: ✅ Configuré automatiquement

### MongoDB - Polymarket Raw (Optionnel)
- **Name**: `MongoDB - Polymarket Raw`
- **Type**: MongoDB (plugin requis)
- **URI**: Variable `MONGO_URI` de `.env`
- **Database**: `polymarket_db`
- **Status**: ⚠️ Nécessite installation du plugin

## 📊 Tables PostgreSQL Importantes

### Table Principale
```sql
-- Données nettoyées
SELECT * FROM polymarket_cleaned LIMIT 10;
```

### Vues Pré-créées
```sql
-- Statistiques par catégorie
SELECT * FROM polymarket_stats_by_category;

-- Événements actifs
SELECT * FROM polymarket_active_events;

-- Top volume
SELECT * FROM polymarket_top_volume;
```

### Tables de Monitoring
```sql
-- Exécutions du pipeline
SELECT * FROM pipeline_runs ORDER BY start_time DESC LIMIT 10;

-- Métriques Kafka
SELECT * FROM kafka_metrics ORDER BY timestamp DESC LIMIT 10;

-- Logs d'erreurs
SELECT * FROM error_logs ORDER BY timestamp DESC LIMIT 10;

-- Statistiques MongoDB
SELECT * FROM mongodb_stats ORDER BY timestamp DESC LIMIT 10;
```

## 🔐 Sécurité - Changement des Mots de Passe

### Pour Production

1. **Modifier `.env`**:
```env
# Airflow
_AIRFLOW_WWW_USER_USERNAME=votre_user
_AIRFLOW_WWW_USER_PASSWORD=motdepasse_securise

# Grafana
GRAFANA_ADMIN_USER=votre_user
GRAFANA_ADMIN_PASSWORD=motdepasse_securise

# PostgreSQL
POSTGRES_USER=votre_user
POSTGRES_PASSWORD=motdepasse_securise
```

2. **Recréer les services**:
```bash
docker-compose down -v
docker-compose up -d
```

## 📝 Variables d'Environnement (.env)

### Obligatoires
```env
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
```

### Recommandées pour Production
```env
# API
POLYMARKET_API_URL=https://gamma-api.polymarket.com/events

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=votre_user_securise
POSTGRES_PASSWORD=votre_password_securise
POSTGRES_DB=polymarket_db

# Grafana
GRAFANA_ADMIN_USER=admin_grafana
GRAFANA_ADMIN_PASSWORD=password_securise

# Airflow
_AIRFLOW_WWW_USER_USERNAME=admin_airflow
_AIRFLOW_WWW_USER_PASSWORD=password_securise

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=polymarket-events

# Général
BATCH_SIZE=100
DB2=polymarket_db
```

## 🚀 Quick Access

**Tout démarrer**:
```powershell
.\start.ps1
```

**Vérifier le statut**:
```powershell
.\check-status.ps1
```

**Accès direct**:
- Airflow: [localhost:8081](http://localhost:8081)
- Grafana: [localhost:3000](http://localhost:3000)
- Spark: [localhost:8082](http://localhost:8082)

---

**Note**: En cas de problème de connexion, vérifier que tous les containers sont démarrés avec `docker-compose ps`

