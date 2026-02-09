-- ================================
-- 📊 Schema pour les données Polymarket nettoyées
-- ================================

-- Table principale pour stocker les données nettoyées de Polymarket
CREATE TABLE IF NOT EXISTS polymarket_cleaned (
    id SERIAL PRIMARY KEY,
    
    -- Identifiants uniques
    mongo_id VARCHAR(50) UNIQUE NOT NULL,  -- _id de MongoDB
    condition_id VARCHAR(100) UNIQUE,
    question_id VARCHAR(100),
    
    -- Informations de base
    slug VARCHAR(255),
    title TEXT NOT NULL,
    description TEXT,
    question TEXT,
    
    -- Catégorisation
    category VARCHAR(100),
    series_slug VARCHAR(255),
    resolution_source VARCHAR(255),
    
    -- Images et icônes
    image TEXT,
    icon TEXT,
    
    -- Résolution
    resolution_title TEXT,
    question_type VARCHAR(50),
    outcomes JSONB,  -- Liste des résultats possibles
    outcome_prices JSONB,  -- Prix actuels des outcomes
    
    -- Statistiques
    volume NUMERIC(20, 2),
    volume_num NUMERIC(20, 4),
    
    -- Timestamps
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    game_start_datetime TIMESTAMP,
    seconds_delay INTEGER,
    
    -- Métadonnées
    seconds_since_start BIGINT,
    
    -- Tracking
    inserted_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index pour améliorer les performances des requêtes
CREATE INDEX IF NOT EXISTS idx_polymarket_mongo_id ON polymarket_cleaned(mongo_id);
CREATE INDEX IF NOT EXISTS idx_polymarket_condition_id ON polymarket_cleaned(condition_id);
CREATE INDEX IF NOT EXISTS idx_polymarket_slug ON polymarket_cleaned(slug);
CREATE INDEX IF NOT EXISTS idx_polymarket_category ON polymarket_cleaned(category);
CREATE INDEX IF NOT EXISTS idx_polymarket_series_slug ON polymarket_cleaned(series_slug);
CREATE INDEX IF NOT EXISTS idx_polymarket_end_date ON polymarket_cleaned(end_date);
CREATE INDEX IF NOT EXISTS idx_polymarket_inserted_at ON polymarket_cleaned(inserted_at DESC);

-- Index GIN pour recherche dans JSONB
CREATE INDEX IF NOT EXISTS idx_polymarket_outcomes ON polymarket_cleaned USING gin(outcomes);
CREATE INDEX IF NOT EXISTS idx_polymarket_outcome_prices ON polymarket_cleaned USING gin(outcome_prices);

-- Vue pour les statistiques par catégorie
CREATE OR REPLACE VIEW polymarket_stats_by_category AS
SELECT 
    category,
    COUNT(*) as total_events,
    AVG(volume_num) as avg_volume,
    SUM(volume_num) as total_volume,
    MIN(end_date) as earliest_end_date,
    MAX(end_date) as latest_end_date
FROM polymarket_cleaned
WHERE category IS NOT NULL
GROUP BY category
ORDER BY total_events DESC;

-- Vue pour les événements actifs
CREATE OR REPLACE VIEW polymarket_active_events AS
SELECT 
    id,
    mongo_id,
    title,
    category,
    series_slug,
    end_date,
    volume,
    outcomes,
    outcome_prices
FROM polymarket_cleaned
WHERE end_date > NOW()
ORDER BY end_date ASC;

-- Vue pour les événements les plus populaires
CREATE OR REPLACE VIEW polymarket_top_volume AS
SELECT 
    id,
    mongo_id,
    title,
    category,
    series_slug,
    volume,
    volume_num,
    end_date,
    inserted_at
FROM polymarket_cleaned
ORDER BY volume_num DESC
LIMIT 100;

-- Fonction pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour updated_at
DROP TRIGGER IF EXISTS update_polymarket_cleaned_updated_at ON polymarket_cleaned;
CREATE TRIGGER update_polymarket_cleaned_updated_at
    BEFORE UPDATE ON polymarket_cleaned
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Afficher les tables créées
\dt

-- Afficher les vues créées
\dv

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO polymarket;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO polymarket;

