# 📊 Grafana Integration - Visualisation et Comparaison des Données

## Vue d'ensemble

Grafana est intégré pour visualiser et comparer les données Polymarket **cleaned** (PostgreSQL) avec les données **raw/non-cleaned** (MongoDB). Cette solution permet une analyse visuelle approfondie de la qualité des données et des métriques.

## 🚀 Accès Grafana

- **URL**: http://localhost:3000
- **Username**: `admin` (configurable via `GRAFANA_ADMIN_USER`)
- **Password**: `admin` (configurable via `GRAFANA_ADMIN_PASSWORD`)

## 📊 Dashboards Disponibles

### 1. **Polymarket - Cleaned Data Analysis**
Dashboard focalisé sur les données nettoyées dans PostgreSQL:
- 📈 Total des données nettoyées
- 📊 Distribution par catégorie
- 🔝 Top événements par volume
- 📅 Timeline d'insertion des données
- 📊 Statistiques par catégorie

### 2. **Polymarket - Cleaned vs Raw Data Comparison** ⭐
Dashboard de comparaison entre données cleaned et raw:
- ✅ Comptage des enregistrements (Cleaned vs Raw)
- 🔍 Comparaison de la qualité des données
- 📊 Distribution des catégories
- 📅 Statut des événements (actifs/terminés)
- 📋 Vue détaillée avec indicateurs de qualité
- ⏰ Timeline d'insertion

## 🔌 Sources de Données Configurées

### PostgreSQL - Polymarket Cleaned
- **Type**: PostgreSQL
- **Database**: `polymarket_db`
- **Table**: `polymarket_cleaned`
- **Host**: `postgres-polymarket:5432`
- **User**: `polymarket`
- **Status**: ✅ Configuré automatiquement

### MongoDB - Polymarket Raw
- **Type**: MongoDB (via plugin)
- **Database**: `polymarket_db`
- **Collections**: `polymarket` (raw), `cleaned`
- **Connection**: Via `MONGO_URI`
- **Status**: ⚠️ Nécessite plugin MongoDB

## 📦 Installation et Démarrage

### 1. Démarrer le container Grafana

```powershell
# Démarrer Grafana avec Docker Compose
docker-compose up -d grafana

# Vérifier les logs
docker-compose logs -f grafana

# Vérifier le statut
docker-compose ps grafana
```

### 2. Première connexion

1. Ouvrir http://localhost:3000
2. Se connecter avec `admin` / `admin`
3. (Optionnel) Changer le mot de passe
4. Les dashboards sont automatiquement chargés !

### 3. Configuration MongoDB (Optionnel)

Pour comparer avec les données MongoDB raw, installer le plugin:

```powershell
# Se connecter au container Grafana
docker exec -it grafana bash

# Installer le plugin MongoDB
grafana-cli plugins install grafana-mongodb-datasource

# Redémarrer Grafana
exit
docker-compose restart grafana
```

Puis configurer la datasource MongoDB manuellement via l'UI Grafana.

## 📊 Utilisation des Dashboards

### Dashboard "Cleaned Data Analysis"

Visualise uniquement les données PostgreSQL nettoyées:

1. **Total Cleaned Data**: Nombre total d'enregistrements
2. **Top Categories**: Graphique des 10 principales catégories
3. **Top Events by Volume**: Liste des 20 meilleurs événements
4. **Distribution by Category**: Camembert de répartition
5. **Statistics by Category**: Tableau récapitulatif
6. **Insertion Timeline**: Évolution dans le temps

### Dashboard "Comparison" (Cleaned vs Raw)

Compare la qualité entre données cleaned et raw:

1. **Side-by-side Counts**: Comparaison du nombre d'enregistrements
2. **Data Quality Comparison**: Tableau de qualité des données
   - Nombre avec images
   - Nombre avec icônes
   - Nombre avec series_slug
   - Pourcentage de qualité
3. **Categories Distribution**: Distribution par catégorie
4. **Status Distribution**: Événements actifs vs terminés
5. **Detailed View**: Vue détaillée avec indicateurs visuels
   - ✅ = champ présent et valide
   - ❌ = champ manquant ou vide
6. **Completeness by Category**: Complétude des données par catégorie

## 🔍 Requêtes SQL Utiles

### Compter les données cleaned

```sql
SELECT COUNT(*) FROM polymarket_cleaned;
```

### Qualité des données par catégorie

```sql
SELECT 
  category,
  COUNT(*) as total,
  COUNT(CASE WHEN image IS NOT NULL AND image != '' THEN 1 END) as with_images,
  ROUND((COUNT(CASE WHEN image IS NOT NULL AND image != '' THEN 1 END)::numeric / COUNT(*) * 100), 2) as image_percentage
FROM polymarket_cleaned
GROUP BY category
ORDER BY total DESC;
```

### Événements actifs vs terminés

```sql
SELECT 
  CASE 
    WHEN end_date > NOW() THEN 'Active'
    WHEN end_date IS NULL THEN 'Unknown'
    ELSE 'Ended'
  END as status,
  COUNT(*) as count
FROM polymarket_cleaned
GROUP BY status;
```

## 🎨 Personnalisation des Dashboards

### Modifier un dashboard existant

1. Ouvrir le dashboard dans Grafana
2. Cliquer sur l'icône ⚙️ (Settings) en haut
3. Modifier les panels, requêtes, variables
4. Sauvegarder avec "Save dashboard"

### Créer un nouveau dashboard

1. Menu → Dashboards → New Dashboard
2. Add visualization
3. Sélectionner la datasource (PostgreSQL ou MongoDB)
4. Écrire la requête SQL/MongoDB
5. Configurer la visualisation
6. Sauvegarder

### Créer des alertes

1. Dans un panel, cliquer sur "Alert"
2. Définir la condition (ex: nombre de records < seuil)
3. Configurer les notifications
4. Sauvegarder

## 📈 Variables de Dashboard

Les dashboards peuvent utiliser des variables pour filtrer dynamiquement:

```sql
-- Exemple de variable de catégorie
SELECT DISTINCT category 
FROM polymarket_cleaned 
WHERE category IS NOT NULL 
ORDER BY category;
```

## 🔧 Configuration Avancée

### Connexion MongoDB personnalisée

Éditer [grafana/provisioning/datasources/datasources.yml](grafana/provisioning/datasources/datasources.yml):

```yaml
- name: MongoDB - Custom
  type: grafana-mongodb-datasource
  url: mongodb://username:password@host:27017
  database: polymarket_db
  jsonData:
    authSource: admin
    ssl: true
```

### Ajouter des variables d'environnement

Dans [Docker-compose.yaml](Docker-compose.yaml):

```yaml
environment:
  - GF_CUSTOM_VARIABLE=value
  - GF_FEATURE_TOGGLES_ENABLE=publicDashboards
```

## 🔍 Monitoring Grafana

### Vérifier la santé du container

```powershell
# Health check
curl http://localhost:3000/api/health

# Logs en temps réel
docker-compose logs -f grafana

# Statistiques du container
docker stats grafana
```

### Accéder aux fichiers de configuration

```powershell
# Se connecter au container
docker exec -it grafana bash

# Voir les configurations
cat /etc/grafana/grafana.ini

# Voir les datasources
ls -la /etc/grafana/provisioning/datasources/
```

## 📊 Métriques Importantes

### Performance des dashboards

- **Temps de chargement**: < 2 secondes idéalement
- **Nombre de requêtes**: Minimiser les requêtes lourdes
- **Refresh interval**: 30s - 1m selon les besoins

### Optimisation PostgreSQL

```sql
-- Créer des index sur les colonnes fréquemment filtrées
CREATE INDEX IF NOT EXISTS idx_category_volume ON polymarket_cleaned(category, volume_num DESC);

-- Analyser les statistiques
ANALYZE polymarket_cleaned;
```

## 🛡️ Sécurité

### Changer le mot de passe admin

```powershell
# Via variable d'environnement dans .env
GRAFANA_ADMIN_PASSWORD=VotreMotDePasseSecurise

# Ou via l'UI Grafana après connexion
# Profile → Change Password
```

### Activer HTTPS

1. Générer des certificats SSL
2. Modifier la configuration Grafana:

```yaml
environment:
  - GF_SERVER_PROTOCOL=https
  - GF_SERVER_CERT_FILE=/path/to/cert.pem
  - GF_SERVER_CERT_KEY=/path/to/key.pem
```

## 📱 Export et Partage

### Exporter un dashboard

1. Ouvrir le dashboard
2. Menu → Share → Export
3. Choisir "Export for sharing externally"
4. Télécharger le JSON

### Importer un dashboard

1. Menu → Dashboards → Import
2. Upload JSON file ou coller le JSON
3. Configurer les datasources
4. Importer

### Snapshots publics

1. Dans le dashboard → Share → Snapshot
2. Création d'une URL publique
3. Définir la durée d'expiration

## 🔄 Backup et Restauration

### Backup des dashboards

```powershell
# Sauvegarder tous les dashboards
docker exec grafana grafana-cli admin export-dashboard

# Sauvegarder le volume Grafana
docker run --rm -v grafana-storage:/data -v ${PWD}:/backup alpine tar czf /backup/grafana-backup.tar.gz /data
```

### Restauration

```powershell
# Restaurer depuis un volume backup
docker run --rm -v grafana-storage:/data -v ${PWD}:/backup alpine tar xzf /backup/grafana-backup.tar.gz -C /
docker-compose restart grafana
```

## 🐛 Dépannage

### Grafana ne démarre pas

```powershell
# Vérifier les logs
docker-compose logs grafana

# Vérifier les permissions du volume
docker volume inspect grafana-storage

# Recréer le container
docker-compose down grafana
docker-compose up -d grafana
```

### Dashboards ne s'affichent pas

```powershell
# Vérifier que les fichiers sont bien montés
docker exec grafana ls -la /var/lib/grafana/dashboards/

# Vérifier les datasources
docker exec grafana ls -la /etc/grafana/provisioning/datasources/

# Forcer le reload
docker-compose restart grafana
```

### Datasource PostgreSQL ne fonctionne pas

1. Vérifier que postgres-polymarket est démarré
2. Tester la connexion depuis le container Grafana:

```powershell
docker exec -it grafana /bin/bash
apk add postgresql-client
psql -h postgres-polymarket -U polymarket -d polymarket_db
```

### Plugin MongoDB ne charge pas

```powershell
# Réinstaller le plugin
docker exec grafana grafana-cli plugins install grafana-mongodb-datasource

# Vérifier les plugins installés
docker exec grafana grafana-cli plugins ls

# Redémarrer Grafana
docker-compose restart grafana
```

## 📚 Ressources

- **Documentation Grafana**: https://grafana.com/docs/
- **Dashboard Examples**: https://grafana.com/grafana/dashboards/
- **PostgreSQL Datasource**: https://grafana.com/docs/grafana/latest/datasources/postgres/
- **MongoDB Plugin**: https://grafana.com/grafana/plugins/grafana-mongodb-datasource/

## 🎯 Cas d'Usage

### 1. Monitoring en temps réel

Créer un dashboard avec auto-refresh 10s pour surveiller:
- Nouvelles données insérées
- Qualité des données en temps réel
- Alertes sur anomalies

### 2. Rapports hebdomadaires

Configurer des rapports PDF automatiques:
- Menu → Dashboards → Select dashboard
- Reporting → Create report
- Définir la fréquence (hebdomadaire)

### 3. Alertes sur la qualité

Créer une alerte si le pourcentage de qualité < 90%:
- Panel → Alert
- Condition: `data_quality_percent < 90`
- Notification: Email/Slack

## 🚀 Prochaines Étapes

1. ✅ Container Grafana opérationnel
2. ✅ Datasources configurées (PostgreSQL)
3. ✅ Dashboards pré-créés
4. 📋 TODO: Configurer plugin MongoDB pour comparaison complète
5. 📋 TODO: Ajouter alertes sur seuils de qualité
6. 📋 TODO: Créer dashboard de métriques Kafka/Airflow

---

**Support**: Pour toute question, vérifier les logs avec `docker-compose logs -f grafana`

