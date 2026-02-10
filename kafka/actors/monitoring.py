"""
Module de monitoring pour les scripts Kafka
Fournit un service de monitoring léger pour les producer et consumer
"""

import os
from datetime import datetime


class MonitoringService:
    """Service de monitoring simple pour les scripts Kafka"""
    
    def __init__(self):
        self.enabled = os.getenv('MONITORING_ENABLED', 'false').lower() == 'true'
    
    def log_pipeline_start(self, run_type, metadata=None):
        """
        Log le démarrage d'un pipeline
        
        Args:
            run_type: Type de run ('producer', 'consumer', etc.)
            metadata: Métadonnées supplémentaires
            
        Returns:
            run_id: ID unique du run
        """
        run_id = f"{run_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.enabled:
            print(f"📊 [MONITORING] Pipeline start: {run_id}")
            if metadata:
                print(f"   Metadata: {metadata}")
        
        return run_id
    
    def log_pipeline_end(self, run_id, status, records_count=0, error_message=None):
        """
        Log la fin d'un pipeline
        
        Args:
            run_id: ID du run
            status: Status final ('success', 'failed')
            records_count: Nombre d'enregistrements traités
            error_message: Message d'erreur si échec
        """
        if self.enabled:
            print(f"📊 [MONITORING] Pipeline end: {run_id}")
            print(f"   Status: {status}")
            print(f"   Records: {records_count}")
            if error_message:
                print(f"   Error: {error_message}")
    
    def log_kafka_metrics(self, topic, partition, offset, messages_count, consumer_group=None):
        """
        Log les métriques Kafka
        
        Args:
            topic: Nom du topic
            partition: Numéro de partition
            offset: Offset actuel
            messages_count: Nombre de messages
            consumer_group: Groupe de consommateurs
        """
        if self.enabled:
            print(f"📊 [MONITORING] Kafka metrics:")
            print(f"   Topic: {topic}, Partition: {partition}, Offset: {offset}")
            print(f"   Messages: {messages_count}")
            if consumer_group:
                print(f"   Consumer group: {consumer_group}")
    
    def log_mongodb_stats(self, collection_name, document_count, insert_count=None, insert_duration_ms=None):
        """
        Log les statistiques MongoDB
        
        Args:
            collection_name: Nom de la collection
            document_count: Nombre total de documents
            insert_count: Nombre de documents insérés
            insert_duration_ms: Durée d'insertion en ms
        """
        if self.enabled:
            print(f"📊 [MONITORING] MongoDB stats:")
            print(f"   Collection: {collection_name}")
            print(f"   Total documents: {document_count}")
            if insert_count:
                print(f"   Inserted: {insert_count}")
            if insert_duration_ms:
                print(f"   Duration: {insert_duration_ms}ms")
    
    def log_error(self, source, error_type, error_message, stack_trace=None):
        """
        Log une erreur
        
        Args:
            source: Source de l'erreur
            error_type: Type d'erreur
            error_message: Message d'erreur
            stack_trace: Stack trace complète
        """
        print(f"❌ [ERROR] {source} - {error_type}")
        print(f"   {error_message}")
        if stack_trace and self.enabled:
            print(f"   Stack trace:\n{stack_trace}")


# Instance globale du service de monitoring
_monitoring_service = None


def get_monitoring_service():
    """
    Retourne l'instance unique du service de monitoring
    
    Returns:
        MonitoringService instance
    """
    global _monitoring_service
    
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    
    return _monitoring_service
