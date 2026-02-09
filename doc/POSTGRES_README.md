# 🗄️ PostgreSQL Integration - Stockage des données nettoyées Polymarket

## Vue d'ensemble

Cette intégration ajoute un container PostgreSQL dédié au stockage des données Polymarket nettoyées. Après le nettoyage dans MongoDB (collection `cleaned`), les données sont automatiquement chargées dans PostgreSQL pour des analyses SQL avancées et une meilleure structuration.

## Architecture

```
API Polymarket → Kafka → MongoDB (raw) → Nettoyage → MongoDB (cleaned) → PostgreSQL
                                                                              ↓
                                                                         Spark Processing
```

## Composants ajoutés

### 1. Container PostgreSQL (`postgres-polymarket`)

- **Image**: `postgres:13`
- **Port**: `5433` (pour éviter conflit avec postgres-airflow)
- **Credentials par défaut**:
  - User: `polymarket`
  - Password: `polymarket123`
  - Database: `polymarket_db`

### 2. Table principale: `polymarket_cleaned`

Structure de la table avec tous les champs nettoyés:

```sql
- mongo_id (VARCHAR) - ID unique de MongoDB
- condition_id (VARCHAR) - ID de condition Polymarket
- question_id (VARCHAR) - ID de la question
- title (TEXT) - Titre de l'événement
- description (TEXT) - Description
- category (VARCHAR) - Catégorie
- series_slug (VARCHAR) - Slug de la série
- image, icon (TEXT) - URLs des images
- outcomes (JSONB) - Résultats possibles
- outcome_prices (JSONB) - Prix actuels
- volume, volume_num (NUMERIC) - Volumes
- start_date, end_date (TIMESTAMP) - Dates
- ... et plus
```

### 3. Vues SQL pré-créées

#### `polymarket_stats_by_category`
Statistiques agrégées par catégorie:
```sql
SELECT * FROM polymarket_stats_by_category;
```

#### `polymarket_active_events`
Événements en cours (end_date > NOW()):
```sql
SELECT * FROM polymarket_active_events;
```

#### `polymarket_top_volume`
Top 100 des événements par volume:
```sql
SELECT * FROM polymarket_top_volume;
```

### 4. Script Python: `mongo_to_postgres.py`

Script standalone pour transférer manuellement les données:

```bash
python mongo_to_postgres.py
```

### 5. Task Airflow: `load_to_postgres`

Intégrée dans le DAG `polymarket_data_pipeline`, cette tâche:
1. Se connecte à MongoDB (collection `cleaned`)
2. Transforme les documents au format PostgreSQL
3. Vide la table PostgreSQL (évite doublons)
4. Insère les données par batch
5. Vérifie l'intégrité des données

## Configuration

### Variables d'environnement (.env)

```bash
# PostgreSQL pour données Polymarket
POSTGRES_HOST=localhost          # Utilisez 'postgres-polymarket' dans Docker
POSTGRES_PORT=5433               # Port exposé sur l'hôte
POSTGRES_USER=polymarket
POSTGRES_PASSWORD=polymarket123
POSTGRES_DB=polymarket_db
```

### Docker Compose

Le container PostgreSQL démarre automatiquement avec:

```bash
docker-compose up -d postgres-polymarket
```

## Utilisation

### 1. Démarrage de l'infrastructure

```bash
# Démarrer tous les containers
docker-compose up -d

# Vérifier que PostgreSQL est prêt
docker-compose ps postgres-polymarket
docker-compose logs postgres-polymarket
```

### 2. Connexion à PostgreSQL

#### Depuis votre machine (Windows):

```bash
# Via psql
psql -h localhost -p 5433 -U polymarket -d polymarket_db

# Via pgAdmin ou DBeaver
Host: localhost
Port: 5433
User: polymarket
Password: polymarket123
Database: polymarket_db
```

#### Depuis un container Docker:

```bash
docker exec -it postgres-polymarket psql -U polymarket -d polymarket_db
```

### 3. Exécution manuelle du transfert

```bash
# Assurer que les variables d'environnement sont configurées
python mongo_to_postgres.py
```

### 4. Via Airflow DAG

Le DAG `polymarket_data_pipeline` exécute automatiquement:

1. ✅ `check_kafka_ready` - Vérifier Kafka
2. ✅ `fetch_api_send_kafka` - API → Kafka
3. ✅ `consume_kafka_insert_mongo` - Kafka → MongoDB (raw)
4. ✅ `clean_polymarket_data` - Nettoyage → MongoDB (cleaned)
5. **🆕 `load_to_postgres`** - MongoDB (cleaned) → PostgreSQL
6. ✅ `spark_processing` - Traitement Spark

## Requêtes SQL utiles

### Compter les documents

```sql
SELECT COUNT(*) FROM polymarket_cleaned;
```

### Top 10 par volume

```sql
SELECT title, category, volume_num, end_date
FROM polymarket_cleaned
ORDER BY volume_num DESC
LIMIT 10;
```

### Événements par catégorie

```sql
SELECT category, COUNT(*) as total,
       AVG(volume_num) as avg_volume
FROM polymarket_cleaned
GROUP BY category
ORDER BY total DESC;
```

### Événements se terminant dans les 24h

```sql
SELECT title, category, end_date, volume
FROM polymarket_cleaned
WHERE end_date BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
ORDER BY end_date ASC;
```

### Recherche dans les outcomes (JSONB)

```sql
SELECT title, outcomes
FROM polymarket_cleaned
WHERE outcomes::text ILIKE '%Trump%'
LIMIT 10;
```

## Monitoring et Logs

### Logs du container PostgreSQL

```bash
docker-compose logs -f postgres-polymarket
```

### Logs de la task Airflow

1. Accéder à Airflow UI: http://localhost:8081
2. Aller dans le DAG `polymarket_data_pipeline`
3. Cliquer sur la task `load_to_postgres`
4. Voir les logs dans l'onglet "Logs"

### Statistiques de la base

```sql
-- Taille de la table
SELECT pg_size_pretty(pg_total_relation_size('polymarket_cleaned'));

-- Nombre d'index
SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'polymarket_cleaned';

-- Statistiques de la table
SELECT * FROM pg_stat_user_tables WHERE relname = 'polymarket_cleaned';
```

## Dépannage

### Le container ne démarre pas

```bash
# Vérifier les logs
docker-compose logs postgres-polymarket

# Recréer le container
docker-compose down postgres-polymarket
docker-compose up -d postgres-polymarket
```

### Erreur de connexion

```bash
# Vérifier que le container est healthy
docker-compose ps

# Tester la connexion depuis le container
docker exec -it postgres-polymarket pg_isready -U polymarket
```

### La table n'existe pas

```bash
# Vérifier que les scripts d'initialisation ont été exécutés
docker exec -it postgres-polymarket psql -U polymarket -d polymarket_db -c "\dt"

# Si nécessaire, réexécuter l'initialisation
docker exec -it postgres-polymarket psql -U polymarket -d polymarket_db -f /docker-entrypoint-initdb.d/02-polymarket-schema.sql
```

### Les données ne sont pas transférées

1. Vérifier que la collection `cleaned` dans MongoDB contient des données:
   ```python
   from pymongo import MongoClient
   client = MongoClient(MONGO_URI)
   print(client['polymarket_db']['cleaned'].count_documents({}))
   ```

2. Exécuter manuellement le script de transfert:
   ```bash
   python mongo_to_postgres.py
   ```

3. Vérifier les logs du DAG Airflow

## Maintenance

### Backup de la base

```bash
# Backup complet
docker exec postgres-polymarket pg_dump -U polymarket polymarket_db > backup_$(date +%Y%m%d).sql

# Backup de la table uniquement
docker exec postgres-polymarket pg_dump -U polymarket -t polymarket_cleaned polymarket_db > backup_table_$(date +%Y%m%d).sql
```

### Restauration

```bash
# Restaurer depuis un backup
cat backup_20260209.sql | docker exec -i postgres-polymarket psql -U polymarket polymarket_db
```

### Nettoyage des anciennes données

```sql
-- Supprimer les événements terminés depuis plus de 30 jours
DELETE FROM polymarket_cleaned
WHERE end_date < NOW() - INTERVAL '30 days';

-- Vacuum pour récupérer l'espace
VACUUM FULL polymarket_cleaned;
```

## Améliorations futures

- [ ] Partitionnement de la table par date
- [ ] Réplication PostgreSQL pour haute disponibilité
- [ ] Intégration avec TimescaleDB pour séries temporelles
- [ ] Dashboard Grafana connecté à PostgreSQL
- [ ] API REST pour interroger PostgreSQL
- [ ] Synchronisation incrémentale (au lieu de TRUNCATE)

## Support

Pour des questions ou problèmes:
1. Vérifier les logs: `docker-compose logs -f postgres-polymarket`
2. Consulter la documentation PostgreSQL: https://www.postgresql.org/docs/
3. Vérifier les variables d'environnement dans `.env`

