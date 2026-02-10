import os
import sys
import json
import time
import traceback
from kafka import KafkaConsumer
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo import ReplaceOne
from dotenv import load_dotenv
from monitoring import get_monitoring_service

# Load environment variables
load_dotenv()

# Service de monitoring
monitoring = get_monitoring_service()

# ================================
# 🔧 Configuration
# ================================

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'polymarket-events')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'polymarket-mongo-consumer')

# Configuration MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('DB2', 'polymarket')
MONGO_COLLECTION_NAME = os.getenv('MONGO_COLLECTION', 'polymarket')

# Taille du batch pour l'insertion MongoDB
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))


def connect_mongodb():
    """
    Connexion à MongoDB Atlas
    
    Retourne:
        - MongoClient si succès
        - None en cas d'erreur
    """
    try:
        if not MONGO_URI:
            print("❌ Error: MONGO_URI not found in .env file")
            return None
        
        print("🔄 Connecting to MongoDB Atlas...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Test de la connexion
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        
        return client
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ Connection error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def ensure_unique_index(collection):
    """
    Crée un index unique sur le champ 'id' pour éviter les doublons
    
    Args:
        collection: collection MongoDB
    """
    try:
        # Créer un index unique sur le champ 'id'
        collection.create_index('id', unique=True)
        print("✅ Index unique créé sur le champ 'id'")
    except Exception as e:
        # L'index existe déjà ou erreur
        print(f"ℹ️  Index 'id' : {e}")


def create_kafka_consumer():
    """
    Crée un consommateur Kafka.
    
    Retourne :
        - instance KafkaConsumer si OK
        - None en cas d'erreur
    """
    try:
        print("\n🔄 Création du consommateur Kafka...")
        print(f"   - Bootstrap servers : {KAFKA_BOOTSTRAP_SERVERS}")
        print(f"   - Topic : {KAFKA_TOPIC}")
        print(f"   - Group ID : {KAFKA_GROUP_ID}")

        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_GROUP_ID,
            # Démarrer au début si nouveau consumer
            auto_offset_reset='earliest',
            # Désérialisation JSON des messages
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            # Commit automatique des offsets
            enable_auto_commit=True,
            auto_commit_interval_ms=1000
        )

        print("✅ Consommateur Kafka créé avec succès !")
        return consumer

    except Exception as e:
        print(f"❌ Erreur lors de la création du consommateur Kafka : {e}")
        return None


def insert_batch_to_mongodb(collection, batch):
    """
    Insère ou met à jour un batch de documents dans MongoDB (évite les doublons via le champ 'id')
    
    Args:
        collection: collection MongoDB
        batch: liste de documents à insérer
    
    Returns:
        Nombre de documents insérés ou mis à jour
    """
    try:
        if batch:
            start_time = time.time()
            
            # Utiliser bulk_write avec ReplaceOne pour éviter les doublons
            # Si le document existe (même 'id'), il est remplacé, sinon inséré
            operations = [
                ReplaceOne(
                    filter={'id': doc['id']},
                    replacement=doc,
                    upsert=True
                )
                for doc in batch if 'id' in doc
            ]
            
            if operations:
                result = collection.bulk_write(operations, ordered=False)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Nombre d'insertions + mises à jour
                total_count = result.upserted_count + result.modified_count
                
                print(f"   ✓ Traité : {total_count} documents ({result.upserted_count} nouveaux, {result.modified_count} mis à jour) en {duration_ms}ms")
                
                # Log vers PostgreSQL
                monitoring.log_mongodb_stats(
                    collection_name=collection.name,
                    document_count=collection.count_documents({}),
                    insert_count=result.upserted_count,
                    insert_duration_ms=duration_ms
                )
                
                return total_count
            else:
                print("   ⚠️  Aucun document avec un champ 'id' valide")
                return 0
        return 0
    except Exception as e:
        print(f"   ❌ Erreur lors de l'insertion : {e}")
        monitoring.log_error(
            source='consumer',
            error_type='mongodb_insert_error',
            error_message=str(e),
            stack_trace=traceback.format_exc()
        )
        return 0


def consume_and_insert(consumer, collection, run_id=None):
    """
    Consomme les messages de Kafka et les insère dans MongoDB par batch
    
    Args:
        consumer: instance de KafkaConsumer
        collection: collection MongoDB
        run_id: ID du run pour le monitoring
    """
    print("\n📨 Démarrage de la consommation des messages Kafka...")
    print(f"   - Taille du batch : {BATCH_SIZE}")
    print(f"   - Collection MongoDB : {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")
    print("\n   ⏳ En attente de messages... (Ctrl+C pour arrêter)\n")
    
    batch = []
    total_inserted = 0
    message_count = 0
    
    try:
        for message in consumer:
            # Récupération des données du message
            data = message.value
            batch.append(data)
            message_count += 1
            
            # Insertion par batch
            if len(batch) >= BATCH_SIZE:
                inserted = insert_batch_to_mongodb(collection, batch)
                total_inserted += inserted
                
                # Log métriques Kafka
                monitoring.log_kafka_metrics(
                    topic=KAFKA_TOPIC,
                    partition=message.partition,
                    offset=message.offset,
                    messages_count=message_count,
                    consumer_group=KAFKA_GROUP_ID
                )
                
                batch = []
                message_count = 0
                print(f"   📊 Total inséré jusqu'à maintenant : {total_inserted} documents\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur...")
        
        # Insérer le dernier batch s'il n'est pas vide
        if batch:
            print(f"\n💾 Insertion du dernier batch ({len(batch)} documents)...")
            inserted = insert_batch_to_mongodb(collection, batch)
            total_inserted += inserted
        
        print(f"\n✅ Total de documents insérés : {total_inserted}")
        print("🛑 Arrêt du consommateur...")
    
    except Exception as e:
        print(f"\n❌ Erreur lors de la consommation : {e}")
        
        monitoring.log_error(
            source='consumer',
            error_type='consumption_error',
            error_message=str(e),
            stack_trace=traceback.format_exc()
        )
        
        # Insérer le dernier batch en cas d'erreur
        if batch:
            print(f"\n💾 Tentative d'insertion du dernier batch...")
            inserted = insert_batch_to_mongodb(collection, batch)
            total_inserted += inserted
    
    # Mettre à jour le monitoring
    if run_id:
        monitoring.log_pipeline_end(run_id, 'success', total_inserted)
    
    return total_inserted


def main():
    """Fonction principale - Consomme depuis Kafka et insère dans MongoDB"""
    print("=" * 60)
    print("    Polymarket Data Consumer (Kafka → MongoDB)")
    print("=" * 60)
    
    # ================================
    # 1) Connexion à MongoDB
    # ================================
    client = connect_mongodb()
    if not client:
        print("\n❌ Impossible de se connecter à MongoDB. Arrêt du script.")
        sys.exit(1)
    
    # Récupération de la collection
    db = client[MONGO_DB_NAME]
    collection = db[MONGO_COLLECTION_NAME]
    
    # Créer un index unique sur le champ 'id' pour éviter les doublons
    ensure_unique_index(collection)
    
    print(f"\n📊 Database: {MONGO_DB_NAME}")
    print(f"📊 Collection: {MONGO_COLLECTION_NAME}")
    print(f"📊 Documents existants: {collection.count_documents({})}")
    
    # ================================
    # 2) Création du consommateur Kafka
    # ================================
    consumer = create_kafka_consumer()
    if not consumer:
        print("\n❌ Impossible de créer le consommateur Kafka. Arrêt du script.")
        client.close()
        sys.exit(1)
    
    # ================================
    # 3) Consommation et insertion
    # ================================
    
    # Démarrer le monitoring
    run_id = monitoring.log_pipeline_start(
        run_type='consumer',
        metadata={
            'kafka_topic': KAFKA_TOPIC,
            'kafka_group': KAFKA_GROUP_ID,
            'mongodb_collection': f"{MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}",
            'batch_size': BATCH_SIZE
        }
    )
    
    try:
        total = consume_and_insert(consumer, collection, run_id)
        print(f"\n🎉 Processus terminé! Total de documents insérés : {total}")
    except Exception as e:
        print(f"\n❌ Erreur fatale : {e}")
        if run_id:
            monitoring.log_pipeline_end(run_id, 'failed', 0, str(e))
    finally:
        # ================================
        # 4) Nettoyage
        # ================================
        print("\n🧹 Nettoyage des ressources...")
        
        if consumer:
            try:
                consumer.close()
                print("   ✓ Consommateur Kafka fermé")
            except Exception:
                pass
        
        if client:
            try:
                client.close()
                print("   ✓ Connexion MongoDB fermée")
            except Exception:
                pass
        
        print("\n👋 Au revoir!")


if __name__ == "__main__":
    main()
