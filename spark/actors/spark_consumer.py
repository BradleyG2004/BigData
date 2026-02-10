"""
Spark Streaming Consumer - Kafka to PostgreSQL
Consomme depuis Kafka, nettoie les données et écrit directement dans PostgreSQL
Remplace CleaningPolymarket.py + mongo_to_postgres.py en un seul pipeline streaming
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when, lit, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, ArrayType, BooleanType
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'polymarket-events')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5433')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'polymarket')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'polymarket')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'polymarket123')


def create_spark_session():
    """
    Crée une session Spark avec les dépendances PostgreSQL
    """
    print("\n🔄 Création de la session Spark...")
    
    spark = SparkSession.builder \
        .appName("PolymarketKafkaToPostgres") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                "org.postgresql:postgresql:42.7.1") \
        .config("spark.sql.streaming.checkpointLocation", "/opt/spark-data/checkpoint") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    print("✅ Session Spark créée avec succès!")
    
    return spark


def get_polymarket_schema():
    """
    Schéma complet des données Polymarket depuis l'API
    """
    return StructType([
        StructField("id", StringType(), True),
        StructField("conditionId", StringType(), True),
        StructField("questionID", StringType(), True),
        StructField("slug", StringType(), True),
        StructField("title", StringType(), True),
        StructField("description", StringType(), True),
        StructField("question", StringType(), True),
        StructField("category", StringType(), True),
        StructField("seriesSlug", StringType(), True),
        StructField("resolutionSource", StringType(), True),
        StructField("image", StringType(), True),
        StructField("icon", StringType(), True),
        StructField("resolutionTitle", StringType(), True),
        StructField("questionType", StringType(), True),
        StructField("outcomes", StringType(), True),  # JSON array as string
        StructField("outcomePrices", StringType(), True),  # JSON array as string
        StructField("volume", DoubleType(), True),
        StructField("volumeNum", DoubleType(), True),
        StructField("startDate", StringType(), True),
        StructField("endDate", StringType(), True),
        StructField("gameStartDatetime", StringType(), True),
        StructField("secondsDelay", IntegerType(), True),
        StructField("secondsSinceStart", IntegerType(), True),
        # Champs à exclure
        StructField("liquidity", DoubleType(), True),
        StructField("archived", BooleanType(), True),
        StructField("new", BooleanType(), True),
        StructField("featured", BooleanType(), True),
        StructField("restricted", BooleanType(), True),
        StructField("closed", BooleanType(), True),
        StructField("active", BooleanType(), True),
    ])

def get_fields_to_remove():
    """
    Liste des champs à supprimer lors du nettoyage
    (même logique que CleaningPolymarket.py)
    """
    return [
        'liquidity', 'archived', 'new', 'featured', 'restricted',
        'sortBy', 'competitive', 'volume24hr', 'volume1wk', 'volume1mo',
        'volume1yr', 'liquidityAmm', 'LiquidityAmm', 'liquidityClob',
        'cyom', 'showAllOutcomes', 'openInterest', 'markets', 'series',
        'tags', 'enableNegRisk', 'negRiskAugmented', 'pendingDeployment',
        'deploying', 'requiresTranslation', 'commentsEnabled',
        'subcategory', 'closed', 'active', 'showMarketImages'
    ]


def read_from_kafka(spark):
    """
    Lit les données en streaming depuis Kafka
    """
    print("\n📨 Connexion à Kafka pour le streaming...")
    print(f"   - Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"   - Topic: {KAFKA_TOPIC}")
    
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()
    
    print("✅ Connexion Kafka établie!")
    return df


def clean_and_filter_stream(df):
    """
    Nettoie et filtre les données du stream Kafka
    Prépare les données pour PostgreSQL (même logique que mongo_to_postgres.py)
    """
    print("\n⚙️ Configuration du pipeline de nettoyage...")
    
    # Parse le JSON depuis Kafka
    schema = get_polymarket_schema()
    
    parsed_df = df \
        .selectExpr("CAST(value AS STRING) as json") \
        .select(from_json(col("json"), schema).alias("data")) \
        .select("data.*")
    
    # Filtrage: image, icon, seriesSlug et resolutionSource doivent exister et ne pas être vides
    print("   🔍 Filtrage: image, icon, seriesSlug, resolutionSource doivent exister")
    filtered_df = parsed_df.filter(
        (col("image").isNotNull()) & (col("image") != "") &
        (col("icon").isNotNull()) & (col("icon") != "") &
        (col("seriesSlug").isNotNull()) & (col("seriesSlug") != "") &
        (col("resolutionSource").isNotNull()) & (col("resolutionSource") != "")
    )
    
    # Suppression des champs indésirables et transformation pour PostgreSQL
    fields_to_remove = get_fields_to_remove()
    print(f"   🧹 Suppression de {len(fields_to_remove)} champs indésirables")
    
    # Sélectionner et renommer les colonnes selon le schéma PostgreSQL
    cleaned_df = filtered_df.select(
        col("id").alias("mongo_id"),  # Utiliser 'id' comme mongo_id
        col("conditionId").alias("condition_id"),
        col("questionID").alias("question_id"),
        col("slug"),
        col("title"),
        col("description"),
        col("question"),
        col("category"),
        col("seriesSlug").alias("series_slug"),
        col("resolutionSource").alias("resolution_source"),
        col("image"),
        col("icon"),
        col("resolutionTitle").alias("resolution_title"),
        col("questionType").alias("question_type"),
        col("outcomes"),  # Garder en JSON
        col("outcomePrices").alias("outcome_prices"),  # Garder en JSON
        col("volume"),
        col("volumeNum").alias("volume_num"),
        to_timestamp(col("startDate")).alias("start_date"),
        to_timestamp(col("endDate")).alias("end_date"),
        to_timestamp(col("gameStartDatetime")).alias("game_start_datetime"),
        col("secondsDelay").alias("seconds_delay"),
        col("secondsSinceStart").alias("seconds_since_start")
    )
    
    print("✅ Pipeline de nettoyage configuré!")
    print("   📊 Prêt pour insertion PostgreSQL")
    return cleaned_df


def write_to_console(df, query_name="console_output"):
    """
    Écrit les résultats dans la console (pour le debug)
    """
    query = df \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .queryName(query_name) \
        .start()
    
    return query


def write_to_postgresql(df):
    """
    Écrit les données nettoyées directement dans PostgreSQL 'polymarket_cleaned'
    Utilise UPSERT (ON CONFLICT DO UPDATE) pour éviter les doublons sur mongo_id
    Même logique que consumer.py pour MongoDB (ReplaceOne avec upsert=True)
    """
    jdbc_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    def write_batch_to_postgres(batch_df, batch_id):
        if batch_df.count() == 0:
            print(f"   ⚠️  Batch {batch_id}: aucune donnée à insérer")
            return
        
        try:
            import psycopg2
            from psycopg2.extras import execute_values
            
            # Convertir Spark DataFrame en liste de tuples
            rows = batch_df.collect()
            
            # Connexion PostgreSQL
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=int(POSTGRES_PORT),
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            cursor = conn.cursor()
            
            # Préparer les données pour insertion
            data = []
            for row in rows:
                data.append((
                    row.mongo_id,
                    row.condition_id,
                    row.question_id,
                    row.slug,
                    row.title,
                    row.description,
                    row.question,
                    row.category,
                    row.series_slug,
                    row.resolution_source,
                    row.image,
                    row.icon,
                    row.resolution_title,
                    row.question_type,
                    row.outcomes,
                    row.outcome_prices,
                    row.volume,
                    row.volume_num,
                    row.start_date,
                    row.end_date,
                    row.game_start_datetime,
                    row.seconds_delay,
                    row.seconds_since_start
                ))
            
            # UPSERT: INSERT ... ON CONFLICT DO UPDATE (même logique que MongoDB ReplaceOne)
            upsert_query = """
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
            
            execute_values(cursor, upsert_query, data, page_size=100)
            conn.commit()
            
            inserted_count = len(data)
            cursor.close()
            conn.close()
            
            print(f"   ✓ Batch {batch_id}: {inserted_count} documents traités (insérés/mis à jour)")
            
        except Exception as e:
            print(f"   ❌ Batch {batch_id} erreur: {e}")
            import traceback
            traceback.print_exc()
    
    query = df \
        .writeStream \
        .foreachBatch(write_batch_to_postgres) \
        .queryName("postgres_polymarket_writer") \
        .option("checkpointLocation", "/opt/spark-data/checkpoint/postgres") \
        .start()
    
    return query


def main():
    """
    Fonction principale - Streaming Kafka → Nettoyage → PostgreSQL
    Remplace CleaningPolymarket.py + mongo_to_postgres.py en un seul pipeline
    """
    print("=" * 70)
    print("    Polymarket Spark Consumer - Kafka → Cleaning → PostgreSQL")
    print("    Remplace CleaningPolymarket.py + mongo_to_postgres.py")
    print("=" * 70)
    
    print(f"\n📊 Configuration:")
    print(f"   - Kafka Topic: {KAFKA_TOPIC}")
    print(f"   - PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    print(f"   - Table: polymarket_cleaned")
    
    # Créer la session Spark
    spark = create_spark_session()
    
    try:
        # Lire depuis Kafka
        kafka_df = read_from_kafka(spark)
        
        # Nettoyer et filtrer les données
        cleaned_df = clean_and_filter_stream(kafka_df)
        
        # Écrire dans PostgreSQL
        print("\n💾 Démarrage de l'écriture dans PostgreSQL...")
        postgres_query = write_to_postgresql(cleaned_df)
        
        # Optionnel: afficher dans la console pour debug
        # console_query = write_to_console(cleaned_df, "cleaned_events")
        
        print("\n✅ Pipeline Spark démarré!")
        print("   📊 Spark UI: http://localhost:8080")
        print("   🔄 Traitement: Kafka → Filtrage → Nettoyage → PostgreSQL")
        print("   🛑 Appuyez sur Ctrl+C pour arrêter\n")
        
        # Attendre l'arrêt
        postgres_query.awaitTermination()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Arrêt demandé par l'utilisateur...")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🛑 Arrêt de Spark...")
        spark.stop()
        print("✅ Spark arrêté proprement!")
        print("\n💡 CleaningPolymarket.py et mongo_to_postgres.py ne sont plus nécessaires!")


if __name__ == "__main__":
    main()
