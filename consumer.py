import os
import sys
import json
from kafka import KafkaConsumer
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# ⚠️ Assure-toi d'avoir installé les dépendances côté Python :
#   pip install kafka-python pymongo python-dotenv

# Load environment variables
load_dotenv()

# ================================
# 🔧 Configuration
# ================================

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'polymarket-events')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'polymarket-mongo-consumer')

# Configuration MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('DB2', 'polymarket_db')
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
    Insère un batch de documents dans MongoDB
    
    Args:
        collection: collection MongoDB
        batch: liste de documents à insérer
    """
    try:
        if batch:
            result = collection.insert_many(batch)
            print(f"   ✓ Inséré : {len(result.inserted_ids)} documents")
            return len(result.inserted_ids)
        return 0
    except Exception as e:
        print(f"   ❌ Erreur lors de l'insertion : {e}")
        return 0


def consume_and_insert(consumer, collection):
    """
    Consomme les messages de Kafka et les insère dans MongoDB par batch
    
    Args:
        consumer: instance de KafkaConsumer
        collection: collection MongoDB
    """
    print("\n📨 Démarrage de la consommation des messages Kafka...")
    print(f"   - Taille du batch : {BATCH_SIZE}")
    print(f"   - Collection MongoDB : {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")
    print("\n   ⏳ En attente de messages... (Ctrl+C pour arrêter)\n")
    
    batch = []
    total_inserted = 0
    
    try:
        for message in consumer:
            # Récupération des données du message
            data = message.value
            batch.append(data)
            
            # Insertion par batch
            if len(batch) >= BATCH_SIZE:
                inserted = insert_batch_to_mongodb(collection, batch)
                total_inserted += inserted
                batch = []
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
        
        # Insérer le dernier batch en cas d'erreur
        if batch:
            print(f"\n💾 Tentative d'insertion du dernier batch...")
            inserted = insert_batch_to_mongodb(collection, batch)
            total_inserted += inserted
    
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
    try:
        total = consume_and_insert(consumer, collection)
        print(f"\n🎉 Processus terminé! Total de documents insérés : {total}")
    except Exception as e:
        print(f"\n❌ Erreur fatale : {e}")
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
