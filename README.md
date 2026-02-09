# 📊 Polymarket Data Pipeline - Orchestration Airflow

> Pipeline de données orchestré par **Apache Airflow** pour collecter, traiter et monitorer les événements Polymarket.

## 🏗️ Architecture avec Orchestration

```
                    ┌─────────────┐
                    │   Airflow   │ (Orchestrateur)
                    │  Scheduler  │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
      ┌─────────┐    ┌─────────┐   ┌─────────┐
      │  Task 1 │    │  Task 2 │   │  Task 3 │
      │ API→Kafka│───▶│Kafka→Mongo──▶│  Spark  │
      └─────────┘    └─────────┘   └─────────┘
            │              │              │
            ▼              ▼              ▼
      [Kafka Topic]  [MongoDB Atlas]  [Analytics]
                           ▲
                           │
                    [Monitoring MongoDB]
```

## 🚀 Démarrage Rapide

```bash
# 1. Configuration
cp .env.example .env
# Éditer .env : remplir MONGO_URI

# 2. Créer dossiers Airflow
mkdir -p dags logs plugins config

# 3. Démarrer
docker-compose up -d

# 4. Accéder à Airflow
# http://localhost:8081
# Username: admin / Password: admin

# 5. Activer le DAG
# Cliquer sur le toggle dans l'UI Airflow
```

## 📊 Workflow du DAG

```
1. check_kafka_ready (vérifie Kafka disponible)
      ↓
2. fetch_api_send_kafka (API → Kafka)
      ↓
3. consume_kafka_insert_mongo (Kafka → MongoDB)
      ↓  
4. spark_processing (traitement analytics)
```

### Schedule

Par défaut : **@hourly** (toutes les heures)

Modifiable dans `dags/polymarket_pipeline_dag.py` :
```python
schedule_interval='@hourly'  # ou @daily, @weekly, cron syntax, etc.
```

## 🔍 Monitoring

### Airflow UI
- **URL** : http://localhost:8081
- **Graph View** : Visualisation du workflow
- **Logs** : Logs détaillés de chaque task
- **Stats** : Performance et historique

### MongoDB Atlas - `polymarket_monitoring`

Collections :
- `pipeline_metrics` : Exécutions des pipelines
- `batch_inserts` : Performance des insertions
- `kafka_metrics` : Métriques Kafka
- `error_logs` : Erreurs capturées

### Spark UI
- **URL** : http://localhost:8080
- Jobs et workers

## 🛠️ Troubleshooting

### DAG n'apparaît pas

```bash
# Vérifier les logs
docker logs airflow-scheduler

# Lister les DAGs
docker exec airflow-scheduler airflow dags list
```

### Erreur Kafka

```bash
# Vérifier Kafka
docker ps | grep broker
docker logs broker

# Tester la connexion
docker exec airflow-webserver python -c "
from kafka import KafkaProducer
p = KafkaProducer(bootstrap_servers='broker:9092')
print('✅ Kafka OK')
p.close()
"
```

### Erreur MongoDB

Vérifier :
1. `MONGO_URI` dans `.env`
2. IP whitelisted dans MongoDB Atlas
3. Credentials corrects

### Réinitialisation complète

```bash
docker-compose down -v
rm -rf logs/*
docker-compose up -d
```

## 📝 Variables Clés (.env)

```env
# Requis
POLYMARKET_API_URL=https://gamma-api.polymarket.com/events
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/

# Optionnel (valeurs par défaut OK)
KAFKA_BOOTSTRAP_SERVERS=broker:9092
KAFKA_TOPIC=polymarket-events
DB2=polymarket_db
MONITORING_DB=polymarket_monitoring
BATCH_SIZE=100
```

## 🎓 Pourquoi Airflow ?

### Avantages

✅ **Orchestration** : Enchaînement automatique des tâches  
✅ **Scheduling** : Exécution programmée (hourly, daily, etc.)  
✅ **Retry Logic** : Relance automatique en cas d'échec  
✅ **Monitoring** : UI complète pour suivre tout  
✅ **Alerting** : Notifications en cas de problème  
✅ **Scalabilité** : Facile d'ajouter des tasks  

### Cas d'usage

- ✅ Pipeline batch régulier (hourly, daily)
- ✅ Dépendances entre tasks
- ✅ Besoin de retry automatique
- ✅ Équipe qui a besoin de visibilité

## 🔄 Évolution du Projet

### Version 1.0 (Sans orchestration)
- Scripts Python indépendants
- Consumer en boucle infinie
- Lancement manuel

### Version 2.0 (Avec Airflow) ← Actuel
- Orchestration Airflow
- Consumer déclenché par task
- Monitoring MongoDB intégré
- Scheduling automatique

## 📚 Documentation

- [README_FULL.md](README.md) - Documentation complète
- [dags/polymarket_pipeline_dag.py](dags/polymarket_pipeline_dag.py) - Code du DAG

---

**Quick Start** : `docker-compose up -d` → http://localhost:8081 → Activer le DAG 🚀
