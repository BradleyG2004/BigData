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


def create_kafka_producer():
    """
    Crée un producteur Kafka.
    
    Retourne :
        - instance KafkaProducer si OK
        - None en cas d'erreur
    """
    try:
        print("\n🔄 Création du producteur Kafka...")
        print(f"   - Bootstrap servers : {KAFKA_BOOTSTRAP_SERVERS}")

        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        print("✅ Producteur Kafka créé avec succès !")
        return producer

    except Exception as e:
        print(f"❌ Erreur lors de la création du producteur Kafka : {e}")
        return None


def fetch_polymarket_data(limit=100):
    """
    Récupère les données depuis l'API Polymarket
    
    Args:
        limit (int): Nombre d'événements à récupérer (default: 100)
    """
    all_items = []
    
    print("\n📊 Récupération des données depuis l'API Polymarket...")
    print(f"   (Limite: {limit} événements)")
    
    try:
        # Construction de l'URL avec les paramètres
        params = {
            'limit': limit,
            'offset': 0
        }
        
        print(f"\n📄 Fetching events...")
        
        # Requête API
        response = requests.get(POLYMARKET_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse la réponse JSON
        data = response.json()
        
        # L'API Polymarket retourne une liste d'événements directement
        if isinstance(data, list):
            all_items = data
            print(f"   ✓ Récupéré {len(all_items)} événements")
        else:
            print(f"   ⚠️  Format de réponse inattendu")
            return None
        
        print("\n✅ Récupération des données terminée!")
                
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrompu par l'utilisateur! {len(all_items)} items collectés.")
        print("   Continuation avec les données collectées...")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Erreur lors de la récupération depuis l'API: {e}")
        if all_items:
            print(f"   Continuation avec {len(all_items)} items déjà collectés")
        else:
            return None
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        if all_items:
            print(f"   Continuation avec {len(all_items)} items déjà collectés")
        else:
            return None
    
    return all_items


def send_to_kafka(producer, data, topic=KAFKA_TOPIC):
    """
    Envoie les données récupérées vers Kafka.
    
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
            # Chaque item est un dict (réponse JSON de l'API)
            producer.send(topic, value=item)

            # Log de progression (tous les 10 messages)
            if idx % 10 == 0 or idx == len(data):
                print(f"   ✓ Envoyé : {idx}/{len(data)} messages")

        # S'assure que tout est bien poussé avant de fermer
        producer.flush()
        print("\n✅ Tous les messages ont été envoyés à Kafka !")

    except Exception as e:
        print(f"❌ Erreur lors de l'envoi des messages à Kafka : {e}")


def main():
    """Fonction principale - Récupère les données de l'API et les envoie à Kafka"""
    print("=" * 60)
    print("    Polymarket Data Producer (API → Kafka)")
    print("=" * 60)
    
    # ================================
    # 1) Création du producteur Kafka
    # ================================
    producer = create_kafka_producer()
    if not producer:
        print("\n❌ Impossible de créer le producteur Kafka. Arrêt du script.")
        sys.exit(1)

    # ================================
    # 2) Récupération des données de l'API
    # ================================
    limit = 100
    print(f"\n📌 Configuré pour récupérer {limit} événements")

    data = fetch_polymarket_data(limit=limit)

    if not data:
        print("\n⚠️  Aucune donnée récupérée depuis l'API Polymarket")
        producer.close()
        sys.exit(0)

    # ================================
    # 3) Envoi vers Kafka
    # ================================
    send_to_kafka(producer, data)

    # ================================
    # 4) Nettoyage
    # ================================
    try:
        producer.close()
        print("\n✅ Producteur Kafka fermé proprement")
    except Exception as e:
        print(f"⚠️  Erreur lors de la fermeture : {e}")

    print("\n🎉 Processus terminé avec succès!")


if __name__ == "__main__":
    main()
