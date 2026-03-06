# 📊 Dashboard Grafana - Comparaison Cleaned vs Raw Data

## 🎯 Vue d'ensemble

Le dashboard de comparaison permet de suivre en temps réel la différence entre :
- **Données brutes** (MongoDB collection `polymarket`)
- **Données nettoyées** (PostgreSQL table `polymarket_cleaned`)

## 🏗️ Architecture

```
┌─────────────┐
│  MongoDB    │  Collection 'polymarket' (raw)
│   Atlas     │  Collection 'cleaned'
└──────┬──────┘
       │
       │ Stats collectées périodiquement
       ▼
┌─────────────────────────────┐
│  PostgreSQL (monitoring)    │
│  Table: mongodb_stats       │  ◄─── Script: collect_mongo_stats.py
│  - collection_name          │
│  - document_count           │
│  - metadata (JSONB)         │
│  - timestamp                │
└──────────────┬──────────────┘
               │
               │ Requêtes SQL
               ▼
┌─────────────────────────────┐
│  Grafana Dashboard          │
│  Panels:                    │
│  ✅ Cleaned Data Count      │
│  📊 Raw Data Count          │
│  🔍 Quality Comparison      │
└─────────────────────────────┘
```

## 📈 Panels du Dashboard

### 1. Raw Data Count (MongoDB)
- **Source**: Table `mongodb_stats`
- **Requête**: 
  ```sql
  SELECT 
    COALESCE(MAX(document_count), 0) as "📊 Raw Data (MongoDB)"
  FROM mongodb_stats 
  WHERE collection_name = 'polymarket'
    AND timestamp >= NOW() - INTERVAL '1 hour';
  ```
- **Affichage**: Compteur avec dernière valeur connue (1 heure)

### 2. Cleaned Data Count (PostgreSQL)
- **Source**: Table `polymarket_cleaned`
- **Requête**: 
  ```sql
  SELECT COUNT(*) as "✅ Cleaned Data (PostgreSQL)" 
  FROM polymarket_cleaned;
  ```
- **Affichage**: Compteur temps réel

### 3. Data Quality Comparison
- **Source**: Les deux sources (UNION ALL)
- **Colonnes**:
  - Data Source
  - Total Records
  - Unique Categories
  - With Images/Icons/Series
  - Data Quality %

### 4-8. Autres Panels
- Distribution par catégories
- Statut des événements
- Top 30 événements
- Timeline d'insertion
- Complétude par catégorie

## 🚀 Utilisation

### Étape 1: Démarrer la collecte des stats

**Mode unique** (une seule collecte):
```powershell
python collect_mongo_stats.py
```

**Mode continu** (collecte toutes les 5 minutes):
```powershell
python collect_mongo_stats.py --continuous --interval 300
```

Options disponibles:
- `--continuous`: Active le mode continu
- `--interval SECONDS`: Intervalle entre collectes (défaut: 300s)

### Étape 2: Vérifier l'insertion des données

```powershell
# Connexion PostgreSQL (port 5433)
docker exec -it postgres-polymarket psql -U polymarket -d polymarket
```

```sql
-- Vérifier les dernières stats collectées
SELECT 
    timestamp,
    collection_name,
    document_count,
    metadata->>'size_bytes' as size_bytes
FROM mongodb_stats
ORDER BY timestamp DESC
LIMIT 10;

-- Statistiques par collection
SELECT 
    collection_name,
    COUNT(*) as nb_entries,
    MAX(document_count) as max_documents,
    MIN(timestamp) as first_entry,
    MAX(timestamp) as last_entry
FROM mongodb_stats
GROUP BY collection_name;
```

### Étape 3: Accéder au Dashboard

1. Ouvrir Grafana: http://localhost:3000
2. Login: `admin` / `admin`
3. Aller dans **Dashboards** → **Polymarket - Cleaned vs Raw Data Comparison**
4. Refresh: Automatique toutes les 1 minute

## 🔧 Configuration

### Variables d'environnement (.env)

```env
# MongoDB
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGO_DB=polymarket

# PostgreSQL (monitoring)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=polymarket
POSTGRES_USER=polymarket
POSTGRES_PASSWORD=polymarket123
```

### Structure de la table mongodb_stats

```sql
CREATE TABLE mongodb_stats (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    collection_name VARCHAR(100),
    document_count BIGINT,              -- Nombre de documents
    insert_count INTEGER,                -- Nombre d'insertions (optionnel)
    insert_duration_ms INTEGER,          -- Durée d'insertion (optionnel)
    metadata JSONB                       -- Métadonnées supplémentaires
);

-- Index pour les requêtes Grafana
CREATE INDEX IF NOT EXISTS idx_mongodb_stats_collection_time 
    ON mongodb_stats(collection_name, timestamp DESC);
```

### Métadonnées JSONB stockées

```json
{
  "size_bytes": 12345678,
  "avg_doc_size": 1024,
  "storage_size": 15000000,
  "total_indexes": 3,
  "index_sizes": {
    "_id_": 524288,
    "condition_id_1": 262144
  }
}
```

## 📊 Exemple d'utilisation avec Airflow

Ajoutez une tâche dans votre DAG pour collecter les stats:

```python
from airflow.operators.python import PythonOperator
import subprocess

def collect_mongodb_statistics():
    """Collecte les statistiques MongoDB pour Grafana"""
    result = subprocess.run(
        ['python', '/opt/airflow/collect_mongo_stats.py'],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Erreur collecte stats: {result.stderr}")
    print(result.stdout)

# Dans le DAG
collect_stats = PythonOperator(
    task_id='collect_mongodb_stats',
    python_callable=collect_mongodb_statistics
)

# Workflow
check_kafka >> fetch >> consume >> clean >> collect_stats >> load_postgres >> spark
```

## 🐛 Dépannage

### Problème: "No Data" dans le panel Raw Data

**Cause**: Aucune statistique collectée dans `mongodb_stats`

**Solution**:
```powershell
# 1. Vérifier les connexions
python collect_mongo_stats.py

# 2. Vérifier la table
docker exec -it postgres-polymarket psql -U polymarket -d polymarket -c "SELECT COUNT(*) FROM mongodb_stats;"

# 3. Vérifier les logs
docker-compose logs postgres-polymarket
```

### Problème: Anciennes données affichées

**Cause**: Requête Grafana filtre sur la dernière heure

**Solution**: Modifier l'intervalle dans le dashboard JSON:
```sql
-- Changer de:
AND timestamp >= NOW() - INTERVAL '1 hour'

-- À:
AND timestamp >= NOW() - INTERVAL '24 hours'
```

### Problème: Script Python plante

**Erreur commune**: `ModuleNotFoundError: No module named 'pymongo'`

**Solution**:
```powershell
# Installer les dépendances
pip install pymongo psycopg2-binary python-dotenv

# Ou via requirements.txt
pip install -r requirements.txt
```

## 📌 Bonnes Pratiques

### 1. Collecte périodique
- Utilisez un cron job ou Airflow pour collecter automatiquement
- Intervalle recommandé: **5-10 minutes**
- Évitez les collectes trop fréquentes (< 1 minute)

### 2. Nettoyage des données anciennes
```sql
-- Supprimer les stats de plus de 30 jours
DELETE FROM mongodb_stats 
WHERE timestamp < NOW() - INTERVAL '30 days';

-- Ou créer un script de maintenance
CREATE OR REPLACE FUNCTION cleanup_old_stats() 
RETURNS void AS $$
BEGIN
    DELETE FROM mongodb_stats 
    WHERE timestamp < NOW() - INTERVAL '30 days';
    
    RAISE NOTICE 'Stats anciennes supprimées';
END;
$$ LANGUAGE plpgsql;

-- Appel manuel ou via cron
SELECT cleanup_old_stats();
```

### 3. Monitoring de la collecte
```sql
-- Vue pour suivre la santé de la collecte
CREATE OR REPLACE VIEW stats_collection_health AS
SELECT 
    collection_name,
    MAX(timestamp) as last_update,
    EXTRACT(EPOCH FROM (NOW() - MAX(timestamp))) / 60 as minutes_since_last_update,
    COUNT(*) as total_entries_today
FROM mongodb_stats
WHERE timestamp >= CURRENT_DATE
GROUP BY collection_name;

-- Vérifier
SELECT * FROM stats_collection_health;
```

## 🎯 Résultat Attendu

Après avoir lancé `collect_mongo_stats.py` et attendu quelques minutes:

```
Dashboard Grafana affiche:
┌─────────────────────────────────────┐
│ ✅ Cleaned Data Count: 1,250       │
│ 📊 Raw Data Count: 1,500           │
│                                     │
│ Data Quality Comparison:            │
│ ┌─────────────┬──────────┬────────┐│
│ │ Source      │ Records  │ Qual % ││
│ ├─────────────┼──────────┼────────┤│
│ │ Cleaned     │ 1,250    │ 95.2% ││
│ │ Raw (Mongo) │ 1,500    │ -     ││
│ └─────────────┴──────────┴────────┘│
└─────────────────────────────────────┘
```

## 📚 Ressources

- [Dashboard JSON](./grafana/dashboards/polymarket-comparison-dashboard.json)
- [Script de collecte](./collect_mongo_stats.py)
- [Table monitoring](./postgres-init/01-init.sql)
- [Grafana Documentation](https://grafana.com/docs/)

---

**Auteur**: Système de monitoring Polymarket  
**Version**: 2.0  
**Date**: Février 2026
