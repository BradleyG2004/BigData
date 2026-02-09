"""
DAG Airflow - Kafka Producer & Consumer
========================================

Ce DAG gère uniquement la partie Kafka du pipeline:
1. Vérifier que Kafka est prêt
2. Fetch API → Envoyer à Kafka (Producer)
3. Consommer depuis Kafka → Insérer dans MongoDB (Consumer)

Schedule: Toutes les 5 minutes (automatique)
Auteur: Data Pipeline Team
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import subprocess
import time
import os
import sys

# Configuration par défaut
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=30),
}


def check_kafka_availability():
    """
    Vérifie que Kafka est disponible et prêt à recevoir des messages.
    """
    print("🔍 Vérification de la disponibilité de Kafka...")
    
    kafka_broker = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    max_retries = 10
    retry_interval = 5
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Tentative {attempt}/{max_retries}...")
            
            # Utilise kafka-broker-api-versions pour tester la connexion
            result = subprocess.run(
                ['kafka-broker-api-versions', '--bootstrap-server', kafka_broker],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("✅ Kafka est disponible et opérationnel")
                return True
            else:
                print(f"⚠️ Kafka pas encore prêt: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ Timeout lors de la tentative {attempt}")
        except Exception as e:
            print(f"❌ Erreur lors de la vérification: {e}")
        
        if attempt < max_retries:
            print(f"⏳ Attente de {retry_interval}s avant nouvelle tentative...")
            time.sleep(retry_interval)
    
    raise Exception("❌ Kafka n'est pas disponible après plusieurs tentatives")


def run_kafka_producer():
    """
    Exécute le producer Kafka qui récupère les données de l'API Polymarket
    et les envoie à Kafka.
    """
    print("="*70)
    print("🚀 DÉMARRAGE DU PRODUCER KAFKA")
    print("="*70)
    print(f"📅 Timestamp: {datetime.now()}")
    print(f"🔗 Kafka Broker: {os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')}")
    print(f"📝 Topic: {os.getenv('KAFKA_TOPIC', 'polymarket-events')}")
    print("="*70)
    
    # Chemin vers le script producer
    producer_script = '/opt/airflow/producer.py'
    
    if not os.path.exists(producer_script):
        raise FileNotFoundError(f"❌ Script producer introuvable: {producer_script}")
    
    print(f"📂 Exécution du script: {producer_script}")
    
    try:
        # Exécute le producer
        result = subprocess.run(
            ['python', producer_script],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max
            cwd='/opt/airflow'
        )
        
        print("\n" + "="*70)
        print("📤 OUTPUT DU PRODUCER")
        print("="*70)
        print(result.stdout)
        
        if result.stderr:
            print("\n" + "="*70)
            print("⚠️ WARNINGS/ERRORS")
            print("="*70)
            print(result.stderr)
        
        if result.returncode != 0:
            raise Exception(f"❌ Le producer a échoué avec le code: {result.returncode}")
        
        print("\n" + "="*70)
        print("✅ PRODUCER TERMINÉ AVEC SUCCÈS")
        print("="*70)
        
    except subprocess.TimeoutExpired:
        raise Exception("❌ Le producer a dépassé le timeout de 10 minutes")
    except Exception as e:
        raise Exception(f"❌ Erreur lors de l'exécution du producer: {e}")


def run_kafka_consumer():
    """
    Exécute le consumer Kafka qui récupère les messages depuis Kafka
    et les insère dans MongoDB.
    """
    print("="*70)
    print("🚀 DÉMARRAGE DU CONSUMER KAFKA")
    print("="*70)
    print(f"📅 Timestamp: {datetime.now()}")
    print(f"🔗 Kafka Broker: {os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')}")
    print(f"📝 Topic: {os.getenv('KAFKA_TOPIC', 'polymarket-events')}")
    print(f"💾 MongoDB: {os.getenv('MONGO_DB', 'polymarket')}")
    print("="*70)
    
    # Chemin vers le script consumer
    consumer_script = '/opt/airflow/consumer.py'
    
    if not os.path.exists(consumer_script):
        raise FileNotFoundError(f"❌ Script consumer introuvable: {consumer_script}")
    
    print(f"📂 Exécution du script: {consumer_script}")
    
    try:
        # Exécute le consumer
        result = subprocess.run(
            ['python', consumer_script],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max
            cwd='/opt/airflow'
        )
        
        print("\n" + "="*70)
        print("📥 OUTPUT DU CONSUMER")
        print("="*70)
        print(result.stdout)
        
        if result.stderr:
            print("\n" + "="*70)
            print("⚠️ WARNINGS/ERRORS")
            print("="*70)
            print(result.stderr)
        
        if result.returncode != 0:
            raise Exception(f"❌ Le consumer a échoué avec le code: {result.returncode}")
        
        print("\n" + "="*70)
        print("✅ CONSUMER TERMINÉ AVEC SUCCÈS")
        print("="*70)
        
    except subprocess.TimeoutExpired:
        raise Exception("❌ Le consumer a dépassé le timeout de 10 minutes")
    except Exception as e:
        raise Exception(f"❌ Erreur lors de l'exécution du consumer: {e}")


def print_summary():
    """
    Affiche un résumé de l'exécution du pipeline Kafka.
    """
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DU PIPELINE KAFKA")
    print("="*70)
    print("✅ Étape 1: Vérification Kafka - SUCCÈS")
    print("✅ Étape 2: Producer Kafka (API → Kafka) - SUCCÈS")
    print("✅ Étape 3: Consumer Kafka (Kafka → MongoDB) - SUCCÈS")
    print("="*70)
    print(f"🎉 Pipeline Kafka exécuté avec succès à {datetime.now()}")
    print("="*70)
    print("\n💡 Prochaines étapes:")
    print("   1. Vérifier les données dans MongoDB collection 'polymarket'")
    print("   2. Le DAG se ré-exécutera automatiquement dans 5 minutes")
    print("   3. Consulter les dashboards Grafana pour voir les stats")
    print("="*70)


# Définition du DAG
with DAG(
    dag_id='kafka_producer_consumer',
    default_args=default_args,
    description='Pipeline Kafka: API → Producer → Kafka → Consumer → MongoDB',
    schedule_interval=timedelta(minutes=5),  # Exécution automatique toutes les 5 minutes
    start_date=datetime(2026, 2, 1),
    catchup=False,
    tags=['kafka', 'polymarket', 'producer', 'consumer', 'automatic'],
    max_active_runs=1,  # Une seule exécution à la fois
) as dag:
    
    # Documentation du DAG
    dag.doc_md = """
    # 🚀 DAG Kafka Producer & Consumer
    
    ## 📋 Description
    Ce DAG gère uniquement la collecte de données via Kafka:
    - **Producer**: Récupère les données de l'API Polymarket et les envoie à Kafka
    - **Consumer**: Lit les messages Kafka et les insère dans MongoDB
    
    ## 🎯 Objectif
    Alimenter la collection MongoDB 'polymarket' avec les données brutes de l'API.
    
    ## ⚙️ Étapes
    1. **check_kafka**: Vérifie la disponibilité de Kafka
    2. **run_producer**: API Polymarket → Kafka
    3. **run_consumer**: Kafka → MongoDB (collection 'polymarket')
    4. **summary**: Affiche le résumé
    
    ## 🔧 Schedule
    - **Automatique toutes les 5 minutes**
    - Peut aussi être déclenché manuellement via l'UI Airflow
    
    ## 📊 Résultat
    - Données brutes dans MongoDB collection: `polymarket`
    - Collecte continue et mise à jour régulière
    
    ## 🔗 DAGs liés
    - `polymarket_data_pipeline`: Pipeline complet (cleaning + PostgreSQL + Spark)
    """
    
    # Tâche 1: Vérifier Kafka
    check_kafka = PythonOperator(
        task_id='check_kafka_ready',
        python_callable=check_kafka_availability,
        doc_md="""
        ### Vérification Kafka
        
        Vérifie que le broker Kafka est disponible avant de lancer le producer.
        - Max retries: 10
        - Interval: 5 secondes
        """
    )
    
    # Tâche 2: Producer Kafka
    producer = PythonOperator(
        task_id='kafka_producer',
        python_callable=run_kafka_producer,
        doc_md="""
        ### Producer Kafka
        
        Récupère les données de l'API Polymarket et les envoie à Kafka.
        
        **Script**: `producer.py`
        **Topic**: `polymarket-events`
        **Timeout**: 10 minutes
        """
    )
    
    # Tâche 3: Consumer Kafka
    consumer = PythonOperator(
        task_id='kafka_consumer',
        python_callable=run_kafka_consumer,
        doc_md="""
        ### Consumer Kafka
        
        Consomme les messages depuis Kafka et les insère dans MongoDB.
        
        **Script**: `consumer.py`
        **Topic**: `polymarket-events`
        **MongoDB Collection**: `polymarket` (raw data)
        **Timeout**: 10 minutes
        """
    )
    
    # Tâche 4: Résumé
    summary = PythonOperator(
        task_id='print_summary',
        python_callable=print_summary,
        doc_md="""
        ### Résumé
        
        Affiche un résumé de l'exécution et les prochaines étapes.
        """
    )
    
    # Définition du workflow
    check_kafka >> producer >> consumer >> summary
