# ============================================
# 🛑 Script d'Arrêt - Polymarket Pipeline
# ============================================

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   🛑 POLYMARKET PIPELINE - Arrêt" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$choice = Read-Host "Voulez-vous également supprimer les volumes (données)? (o/n)"

Write-Host ""
Write-Host "🛑 Arrêt des services..." -ForegroundColor Yellow
Write-Host ""

if ($choice -eq "o" -or $choice -eq "O") {
    docker-compose down -v
    Write-Host ""
    Write-Host "✅ Services arrêtés et volumes supprimés" -ForegroundColor Green
    Write-Host "⚠️  Toutes les données ont été effacées" -ForegroundColor Yellow
} else {
    docker-compose down
    Write-Host ""
    Write-Host "✅ Services arrêtés (données conservées)" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

