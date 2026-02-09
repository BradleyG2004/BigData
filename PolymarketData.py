import os
import sys
import json
import requests
from kafka import KafkaProducer
from dotenv import load_dotenv

# ⚠️ Assure-toi d'avoir installé les dépendances côté Python :
#   pip install requests kafka-python python-dotenv

# Load environment variables
load_dotenv()

# ================================
# 🔧 Configuration
# ================================

# URL de l'API Polymarket
POLYMARKET_API_URL = os.getenv('POLYMARKET_API_URL')

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'polymarket-events')

    """
    Crée un producteur Kafka.
    
    Utilise les variables d'environnement :
        - KAFKA_BOOTSTRAP_SERVERS (ex: localhost:9092)
    
    Retourne :
        - instance KafkaProducer si OK
        - None en cas d'erreur
    """
    try:
        # Import local pour éviter une dépendance dure si tu n'utilises pas Kafka
        from kafka import KafkaProducer

        print("\n🔄 Création du producteur Kafka...")
        print(f"   - Bootstrap servers : {KAFKA_BOOTSTRAP_SERVERS}")

        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            # Sérialisation JSON des messages
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        print("✅ Producteur Kafka créé avec succès !")
        return producer

    except Exception as e:
        print(f"❌ Erreur lors de la création du producteur Kafka : {e}")
        return None
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return None

def fetch_polymarket_data(limit=100):
    """
    Fetch data from Polymarket API
    
    Args:
        limit (int): Number of events to fetch (default: 100)
    """
    all_items = []
    
    print("\n📊 Starting to fetch data from Polymarket API...")
    print(f"   (Limit: {limit} events)")
    
    try:
        # Build URL with parameters
        params = {
            'limit': limit,
            'offset': 0
        }
        
        print(f"\n📄 Fetching events...")
        
        # Make the API request
        response = requests.get(POLYMARKET_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Polymarket API returns a list of events directly
        if isinstance(data, list):
            all_items = data
            print(f"   ✓ Retrieved {len(all_items)} events")
        else:
            print(f"   ⚠️  Unexpected response format")
            return None
        
        print("\n✅ Data retrieval completed!")
                
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user! Collected {len(all_items)} items so far.")
        print("   Will proceed to insert what has been collected...")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error fetching data from API: {e}")
        if all_items:
            print(f"   Will proceed with {len(all_items)} items already collected")
        else:
            return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if all_items:
            print(f"   Will proceed with {len(all_items)} items already collected")
        else:
            return None
    
    return all_items

def send_to_kafka(producer, data, topic=KAFKA_TOPIC):
    """
    Envoie les données récupérées depuis l'API Polymarket vers Kafka.
    
    Args:
        producer: instance de KafkaProducer
        data (list[dict]): liste d'événements à envoyer
        topic (str): nom du topic Kafka
    """
    if not producer:
        print("⚠️  Producteur Kafka introuvable, envoi annulé.")
        return

    if not data:
        print("⚠️  Aucune donnée à envoyer à Kafka.")
        return

    print(f"\n📨 Envoi des données vers Kafka...")
    print(f"   - Topic : {topic}")
    print(f"   - Nombre d'événements : {len(data)}")

    try:
        for idx, item in enumerate(data, start=1):
            # Chaque item est supposé être un dict (réponse JSON de l'API)
            producer.send(topic, value=item)

            # Petit log de progression (tous les 10 messages par ex.)
            if idx % 10 == 0 or idx == len(data):
                print(f"   ✓ Envoyé : {idx}/{len(data)} messages")

        # S'assure que tout est bien poussé avant de fermer
        producer.flush()
        print("\n✅ Tous les messages ont été envoyés à Kafka !")

    except Exception as e:
        print(f"❌ Erreur lors de l'envoi des messages à Kafka : {e}")

def insert_to_mongodb(client, data, db_name=os.getenv('DB2'), collection_name='polymarket'):
    """Insert data into MongoDB collection"""
    try:
        # Get database and collection
        db = client[db_name]
        collection = db[collection_name]
        
        print(f"\n💾 Inserting data into '{db_name}.{collection_name}'...")
        
        # Clear existing data (optional - comment out if you want to keep existing data)
        existing_count = collection.count_documents({})
        if existing_count > 0:
            print(f"   ⚠️  Collection already contains {existing_count} documents")
            choice = input("   Delete existing data? (y/n): ").lower()
            if choice == 'y':
                collection.delete_many({})
                print("   ✓ Existing data deleted")
        
        # Insert data in batches for better performance
        if data:
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                result = collection.insert_many(batch)
                total_inserted += len(result.inserted_ids)
                print(f"   ✓ Inserted batch {i//batch_size + 1}: {total_inserted}/{len(data)} documents")
            
            print(f"\n✅ Successfully inserted {total_inserted} documents!")
            
            # Show some stats
            print(f"\n📊 Collection stats:")
            print(f"   - Database: {db_name}")
            print(f"   - Collection: {collection_name}")
            print(f"   - Total documents: {collection.count_documents({})}")
            
        else:
            print("⚠️  No data to insert")
            
    except Exception as e:
        print(f"❌ Error inserting data: {e}")

def main():
    """Main function - Fetch and load Polymarket data"""
    print("=" * 50)
    print("    Polymarket Data Loader")
    print("=" * 50)
    
    # ================================
    # 1) Connexion éventuelle à MongoDB
    # ================================
    # - Si OUTPUT_MODE est 'kafka', MongoDB n'est pas obligatoire.
    # - Si OUTPUT_MODE est 'mongo' ou 'both', on essaie de se connecter.

    client = None
    if OUTPUT_MODE in ('mongo', 'both'):
        client = connect_mongodb()

        if not client:
            print("\n⚠️  Impossible de se connecter à MongoDB.")
            if OUTPUT_MODE == 'mongo':
                print("   ➜ Mode 'mongo' requis, arrêt du script.")
                sys.exit(1)
            else:
                print("   ➜ On continue en mode Kafka uniquement.")

    # ================================
    # 2) Création du producteur Kafka
    # ================================
    producer = None
    if OUTPUT_MODE in ('kafka', 'both'):
        producer = create_kafka_producer()
        if not producer and OUTPUT_MODE == 'kafka':
            print("\n❌ Impossible de créer le producteur Kafka en mode 'kafka' seul. Arrêt du script.")
            sys.exit(1)

    # ================================
    # 3) Récupération des données
    # ================================
    limit = 100
    print(f"\n📌 Configuré pour récupérer {limit} événements")

    data = fetch_polymarket_data(limit=limit)

    if not data:
        print("\n⚠️  Aucune donnée récupérée depuis l'API Polymarket")
        # On ferme proprement et on sort
        if client:
            client.close()
            print("\n✅ MongoDB connection closed")
        if producer:
            producer.close()
        sys.exit(0)

    # ================================
    # 4) Envoi / insertion selon OUTPUT_MODE
    # ================================
    print(f"\n🚀 Mode de sortie : {OUTPUT_MODE}")

    if OUTPUT_MODE in ('kafka', 'both') and producer:
        send_to_kafka(producer, data)

    if OUTPUT_MODE in ('mongo', 'both') and client:
        insert_to_mongodb(client, data)

    # ================================
    # 5) Nettoyage
    # ================================
    if client:
        client.close()
        print("\n✅ MongoDB connection closed")

    if producer:
        try:
            producer.close()
            print("✅ Producteur Kafka fermé proprement")
        except Exception:
            pass

if __name__ == "__main__":
    main()
