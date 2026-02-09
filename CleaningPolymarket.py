import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables from parent directory
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(parent_dir, '.env')
load_dotenv(env_path)

def connect_mongodb():
    """Connect to MongoDB Atlas"""
    try:
        mongo_uri = os.getenv('MONGO_URI')
        
        if not mongo_uri:
            print("❌ Error: MONGO_URI not found in .env file")
            return None
        
        print("🔄 Connecting to MongoDB Atlas...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        
        return client
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ Connection error: {e}")
        return None
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return None

def clean_polymarket_data(client, db_name=None):
    """
    Clean Polymarket data:
    - Filter out documents where image or icon are empty strings or missing
    - Remove unwanted fields from documents
    """
    try:
        if db_name is None:
            db_name = os.getenv('DB2')
        
        db = client[db_name]
        source_collection = db['polymarket']
        target_collection = db['cleaned']
        
        print(f"\n📊 Starting data cleaning process...")
        print(f"   Source: {db_name}.polymarket")
        print(f"   Target: {db_name}.cleaned")
        
        # Count source documents
        total_docs = source_collection.count_documents({})
        print(f"\n📄 Total documents in source collection: {total_docs}")
        
        # Check if target collection exists
        existing_count = target_collection.count_documents({})
        if existing_count > 0:
            print(f"\n⚠️  Target collection already contains {existing_count} documents")
            choice = input("   Delete existing data in 'cleaned' collection? (y/n): ").lower()
            if choice == 'y':
                target_collection.delete_many({})
                print("   ✓ Existing data deleted")
            else:
                print("   ✓ Will append to existing data")
        
        # Fields to remove from documents
        fields_to_remove = [
            'liquidity',
            'archived',
            'new',
            'featured',
            'restricted',
            'sortBy',
            'competitive',
            'volume24hr',
            'volume1wk',
            'volume1mo',
            'volume1yr',
            'liquidityAmm',
            'LiquidityAmm',
            'liquidityClob',
            'cyom',
            'showAllOutcomes',
            'openInterest',
            'markets',
            'series',
            'tags',
            'enableNegRisk',
            'negRiskAugmented',
            'pendingDeployment',
            'deploying',
            'requiresTranslation',
            'commentsEnabled',
            'subcategory',
            'closed',
            'active',
            'showMarketImages'
        ]
        
        # Filter criteria: both image and icon must exist and not be empty strings
        filter_query = {
            'image': {'$exists': True, '$ne': ''},
            'icon': {'$exists': True, '$ne': ''},
            'seriesSlug': {'$exists': True, '$ne': ''},
            'resolutionSource': {'$exists': True, '$ne': ''}
        }
        
        print(f"\n🔍 Filtering documents...")
        print(f"   Criteria: image and icon must exist and not be empty")
        
        # Fetch filtered documents
        filtered_docs = list(source_collection.find(filter_query))
        filtered_count = len(filtered_docs)
        
        print(f"   ✓ Found {filtered_count} documents matching criteria")
        print(f"   ✗ Excluded {total_docs - filtered_count} documents")
        
        if filtered_count == 0:
            print("\n⚠️  No documents match the filtering criteria")
            return
        
        # Clean documents (remove unwanted fields)
        print(f"\n🧹 Cleaning documents...")
        print(f"   Removing fields: {', '.join(fields_to_remove)}")
        
        cleaned_docs = []
        for doc in filtered_docs:
            # Remove unwanted fields
            for field in fields_to_remove:
                doc.pop(field, None)
            cleaned_docs.append(doc)
        
        print(f"   ✓ Cleaned {len(cleaned_docs)} documents")
        
        # Insert cleaned documents into target collection
        print(f"\n💾 Inserting cleaned data into '{db_name}.cleaned'...")
        
        if cleaned_docs:
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(cleaned_docs), batch_size):
                batch = cleaned_docs[i:i + batch_size]
                result = target_collection.insert_many(batch)
                total_inserted += len(result.inserted_ids)
                print(f"   ✓ Inserted batch {i//batch_size + 1}: {total_inserted}/{len(cleaned_docs)} documents")
            
            print(f"\n✅ Successfully inserted {total_inserted} documents!")
            
            # Show statistics
            print(f"\n📊 Cleaning summary:")
            print(f"   - Source documents: {total_docs}")
            print(f"   - Filtered documents: {filtered_count}")
            print(f"   - Excluded documents: {total_docs - filtered_count}")
            print(f"   - Cleaned & inserted: {total_inserted}")
            print(f"   - Total in 'cleaned' collection: {target_collection.count_documents({})}")
            
            # Show sample of cleaned document
            sample = target_collection.find_one()
            if sample:
                print(f"\n📝 Sample cleaned document fields:")
                print(f"   {', '.join(list(sample.keys())[:10])}...")
        else:
            print("⚠️  No data to insert")
            
    except Exception as e:
        print(f"❌ Error during cleaning process: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function - Clean Polymarket data"""
    print("=" * 60)
    print("    Polymarket Data Cleaning Script")
    print("=" * 60)
    
    # Connect to MongoDB
    client = connect_mongodb()
    
    if not client:
        print("\n❌ Cannot proceed without MongoDB connection")
        sys.exit(1)
    
    # Clean the data
    clean_polymarket_data(client)
    
    # Close the connection
    client.close()
    print("\n✅ MongoDB connection closed")
    print("=" * 60)

if __name__ == "__main__":
    main()
