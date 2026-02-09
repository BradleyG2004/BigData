@echo off
echo ================================================
echo  Polymarket Data Pipeline - Arret
echo ================================================
echo.

echo [1/2] Arret de Kafka...
docker-compose down
if errorlevel 1 (
    echo ERREUR: Probleme lors de l'arret de Kafka
) else (
    echo    - Kafka arrete
)
echo.

echo [2/2] Fermeture des processus Python...
taskkill /F /FI "WindowTitle eq Polymarket Consumer*" >nul 2>&1
if errorlevel 1 (
    echo    - Aucun processus consumer a arreter
) else (
    echo    - Consumer arrete
)
echo.

echo ================================================
echo  Pipeline arrete!
echo ================================================
echo.
pause
