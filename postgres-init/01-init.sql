-- ================================
-- 📊 Tables de monitoring
-- ================================

-- Table pour tracker les exécutions du pipeline
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,  -- 'producer', 'consumer', 'spark'
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL,    -- 'running', 'success', 'failed'
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB
);

-- Table pour tracker les messages Kafka
CREATE TABLE IF NOT EXISTS kafka_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    topic VARCHAR(100) NOT NULL,
    partition INTEGER,
    offset BIGINT,
    messages_count INTEGER,
    lag BIGINT,
    consumer_group VARCHAR(100)
);

-- Table pour les erreurs
CREATE TABLE IF NOT EXISTS error_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    source VARCHAR(50) NOT NULL,    -- 'producer', 'consumer', 'spark'
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    context JSONB
);

-- Table pour les statistiques MongoDB
CREATE TABLE IF NOT EXISTS mongodb_stats (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    collection_name VARCHAR(100),
    document_count BIGINT,
    insert_count INTEGER,
    insert_duration_ms INTEGER,
    metadata JSONB
);

-- Index pour améliorer les performances
CREATE INDEX idx_pipeline_runs_type_time ON pipeline_runs(run_type, start_time DESC);
CREATE INDEX idx_kafka_metrics_topic_time ON kafka_metrics(topic, timestamp DESC);
CREATE INDEX idx_error_logs_source_time ON error_logs(source, timestamp DESC);
CREATE INDEX idx_mongodb_stats_time ON mongodb_stats(timestamp DESC);

-- Vue pour avoir un résumé des exécutions
CREATE OR REPLACE VIEW pipeline_summary AS
SELECT 
    run_type,
    status,
    COUNT(*) as total_runs,
    SUM(records_processed) as total_records,
    AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration_seconds,
    MAX(start_time) as last_run
FROM pipeline_runs
WHERE end_time IS NOT NULL
GROUP BY run_type, status
ORDER BY run_type, status;

-- Afficher les tables créées
\dt
