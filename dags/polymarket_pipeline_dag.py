"""
DAG Airflow - Pipeline Polymarket Data
Orchestration complète : API → Kafka → MongoDB → Spark
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.python import PythonSensor
import os
import sys

# Ajouter le répertoire du projet au path pour importer les modules
sys.path.insert(0, '/opt/airflow/project')

default_args = {
    'owner': 'polymarket',
    'depends_on_past': False,
    'start_date': datetime(2026, 2, 9),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'polymarket_data_pipeline',
    default_args=default_args,
    description='Pipeline complet de collecte et traitement des données Polymarket',
    schedule_interval='@hourly',  # Exécution toutes les heures
    catchup=False,
    tags=['polymarket', 'kafka', 'mongodb', 'spark'],
)


def check_kafka_available():
    """Vérifie que Kafka est disponible"""
    from kafka import KafkaProducer
    import time
    
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'broker:9092')
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                request_timeout_ms=5000
            )
            producer.close()
            print(f"✅ Kafka est disponible sur {bootstrap_servers}")
            return True
        except Exception as e:
            print(f"⚠️ Tentative {attempt + 1}/{max_retries} - Kafka non disponible: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    
    raise Exception("❌ Kafka n'est pas disponible après plusieurs tentatives")


def fetch_api_and_send_to_kafka():
    """
    Étape 1 : Récupère les données de l'API Polymarket et les envoie à Kafka
    """
    import json
    import requests
    from kafka import KafkaProducer
    from monitoring_mongo import get_monitoring_service
    
    print("=" * 60)
    print("  📡 ÉTAPE 1: API → Kafka")
    print("=" * 60)
    
    # Configuration
    api_url = os.getenv('POLYMARKET_API_URL')
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'broker:9092')
    topic = os.getenv('KAFKA_TOPIC', 'polymarket-events')
    
    # Monitoring
    monitoring = get_monitoring_service()
    run_id = monitoring.log_pipeline_start('producer', {'source': 'airflow'})
    
    try:
        # 1. Créer le producteur Kafka
        print(f"\n🔄 Connexion à Kafka ({bootstrap_servers})...")
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("✅ Producteur Kafka créé")
        
        # 2. Récupérer les données de l'API
        print(f"\n📊 Récupération depuis {api_url}...")
        response = requests.get(api_url, params={'limit': 100}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            raise ValueError("Format de réponse inattendu de l'API")
        
        print(f"✅ Récupéré {len(data)} événements")
        
        # 3. Envoyer à Kafka
        print(f"\n📨 Envoi vers Kafka (topic: {topic})...")
        for idx, item in enumerate(data, start=1):
            producer.send(topic, value=item)
            if idx % 10 == 0:
                print(f"   ✓ Envoyé : {idx}/{len(data)} messages")
        
        producer.flush()
        producer.close()
        print(f"\n✅ Tous les messages envoyés à Kafka!")
        
        # Monitoring
        monitoring.log_pipeline_end(run_id, 'success', len(data))
        
        return len(data)
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        monitoring.log_pipeline_end(run_id, 'failed', 0, str(e))
        raise


def consume_kafka_and_insert_mongo():
    """
    Étape 2 : Consomme depuis Kafka et insère dans MongoDB
    """
    import json
    import time
    from kafka import KafkaConsumer
    from pymongo import MongoClient
    from monitoring_mongo import get_monitoring_service
    
    print("=" * 60)
    print("  💾 ÉTAPE 2: Kafka → MongoDB")
    print("=" * 60)
    
    # Configuration
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'broker:9092')
    topic = os.getenv('KAFKA_TOPIC', 'polymarket-events')
    group_id = f"airflow-consumer-{int(time.time())}"  # Unique group ID
    
    mongo_uri = os.getenv('MONGO_URI')
    db_name = os.getenv('DB2', 'polymarket')
    collection_name = os.getenv('MONGO_COLLECTION', 'polymarket')
    batch_size = int(os.getenv('BATCH_SIZE', '100'))
    
    # Monitoring
    monitoring = get_monitoring_service()
    run_id = monitoring.log_pipeline_start('consumer', {'source': 'airflow'})
    
    try:
        # 1. Connexion MongoDB
        print(f"\n🔄 Connexion à MongoDB...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[db_name]
        collection = db[collection_name]
        print(f"✅ Connecté à {db_name}.{collection_name}")
        
        # 2. Créer le consumer Kafka
        print(f"\n🔄 Connexion à Kafka ({bootstrap_servers})...")
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset='earliest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            enable_auto_commit=False,
            consumer_timeout_ms=30000  # Timeout après 30 secondes sans messages
        )
        print(f"✅ Consumer créé (group: {group_id})")
        
        # 3. Consommer et insérer
        print(f"\n📨 Consommation des messages...")
        batch = []
        total_inserted = 0
        
        for message in consumer:
            batch.append(message.value)
            
            if len(batch) >= batch_size:
                start_time = time.time()
                result = collection.insert_many(batch)
                duration_ms = int((time.time() - start_time) * 1000)
                
                total_inserted += len(result.inserted_ids)
                print(f"   ✓ Inséré batch de {len(batch)} documents ({duration_ms}ms)")
                
                # Log monitoring
                monitoring.log_batch_insert(
                    collection_name=collection_name,
                    count=len(batch),
                    duration_ms=duration_ms
                )
                
                batch = []
                consumer.commit()
        
        # Insérer le dernier batch
        if batch:
            result = collection.insert_many(batch)
            total_inserted += len(result.inserted_ids)
            print(f"   ✓ Inséré dernier batch de {len(batch)} documents")
        
        print(f"\n✅ Total inséré dans MongoDB: {total_inserted} documents")
        
        # Monitoring
        monitoring.log_pipeline_end(run_id, 'success', total_inserted)
        
        consumer.close()
        client.close()
        
        return total_inserted
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        monitoring.log_pipeline_end(run_id, 'failed', 0, str(e))
        raise


def clean_polymarket_data_task():
    """
    Étape 3 : Nettoyage des données Polymarket
    Filtre et nettoie les données insérées dans MongoDB
    """
    from pymongo import MongoClient
    from monitoring_mongo import get_monitoring_service
    
    print("=" * 60)
    print("  🧹 ÉTAPE 3: Nettoyage des données")
    print("=" * 60)
    
    # Configuration
    mongo_uri = os.getenv('MONGO_URI')
    db_name = os.getenv('DB2', 'polymarket')
    
    # Monitoring
    monitoring = get_monitoring_service()
    run_id = monitoring.log_pipeline_start('cleaning', {'source': 'airflow'})
    
    try:
        # Connexion MongoDB
        print(f"\n🔄 Connexion à MongoDB ({db_name})...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        source_collection = db['polymarket']
        target_collection = db['cleaned']
        
        # Compter les documents source
        total_docs = source_collection.count_documents({})
        print(f"✅ Documents dans 'polymarket': {total_docs}")
        
        # Vérifier si la collection cible existe déjà
        existing_count = target_collection.count_documents({})
        if existing_count > 0:
            print(f"⚠️  Collection 'cleaned' contient déjà {existing_count} documents")
            target_collection.delete_many({})
            print("   ✓ Données existantes supprimées")
        
        # Champs à supprimer
        fields_to_remove = [
            'liquidity', 'archived', 'new', 'featured', 'restricted', 'sortBy',
            'competitive', 'volume24hr', 'volume1wk', 'volume1mo', 'volume1yr',
            'liquidityAmm', 'LiquidityAmm', 'liquidityClob', 'cyom', 'showAllOutcomes',
            'openInterest', 'markets', 'series', 'tags', 'enableNegRisk',
            'negRiskAugmented', 'pendingDeployment', 'deploying', 'requiresTranslation',
            'commentsEnabled', 'subcategory', 'closed', 'active', 'showMarketImages'
        ]
        
        # Critères de filtrage: DÉSACTIVÉ - Prend TOUS les documents
        # Si vous voulez filtrer, décommentez les lignes ci-dessous
        # filter_query = {
        #     'image': {'$exists': True, '$ne': ''},
        #     'icon': {'$exists': True, '$ne': ''},
        #     'seriesSlug': {'$exists': True, '$ne': ''},
        #     'resolutionSource': {'$exists': True, '$ne': ''}
        # }
        
        print(f"\n🔍 Récupération de tous les documents...")
        filtered_docs = list(source_collection.find({}))  # Pas de filtrage
        filtered_count = len(filtered_docs)
        
        print(f"   ✓ Total: {filtered_count} documents à nettoyer")
        # print(f"   ✗ Exclu {total_docs - filtered_count} documents")  # Plus de filtrage
        
        if filtered_count == 0:
            print("\n⚠️  Aucun document ne correspond aux critères")
            monitoring.log_pipeline_end(run_id, 'success', 0, 'No documents to clean')
            return 0
        
        # Nettoyer les documents
        print(f"\n🧹 Nettoyage de {filtered_count} documents...")
        cleaned_docs = []
        for doc in filtered_docs:
            for field in fields_to_remove:
                doc.pop(field, None)
            cleaned_docs.append(doc)
        
        # Insérer dans la collection cible
        print(f"\n💾 Insertion dans '{db_name}.cleaned'...")
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(cleaned_docs), batch_size):
            batch = cleaned_docs[i:i + batch_size]
            result = target_collection.insert_many(batch)
            total_inserted += len(result.inserted_ids)
            print(f"   ✓ Batch {i//batch_size + 1}: {total_inserted}/{len(cleaned_docs)}")
        
        print(f"\n✅ {total_inserted} documents nettoyés et insérés!")
        print(f"\n📊 Résumé:")
        print(f"   - Documents source: {total_docs}")
        print(f"   - Documents nettoyés: {filtered_count}")
        # print(f"   - Exclus: {total_docs - filtered_count}")  # Plus d'exclusion
        print(f"   - Insérés: {total_inserted}")
        
        client.close()
        
        # Monitoring
        monitoring.log_pipeline_end(run_id, 'success', total_inserted)
        monitoring.log_batch_insert('cleaning', total_inserted, 0)
        
        return total_inserted
        
    except Exception as e:
        print(f"\n❌ Erreur lors du nettoyage: {e}")
        monitoring.log_pipeline_end(run_id, 'failed', 0, str(e))
        monitoring.log_error('cleaning', str(e))
        raise


def process_with_spark():
    """
    Étape 4 : Traitement avec Spark
    """
    from monitoring_mongo import get_monitoring_service
    
    print("=" * 60)
    print("  🔥 ÉTAPE 4: Traitement Spark")
    print("=" * 60)
    
    monitoring = get_monitoring_service()
    run_id = monitoring.log_pipeline_start('spark', {'source': 'airflow'})
    
    try:
        # Pour l'instant, on log juste que Spark a été appelé
        # Vous pouvez implémenter le traitement Spark ici
        print("✅ Spark processing placeholder")
        
        monitoring.log_pipeline_end(run_id, 'success', 0)
        return True
        
    except Exception as e:
        print(f"❌ Erreur Spark: {e}")
        monitoring.log_pipeline_end(run_id, 'failed', 0, str(e))
        raise


def load_to_postgres():
    """
    Étape 5 : Charger les données nettoyées dans PostgreSQL
    Transfère les données de MongoDB (collection cleaned) vers PostgreSQL
    """
    import json
    from datetime import datetime
    from pymongo import MongoClient
    import psycopg2
    from psycopg2.extras import execute_values
    from monitoring_mongo import get_monitoring_service
    
    print("=" * 60)
    print("  🗄️ ÉTAPE 5: Chargement dans PostgreSQL")
    print("=" * 60)
    
    # Configuration
    mongo_uri = os.getenv('MONGO_URI')
    db_name = os.getenv('DB2', 'polymarket')
    
    pg_host = os.getenv('POSTGRES_HOST', 'postgres-polymarket')
    pg_port = int(os.getenv('POSTGRES_PORT', '5432'))
    pg_user = os.getenv('POSTGRES_USER', 'polymarket')
    pg_password = os.getenv('POSTGRES_PASSWORD', 'polymarket123')
    pg_db = os.getenv('POSTGRES_DB', 'polymarket')
    
    batch_size = int(os.getenv('BATCH_SIZE', '100'))
    
    # Monitoring
    monitoring = get_monitoring_service()
    run_id = monitoring.log_pipeline_start('postgres_load', {'source': 'airflow'})
    
    try:
        # 1. Connexion MongoDB
        print(f"\n🔄 Connexion à MongoDB ({db_name}.cleaned)...")
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = mongo_client[db_name]
        collection = db['cleaned']
        total_docs = collection.count_documents({})
        print(f"✅ {total_docs} documents à transférer")
        
        if total_docs == 0:
            print("⚠️ Aucun document à transférer")
            monitoring.log_pipeline_end(run_id, 'success', 0, 'No documents to transfer')
            return 0
        
        # 2. Connexion PostgreSQL
        print(f"\n🔄 Connexion à PostgreSQL ({pg_host}:{pg_port})...")
        pg_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            user=pg_user,
            password=pg_password,
            database=pg_db
        )
        print("✅ Connecté à PostgreSQL")
        
        # 3. Vider la table avant insertion (pour éviter doublons)
        print("\n🗑️ Vidage de la table polymarket_cleaned...")
        cursor = pg_conn.cursor()
        cursor.execute("TRUNCATE TABLE polymarket_cleaned RESTART IDENTITY CASCADE;")
        pg_conn.commit()
        cursor.close()
        print("✅ Table vidée")
        
        # 4. Fonction de parsing des dates
        def parse_datetime(value):
            if not value:
                return None
            try:
                if isinstance(value, datetime):
                    return value
                if isinstance(value, (int, float)):
                    return datetime.fromtimestamp(value)
                if isinstance(value, str):
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                return None
            except:
                return None
        
        # 5. Fonction de transformation des documents
        def transform_document(doc):
            try:
                mongo_id = str(doc.get('_id', ''))
                condition_id = doc.get('conditionId') or doc.get('condition_id')
                question_id = doc.get('questionID') or doc.get('question_id')
                
                outcomes = json.dumps(doc.get('outcomes', [])) if doc.get('outcomes') else None
                outcome_prices = json.dumps(doc.get('outcomePrices', [])) if doc.get('outcomePrices') else None
                
                return (
                    mongo_id,
                    condition_id,
                    question_id,
                    doc.get('slug'),
                    doc.get('title', ''),
                    doc.get('description', ''),
                    doc.get('question', ''),
                    doc.get('category'),
                    doc.get('seriesSlug'),
                    doc.get('resolutionSource'),
                    doc.get('image'),
                    doc.get('icon'),
                    doc.get('resolutionTitle'),
                    doc.get('questionType'),
                    outcomes,
                    outcome_prices,
                    doc.get('volume'),
                    doc.get('volumeNum'),
                    parse_datetime(doc.get('startDate')),
                    parse_datetime(doc.get('endDate')),
                    parse_datetime(doc.get('gameStartDatetime')),
                    doc.get('secondsDelay'),
                    doc.get('secondsSinceStart')
                )
            except Exception as e:
                print(f"⚠️ Erreur transformation: {e}")
                return None
        
        # 6. Transfert par batch
        print(f"\n📦 Transfert des données (batch size: {batch_size})...")
        
        insert_query = """
        INSERT INTO polymarket_cleaned (
            mongo_id, condition_id, question_id, slug, title, description, question,
            category, series_slug, resolution_source, image, icon,
            resolution_title, question_type, outcomes, outcome_prices,
            volume, volume_num, start_date, end_date, game_start_datetime,
            seconds_delay, seconds_since_start
        ) VALUES %s
        ON CONFLICT (mongo_id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            volume = EXCLUDED.volume,
            volume_num = EXCLUDED.volume_num,
            outcome_prices = EXCLUDED.outcome_prices,
            updated_at = NOW()
        """
        
        batch = []
        total_inserted = 0
        total_errors = 0
        
        for idx, doc in enumerate(collection.find({}), start=1):
            transformed = transform_document(doc)
            
            if transformed:
                batch.append(transformed)
            else:
                total_errors += 1
            
            if len(batch) >= batch_size:
                cursor = pg_conn.cursor()
                execute_values(cursor, insert_query, batch, page_size=100)
                pg_conn.commit()
                cursor.close()
                
                total_inserted += len(batch)
                print(f"   ✓ Batch {total_inserted//batch_size}: {total_inserted}/{total_docs} documents")
                batch = []
        
        # Dernier batch
        if batch:
            cursor = pg_conn.cursor()
            execute_values(cursor, insert_query, batch, page_size=100)
            pg_conn.commit()
            cursor.close()
            total_inserted += len(batch)
            print(f"   ✓ Dernier batch: {total_inserted}/{total_docs} documents")
        
        # Vérification
        cursor = pg_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM polymarket_cleaned;")
        pg_count = cursor.fetchone()[0]
        cursor.close()
        
        print(f"\n✅ Transfert terminé!")
        print(f"\n📊 Résumé:")
        print(f"   - Documents MongoDB: {total_docs}")
        print(f"   - Documents insérés: {total_inserted}")
        print(f"   - Erreurs: {total_errors}")
        print(f"   - Documents PostgreSQL: {pg_count}")
        
        # Fermeture
        pg_conn.close()
        mongo_client.close()
        
        # Monitoring
        monitoring.log_pipeline_end(run_id, 'success', total_inserted)
        
        return total_inserted
        
    except Exception as e:
        print(f"\n❌ Erreur lors du chargement: {e}")
        import traceback
        traceback.print_exc()
        monitoring.log_pipeline_end(run_id, 'failed', 0, str(e))
        raise


# ================================
# Définition des tâches
# ================================

# Sensor pour vérifier que Kafka est prêt
check_kafka = PythonSensor(
    task_id='check_kafka_ready',
    python_callable=check_kafka_available,
    timeout=300,
    poke_interval=10,
    mode='poke',
    dag=dag,
)

# Task 1: Récupérer API et envoyer à Kafka
fetch_and_send = PythonOperator(
    task_id='fetch_api_send_kafka',
    python_callable=fetch_api_and_send_to_kafka,
    dag=dag,
)

# Task 2: Consommer Kafka et insérer dans MongoDB
consume_and_insert = PythonOperator(
    task_id='consume_kafka_insert_mongo',
    python_callable=consume_kafka_and_insert_mongo,
    dag=dag,
)

# Task 3: Nettoyer les données Polymarket
clean_data = PythonOperator(
    task_id='clean_polymarket_data',
    python_callable=clean_polymarket_data_task,
    dag=dag,
)

# Task 4: Traitement Spark (optionnel)
spark_processing = PythonOperator(
    task_id='spark_processing',
    python_callable=process_with_spark,
    dag=dag,
)

# Task 5: Charger les données nettoyées dans PostgreSQL
load_postgres = PythonOperator(
    task_id='load_to_postgres',
    python_callable=load_to_postgres,
    dag=dag,
)

# ================================
# Définition du flux d'exécution
# ================================

check_kafka >> fetch_and_send >> consume_and_insert >> clean_data >> load_postgres >> spark_processing
