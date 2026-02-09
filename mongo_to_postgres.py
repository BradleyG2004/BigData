"""
Script pour transférer les données nettoyées de MongoDB vers PostgreSQL
Lit la collection 'cleaned' dans MongoDB et insère dans la table 'polymarket_cleaned' dans PostgreSQL
"""

import os
import sys
import json
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ================================
# Configuration MongoDB
# ================================
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('DB2', 'polymarket_db')
MONGO_COLLECTION = 'cleaned'

# ================================
# Configuration PostgreSQL
# ================================
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5433'))
POSTGRES_USER = os.getenv('POSTGRES_USER', 'polymarket')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'polymarket123')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'polymarket_db')

# Taille des batchs pour l'insertion
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))


def connect_mongodb():
    """Connexion à MongoDB Atlas"""
    try:
        if not MONGO_URI:
            print("❌ Erreur: MONGO_URI non trouvé dans .env")
            return None
        
        print("🔄 Connexion à MongoDB Atlas...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ Connecté à MongoDB Atlas!")
        
        return client
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ Erreur de connexion MongoDB: {e}")
        return None
    except Exception as e:
        print(f"❌ Erreur inattendue MongoDB: {e}")
        return None


def connect_postgresql():
    """Connexion à PostgreSQL"""
    try:
        print(f"\n🔄 Connexion à PostgreSQL ({POSTGRES_HOST}:{POSTGRES_PORT})...")
        
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB
        )
        
        print("✅ Connecté à PostgreSQL!")
        return conn
        
    except psycopg2.Error as e:
        print(f"❌ Erreur de connexion PostgreSQL: {e}")
        return None
    except Exception as e:
        print(f"❌ Erreur inattendue PostgreSQL: {e}")
        return None


def parse_datetime(value):
    """Parse une date string en datetime object"""
    if not value:
        return None
    
    try:
        # Si c'est déjà un datetime
        if isinstance(value, datetime):
            return value
        
        # Si c'est un timestamp Unix
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        
        # Si c'est une string ISO
        if isinstance(value, str):
            # Essayer plusieurs formats
            for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d']:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        
        return None
        
    except Exception as e:
        print(f"⚠️ Erreur parsing date '{value}': {e}")
        return None


def transform_document(doc):
    """
    Transforme un document MongoDB en tuple pour PostgreSQL
    Extrait et formate les champs nécessaires
    """
    try:
        # Convertir ObjectId en string
        mongo_id = str(doc.get('_id', ''))
        
        # Extraire les champs
        condition_id = doc.get('conditionId') or doc.get('condition_id')
        question_id = doc.get('questionID') or doc.get('question_id')
        slug = doc.get('slug')
        title = doc.get('title', '')
        description = doc.get('description', '')
        question = doc.get('question', '')
        
        category = doc.get('category')
        series_slug = doc.get('seriesSlug')
        resolution_source = doc.get('resolutionSource')
        
        image = doc.get('image')
        icon = doc.get('icon')
        
        resolution_title = doc.get('resolutionTitle')
        question_type = doc.get('questionType')
        
        # Traiter les outcomes et prices (garder en JSON)
        outcomes = json.dumps(doc.get('outcomes', [])) if doc.get('outcomes') else None
        outcome_prices = json.dumps(doc.get('outcomePrices', [])) if doc.get('outcomePrices') else None
        
        # Volumes
        volume = doc.get('volume')
        volume_num = doc.get('volumeNum')
        
        # Dates
        start_date = parse_datetime(doc.get('startDate'))
        end_date = parse_datetime(doc.get('endDate'))
        game_start = parse_datetime(doc.get('gameStartDatetime'))
        
        # Autres champs numériques
        seconds_delay = doc.get('secondsDelay')
        seconds_since_start = doc.get('secondsSinceStart')
        
        return (
            mongo_id,
            condition_id,
            question_id,
            slug,
            title,
            description,
            question,
            category,
            series_slug,
            resolution_source,
            image,
            icon,
            resolution_title,
            question_type,
            outcomes,
            outcome_prices,
            volume,
            volume_num,
            start_date,
            end_date,
            game_start,
            seconds_delay,
            seconds_since_start
        )
        
    except Exception as e:
        print(f"⚠️ Erreur transformation document {doc.get('_id')}: {e}")
        return None


def clear_postgres_table(conn):
    """Vider la table PostgreSQL avant insertion"""
    try:
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE polymarket_cleaned RESTART IDENTITY CASCADE;")
        conn.commit()
        cursor.close()
        print("✅ Table PostgreSQL vidée")
        return True
    except Exception as e:
        print(f"❌ Erreur vidage table: {e}")
        conn.rollback()
        return False


def insert_batch_to_postgres(conn, batch):
    """Insère un batch de documents dans PostgreSQL"""
    try:
        cursor = conn.cursor()
        
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
        
        execute_values(cursor, insert_query, batch, page_size=100)
        conn.commit()
        cursor.close()
        
        return len(batch)
        
    except Exception as e:
        print(f"❌ Erreur insertion batch: {e}")
        conn.rollback()
        return 0


def transfer_data():
    """
    Fonction principale: Transfère les données de MongoDB vers PostgreSQL
    """
    print("=" * 60)
    print("  🔄 Transfert MongoDB → PostgreSQL")
    print("=" * 60)
    
    # Connexions
    mongo_client = connect_mongodb()
    if not mongo_client:
        print("\n❌ Impossible de se connecter à MongoDB")
        return False
    
    pg_conn = connect_postgresql()
    if not pg_conn:
        print("\n❌ Impossible de se connecter à PostgreSQL")
        mongo_client.close()
        return False
    
    try:
        # Accéder à la collection MongoDB
        db = mongo_client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION]
        
        total_docs = collection.count_documents({})
        print(f"\n📊 Total documents dans '{MONGO_COLLECTION}': {total_docs}")
        
        if total_docs == 0:
            print("⚠️ Aucun document à transférer")
            return True
        
        # Demander confirmation pour vider la table
        print(f"\n🗑️ Voulez-vous vider la table PostgreSQL avant insertion? (y/n): ", end='')
        choice = input().lower() if sys.stdin.isatty() else 'y'
        
        if choice == 'y':
            if not clear_postgres_table(pg_conn):
                return False
        
        # Transférer les données par batch
        print(f"\n📦 Début du transfert (batch size: {BATCH_SIZE})...")
        
        batch = []
        total_inserted = 0
        total_errors = 0
        
        for idx, doc in enumerate(collection.find({}), start=1):
            transformed = transform_document(doc)
            
            if transformed:
                batch.append(transformed)
            else:
                total_errors += 1
            
            # Insérer le batch quand il est plein
            if len(batch) >= BATCH_SIZE:
                inserted = insert_batch_to_postgres(pg_conn, batch)
                total_inserted += inserted
                print(f"   ✓ Batch {total_inserted//BATCH_SIZE}: {total_inserted}/{total_docs} documents insérés")
                batch = []
        
        # Insérer le dernier batch
        if batch:
            inserted = insert_batch_to_postgres(pg_conn, batch)
            total_inserted += inserted
            print(f"   ✓ Dernier batch: {total_inserted}/{total_docs} documents insérés")
        
        print(f"\n✅ Transfert terminé!")
        print(f"\n📊 Résumé:")
        print(f"   - Documents source (MongoDB): {total_docs}")
        print(f"   - Documents insérés (PostgreSQL): {total_inserted}")
        print(f"   - Erreurs de transformation: {total_errors}")
        
        # Vérifier l'insertion dans PostgreSQL
        cursor = pg_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM polymarket_cleaned;")
        pg_count = cursor.fetchone()[0]
        cursor.close()
        
        print(f"   - Documents dans PostgreSQL: {pg_count}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur lors du transfert: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Fermer les connexions
        if pg_conn:
            pg_conn.close()
            print("\n✅ Connexion PostgreSQL fermée")
        
        if mongo_client:
            mongo_client.close()
            print("✅ Connexion MongoDB fermée")


def main():
    """Point d'entrée principal"""
    success = transfer_data()
    
    print("=" * 60)
    
    if success:
        print("✅ Script terminé avec succès!")
        sys.exit(0)
    else:
        print("❌ Script terminé avec des erreurs")
        sys.exit(1)


if __name__ == "__main__":
    main()

