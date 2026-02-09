"""
Spark Streaming Consumer - Kafka to Processing
Consomme les messages depuis Kafka et effectue des traitements avec Spark
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, avg, sum as spark_sum
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, ArrayType
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'polymarket-events')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'monitoring')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'polymarket')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'polymarket123')


def create_spark_session():
    """
    Crée une session Spark avec les dépendances nécessaires
    """
    print("\n🔄 Création de la session Spark...")
    
    spark = SparkSession.builder \
        .appName("PolymarketSparkConsumer") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                "org.postgresql:postgresql:42.7.1") \
        .config("spark.sql.streaming.checkpointLocation", "/opt/spark-data/checkpoint") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    print("✅ Session Spark créée avec succès!")
    
    return spark


def get_schema():
    """
    Définit le schéma des données Polymarket
    Adapte selon la structure réelle de ton API
    """
    return StructType([
        StructField("id", StringType(), True),
        StructField("title", StringType(), True),
        StructField("category", StringType(), True),
        StructField("active", StringType(), True),
        StructField("closed", StringType(), True),
        StructField("volume", DoubleType(), True),
        StructField("liquidity", DoubleType(), True),
        # Ajoute d'autres champs selon ton API
    ])


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


def process_stream(df):
    """
    Traite les données du stream Kafka
    """
    print("\n⚙️ Configuration du traitement des données...")
    
    # Parse le JSON depuis Kafka
    schema = get_schema()
    
    parsed_df = df \
        .selectExpr("CAST(value AS STRING) as json") \
        .select(from_json(col("json"), schema).alias("data")) \
        .select("data.*")
    
    # Exemple de transformation: agrégations par catégorie
    aggregated_df = parsed_df \
        .groupBy("category") \
        .agg(
            count("*").alias("event_count"),
            avg("volume").alias("avg_volume"),
            spark_sum("volume").alias("total_volume")
        )
    
    print("✅ Pipeline de traitement configuré!")
    return parsed_df, aggregated_df


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


def write_to_postgres(df, table_name):
    """
    Écrit les résultats dans PostgreSQL
    Note: Pour le streaming, on utilise foreachBatch
    """
    jdbc_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    def write_batch_to_postgres(batch_df, batch_id):
        batch_df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", table_name) \
            .option("user", POSTGRES_USER) \
            .option("password", POSTGRES_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()
        
        print(f"   ✓ Batch {batch_id} écrit dans PostgreSQL ({batch_df.count()} lignes)")
    
    query = df \
        .writeStream \
        .foreachBatch(write_batch_to_postgres) \
        .queryName(f"postgres_{table_name}") \
        .start()
    
    return query


def main():
    """
    Fonction principale - Démarre le streaming Spark
    """
    print("=" * 60)
    print("    Polymarket Spark Streaming Consumer")
    print("=" * 60)
    
    # Créer la session Spark
    spark = create_spark_session()
    
    try:
        # Lire depuis Kafka
        kafka_df = read_from_kafka(spark)
        
        # Traiter les données
        parsed_df, aggregated_df = process_stream(kafka_df)
        
        # Afficher dans la console
        print("\n🖥️  Démarrage de l'affichage console...")
        console_query = write_to_console(parsed_df, "parsed_events")
        
        # Optionnel: écrire les agrégations dans PostgreSQL
        # Décommente pour activer
        # print("\n💾 Démarrage de l'écriture PostgreSQL...")
        # postgres_query = write_to_postgres(aggregated_df, "spark_aggregations")
        
        print("\n✅ Streaming démarré!")
        print("   📊 Spark UI: http://localhost:8080")
        print("   🛑 Appuyez sur Ctrl+C pour arrêter\n")
        
        # Attendre l'arrêt
        console_query.awaitTermination()
        
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


if __name__ == "__main__":
    main()
