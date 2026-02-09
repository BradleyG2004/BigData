# ============================================
# 🚀 Script de Démarrage - Polymarket Pipeline
# ============================================
# Ce script démarre tous les services nécessaires
# et vérifie leur état

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   🚀 POLYMARKET PIPELINE - Démarrage" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si Docker est en cours d'exécution
Write-Host "🔍 Vérification de Docker..." -ForegroundColor Yellow
try {
    docker ps > $null 2>&1
    Write-Host "✅ Docker est actif" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker n'est pas actif. Veuillez démarrer Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Vérifier si le fichier .env existe
Write-Host "🔍 Vérification du fichier .env..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✅ Fichier .env trouvé" -ForegroundColor Green
} else {
    Write-Host "⚠️  Fichier .env non trouvé. Vérifiez votre configuration MongoDB." -ForegroundColor Yellow
}

Write-Host ""

# Démarrer tous les services
Write-Host "🚀 Démarrage de tous les services..." -ForegroundColor Yellow
Write-Host ""
docker-compose up -d

Write-Host ""
Write-Host "⏳ Attente du démarrage des services (30 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""

# Vérifier l'état des services
Write-Host "📊 État des services:" -ForegroundColor Cyan
Write-Host ""
docker-compose ps

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   🎉 Services démarrés!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 URLs d'accès:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   🌬️  Airflow:        http://localhost:8081" -ForegroundColor White
Write-Host "       Credentials:    admin / admin" -ForegroundColor Gray
Write-Host ""
Write-Host "   📊 Grafana:         http://localhost:3000" -ForegroundColor White
Write-Host "       Credentials:    admin / admin" -ForegroundColor Gray
Write-Host ""
Write-Host "   🔥 Spark Master:    http://localhost:8082" -ForegroundColor White
Write-Host ""
Write-Host "   🗄️  PostgreSQL:     localhost:5433" -ForegroundColor White
Write-Host "       Database:       polymarket" -ForegroundColor Gray
Write-Host "       User:           polymarket" -ForegroundColor Gray
Write-Host "       Password:       polymarket123" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 Commandes utiles:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   Voir les logs:          docker-compose logs -f [service]" -ForegroundColor White
Write-Host "   Arrêter:                docker-compose down" -ForegroundColor White
Write-Host "   Redémarrer un service:  docker-compose restart [service]" -ForegroundColor White
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "   - GUIDE_COMPLET.md      : Guide de démarrage complet" -ForegroundColor White
Write-Host "   - POSTGRES_README.md    : Documentation PostgreSQL" -ForegroundColor White
Write-Host "   - GRAFANA_README.md     : Documentation Grafana" -ForegroundColor White
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Proposer d'ouvrir les URLs
$openUrls = Read-Host "Voulez-vous ouvrir les URLs dans votre navigateur? (o/n)"
if ($openUrls -eq "o" -or $openUrls -eq "O") {
    Write-Host ""
    Write-Host "🌐 Ouverture des URLs..." -ForegroundColor Yellow
    Start-Process "http://localhost:8081"
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:3000"
    Write-Host "✅ URLs ouvertes!" -ForegroundColor Green
}

Write-Host ""
Write-Host "✨ Prêt à démarrer! Bonne analyse! ✨" -ForegroundColor Green
Write-Host ""

