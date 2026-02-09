"""
Script rapide pour vérifier le contenu des collections MongoDB
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB2', 'polymarket')

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ Connexion MongoDB établie")
    
    db = client[DB_NAME]
    
    # Vérifier collection polymarket (raw)
    raw_count = db['polymarket'].count_documents({})
    print(f"\n📊 Collection 'polymarket' (raw): {raw_count} documents")
    
    if raw_count > 0:
        sample = db['polymarket'].find_one()
        print(f"   Exemple de champs: {list(sample.keys())[:10]}")
    
    # Vérifier collection cleaned
    cleaned_count = db['cleaned'].count_documents({})
    print(f"📊 Collection 'cleaned': {cleaned_count} documents")
    
    if cleaned_count > 0:
        sample = db['cleaned'].find_one()
        print(f"   Exemple de champs: {list(sample.keys())[:10]}")
    
    # Lister toutes les collections
    print(f"\n📚 Collections dans la base '{DB_NAME}':")
    for name in db.list_collection_names():
        count = db[name].count_documents({})
        print(f"   - {name}: {count} documents")
    
    client.close()
    
except Exception as e:
    print(f"❌ Erreur: {e}")
