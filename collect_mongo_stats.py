"""
Script pour collecter les statistiques MongoDB et les stocker dans PostgreSQL.
Ce script alimente la table mongodb_stats utilisée par Grafana pour la comparaison.

Exécution: 
    python collect_mongo_stats.py

Configuration via .env:
    MONGO_URI=mongodb+srv://...
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5433
    POSTGRES_DB=polymarket
    POSTGRES_USER=polymarket
    POSTGRES_PASSWORD=polymarket123
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
from pymongo import MongoClient
import psycopg2
from psycopg2.extras import execute_values

# Charger les variables d'environnement
load_dotenv()

# Configuration MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB', 'polymarket')

# Configuration PostgreSQL
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5433'),
    'database': os.getenv('POSTGRES_DB', 'polymarket'),
    'user': os.getenv('POSTGRES_USER', 'polymarket'),
    'password': os.getenv('POSTGRES_PASSWORD', 'polymarket123')
}


def get_mongodb_stats(mongo_client: MongoClient, db_name: str, collection_name: str) -> Dict[str, Any]:
    """
    Récupère les statistiques d'une collection MongoDB.
    
    Args:
        mongo_client: Client MongoDB
        db_name: Nom de la base de données
        collection_name: Nom de la collection
        
    Returns:
        Dict contenant les statistiques de la collection
    """
    try:
        db = mongo_client[db_name]
        collection = db[collection_name]
        
        # Compteur de documents
        document_count = collection.count_documents({})
        
        # Statistiques supplémentaires
        stats = db.command("collStats", collection_name)
        
        # Récupère quelques métadonnées utiles
        metadata = {
            'size_bytes': stats.get('size', 0),
            'avg_doc_size': stats.get('avgObjSize', 0),
            'storage_size': stats.get('storageSize', 0),
            'total_indexes': stats.get('nindexes', 0),
            'index_sizes': stats.get('indexSizes', {})
        }
        
        return {
            'collection_name': collection_name,
            'document_count': document_count,
            'metadata': metadata,
            'timestamp': datetime.now()
        }
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des stats MongoDB pour {collection_name}: {e}")
        return None


def insert_stats_to_postgres(conn, stats: Dict[str, Any]) -> bool:
    """
    Insère les statistiques dans PostgreSQL.
    
    Args:
        conn: Connexion PostgreSQL
        stats: Statistiques à insérer
        
    Returns:
        True si l'insertion réussit, False sinon
    """
    try:
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO mongodb_stats (
            timestamp,
            collection_name,
            document_count,
            insert_count,
            insert_duration_ms,
            metadata
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        )
        """
        
        cursor.execute(insert_query, (
            stats['timestamp'],
            stats['collection_name'],
            stats['document_count'],
            None,  # insert_count (pour les futures insertions trackées)
            None,  # insert_duration_ms
            json.dumps(stats['metadata'])
        ))
        
        conn.commit()
        cursor.close()
        
        print(f"✅ Stats insérées pour {stats['collection_name']}: {stats['document_count']} documents")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion dans PostgreSQL: {e}")
        conn.rollback()
        return False


def collect_and_store_stats(continuous: bool = False, interval: int = 300):
    """
    Collecte les statistiques MongoDB et les stocke dans PostgreSQL.
    
    Args:
        continuous: Si True, exécution en boucle continue
        interval: Intervalle en secondes entre deux collectes (mode continu)
    """
    print("🚀 Démarrage de la collecte des statistiques MongoDB...")
    print(f"📊 Mode: {'Continu' if continuous else 'Unique'}")
    if continuous:
        print(f"⏱️  Intervalle: {interval} secondes")
    print("=" * 60)
    
    # Connexion MongoDB
    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_client.admin.command('ping')
        print("✅ Connexion MongoDB établie")
    except Exception as e:
        print(f"❌ Erreur de connexion MongoDB: {e}")
        return
    
    # Connexion PostgreSQL
    try:
        pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        print("✅ Connexion PostgreSQL établie")
    except Exception as e:
        print(f"❌ Erreur de connexion PostgreSQL: {e}")
        mongo_client.close()
        return
    
    # Collections à surveiller
    collections_to_monitor = ['polymarket', 'cleaned']
    
    try:
        iteration = 0
        while True:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"📈 Collecte #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            for collection_name in collections_to_monitor:
                print(f"\n🔍 Collection: {collection_name}")
                
                # Récupère les statistiques
                stats = get_mongodb_stats(mongo_client, MONGO_DB, collection_name)
                
                if stats:
                    # Affiche les statistiques
                    print(f"   📊 Documents: {stats['document_count']:,}")
                    print(f"   💾 Taille: {stats['metadata']['size_bytes'] / 1024 / 1024:.2f} MB")
                    print(f"   📏 Taille moyenne doc: {stats['metadata']['avg_doc_size']:,} bytes")
                    
                    # Insère dans PostgreSQL
                    insert_stats_to_postgres(pg_conn, stats)
                else:
                    print(f"   ⚠️  Impossible de récupérer les stats")
            
            # Sort de la boucle si mode unique
            if not continuous:
                print("\n✅ Collecte unique terminée avec succès")
                break
            
            # Attend avant la prochaine collecte
            print(f"\n⏳ Prochaine collecte dans {interval} secondes...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
    finally:
        # Fermeture des connexions
        pg_conn.close()
        mongo_client.close()
        print("\n👋 Connexions fermées. Au revoir!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Collecte des statistiques MongoDB vers PostgreSQL')
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Exécution en mode continu (boucle infinie)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Intervalle en secondes entre deux collectes (mode continu, défaut: 300)'
    )
    
    args = parser.parse_args()
    
    # Vérification des variables d'environnement
    if not MONGO_URI:
        print("❌ ERREUR: Variable MONGO_URI non définie dans .env")
        sys.exit(1)
    
    # Lance la collecte
    collect_and_store_stats(continuous=args.continuous, interval=args.interval)
