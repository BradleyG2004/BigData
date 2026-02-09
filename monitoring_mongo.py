"""
Module de monitoring MongoDB
Stocke les métriques dans MongoDB Atlas
"""

import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

# Configuration MongoDB
MONGO_URI = os.getenv('MONGO_URI')
MONITORING_DB = os.getenv('MONITORING_DB', 'polymarket_monitoring')
MONITORING_COLLECTION = os.getenv('MONITORING_COLLECTION', 'pipeline_metrics')


class MongoMonitoringService:
    """Service de monitoring avec MongoDB Atlas"""
    
    def __init__(self, enabled=True):
        """
        Initialise le service de monitoring
        
        Args:
            enabled (bool): Active/désactive le monitoring
        """
        self.enabled = enabled
        self.client = None
        self.db = None
        self.collection = None
        
        if self.enabled and MONGO_URI:
            self._connect()
        else:
            print("⚠️ Monitoring désactivé ou MONGO_URI non configuré")
            self.enabled = False
    
    def _connect(self):
        """Établit la connexion à MongoDB"""
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[MONITORING_DB]
            self.collection = self.db[MONITORING_COLLECTION]
            print(f"✅ Monitoring MongoDB connecté ({MONITORING_DB}.{MONITORING_COLLECTION})")
        except Exception as e:
            print(f"⚠️ Monitoring MongoDB non disponible: {e}")
            self.enabled = False
    
    def log_pipeline_start(self, run_type, metadata=None):
        """
        Enregistre le début d'une exécution
        
        Args:
            run_type (str): 'producer', 'consumer', ou 'spark'
            metadata (dict): Métadonnées additionnelles
        
        Returns:
            str: ID du run créé (ObjectId MongoDB)
        """
        if not self.enabled:
            return None
        
        try:
            doc = {
                'run_type': run_type,
                'start_time': datetime.utcnow(),
                'end_time': None,
                'status': 'running',
                'records_processed': 0,
                'error_message': None,
                'metadata': metadata or {}
            }
            
            result = self.collection.insert_one(doc)
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"⚠️ Erreur log_pipeline_start: {e}")
            return None
    
    def log_pipeline_end(self, run_id, status, records_processed=0, error_message=None):
        """
        Enregistre la fin d'une exécution
        
        Args:
            run_id (str): ID du run (ObjectId string)
            status (str): 'success' ou 'failed'
            records_processed (int): Nombre d'enregistrements traités
            error_message (str): Message d'erreur si échec
        """
        if not self.enabled or run_id is None:
            return
        
        try:
            from bson.objectid import ObjectId
            
            self.collection.update_one(
                {'_id': ObjectId(run_id)},
                {
                    '$set': {
                        'end_time': datetime.utcnow(),
                        'status': status,
                        'records_processed': records_processed,
                        'error_message': error_message
                    }
                }
            )
        except Exception as e:
            print(f"⚠️ Erreur log_pipeline_end: {e}")
    
    def log_kafka_metrics(self, topic, partition=None, offset=None, 
                         messages_count=0, lag=None, consumer_group=None):
        """
        Enregistre des métriques Kafka
        
        Args:
            topic (str): Nom du topic
            partition (int): Numéro de partition
            offset (int): Offset actuel
            messages_count (int): Nombre de messages traités
            lag (int): Lag du consumer
            consumer_group (str): Groupe de consumers
        """
        if not self.enabled:
            return
        
        try:
            metrics_collection = self.db['kafka_metrics']
            
            doc = {
                'timestamp': datetime.utcnow(),
                'topic': topic,
                'partition': partition,
                'offset': offset,
                'messages_count': messages_count,
                'lag': lag,
                'consumer_group': consumer_group
            }
            
            metrics_collection.insert_one(doc)
            
        except Exception as e:
            print(f"⚠️ Erreur log_kafka_metrics: {e}")
    
    def log_batch_insert(self, collection_name, count, duration_ms):
        """
        Enregistre une insertion batch dans MongoDB
        
        Args:
            collection_name (str): Nom de la collection
            count (int): Nombre de documents insérés
            duration_ms (int): Durée en millisecondes
        """
        if not self.enabled:
            return
        
        try:
            batch_collection = self.db['batch_inserts']
            
            doc = {
                'timestamp': datetime.utcnow(),
                'collection': collection_name,
                'count': count,
                'duration_ms': duration_ms
            }
            
            batch_collection.insert_one(doc)
            
        except Exception as e:
            print(f"⚠️ Erreur log_batch_insert: {e}")
    
    def log_error(self, source, error_type, error_message, stack_trace=None, context=None):
        """
        Enregistre une erreur
        
        Args:
            source (str): 'producer', 'consumer', ou 'spark'
            error_type (str): Type d'erreur
            error_message (str): Message d'erreur
            stack_trace (str): Stack trace complète
            context (dict): Contexte additionnel
        """
        if not self.enabled:
            return
        
        try:
            errors_collection = self.db['error_logs']
            
            doc = {
                'timestamp': datetime.utcnow(),
                'source': source,
                'error_type': error_type,
                'error_message': error_message,
                'stack_trace': stack_trace,
                'context': context or {}
            }
            
            errors_collection.insert_one(doc)
            
        except Exception as e:
            print(f"⚠️ Erreur log_error: {e}")
    
    def get_pipeline_summary(self, hours=24):
        """
        Obtient un résumé des exécutions récentes
        
        Args:
            hours (int): Nombre d'heures à inclure
            
        Returns:
            dict: Statistiques des pipelines
        """
        if not self.enabled:
            return {}
        
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            pipeline = [
                {'$match': {'start_time': {'$gte': cutoff_time}}},
                {
                    '$group': {
                        '_id': {'run_type': '$run_type', 'status': '$status'},
                        'count': {'$sum': 1},
                        'total_records': {'$sum': '$records_processed'},
                        'avg_duration': {
                            '$avg': {
                                '$subtract': ['$end_time', '$start_time']
                            }
                        }
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            return results
            
        except Exception as e:
            print(f"⚠️ Erreur get_pipeline_summary: {e}")
            return {}
    
    def close(self):
        """Ferme la connexion MongoDB"""
        if self.client:
            self.client.close()


# Instance globale (singleton)
_monitoring_service = None


def get_monitoring_service():
    """
    Retourne l'instance du service de monitoring (singleton)
    """
    global _monitoring_service
    if _monitoring_service is None:
        # Active par défaut, désactive avec ENABLE_MONITORING=false
        enabled = os.getenv('ENABLE_MONITORING', 'true').lower() == 'true'
        _monitoring_service = MongoMonitoringService(enabled=enabled)
    return _monitoring_service
